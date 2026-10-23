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
MODEL = 'qwen3.5:4b'


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    example: Literal['heart', 'breast']


def write_status(folder, status, **extra):
    path = folder / 'status.json'
    tmp = folder / 'status.json.tmp'
    tmp.write_text(json.dumps({'status': status, 'updated_at': storage.now(), **extra}))
    tmp.replace(path)


def recover_interrupted():
    for path in (storage.ROOT / 'agent-runs').glob('*/status.json'):
        if json.loads(path.read_text()).get('status') in ('queued', 'running'):
            write_status(path.parent, 'interrupted', error='服务已重启，请重新运行。')


def supervise(rid, example):
    folder = storage.ROOT / 'agent-runs' / rid
    try:
        write_status(folder, 'running')
        # Allowlist environment: no model keys, tracing tokens or paid API access.
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'SYSTEMROOT')}
        env['OPENRESEARCH_DATA_DIR'] = str(storage.ROOT)
        proc = subprocess.run([sys.executable, '-m', 'scripts.run_agent', '--example', example,
                               '--run-id', rid, '--model', MODEL], cwd=PROJECT, env=env,
                              timeout=450, capture_output=True)
        trace_path = folder / 'trace.json'
        trace = json.loads(trace_path.read_text()) if trace_path.exists() else []
        last = trace[-1] if trace else {}
        status = last.get('status', 'failed') if last.get('kind') == 'session_ended' else 'failed'
        if proc.returncode and status == 'completed_draft': status = 'failed'
        write_status(folder, status)
    except subprocess.TimeoutExpired:
        write_status(folder, 'timeout', error='达到 450 秒进程时限，已停止。')
    except Exception:
        write_status(folder, 'failed', error='本地 Agent 启动失败；请检查数据和 Ollama 服务。')
    finally:
        slot.release()


@router.get('/capabilities')
def capabilities():
    try:
        response = httpx.get('http://127.0.0.1:11434/api/tags', timeout=2)
        response.raise_for_status()
        available = MODEL in [m['name'] for m in response.json().get('models', [])]
    except (httpx.HTTPError, ValueError, KeyError):
        available = False
    return {'framework': 'LangGraph', 'provider': 'Ollama', 'model': MODEL,
            'available': available, 'scope': 'public_examples_only', 'semantic_review': False}


@router.post('/runs', status_code=202)
def start(request: AgentRequest):
    if not capabilities()['available']:
        raise HTTPException(503, '本机 Ollama 或 qwen3.5:4b 不可用；没有自动下载或替代模型。')
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
        return json.loads(path.read_text()) if path.exists() else default
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
