"""Integration review regression cases; no real sponsor API calls."""
import json
import sys
from types import SimpleNamespace

import httpx
import pytest

from backend import agent_api, storage, zetaris
from backend.agent_runtime import NightshiftProvider
from scripts import run_agent


def test_web_worker_cannot_reload_dotenv_or_choose_cloud(tmp_path, monkeypatch):
    rid = 'integration-worker'
    monkeypatch.setattr(storage, 'ROOT', tmp_path)
    folder = tmp_path / 'agent-runs' / rid
    folder.mkdir(parents=True)
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-not-a-real-token')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-not-a-real-key')
    captured = {}
    def run(command, **kwargs):
        captured.update(command=command, **kwargs)
        (folder / 'trace.json').write_text(json.dumps([{'kind':'session_ended','status':'completed_draft'}]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(agent_api.subprocess, 'run', run)
    assert agent_api.slot.acquire(blocking=False)
    agent_api.supervise(rid, 'heart')
    assert '--provider' in captured['command']
    assert captured['command'][captured['command'].index('--provider') + 1] == 'ollama'
    assert '--no-memory' in captured['command']
    assert captured['env']['OPENRESEARCH_NO_DOTENV'] == '1'
    assert 'METERLESS_RUNTIME_TOKEN' not in captured['env']
    assert 'DEEPSEEK_API_KEY' not in captured['env']


def test_dotenv_is_opt_in_and_worker_blocked(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    path.write_text('OPENRESEARCH_REVIEW_TEST=yes\n')
    monkeypatch.delenv('OPENRESEARCH_REVIEW_TEST', raising=False)
    monkeypatch.setenv('OPENRESEARCH_NO_DOTENV','1')
    run_agent.load_env(path)
    import os
    assert 'OPENRESEARCH_REVIEW_TEST' not in os.environ
    monkeypatch.setattr(sys, 'argv', ['run_agent', '--env-file', str(path)])
    with pytest.raises(SystemExit) as exc:
        run_agent.main()
    assert exc.value.code == 2


@pytest.mark.parametrize('sql', [
    'SELECT 1; DROP TABLE t', 'WITH x AS (SELECT 1) DELETE FROM t',
    'EXPLAIN INSERT INTO t VALUES (1)', 'SELECT * INTO t FROM s',
    'SELECT 1 /* hidden command */',
])
def test_prefixed_or_stacked_writes_are_rejected(sql):
    assert not zetaris.is_read_only(sql)


@pytest.mark.parametrize('finish,served', [('length','nvidia/test'),('tool_calls','other/model')])
def test_nightshift_truncation_and_wrong_model_fail_closed(monkeypatch, finish, served):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    def post(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request('POST','http://unit.test'),json={
            'model':served,'choices':[{'finish_reason':finish,'message':{'tool_calls':[]}}]})
    monkeypatch.setattr(httpx, 'post', post)
    with pytest.raises(ValueError): NightshiftProvider('nvidia/test').chat([], [])


def test_nightshift_records_actual_model_and_preserves_call_id(monkeypatch):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN','test-token')
    def post(*args, **kwargs):
        return httpx.Response(200,request=httpx.Request('POST','http://unit.test'),json={
            'model':'nvidia/test','choices':[{'finish_reason':'tool_calls','message':{
                'tool_calls':[{'id':'call-original','function':{'name':'inspect_dataset','arguments':'{}'}}]}}]})
    monkeypatch.setattr(httpx,'post',post)
    result=NightshiftProvider('nvidia/test').chat([],[])
    assert result['served_model']=='nvidia/test'
    assert result['message']['tool_calls'][0]['id']=='call-original'


def test_unpinned_nightshift_agent_does_not_send_a_request(monkeypatch):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN','test-token')
    monkeypatch.delenv('NEMOTRON_MODEL',raising=False)
    def post(*args, **kwargs):
        raise AssertionError('Unpinned model must fail before any request')
    monkeypatch.setattr(httpx,'post',post)
    with pytest.raises(ValueError,match='Pin an exact'):
        NightshiftProvider().chat([],[])
