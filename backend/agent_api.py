"""Local experimental Agent entry point, isolated from the fixed analysis workflow."""
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from backend import storage

router = APIRouter(prefix='/api/agent')
pool = ThreadPoolExecutor(max_workers=1)
slot = threading.BoundedSemaphore(1)
PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OLLAMA_MODEL = 'qwen3.5:4b'


def agent_config():
    """Provider/model/memory come from the server environment, never from a request.

    The web worker keeps #10's strict allowlist: only loopback credentials are
    forwarded for Nightshift, and the NVIDIA key never leaves Nightshift itself.
    """
    provider = (os.environ.get('OPENRESEARCH_AGENT_PROVIDER') or 'ollama').strip().lower()
    if provider not in ('ollama', 'nightshift'):
        provider = 'ollama'
    if provider == 'nightshift':
        model = (os.environ.get('OPENRESEARCH_AGENT_MODEL')
                 or os.environ.get('NEMOTRON_MODEL') or '').strip()
    else:
        model = (os.environ.get('OPENRESEARCH_AGENT_MODEL') or DEFAULT_OLLAMA_MODEL).strip()
    memory = os.environ.get('OPENRESEARCH_AGENT_MEMORY') == '1'
    return provider, model, memory


def _nightshift_available(model):
    token = os.environ.get('METERLESS_RUNTIME_TOKEN', '')
    if not token or not model or model == 'meterless/auto':
        return False
    base = (os.environ.get('METERLESS_BASE_URL') or 'http://127.0.0.1:8088/v1').rstrip('/')
    try:
        response = httpx.get(f'{base}/models', timeout=4,
                             headers={'Authorization': f'Bearer {token}',
                                      'meterless-app': 'openresearch-agent',
                                      'meterless-scope': 'user'})
        response.raise_for_status()
        return model in {m.get('id') for m in response.json().get('data', [])}
    except (httpx.HTTPError, ValueError, KeyError):
        return False


def _ollama_available(model):
    try:
        response = httpx.get('http://127.0.0.1:11434/api/tags', timeout=2)
        response.raise_for_status()
        return model in [m['name'] for m in response.json().get('models', [])]
    except (httpx.HTTPError, ValueError, KeyError):
        return False


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    example: Literal['heart', 'breast']


def write_status(folder, status, **extra):
    path = folder / 'status.json'
    tmp = folder / 'status.json.tmp'
    tmp.write_text(json.dumps({'status': status, 'updated_at': storage.now(), **extra}), encoding='utf-8')
    tmp.replace(path)


def recover_interrupted():
    for path in (storage.ROOT / 'agent-runs').glob('*/status.json'):
        if json.loads(path.read_text(encoding='utf-8')).get('status') in ('queued', 'running'):
            write_status(path.parent, 'interrupted', error='服务已重启，请重新运行。')


def supervise(rid, example):
    folder = storage.ROOT / 'agent-runs' / rid
    try:
        write_status(folder, 'running')
        provider, model, memory = agent_config()
        # Allowlist environment: no model keys, tracing tokens or paid API access.
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'SYSTEMROOT')}
        env['OPENRESEARCH_DATA_DIR'] = str(storage.ROOT)
        env['OPENRESEARCH_NO_DOTENV'] = '1'
        env['PYTHONUTF8'] = '1'  # parent and child must agree on file encoding
        if provider == 'nightshift':
            # Loopback-only credentials. The NVIDIA key stays inside Nightshift.
            for key in ('METERLESS_BASE_URL', 'METERLESS_RUNTIME_TOKEN',
                        'OPENRESEARCH_ALLOW_NEMOTRON_SUBSTITUTION'):
                if os.environ.get(key):
                    env[key] = os.environ[key]
        argv = [sys.executable, '-m', 'scripts.run_agent', '--example', example,
                '--run-id', rid, '--provider', provider, '--model', model]
        argv += ['--memory-dir', str(storage.ROOT / 'hmem')] if memory else ['--no-memory']
        proc = subprocess.run(argv, cwd=PROJECT, env=env, timeout=450, capture_output=True)
        trace_path = folder / 'trace.json'
        trace = json.loads(trace_path.read_text(encoding='utf-8')) if trace_path.exists() else []
        last = trace[-1] if trace else {}
        status = last.get('status', 'failed') if last.get('kind') == 'session_ended' else 'failed'
        if proc.returncode and status == 'completed_draft': status = 'failed'
        if status == 'failed':
            # Surface the child's own words; a generic message hid real refusals.
            detail = (last.get('detail') or '').strip()
            stderr = (proc.stderr or b'').decode('utf-8', 'replace').strip().splitlines()
            reason = detail or (stderr[-1] if stderr else '')
            write_status(folder, status, error=(reason[:400] or 'Agent 进程未生成完整草稿。'))
        else:
            write_status(folder, status)
    except subprocess.TimeoutExpired:
        write_status(folder, 'timeout', error='达到 450 秒进程时限，已停止。')
    except Exception:
        provider, model, _memory = agent_config()
        write_status(folder, 'failed', error=f'本地 Agent 启动失败；请检查数据与 {provider} 服务（{model}）。')
    finally:
        slot.release()


@router.get('/capabilities')
def capabilities():
    provider, model, memory = agent_config()
    available = _nightshift_available(model) if provider == 'nightshift' else _ollama_available(model)
    return {'framework': 'LangGraph', 'provider': provider, 'model': model,
            'available': available, 'memory_enabled': memory,
            'scope': 'public_examples_only', 'semantic_review': False}


@router.post('/runs', status_code=202)
def start(request: AgentRequest):
    caps = capabilities()
    if not caps['available']:
        provider = caps.get('provider') or agent_config()[0]
        model = caps.get('model') or agent_config()[1]
        raise HTTPException(503, f"本机 {provider} 模型 {model or '(未配置)'} 不可用；"
                                 f"没有自动下载或替代模型。")
    if not (PROJECT / 'data/public' / f'uci-{request.example}' / 'prepared.csv').exists():
        raise HTTPException(409, '请先在原工作台加载对应公开案例，完成下载与校验。')
    if not slot.acquire(blocking=False):
        raise HTTPException(429, '已有 Agent 正在运行；本机一次运行一个。')
    rid = str(uuid4())
    try:
        folder = storage.ROOT / 'agent-runs' / rid
        folder.mkdir(parents=True)
        write_status(folder, 'queued')
        pool.submit(supervise, rid, request.example)
    except Exception:
        slot.release()
        raise
    return {'id': rid}


@router.get('/runs/{rid}')
def get_run(rid: UUID):
    folder = storage.ROOT / 'agent-runs' / str(rid)
    if not folder.exists(): raise HTTPException(404, 'Agent run not found.')
    def read(name, default):
        path = folder / name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    trace = read('trace.json', [])
    ended = trace[-1] if trace and trace[-1].get('kind') == 'session_ended' else {}
    state = read('status.json', {'status': ended.get('status', 'running')})
    return {'id': str(rid), **state, 'events': trace, 'report': read('report.json', None),
            'engineering_review': read('engineering-review.json', None)}


@router.get('/runs')
def history():
    root = storage.ROOT / 'agent-runs'
    folders = sorted(root.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    result = []
    for folder in folders:
        try: run = get_run(UUID(folder.name))
        except ValueError: continue
        first = run['events'][0] if run['events'] else {}
        result.append({'id': run['id'], 'status': run['status'], 'example': first.get('example'),
                       'created_at': first.get('at')})
    return result
