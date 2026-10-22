import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend import storage
from backend.app import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'ROOT',tmp_path)
    with TestClient(app) as c:yield c

def test_end_to_end_real_worker(client):
    d=client.post('/api/demo').json()
    r=client.post('/api/runs',json={'dataset_id':d['dataset_id'],'target':'outcome','question':'Which predictors are useful?','independent_rows':True})
    assert r.status_code==202
    rid=r.json()['id']
    for _ in range(150):
        state=client.get('/api/runs/'+rid).json()
        if state['status'] not in ('queued','running'):break
        time.sleep(.2)
    assert state['status']=='completed_with_warnings',state
    assert state['result']['literature']['status']=='disabled'
    assert state['result']['analysis']['n_test']==80
    report=client.get('/api/runs/'+rid+'/report')
    assert report.status_code==200 and 'not causal evidence' in report.text
    assert (storage.ROOT/'runs'/rid/'analysis.json').exists()
    assert client.get('/api/runs/'+rid+'/evidence').json()['provenance']['kind']=='synthetic_demo_not_clinical'
    assert state['result']['claims']
    assert state['result']['review']['claim_verification']['claims_checked']==len(state['result']['analysis']['factors'])
    assert (storage.ROOT/'runs'/rid/'claims.json').exists()
    assert client.get('/api/history').json()[0]['id']==rid
    assert '可追溯结论' in report.text

def test_bad_requests_and_origin(client):
    assert client.post('/api/demo',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/runs/not-a-uuid').status_code==422
    assert client.post('/api/datasets',files={'file':('a.csv',b'a,a\n1,2')}).status_code==422
    d=client.post('/api/demo').json()
    base={'dataset_id':d['dataset_id'],'target':'outcome','question':'Analyze this dataset'}
    assert client.post('/api/runs',json=base).status_code==422
    assert client.post('/api/runs',json={**base,'independent_rows':True,'target':'nope'}).status_code==422
    assert client.post('/api/runs',json={**base,'independent_rows':True,'allow_literature':True}).status_code==422

def test_preview_blocks_unsafe_scope_and_stale_confirmation(client):
    dataset=client.post('/api/demo').json()
    body={'dataset_id':dataset['dataset_id'],'target':'outcome','question':'Analyze the recorded outcome.', 'independent_rows':True}
    plan=client.post('/api/plans',json=body).json()
    assert plan['status']=='ready'
    changed={**body,'question':'Analyze a different recorded outcome.','plan_fingerprint':plan['fingerprint']}
    assert client.post('/api/runs',json=changed).status_code==409
    causal={**body,'intent':'causal_effect'}
    assert client.post('/api/plans',json=causal).json()['status']=='blocked'
    assert client.post('/api/runs',json=causal).status_code==422
    assert client.get('/api/history').json()==[]

def test_failed_public_download_never_returns_demo_data(client,monkeypatch):
    import backend.app as module
    def fail(*args): raise RuntimeError('network unavailable')
    monkeypatch.setattr(module,'fetch_public_data',fail)
    r=client.post('/api/examples/heart')
    assert r.status_code==503 and '未使用替代数据' in r.json()['detail']
