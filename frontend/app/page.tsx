'use client';
import {useEffect,useRef,useState} from 'react';
import {EvidenceCards,PlanCard} from './evidence-cards';
import type {Dataset,HistoryItem,Plan,Run} from './types';

const stages:Record<string,string>={planner:'规划',data:'数据检查',model:'实际计算',literature:'文献检索',critic:'证据核验',report:'生成报告'};
const statuses:Record<string,string>={queued:'排队中',running:'运行中',completed_with_warnings:'已完成 · 请查看局限',failed:'运行失败',complete:'完成',pending:'等待',disabled:'未启用',retrieved:'已检索',empty:'未找到记录'};
const metrics:Record<string,[string,string]>={balanced_accuracy:['平衡准确率','各类别召回率的平均值'],f1_macro:['宏平均 F1','兼顾各类别的精确率与召回率'],baseline_balanced_accuracy:['简单基线','只使用训练类别分布作预测'],roc_auc:['ROC AUC','衡量区分两类样本的能力'],average_precision:['平均精确率','汇总精确率与召回率表现'],rmse:['均方根误差','越小越好，单位与目标相同'],mae:['平均绝对误差','越小越好，单位与目标相同'],r2:['R²','可能为负值；不是准确率'],baseline_rmse:['基线误差','用训练目标均值作预测']};
const LAST_RUN='openresearch.lastRunId';
function remember(id:string|null){try{if(id)localStorage.setItem(LAST_RUN,id);else localStorage.removeItem(LAST_RUN)}catch{/* Persistence is optional; the API history remains available. */}}
async function api<T>(url:string,init?:RequestInit):Promise<T>{
  const r=await fetch(url,init);const d=await r.json();
  if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:d.detail?.message||'请求未通过验证，请检查输入或服务状态。');
  return d;
}
function message(e:unknown){return e instanceof Error?e.message:'请求失败，请重试。'}

export default function Home(){
  const [dataset,setDataset]=useState<Dataset|null>(null),[target,setTarget]=useState('');
  const [question,setQuestion]=useState('哪些变量有助于预测样本中已记录的结果？这些解释有哪些局限？');
  const [task,setTask]=useState('auto'),[intent,setIntent]=useState('prediction'),[design,setDesign]=useState('independent');
  const [independent,setIndependent]=useState(false),[literature,setLiterature]=useState(false),[query,setQuery]=useState('');
  const [run,setRun]=useState<Run|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState('workspace');
  const [preview,setPreview]=useState<{plan:Plan;input:string}|null>(null),[history,setHistory]=useState<HistoryItem[]>([]);
  const [restoring,setRestoring]=useState(true),[pollPaused,setPollPaused]=useState(false);
  const timer=useRef<ReturnType<typeof setTimeout>|null>(null);
  const active=run?.status==='queued'||run?.status==='running';
  const draft=JSON.stringify({dataset_id:dataset?.dataset_id,target,question,task,intent,study_design:design,independent_rows:independent,allow_literature:literature,literature_query:query});
  const currentPlan=preview?.input===draft?preview.plan:null;
  const locked=busy||active||restoring;
  const result=run?.result;

  useEffect(()=>{let cancelled=false;
    async function restore(){
      try{
        const items=await api<HistoryItem[]>('/api/history');if(!cancelled)setHistory(items);
        let id:string|null=null;try{id=localStorage.getItem(LAST_RUN)}catch{}
        if(id&&/^[a-f0-9-]{36}$/.test(id)){
          const saved=await api<Run>('/api/runs/'+id);
          if(!cancelled){setRun(saved);setTab(saved.result?'results':'execution')}
        }
      }catch(e){if(!cancelled){setError('恢复工作台失败：'+message(e));remember(null)}}
      finally{if(!cancelled)setRestoring(false)}
    }
    void restore();return()=>{cancelled=true};
  },[]);

  useEffect(()=>{if(!active||!run||pollPaused)return;let cancelled=false,failures=0;
    const poll=async()=>{
      try{const d=await api<Run>('/api/runs/'+run.id);if(cancelled)return;failures=0;setRun(d);setError('');
        if(d.status==='queued'||d.status==='running')timer.current=setTimeout(poll,900);
        else api<HistoryItem[]>('/api/history').then(setHistory).catch(()=>{});
      }catch(e){if(cancelled)return;failures++;setError('获取执行状态失败：'+message(e));
        if(failures>=5)setPollPaused(true);else timer.current=setTimeout(poll,2000);
      }
    };
    timer.current=setTimeout(poll,400);return()=>{cancelled=true;if(timer.current)clearTimeout(timer.current)};
  },[run?.id,active,pollPaused]);

  function acceptDataset(d:Dataset){
    setDataset(d);setTarget(d.profile?.target||d.overview.fields.at(-1)?.name||'');
    setQuestion(d.profile?.question||'哪些变量有助于预测样本中已记录的结果？这些解释有哪些局限？');
    setQuery(d.profile?.query||'');setIndependent(false);setIntent('prediction');setDesign('independent');
    setPreview(null);setRun(null);remember(null);setTab('workspace');
  }
  async function loadExample(name:string){
    setBusy(true);setError('');try{acceptDataset(await api<Dataset>(name==='synthetic'?'/api/demo':'/api/examples/'+name,{method:'POST'}))}
    catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function upload(file:File){
    setBusy(true);setError('');try{const f=new FormData();f.append('file',file);acceptDataset(await api<Dataset>('/api/datasets',{method:'POST',body:f}))}
    catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function previewPlan(){
    setBusy(true);setError('');setPreview(null);
    try{setPreview({plan:await api<Plan>('/api/plans',{method:'POST',headers:{'Content-Type':'application/json'},body:draft}),input:draft})}
    catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function start(){
    if(!dataset||currentPlan?.status!=='ready')return;
    setBusy(true);setError('');try{
      const d=await api<{id:string}>('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...JSON.parse(draft),plan_fingerprint:currentPlan.fingerprint})});
      setRun({id:d.id,status:'queued',stage:'planner',events:[],plan:currentPlan});remember(d.id);setPollPaused(false);setTab('execution');
    }catch(e){setError(message(e))}finally{setBusy(false)}
  }
  async function openRun(id:string){
    setBusy(true);setError('');try{const d=await api<Run>('/api/runs/'+id);setRun(d);remember(id);setPollPaused(false);setTab(d.result?'results':'execution')}
    catch(e){setError(message(e))}finally{setBusy(false)}
  }

  return <div className="shell">
    <aside><a className="brand" href="/">◈ <span>OpenResearch<small>可追溯的科研工作台</small></span></a><p className="side-label">研究流程</p>
      <nav>{[['workspace','01','工作台'],['execution','02','执行过程'],['results','03','结论与证据'],['report','04','研究报告']].map(([id,n,label])=><button key={id} className={tab===id?'selected':''} onClick={()=>setTab(id)}><span>{n}</span>{label}{id==='execution'&&active&&<i/>}</button>)}</nav>
      <div className="side-bottom"><span className="live-dot"/> 本机研究空间<p>上传数据与计算保留在本机。加载公开案例会访问 UCI；启用检索后，仅公开检索词发往 PubMed。</p><small>Track 02 · Explain why</small></div>
    </aside>
    <main>
      <header><span>OPENRESEARCH / 研究工作台</span><a href="/agent">体验真实 Agent 循环 →</a><span className="badge">当前页面：固定分析流程</span></header>
      <section className="intro"><div><p className="eyebrow">先看证据，再谈结论</p><h1>{tab==='workspace'?'让每一个研究结论，都有据可查。':tab==='execution'?'看清分析正在做什么。':tab==='results'?'结果是什么，依据又是什么？':'保留完整、可复查的研究记录。'}</h1><p>{tab==='workspace'?'选一个公开案例，核对方案，查看实际计算与证据缺口。':'计算结果、来源和方法限制，放在一起检查。'}</p></div><div className="status-pill">{restoring?'恢复中':active?'● 分析中':result?'✓ 报告已就绪':'○ 准备开始'}</div></section>
      {error&&<div role="alert" className="alert error">{error}</div>}
      {pollPaused&&<div className="alert">状态查询已暂停，分析任务可能仍在运行。<button className="text-button" onClick={()=>{setPollPaused(false);setError('')}}>重新查询状态</button></div>}

      {tab==='workspace'&&<div className="workspace-grid">
        <section className="card"><div className="card-heading"><h2>开始一次研究</h2><span>01 / 数据与问题</span></div>
          <div className="example-picker"><h3>没有自己的数据？从真实公开案例开始</h3><p>首次加载会下载并校验小型 UCI 数据包（每个不足 130 KB，CC BY 4.0）。</p>
            <div className="example-buttons"><button className="button secondary" disabled={locked} onClick={()=>loadExample('heart')}>心脏病公开案例 · 303 行</button><button className="button secondary" disabled={locked} onClick={()=>loadExample('breast')}>乳腺癌公开案例 · 569 行</button></div>
            <button className="text-button" disabled={locked} onClick={()=>loadExample('synthetic')}>使用合成数据演示</button>
          </div>
          <div className="upload-box"><label className="button secondary">上传自己的数据<input aria-label="上传数据集" type="file" accept=".csv,.xlsx" disabled={locked} onChange={e=>{if(e.target.files?.[0])upload(e.target.files[0])}}/></label><p>CSV 或纯数值 XLSX · 最大 5 MiB · 5,000 行</p></div>
          {busy&&<p role="status">正在处理，请稍候…</p>}
          {dataset&&<><div className="mini-stats"><div><b>{dataset.overview.rows}</b><span>样本行</span></div><div><b>{dataset.overview.columns}</b><span>字段</span></div><div><b>{dataset.overview.missing_cells}</b><span>缺失单元格</span></div></div>
            <p className="source-label">{dataset.profile?<><a href={dataset.profile.source_url} target="_blank" rel="noreferrer">{dataset.profile.label} ↗</a> · 内容指纹已核验 · {dataset.profile.license}</>:dataset.kind==='synthetic_demo_not_clinical'?'合成演示数据 · 不是真实临床数据':'用户上传 · 数据来源和语义未独立核验'}</p></>}
          <fieldset disabled={locked}>
            <label className="field">研究问题<textarea value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1500} rows={3}/></label>
            <div className="field-pair"><label className="field">目标变量<select value={target} onChange={e=>setTarget(e.target.value)} disabled={!dataset}>{!dataset&&<option>先选择数据集</option>}{dataset?.overview.fields.map(c=><option key={c.name} value={c.name}>{dataset.profile?.fields[c.name]?.label||c.name} ({c.name})</option>)}</select></label>
              <label className="field">分析类型<select value={task} onChange={e=>setTask(e.target.value)}><option value="auto">根据目标自动识别</option><option value="classification">分类：预测类别</option><option value="regression">回归：预测数值</option></select></label></div>
            <div className="field-pair"><label className="field">研究目的<select value={intent} onChange={e=>setIntent(e.target.value)}><option value="prediction">解释样本中的预测表现</option><option value="causal_effect">估计因果或治疗效应</option><option value="future_risk">预测未来发病风险</option><option value="survival">分析生存与随访结局</option></select></label>
              <label className="field">数据设计<select value={design} onChange={e=>setDesign(e.target.value)}><option value="independent">独立个体观测</option><option value="repeated">同一个体多次记录</option><option value="temporal">时间序列</option><option value="survey">复杂抽样调查</option></select></label></div>
            <label className="check"><input type="checkbox" checked={independent} onChange={e=>setIndependent(e.target.checked)}/>我已确认每行代表独立观测，不含重复受试者或时间序列。</label>
            <label className="check"><input type="checkbox" checked={literature} onChange={e=>setLiterature(e.target.checked)}/>检索 PubMed 文献，仅发送下方公开检索词。</label>
            {literature&&<label className="field">公开文献检索词（不含个人信息）<input value={query} onChange={e=>setQuery(e.target.value)} maxLength={300}/></label>}
            <button className="button secondary run-button" disabled={!dataset||question.trim().length<10} onClick={previewPlan}>预览分析方案</button>
          </fieldset>
          {preview&&!currentPlan&&<p className="alert">输入已修改，请重新预览方案。</p>}
          {currentPlan&&<PlanCard plan={currentPlan}/>}
          <button className="button primary run-button" disabled={locked||currentPlan?.status!=='ready'} onClick={start}>确认方案并开始分析 →</button>
        </section>
        <div className="context-column"><section className="card dark"><p className="eyebrow">你只需要检查结果</p><h2>这个问题能回答吗？<br/>这个结论可靠吗？</h2>
          {[['01','先检查适用性','明确目标、数据设计与方法范围；不适用就停止。'],['02','执行真实计算','训练和测试分离，保留简单基线与完整结果。'],['03','展开查看依据','数值对应计算文件，文献片段对应原始摘要。']].map(([n,t,d])=><div className="method" key={n}><span>{n}</span><div><h3>{t}</h3><p>{d}</p></div></div>)}
        </section>
        {dataset?.profile&&<section className="card"><h3>这个案例的解释边界</h3>{dataset.profile.limitations.map(l=><p key={l}>{l}</p>)}</section>}
        <section className="card"><h3>最近的研究</h3>{history.length?history.map(h=><button className="history-item" key={h.id} disabled={locked} onClick={()=>openRun(h.id)}><b>{h.question}</b><small>{statuses[h.status]||h.status} · {new Date(h.created_at).toLocaleString('zh-CN')}</small></button>):<p>完成分析后可在这里重新打开，刷新不会丢失报告。</p>}</section>
        {dataset&&<section className="card"><h3>数据字段</h3><div className="schema">{dataset.overview.fields.map(f=><div key={f.name}><span>{dataset.profile?.fields[f.name]?.label||f.name}<small className="field-code">{f.name}</small></span><small>{f.missing} 项缺失</small></div>)}</div></section>}
        </div>
      </div>}

      {tab==='execution'&&<section className="card"><div className="card-heading"><h2>执行记录</h2><span>{statuses[run?.status||'']||'尚未开始'}</span></div><p>这里展示工具动作与结果摘要，不展示内部思维链。</p>
        <div className="stage-grid">{Object.entries(stages).map(([s,label],i)=>{const e=run?.events.filter(x=>x.stage===s).at(-1);return <div key={s} className={'stage '+(e?.status||'pending')}><span>0{i+1}</span><h3>{label}</h3><small>{statuses[e?.status||'pending']||e?.status}</small></div>})}</div>
        {run?.error&&<div role="alert" className="alert error">{run.error}</div>}
        <ol className="events" aria-live="polite">{run?.events.map((e,i)=><li key={i}><time>{new Date(e.at).toLocaleTimeString('zh-CN')}</time><div><b>{stages[e.stage]||e.stage} / {statuses[e.status]||e.status}</b><p>{e.summary}</p></div></li>)}</ol>
        {run?.plan&&<details><summary>查看本次确认的分析方案</summary><PlanCard plan={run.plan}/></details>}
        {!run&&<p className="empty">请从工作台预览方案并开始分析。</p>}{result&&<button className="button primary" onClick={()=>setTab('results')}>查看结论与依据 →</button>}
      </section>}

      {tab==='results'&&(result?<>
        <section className="alert"><b>已生成 {result.claims?.length??result.analysis.factors.length} 条计算结果；尚未确认文献支持或反驳。</b><p>模型评估来自 {result.analysis.n_test} 行留出测试数据。下方评分不代表临床有效性，特征重要性不代表因果。</p></section>
        <div className="metrics">{Object.entries(result.analysis.metrics).map(([k,v])=><div className="card metric" key={k}><span>{metrics[k]?.[0]||k}</span><strong>{v.toFixed(3)}</strong><small>{metrics[k]?.[1]||'测试集计算'}</small></div>)}</div>
        <EvidenceCards result={result}/>
        <div className="results-grid"><section className="card"><div className="card-heading"><h2>预测重要性</h2><span>实际置换计算</span></div><p>打乱特征后，模型评分变化有多大。负值保留；标准差不是置信区间。</p><div className="bars">{result.analysis.factors.map(f=><div key={f.feature} className="factor"><div><b>{result.provenance.profile?.fields[f.feature]?.label||f.feature}</b><span>{f.importance.toFixed(4)} <small>± {f.repeat_std.toFixed(4)}</small></span></div><div className="bar-track"><div className={f.importance<0?'negative':''} style={{width:Math.max(1,Math.abs(f.importance)/Math.max(...result.analysis.factors.map(x=>Math.abs(x.importance)),.0001)*100)+'%'}}/></div><small>{f.evidence_id} · {f.feature}</small></div>)}</div></section>
          <section className="card"><h2>方法与局限</h2><p>{result.analysis.n_train} 行训练 / {result.analysis.n_test} 行测试。训练集三折交叉验证均分：{result.analysis.cv.mean.toFixed(3)}（{result.analysis.cv.scoring}）。</p><h3>排除的字段</h3>{result.analysis.excluded.length?result.analysis.excluded.map(e=><p key={e.feature}><b>{e.feature}</b><br/>{e.reason}</p>):<p>没有排除字段。</p>}
          <ul className="limitations">{(result.plan?.limitations||result.analysis.limitations).map(l=><li key={l}>{l}</li>)}</ul>
          <details><summary>查看工具记录的全部方法限制</summary><ul>{result.analysis.limitations.map(l=><li key={l}>{l}</li>)}</ul></details></section>
        </div>
        <section className="card literature"><div className="card-heading"><h2>检索到的科学文献</h2><span>{statuses[result.literature.status]||result.literature.status}</span></div>
          <p>{result.literature.status==='disabled'?'本次未启用外部检索，因此没有文献支持结论。':result.literature.status==='failed'?'外部检索失败；没有生成替代引用。':`检索到 ${result.literature.records.length} 条记录。论文存在不代表它支持模型结论。`}</p>
          {result.literature.records.map(p=><article key={p.pmid}><span className="badge">{p.access==='abstract_only'?'只读取摘要':'仅有元数据'} · 待内容审查</span><h3><a href={p.url} target="_blank" rel="noreferrer">{p.title} ↗</a></h3><p>{p.year} · PMID {p.pmid}{p.doi&&' · DOI '+p.doi}</p><details><summary>阅读检索到的摘要</summary><p>{p.abstract||'未获取到摘要。'}</p></details></article>)}
        </section>
      </>:<section className="card empty">分析完成后，这里会展示计算结果和证据。</section>)}

      {tab==='report'&&(result?<section className="card"><div className="card-heading"><h2>完整研究报告</h2><div className="downloads"><a className="button secondary" href={'/api/runs/'+run?.id+'/evidence'}>下载证据 JSON ↓</a><a className="button primary" href={'/api/runs/'+run?.id+'/report'}>下载 Markdown ↓</a></div></div><p className="hash">数据 SHA-256：{result.provenance.sha256}</p><pre className="report">{result.report}</pre></section>:<section className="card empty">报告将由本次实际计算与检索记录生成。</section>)}
      <footer>OpenResearch Agent <span>本机研究原型 · 不作临床或因果结论</span></footer>
    </main>
  </div>;
}
