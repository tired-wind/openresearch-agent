import type {Plan,Result} from './types';

export function PlanCard({plan}:{plan:Plan}) {
  return <section className="plan-box" aria-label="分析方案">
    <div className="card-heading"><h2>分析前先核对</h2><span className={'badge '+(plan.status==='blocked'?'blocked':'')}>{plan.status==='ready'?'可运行 · 请确认范围':'暂不能运行'}</span></div>
    <p>以下是规则检查和工具执行方案，不代表大模型已经理解研究问题。</p>
    <ul className="plan-checks">{plan.checks.map(c=><li key={c.code} className={c.status}><b>{c.status==='pass'?'✓':c.status==='blocked'?'停止':'注意'} · {c.message}</b>{c.action&&<p>{c.action}</p>}</li>)}</ul>
    <details><summary>查看具体步骤与方法限制</summary><ol>{plan.steps.map(s=><li key={s}>{s}</li>)}</ol><ul>{plan.limitations.map(s=><li key={s}>{s}</li>)}</ul></details>
  </section>;
}

export function EvidenceCards({result}:{result:Result}) {
  if(!result.claims)return <p className="alert">这是旧版本保存的报告，没有结论证据卡。可重新分析以生成。</p>;
  return <section className="card claims"><div className="card-heading"><h2>结论与依据</h2><span>{result.claims.length} 条可追溯计算</span></div>
    <p>每张卡都区分计算结果与外部文献。摘要出现相关词语，只能作为进一步核对的线索。</p>
    {result.claims.map(c=><article className="claim-card" key={c.id}>
      <div className="claim-heading"><h3>{c.label}</h3><span className="badge">{c.anchors.length?'有摘要线索 · 待审查':'文献证据不足'}</span></div>
      <p className="claim-statement">{c.statement}</p>
      <details><summary>查看依据：{c.label}</summary>
        <h4>实际计算</h4><p>在 {c.n_test} 行测试数据上评估；评分为 {c.metric}。重复打乱的标准差为 {c.repeat_std.toFixed(4)}，不是置信区间。</p>
        <code className="artifact-pointer">{c.artifact}#{c.pointer}</code><p className="hash">原始数值：{c.value} · {c.id}</p>
        <h4>外部证据</h4>
        {!c.anchors.length&&<p>本次没有找到已检索摘要中的字段词语线索。这不证明科学文献中不存在相关证据。</p>}
        {c.anchors.map(a=>{const p=result.literature.records.find(p=>p.evidence_id===a.source_id);return <div className="source-anchor" key={a.source_id}>
          <a href={a.url} target="_blank" rel="noreferrer">{p?.title||'PubMed '+a.pmid} ↗</a>
          <blockquote>{a.quote}</blockquote><p>PMID {a.pmid} · 摘要字符位置 {a.start}–{a.end} · 仅摘要，未读全文</p>
          <p>{a.scope}</p>
        </div>})}
        <h4>不能据此得出的结论</h4><ul>{c.limitations.map(l=><li key={l}>{l}</li>)}</ul>
      </details>
    </article>)}
  </section>;
}
