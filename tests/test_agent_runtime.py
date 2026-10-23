"""Offline control-plane tests. Scripted providers are NOT real-model evidence."""
import json
from pathlib import Path

import pandas as pd
import pytest
from backend import agent_runtime as runtime
from backend.agent_api import AgentRequest


@pytest.fixture
def session(tmp_path, monkeypatch):
    frame = pd.read_csv(Path(__file__).parents[1] / 'demo/synthetic_health.csv')
    monkeypatch.setattr(runtime, 'load_public_dataset', lambda _: (frame, 'test-only-synthetic'))
    obj = runtime.ResearchSession('heart', tmp_path, None)
    obj.profile = {**obj.profile, 'target': 'outcome'}
    return obj


def call(name, **arguments):
    return {'message': {'role': 'assistant', 'content': '', 'tool_calls': [
        {'function': {'name': name, 'arguments': arguments}}]}}


def test_model_sees_rejection_and_changes_next_action(session, monkeypatch):
    """A model proposes a forbidden tool, receives rejection, then repairs its call."""
    observed = []
    class ScriptedProvider:
        model = 'test-script-not-a-real-model'
        def chat(self, messages, schemas):
            step = len(observed)
            observed.append(messages)
            if step == 0: return call('execute_python', code='raise SystemExit()')
            if step == 1:
                assert 'not allowed' in messages[-1]['content']
                return call('inspect_dataset')
            if step == 2: return call('analyze_dataset')
            if step == 3:
                assert 'metrics' in json.loads(messages[-1]['content'])
                return call('search_pubmed', query='synthetic test query')
            if step == 4:
                assert json.loads(messages[-1]['content'])['status'] == 'failed'
                return call('finish_investigation', summary='文献检索失败，无法建立外部支持。',
                            features=[session.result['factors'][0]['feature']], pmids=[])
            raise AssertionError('Unexpected extra loop')
    session.provider = ScriptedProvider()
    monkeypatch.setattr(runtime, 'retrieve', lambda _: {'status': 'failed', 'message': 'test outage', 'records': []})
    assert session.run() == 'completed_draft'
    assert len(observed) == 5
    assert session.report['references'] == []
    assert session.report['interpretation_status'] == 'unverified_model_draft'
    assert session.report['computed_metrics'] == session.result['metrics']
    events = json.loads((session.folder / 'trace.json').read_text())
    assert events[4]['status'] == 'rejected'


def test_invented_or_unread_citations_cannot_be_published(session):
    session.provider = type('Fake', (), {'model': 'test'})()
    session.tool('inspect_dataset', {})
    session.tool('analyze_dataset', {})
    session.searches = 1
    args = {'summary': '这是尚未审核的解释草稿。', 'features': [session.result['factors'][0]['feature']], 'pmids': ['999999']}
    with pytest.raises(ValueError, match='Read each cited'):
        session.tool('finish_investigation', args)
    with pytest.raises(ValueError, match='not retrieved'):
        session.tool('read_abstract', {'pmid': '999999'})
    assert not (session.folder / 'report.json').exists()


def test_bad_parameters_and_early_completion_are_rejected(session):
    with pytest.raises(ValueError): session.tool('analyze_dataset', {'path': '/etc/passwd'})
    with pytest.raises(ValueError, match='Inspect'): session.tool('analyze_dataset', {})
    with pytest.raises(ValueError, match='required'): session.tool('finish_investigation', {
        'summary': '未经计算不能直接给出研究结论。', 'features': ['invented'], 'pmids': []})
    with pytest.raises(ValueError): AgentRequest(example='private-upload')
    with pytest.raises(ValueError): AgentRequest(example='heart', endpoint='https://paid.example')


def test_repeated_bad_model_action_stops_at_budget(session):
    class StuckProvider:
        model = 'scripted-stuck-provider'
        def chat(self, messages, tools): return call('unknown_tool')
    session.provider = StuckProvider()
    assert session.run() == 'budget_exhausted'
    assert sum(e['kind'] == 'model_started' for e in session.events) == 10
    assert session.report is None


def test_provider_truncated_calls_never_execute(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'done_reason': 'length', 'message': {'tool_calls': []}}
    monkeypatch.setattr(runtime.httpx, 'post', lambda *a, **k: Response())
    with pytest.raises(ValueError, match='truncated'):
        runtime.OllamaProvider().chat([], [])
