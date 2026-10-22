from uuid import uuid4
from pathlib import Path
import pandas as pd
import pytest
from pydantic import ValidationError
from backend.planning import ResearchRequest, build_plan

RAW=(Path(__file__).parents[1]/'demo/synthetic_health.csv').read_bytes()

def request(**kwargs):
    return ResearchRequest(dataset_id=uuid4(),target='outcome',question='Which features predict the recorded outcome?',independent_rows=True,**kwargs)

def plan(req,frame=None,raw=RAW):
    if frame is None:frame=pd.read_csv(Path(__file__).parents[1]/'demo/synthetic_health.csv')
    return build_plan(req,frame,raw,None)

def test_input_changes_invalidate_confirmation():
    req=request();first=plan(req)
    assert first.status=='ready'
    assert first.fingerprint==plan(req).fingerprint
    assert first.fingerprint!=plan(req.model_copy(update={'question':'Which other features predict this outcome?'})).fingerprint
    assert first.fingerprint!=plan(req,raw=RAW+b'\n').fingerprint

@pytest.mark.parametrize('change',[{'intent':'causal_effect'},{'intent':'future_risk'},{'intent':'survival'},
    {'study_design':'repeated'},{'study_design':'temporal'},{'study_design':'survey'},
    {'question':'这些测量导致心脏病的因果效应是什么？'},{'question':'Estimate the causal effect of cholesterol.'},
    {'independent_rows':False},{'allow_literature':True}])
def test_unsupported_designs_block_before_execution(change):
    assert plan(request().model_copy(update=change)).status=='blocked'

def test_survey_and_follow_up_fields_do_not_pass_independence_checkbox():
    frame=pd.read_csv(Path(__file__).parents[1]/'demo/synthetic_health.csv')
    frame['SDMVPSU']=1
    assert plan(request(),frame).status=='blocked'
    frame=frame.drop(columns='SDMVPSU').assign(time=5,DEATH_EVENT=0)
    assert plan(request(),frame).status=='blocked'

def test_invalid_provider_like_payload_rejected():
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate({**request().model_dump(),'python_code':'raise SystemExit()'})
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate_json('not json')
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate({**request().model_dump(),'question':' '*20})

def test_scope_keyword_does_not_match_inside_because():
    assert plan(request().model_copy(update={'question':'Review predictions because uncertainty matters.'})).status=='ready'

def test_missing_target_and_small_data_return_actionable_plans():
    assert plan(request().model_copy(update={'target':'absent'})).status=='blocked'
    frame=pd.read_csv(Path(__file__).parents[1]/'demo/synthetic_health.csv').head(15)
    assert any(c.code=='sample_size' and c.status=='blocked' for c in plan(request(),frame).checks)
