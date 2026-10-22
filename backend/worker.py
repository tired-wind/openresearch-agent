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
from backend.catalog import identify
from backend.evidence import build_claims, verify_claims

def execute(run_id):
    state=storage.load(run_id)
    def stage(name,status,summary):
        state['stage']=name
        state['events'].append({'stage':name,'status':status,'summary':summary,'at':storage.now()})
        storage.save(state)
    try:
        state['status']='running'
        req=state['request']
        stage('planner','running','核对已确认的分析方案、目标与数据指纹。')
        plan=state['plan']
        storage.artifact(run_id,'plan.json',plan)
        stage('planner','complete','方案已保存；仅分析预测表现，不作因果结论。')
        stage('data','running','解析文件，检查字段、缺失与重复。')
        meta=json.loads((storage.ROOT/'uploads'/f"{req['dataset_id']}.json").read_text())
        raw=(storage.ROOT/'uploads'/f"{req['dataset_id']}{meta['suffix']}").read_bytes()
        if hashlib.sha256(raw).hexdigest()!=plan['dataset_sha256']:
            raise ValueError('Dataset changed after planning; create a new plan.')
        profile=identify(raw)
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
        stage('data','complete',f"已验证 {len(df)} 行、{len(df.columns)} 个字段。")
        stage('model','running','划分训练与测试集；训练折内预处理，计算留出集评分与置换重要性。')
        result=analyze(df,req['target'],plan['task'])
        storage.artifact(run_id,'analysis.json',result)
        stage('model','complete',f"计算了 {len(result['factors'])} 个排序特征，排除 {len(result['excluded'])} 个字段。")
        stage('literature','running','仅使用已确认的公开检索词查询 PubMed。' if req['allow_literature'] else '用户未启用外部文献检索。')
        lit=retrieve(req['literature_query']) if req['allow_literature'] else {'status':'disabled','query':None,'records':[],'message':'External literature search disabled. No external support established.'}
        storage.artifact(run_id,'literature.json',lit)
        stage('literature','failed' if lit['status']=='failed' else 'complete',f"{lit['status']}: 检索到 {len(lit['records'])} 条记录；支持或冲突关系尚未确认。")
        stage('critic','running','核对指标、切分、引用身份、结论数值与摘要原文位置。')
        review=critique(result,lit)
        claims=build_claims(result,lit,profile)
        verification=verify_claims(claims,result,lit)
        review['claim_verification']=verification
        storage.artifact(run_id,'claims.json',claims)
        storage.artifact(run_id,'review.json',review)
        stage('critic','complete','计算与引用位置核验通过；科学支持关系仍需内容审查。')
        stage('report','running','根据已保存的实际计算和来源生成报告。')
        provenance={'run_id':run_id,'kind':meta['kind'],'sha256':hashlib.sha256(raw).hexdigest(),'profile':profile,'versions':{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn']},'python':platform.python_version()}
        storage.artifact(run_id,'provenance.json',provenance)
        report=render(req['question'],summary,result,lit,review,provenance,claims,plan)
        storage.artifact(run_id,'report.md',report)
        state['result']={'overview':summary,'analysis':result,'literature':lit,'review':review,'provenance':provenance,'report':report,'plan':plan,'claims':claims}
        state['status']='completed_with_warnings'
        stage('report','complete','报告已保存；请先阅读方法局限再解释结果。')
    except Exception as exc:
        state['status']='failed'
        state['error']=str(exc) if isinstance(exc,ValueError) else f'{type(exc).__name__}: workflow failed; inspect local artifacts.'
        stage(state.get('stage','planner'),'failed',state['error'])

if __name__=='__main__':
    from uuid import UUID
    execute(str(UUID(sys.argv[1])))
