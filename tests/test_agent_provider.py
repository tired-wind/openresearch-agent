"""NightshiftProvider model-identity rules, with no network.

Nightshift's active lane rotates between Nemotron models on its own schedule, so
an exact-id match fails at random. Strict equality stays the default; opting in
accepts another Nemotron but never a non-Nemotron model.
"""
import httpx
import pytest

from backend.agent_runtime import NightshiftProvider

PINNED = 'nvidia/nemotron-3.5-lightning-30b-a3b'
REQUEST = httpx.Request('POST', 'http://unit.test/v1/chat/completions')


def reply(served, finish='stop'):
    return httpx.Response(200, request=REQUEST, json={
        'model': served,
        'choices': [{'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': finish}],
    })


def provider_with(monkeypatch, payload):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    monkeypatch.setattr('backend.agent_runtime.httpx.post', lambda *a, **k: payload)
    return NightshiftProvider(PINNED)


def test_exact_match_passes(monkeypatch):
    result = provider_with(monkeypatch, reply(PINNED)).chat([{'role': 'user', 'content': 'hi'}], [])
    assert result['served_model'] == PINNED


def test_substitution_is_rejected_by_default(monkeypatch):
    monkeypatch.delenv('OPENRESEARCH_ALLOW_NEMOTRON_SUBSTITUTION', raising=False)
    provider = provider_with(monkeypatch, reply('nvidia/nemotron-3-ultra-550b-a55b'))
    with pytest.raises(ValueError, match='served a different model'):
        provider.chat([{'role': 'user', 'content': 'hi'}], [])


def test_substitution_allowed_when_opted_in(monkeypatch):
    monkeypatch.setenv('OPENRESEARCH_ALLOW_NEMOTRON_SUBSTITUTION', '1')
    provider = provider_with(monkeypatch, reply('nvidia/nemotron-3-ultra-550b-a55b'))
    result = provider.chat([{'role': 'user', 'content': 'hi'}], [])
    # The model that actually served is reported, never the requested one.
    assert result['served_model'] == 'nvidia/nemotron-3-ultra-550b-a55b'


def test_opt_in_still_rejects_a_non_nemotron_model(monkeypatch):
    monkeypatch.setenv('OPENRESEARCH_ALLOW_NEMOTRON_SUBSTITUTION', '1')
    provider = provider_with(monkeypatch, reply('meta/llama-3-70b'))
    with pytest.raises(ValueError, match='served a different model'):
        provider.chat([{'role': 'user', 'content': 'hi'}], [])


def test_auto_model_is_refused_before_any_request(monkeypatch):
    monkeypatch.setenv('METERLESS_RUNTIME_TOKEN', 'test-token')
    called = {'n': 0}

    def handler(*args, **kwargs):
        called['n'] += 1
        return reply(PINNED)

    monkeypatch.setattr('backend.agent_runtime.httpx.post', handler)
    with pytest.raises(ValueError, match='Pin an exact discovered model ID'):
        NightshiftProvider('meterless/auto').chat([{'role': 'user', 'content': 'hi'}], [])
    assert called['n'] == 0


def test_incomplete_finish_reason_is_rejected(monkeypatch):
    provider = provider_with(monkeypatch, reply(PINNED, finish='length'))
    with pytest.raises(ValueError, match='incomplete or blocked'):
        provider.chat([{'role': 'user', 'content': 'hi'}], [])
