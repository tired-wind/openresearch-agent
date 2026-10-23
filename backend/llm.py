"""Nemotron through Meterless Nightshift is the only reasoning engine.

OpenAI-compatible route served by the local Nightshift runtime. The runtime
token stays in .env; the NVIDIA key lives inside Nightshift's Providers and is
never read here. Like backend.zetaris, failures return status='failed' instead
of raising, and every result carries the model that actually answered so the
report can state which engine produced each judgement.
"""
from __future__ import annotations
import os
from typing import Any
import httpx

DEFAULT_BASE = 'http://127.0.0.1:8088/v1'
DEFAULT_MODEL = 'meterless/auto'
TIMEOUT = httpx.Timeout(120.0)


def settings() -> tuple[str, str, str]:
    base = (os.environ.get('METERLESS_BASE_URL') or DEFAULT_BASE).rstrip('/')
    return base, os.environ.get('METERLESS_RUNTIME_TOKEN', ''), os.environ.get('METERLESS_MODEL') or DEFAULT_MODEL


def configured() -> bool:
    base, token, _ = settings()
    return bool(base and token)


def chat(messages: list[dict[str, str]], *, model: str | None = None, json_mode: bool = False,
         temperature: float | None = None, max_tokens: int | None = None,
         client: httpx.Client | None = None) -> dict[str, Any]:
    """One completion through Nightshift; returns status/content/model/usage."""
    base, token, default_model = settings()
    chosen = model or default_model
    base_result: dict[str, Any] = {'model': chosen, 'content': '', 'usage': None}
    if not (base and token):
        return {**base_result, 'status': 'disabled', 'message': 'Meterless Nightshift is not configured; set METERLESS_BASE_URL and METERLESS_RUNTIME_TOKEN.'}

    payload: dict[str, Any] = {'model': chosen, 'messages': messages}
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    if temperature is not None:
        payload['temperature'] = temperature
    if max_tokens is not None:
        payload['max_tokens'] = max_tokens

    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)
    try:
        response = client.post(
            f'{base}/chat/completions',
            headers={
                'Authorization': f'Bearer {token}',
                'meterless-app': 'openresearch-agent',
                'meterless-scope': 'user',
                'Content-Type': 'application/json',
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
        served = body.get('model') or chosen
        choice = (body.get('choices') or [{}])[0]
        content = (choice.get('message') or {}).get('content') or ''
        if not content.strip():
            raise ValueError('empty completion')
        return {
            **base_result,
            'model': served,
            'status': 'ok',
            'content': content,
            'usage': body.get('usage'),
            'message': f'Completion served by {served} through Meterless Nightshift.',
        }
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else '?'
        hint = ' Check that Nightshift is running and the Runtime token matches its Console value.' if status in (401, 403) else ''
        detail = exc.response.text[:300] if exc.response is not None else ''
        return {**base_result, 'status': 'failed', 'message': f'Nightshift returned HTTP {status}.{hint} {detail}'.strip()}
    except Exception as exc:
        return {**base_result, 'status': 'failed', 'message': f'Nightshift request failed ({type(exc).__name__}): {exc}'}
    finally:
        if own:
            client.close()


def list_models(client: httpx.Client | None = None) -> dict[str, Any]:
    """Model discovery, so the UI can pin a Nemotron-backed lane explicitly."""
    base, token, _ = settings()
    if not (base and token):
        return {'status': 'disabled', 'models': [], 'message': 'Meterless Nightshift is not configured.'}
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)
    try:
        response = client.get(f'{base}/models', headers={
            'Authorization': f'Bearer {token}',
            'meterless-app': 'openresearch-agent',
            'meterless-scope': 'user',
        })
        response.raise_for_status()
        models = [m.get('id') for m in response.json().get('data', []) if m.get('id')]
        return {'status': 'ok', 'models': models, 'message': f'{len(models)} models reachable through Nightshift.'}
    except Exception as exc:
        return {'status': 'failed', 'models': [], 'message': f'Model discovery failed ({type(exc).__name__}): {exc}'}
    finally:
        if own:
            client.close()


def nemotron_models(client: httpx.Client | None = None) -> list[str]:
    """Hosted Nemotron ids currently reachable; used for the NVIDIA-award evidence."""
    result = list_models(client=client)
    return [m for m in result.get('models', []) if 'nemotron' in m.lower()]
