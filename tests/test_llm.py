"""Failure paths and payload rules for backend.llm; no network required.

The contract mirrors NightshiftProvider: auto routing is refused, and a response
must name the serving model. A still-Nemotron substitution is reported rather
than raised, so a caller can choose to cite the model that actually answered.
"""
import json

import httpx
import pytest

from backend import llm

PINNED = 'nvidia/nemotron-3.5-lightning-30b-a3b'


def test_unconfigured_returns_disabled_without_network(monkeypatch):
    monkeypatch.delenv('METERLESS_RUNTIME_TOKEN', raising=False)
    result = llm.chat([{'role': 'user', 'content': 'hi'}])
    assert result['status'] == 'disabled'
    assert 'METERLESS_RUNTIME_TOKEN' in result['message']


def test_auto_model_is_refused_without_a_request(monkeypatch):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    called = {'n': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called['n'] += 1
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], model='meterless/auto', client=client)

    assert result['status'] == 'failed'
    assert 'meterless/auto' in result['message']
    assert called['n'] == 0  # refused before any network call


def test_json_mode_adds_response_format(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured['body'] = json.loads(request.content)
        raise httpx.ConnectError('no server', request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED, json_mode=True, client=client)

    assert captured['body']['response_format'] == {'type': 'json_object'}


def test_failed_request_is_reported_not_raised(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    result = llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED,
                      client=httpx.Client(timeout=2))
    assert result['status'] == 'failed'
    assert 'Nightshift request failed' in result['message']


def test_empty_completion_is_rejected(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'model': PINNED, 'choices': [{'message': {'content': '   '}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED, client=client)

    assert result['status'] == 'failed'
    assert 'empty completion' in result['message']


def test_missing_serving_model_is_rejected(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'choices': [{'message': {'content': 'ready'}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED, client=client)

    assert result['status'] == 'failed'
    assert 'did not identify the serving model' in result['message']


def test_substituted_model_is_reported_with_the_served_id(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            'model': 'nvidia/nemotron-3.5-super-vl-120b-a12b',
            'choices': [{'message': {'content': 'ready'}}],
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED, client=client)

    assert result['status'] == 'failed'
    assert result['model'] == 'nvidia/nemotron-3.5-super-vl-120b-a12b'
    assert 'instead of' in result['message']


def test_successful_completion_reports_serving_model(monkeypatch):
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://unit.test/v1')
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers['meterless-app'] == 'openresearch-agent'
        assert request.headers['meterless-scope'] == 'user'
        assert request.headers['authorization'] == 'Bearer test-token'
        return httpx.Response(200, json={
            'model': PINNED,
            'choices': [{'message': {'content': 'ready'}}],
            'usage': {'total_tokens': 9},
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = llm.chat([{'role': 'user', 'content': 'hi'}], model=PINNED, client=client)

    assert result['status'] == 'ok'
    assert result['model'] == PINNED
    assert result['content'] == 'ready'
    assert result['usage']['total_tokens'] == 9


def test_nemotron_filter():
    models = ['meterless/auto', PINNED, 'local-runtime/nemotron-3-nano-30b-a3b']
    nemo = [m for m in models if 'nemotron' in m.lower()]
    assert len(nemo) == 2
