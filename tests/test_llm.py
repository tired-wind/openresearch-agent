"""Failure paths and payload rules for backend.llm; no network required."""
import httpx
import pytest
from backend import llm


def test_unconfigured_returns_disabled_without_network(monkeypatch):
    monkeypatch.delenv('METERLESS_RUNTIME_TOKEN', raising=False)
    result = llm.chat([{'role': 'user', 'content': 'hi'}])
    assert result['status'] == 'disabled'
    assert 'METERLESS_RUNTIME_TOKEN' in result['message']


def test_json_mode_adds_response_format(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured['body'] = json_body(request)
        raise httpx.ConnectError('no server', request=request)

    def json_body(request: httpx.Request):
        import json
        return json.loads(request.content)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        llm.chat([{'role': 'user', 'content': 'hi'}], json_mode=True, client=client)

    assert captured['body']['response_format'] == {'type': 'json_object'}


def test_failed_request_is_reported_not_raised(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    result = llm.chat([{'role': 'user', 'content': 'hi'}], client=httpx.Client(timeout=2))
    assert result['status'] == 'failed'
    assert 'Nightshift request failed' in result['message']


def test_empty_completion_is_rejected(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'model': 'nvidia/nemotron-x', 'choices': [{'message': {'content': '   '}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], client=client)

    assert result['status'] == 'failed'
    assert 'empty completion' in result['message']


def test_successful_completion_reports_serving_model(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers['meterless-app'] == 'openresearch-agent'
        assert request.headers['meterless-scope'] == 'user'
        assert request.headers['authorization'] == 'Bearer test-token'
        return httpx.Response(200, json={
            'model': 'nvidia/nemotron-3.5-lightning-30b-a3b',
            'choices': [{'message': {'content': 'ready'}}],
            'usage': {'total_tokens': 9},
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], client=client)

    assert result['status'] == 'ok'
    assert result['model'] == 'nvidia/nemotron-3.5-lightning-30b-a3b'
    assert result['content'] == 'ready'
    assert result['usage']['total_tokens'] == 9


def test_nemotron_filter():
    models = ['meterless/auto', 'nvidia/nemotron-3.5-lightning-30b-a3b', 'local-runtime/nemotron-3-nano-30b-a3b']
    nemo = [m for m in models if 'nemotron' in m.lower()]
    assert len(nemo) == 2
