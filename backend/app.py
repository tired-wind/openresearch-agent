from __future__ import annotations
import json
import os
import sys
import threading
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from uuid import uuid4, UUID
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.catalog import CATALOG, identify
from backend.planning import ResearchRequest, build_plan
from scripts.fetch_public_data import fetch as fetch_public_data
from backend import storage
from backend.analysis import read_table, overview, MAX_BYTES, InputError

POOL=ThreadPoolExecutor(max_workers=1)
SLOTS=threading.BoundedSemaphore(4)
PROJECT=Path(__file__).resolve().parents[1]

@asynccontextmanager
async def lifespan(app):
    # A process restart must not leave misleading 'running' jobs forever.
    with storage.connect() as con:
        for rid,payload in con.execute('SELECT id,payload FROM runs').fetchall():
            s=json.loads(payload)
            if s['status'] in ('running','queued'):
                s.update(status='failed',error='Server restarted; create a new run.')
                con.execute('UPDATE runs SET payload=? WHERE id=?',(json.dumps(s),rid))
    yield

app=FastAPI(title='OpenResearch Agent',version='0.1.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])

@app.middleware('http')
async def local_boundary(request,call_next):
    if request.method in ('POST','PUT','DELETE'):
        origin=request.headers.get('origin')
        if origin and origin not in ('http://localhost:3018','http://127.0.0.1:3018','http://localhost:8018','http://127.0.0.1:8018'):
            return JSONResponse({'detail':'Untrusted browser origin.'},status_code=403)
        try:
            if int(request.headers.get('content-length','0')) > 6*1024*1024:
                return JSONResponse({'detail':'Request too large.'},status_code=413)
        except ValueError:
            return JSONResponse({'detail':'Invalid content length.'},status_code=400)
    return await call_next(request)

def meta_for(dataset_id):
    p=storage.ROOT/'uploads'/f'{dataset_id}.json'
    if not p.exists(): raise HTTPException(404,'Dataset not found.')
    return json.loads(p.read_text())

def register(raw,suffix,kind):
    try: df=read_table(raw,suffix)
    except InputError as exc: raise HTTPException(422,str(exc))
    did=str(uuid4()); folder=storage.ROOT/'uploads'; folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    (folder/f'{did}{suffix}').write_bytes(raw)
    profile=identify(raw)
    if profile: kind='verified_public_example'
    (folder/f'{did}.json').write_text(json.dumps({'suffix':suffix,'kind':kind,'profile':profile,'created_at':storage.now()}))
    info=overview(df)
    # Summary for UI excludes numeric values; avoid NaN in schema endpoint.
    info.pop('numeric_summary',None)
    return {'dataset_id':did,'kind':kind,'profile':profile,'overview':info}

@app.get('/api/health')
def health():
    with storage.connect() as con: con.execute('SELECT 1')
    return {'status':'ok','mode':'deterministic','sponsors':'not integrated','llm':'disabled'}

@app.post('/api/datasets')
async def upload(file:UploadFile=File(...)):
    raw=await file.read(MAX_BYTES+1)
    await file.close()
    return register(raw,Path(file.filename or '').suffix.lower(),'user_upload')

@app.post('/api/demo')
def demo(): return register((PROJECT/'demo/synthetic_health.csv').read_bytes(),'.csv','synthetic_demo_not_clinical')

@app.get('/api/demo.csv')
def demo_csv(): return FileResponse(PROJECT/'demo/synthetic_health.csv',media_type='text/csv',filename='synthetic_health.csv')

@app.get('/api/examples')
def examples():
    return [{'id':key,**value} for key,value in CATALOG.items()]

@app.post('/api/examples/{name}')
def public_example(name:Literal['heart','breast']):
    try:
        fetch_public_data(name)
        raw=(PROJECT/'data/public'/f'uci-{name}'/'prepared.csv').read_bytes()
        if not identify(raw):
            raise ValueError('Prepared file checksum differs from the reviewed example.')
    except Exception as exc:
        raise HTTPException(503,'公开案例暂时不可用或内容校验失败；未使用替代数据。请稍后重试。') from exc
    return register(raw,'.csv','verified_public_example')

def plan_for(request:ResearchRequest):
    meta=meta_for(str(request.dataset_id))
    raw=(storage.ROOT/'uploads'/f'{request.dataset_id}{meta["suffix"]}').read_bytes()
    try: frame=read_table(raw,meta['suffix'])
    except InputError as exc: raise HTTPException(422,str(exc))
    return build_plan(request,frame,raw,identify(raw))

@app.post('/api/plans')
def preview_plan(request:ResearchRequest):
    return plan_for(request).model_dump(mode='json')

@app.get('/api/history')
def history():
    with storage.connect() as con:
        states=[json.loads(row[0]) for row in con.execute('SELECT payload FROM runs ORDER BY rowid DESC LIMIT 20')]
    return [{'id':s['id'],'status':s['status'],'question':s['request']['question'],
             'created_at':s['created_at'],'target':s['request']['target']} for s in states]

def supervise(run_id):
    try:
        env=os.environ.copy(); env['OPENRESEARCH_DATA_DIR']=str(storage.ROOT)
        # No credentials are needed by this fixed computation worker.
        env={k:v for k,v in env.items() if not any(w in k.upper() for w in ('API_KEY','TOKEN','SECRET','PASSWORD'))}
        proc=subprocess.run([sys.executable,'-m','backend.worker',run_id],cwd=PROJECT,env=env,timeout=150,capture_output=True)
        state=storage.load(run_id)
        if proc.returncode or state['status'] in ('queued','running'):
            state.update(status='failed',error='Worker exited without a complete result.'); storage.save(state)
    except subprocess.TimeoutExpired:
        state=storage.load(run_id); state.update(status='failed',error='Analysis exceeded 150-second limit.'); storage.save(state)
    finally: SLOTS.release()

@app.post('/api/runs',status_code=202)
def create_run(request:ResearchRequest):
    plan=plan_for(request)
    if plan.status=='blocked':
        raise HTTPException(422,{'message':'当前问题或数据不适合此分析方法。','plan':plan.model_dump(mode='json')})
    if request.plan_fingerprint and request.plan_fingerprint!=plan.fingerprint:
        raise HTTPException(409,'输入已改变，请重新预览方案后再运行。')
    if not SLOTS.acquire(blocking=False): raise HTTPException(429,'Analysis queue is full (4 runs).')
    rid=str(uuid4()); state={'id':rid,'status':'queued','stage':'planner','created_at':storage.now(),'events':[], 'request':request.model_dump(mode='json'),'plan':plan.model_dump(mode='json')}
    try:
        storage.save(state); POOL.submit(supervise,rid)
    except Exception:
        SLOTS.release(); raise
    return {'id':rid,'status':'queued'}

@app.get('/api/runs/{run_id}')
def get_run(run_id:UUID):
    state=storage.load(str(run_id))
    if state is None: raise HTTPException(404,'Run not found.')
    return state

@app.get('/api/runs/{run_id}/report',response_class=PlainTextResponse)
def report(run_id:UUID):
    state=get_run(run_id)
    if 'result' not in state: raise HTTPException(409,'Report is not ready.')
    return PlainTextResponse(state['result']['report'],headers={'Content-Disposition':f'attachment; filename="openresearch-{run_id}.md"'})

@app.get('/api/runs/{run_id}/evidence')
def evidence(run_id:UUID):
    state=get_run(run_id)
    if 'result' not in state: raise HTTPException(409,'Evidence is not ready.')
    return JSONResponse(state['result'],headers={'Content-Disposition':f'attachment; filename="evidence-{run_id}.json"'})
