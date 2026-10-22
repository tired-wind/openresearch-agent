import math

def critique(analysis, literature):
    findings=[]
    if not all(math.isfinite(v) for v in analysis['metrics'].values()):
        raise ValueError('Non-finite model metric; report blocked.')
    if set(analysis['split']['train_indices']) & set(analysis['split']['test_indices']):
        raise ValueError('Train/test overlap; report blocked.')
    if analysis['excluded']:
        findings.append({'severity':'warning','action':'Review excluded columns for identifiers and target leakage.','evidence_ids':['analysis-1']})
    if any(r['evidence_id'] != 'pubmed-'+r['pmid'] or r['url'] != 'https://pubmed.ncbi.nlm.nih.gov/'+r['pmid']+'/' for r in literature['records']):
        raise ValueError('Citation identity mismatch; report blocked.')
    findings.append({'severity':'warning','action':'Read candidate papers and assess population, exposure and outcome before labeling support or contradiction.','evidence_ids':[r['evidence_id'] for r in literature['records']]})
    return {'status':'passed_with_limitations','checks':['Finite computed metrics','Disjoint train/test rows','Citation identifier consistency'], 'findings':findings,
        'scope':'Deterministic artifact checks. Not an independent scientific peer review or full-text citation verification.'}

def render(question, summary, analysis, literature, review, provenance, claims=None, plan=None):
    lines=['# OpenResearch Agent — Research report','', '## Research question',question,'',
        '## Dataset and provenance',f"Source: {provenance['kind']}. SHA-256: {provenance['sha256']}.",
        f"Observed {summary['rows']} rows and {summary['columns']} columns. Analyzed {analysis['n_analyzed']} rows; train {analysis['n_train']}, test {analysis['n_test']}.",
        '', '## Methodology',f"{analysis['task']} target: {analysis['target']}. Model: {analysis['model']}. Seed: {analysis['seed']}.",
        'Preprocessing fitted on training rows only. Three-fold training CV and separate 25% holdout. Exact duplicate rows removed before splitting.',
        f"CV scoring: {analysis['cv']['scoring']}; mean {analysis['cv']['mean']:.6f}, fold SD {analysis['cv']['std']:.6f}. Negative RMSE scores use higher-is-better convention.",
        f"Positive class (binary only): {analysis['positive_class']}.", '', '## Model evaluation [computation: analysis-1]']
    lines += [f'- {k}: {v:.6f}' for k,v in analysis['metrics'].items()]
    lines += ['', '## Ranked predictive factors [computation]', '| Factor | Permutation score decrease | Repeat SD | Evidence |','|---|---:|---:|---|']
    lines += [f"| {r['feature'].replace('|','/')} | {r['importance']:.6f} | {r['repeat_std']:.6f} | {r['evidence_id']} |" for r in analysis['factors']]
    lines += ['', 'Importance is measured in the scoring metric units; negative values are retained. No causal direction is inferred.', '', '## Excluded features [dataset observation]']
    lines += [f"- {r['feature']}: {r['reason']}" for r in analysis['excluded']] or ['- None.']
    lines += ['', '## Scientific evidence [retrieved sources]', f"Retrieval status: {literature['status']}. {literature['message']}",
        'No source is automatically labeled supporting or conflicting. Search matches alone cannot establish either relationship.']
    for r in literature['records']:
        lines += [f"- [{r['title']}]({r['url']}) — {', '.join(r['authors'])} ({r['year']}); PMID {r['pmid']}; DOI {r['doi'] or 'not provided'}. Access: {r['access']}; relation: uncertain; evidence: {r['evidence_id']}."]
    lines += ['', '## Uncertainty and limitations']+[f'- {x}' for x in analysis['limitations']]
    lines += ['', '## Verification',review['scope']]+[f"- {x['action']}" for x in review['findings']]
    lines += ['', '## Reproducibility',f"Run ID: {provenance['run_id']}. Dataset digest above. Dependency versions: {provenance['versions']}.",
        'Persisted artifacts: plan.json, overview.json, analysis.json (including split indices), literature.json, review.json, provenance.json, report.md. No dataset rows were sent to a model.',
        'Execution mode: deterministic research workflow; LLM and sponsor integrations not active. Hypotheses are not validated findings.']
    if provenance.get('profile'):
        p=provenance['profile']
        lines += ['', '## Public dataset attribution', f"{p['attribution']}. {p['source_url']}. License: {p['license']} (https://creativecommons.org/licenses/by/4.0/).",
                  'Prepared data: original ID removed (WDBC), or binary target replaces num and nominal codes preserved (Cleveland).']
        lines += [f'- {x}' for x in p['limitations']]
    if plan:
        lines += ['', '## 分析方案与适用性']+[f'- {c["status"]}: {c["message"]} {c["action"]}' for c in plan['checks']]
        lines += [f'- {x}' for x in plan['limitations']]
    if claims:
        lines += ['', '## 可追溯结论（claims.json）']
        for c in claims:
            lines += ['', f'### {c["id"]}: {c["label"]}', c['statement'],
                      f'计算依据：{c["artifact"]}#{c["pointer"]}; metric={c["metric"]}; n_test={c["n_test"]}; repeat_sd={c["repeat_std"]:.6f}.',
                      '文献状态：待内容审查。' if c['anchors'] else '文献状态：证据不足；未找到已检索摘要中的字段词语线索。']
            for a in c['anchors']:
                lines += [f'- PMID {a["pmid"]}: {a["url"]}; abstract characters [{a["start"]}:{a["end"]}].',
                          '  摘要原文片段（仅词语命中，不等于支持）：'+a['quote'].replace('\n',' ')]
    return '\n'.join(lines)+'\n'
