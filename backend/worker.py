"""One bounded process per analysis. Called only with server-generated UUIDs."""
import sys
import json
import hashlib
import platform
import importlib.metadata
from pathlib import Path
from backend import storage
from backend.analysis import read_table, overview, analyze
from backend.literature import retrieve
from backend.report import critique, render

def execute(run_id):
    state=storage.load(run_id)
    def stage(name,status,summary):
        state['stage']=name
        state['events'].append({'stage':name,'status':status,'summary':summary,'at':storage.now()})
        storage.save(state)
    try:
        state['status']='running'
        req=state['request']
        stage('planner','running','Construct a bounded plan from explicit target and task settings.')
        plan={'mode':'deterministic','question':req['question'],'target':req['target'],'task_requested':req['task'],
              'stages':['planner','data','model','literature','critic','report'],'max_review_rounds':1,
              'external_query':req['literature_query'] if req['allow_literature'] else None,
              'limits':'Prediction only; independent rows; no arbitrary code or causal identification.'}
        storage.artifact(run_id,'plan.json',plan)
        stage('planner','complete','Plan persisted. Prediction scope; no causal claims.')
        stage('data','running','Parse bounded file; inspect schema, missingness and duplicates.')
        meta=json.loads((storage.ROOT/'uploads'/f"{req['dataset_id']}.json").read_text())
        raw=(storage.ROOT/'uploads'/f"{req['dataset_id']}{meta['suffix']}").read_bytes()
        df=read_table(raw,meta['suffix'])
        summary=overview(df)
        # pandas numeric summaries can contain missing values; normalize for strict JSON.
        def finite_json(value):
            import math
            if isinstance(value, dict): return {k: finite_json(v) for k,v in value.items()}
            if isinstance(value, list): return [finite_json(v) for v in value]
            if isinstance(value, float) and not math.isfinite(value): return None
            return value
        summary=finite_json(summary)
        storage.artifact(run_id,'overview.json',summary)
        stage('data','complete',f"Validated {len(df)} rows and {len(df.columns)} columns.")
        stage('model','running','Split rows; fit preprocessing within training folds; evaluate and permute holdout features.')
        result=analyze(df,req['target'],req['task'])
        storage.artifact(run_id,'analysis.json',result)
        stage('model','complete',f"Computed {len(result['factors'])} ranked factors; excluded {len(result['excluded'])} fields.")
        stage('literature','running','Query PubMed with the approved search text only.' if req['allow_literature'] else 'External search disabled by user.')
        lit=retrieve(req['literature_query']) if req['allow_literature'] else {'status':'disabled','query':None,'records':[],'message':'External literature search disabled. No external support established.'}
        storage.artifact(run_id,'literature.json',lit)
        stage('literature','failed' if lit['status']=='failed' else 'complete',f"{lit['status']}: {len(lit['records'])} retrieved records. Support/contradiction remains uncertain.")
        stage('critic','running','Check numeric finiteness, split separation and reference identifiers.')
        review=critique(result,lit)
        storage.artifact(run_id,'review.json',review)
        stage('critic','complete','Artifact checks passed with explicit scientific limitations.')
        stage('report','running','Render report directly from stored computations and source records.')
        provenance={'run_id':run_id,'kind':meta['kind'],'sha256':hashlib.sha256(raw).hexdigest(),'versions':{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn']},'python':platform.python_version()}
        storage.artifact(run_id,'provenance.json',provenance)
        report=render(req['question'],summary,result,lit,review,provenance)
        storage.artifact(run_id,'report.md',report)
        state['result']={'overview':summary,'analysis':result,'literature':lit,'review':review,'provenance':provenance,'report':report,'plan':plan}
        state['status']='completed_with_warnings'
        stage('report','complete','Report persisted. Read limitations before interpreting results.')
    except Exception as exc:
        state['status']='failed'
        state['error']=str(exc) if isinstance(exc,ValueError) else f'{type(exc).__name__}: workflow failed; inspect local artifacts.'
        stage(state.get('stage','planner'),'failed',state['error'])

if __name__=='__main__':
    from uuid import UUID
    execute(str(UUID(sys.argv[1])))
