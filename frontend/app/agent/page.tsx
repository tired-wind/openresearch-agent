'use client';

import {useEffect, useState} from 'react';
import './style.css';

type Event = {seq:number;at:string;kind:string;turn?:number;tool?:string;arguments?:unknown;result?:unknown;status?:string;calls?:unknown;usage?:unknown;model?:string;question?:string;duration_ms?:number;strategy?:string;threshold?:number;considered?:number;memories?:{id:string;score:number;layer:string;reason:string}[];memory_id?:string;layer?:string;source?:string};
type Report = {model_draft:string;computed_metrics:Record<string,number>;selected_computed_factors:{feature:string;importance:number;repeat_std:number}[];references:{pmid:string;title:string;url:string}[];limitations:string[]};
type Run = {id:string;status:string;error?:string;events:Event[];report:Report|null;engineering_review?:{issues:string[]}};
type History = {id:string;status:string;example?:string;created_at?:string};
type Caps = {provider:string;model:string;available:boolean;memory_enabled?:boolean};
const labels:Record<string,string> = {inspect_dataset:'读取数据与字段含义',analyze_dataset:'执行 Python 建模',search_pubmed:'检索 PubMed',read_abstract:'阅读真实摘要',finish_investigation:'提交解释草稿'};
const status:Record<string,string> = {running:'正在运行',queued:'等待执行',completed_draft:'已生成草稿 · 语义待核验',failed:'执行失败',timeout:'运行超时',budget_exhausted:'达到执行预算',context_budget_exhausted:'达到上下文预算',interrupted:'运行中断'};
async function api<T>(url:string, init?:RequestInit):Promise<T>{const r=await fetch(url,init);const d=await r.json();if(!r.ok)throw new Error(d.detail||'请求失败');return d;}
function observation(value:unknown):string{
 if(!value||typeof value!=='object')return '';
 const r=value as Record<string,unknown>;
 if(typeof r.error==='string')return '拒绝原因：'+r.error;
 if(Array.isArray(r.records))return `检索状态：${r.status}；返回 ${r.records.length} 条记录。`;
 if(typeof r.title==='string')return r.title;
 if(r.overview&&typeof r.overview==='object'){const o=r.overview as {rows:number;columns:number};return `读取 ${o.rows} 行、${o.columns} 个字段。`;}
 if(r.metrics)return `实际建模完成：训练集 ${r.n_train} 行，测试集 ${r.n_test} 行。`;
 if(r.status==='draft_saved')return '草稿已保存；科学语义仍未核验。';
 return '';
}

export default function AgentDemo(){
  const [run,setRun]=useState<Run|null>(null),[history,setHistory]=useState<History[]>([]),[error,setError]=useState('');
  const [example,setExample]=useState('heart'),[busy,setBusy]=useState(false),[available,setAvailable]=useState<boolean|null>(null),[caps,setCaps]=useState<Caps|null>(null);
  const active=run?.status==='running'||run?.status==='queued';
  async function open(id:string){setRun(await api<Run>('/api/agent/runs/'+id));}
  useEffect(()=>{Promise.all([api<Caps>('/api/agent/capabilities'),api<History[]>('/api/agent/runs')]).then(([c,h])=>{setCaps(c);setAvailable(c.available);setHistory(h);if(h.length)void open(h[0].id).catch(e=>setError(String(e)))}).catch(e=>setError(String(e)))},[]);
  useEffect(()=>{if(!run||!active)return;let cancelled=false;const id=run.id;const timer=setInterval(()=>{api<Run>('/api/agent/runs/'+id).then(r=>{if(!cancelled)setRun(r)}).catch(e=>{if(!cancelled)setError(String(e))})},1200);return()=>{cancelled=true;clearInterval(timer)}},[run?.id,active]);
  async function start(){setBusy(true);setError('');try{const r=await api<{id:string}>('/api/agent/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({example})});await open(r.id);setHistory(await api<History[]>('/api/agent/runs'))}catch(e){setError(String(e))}finally{setBusy(false)}}
  return <main className="agent-demo">
    <header><a href="/">← 数据分析工作台</a><span>实验功能 · 单 Agent / 真实本机模型</span></header>
    <h1>看一次 Agent 如何工作</h1><p className="lead">每张动作卡来自模型实际发出的工具调用。计算由 Python 完成；模型解释单独标记为待核验草稿。</p>
    <div className="architecture"><div><small>编排框架</small><strong>LangGraph</strong><span>状态与条件循环</span></div><b>→</b><div><small>模型服务</small><strong>{caps?`${caps.provider} / ${caps.model.split('/').pop()}`:'检查中…'}</strong><span>{caps?.memory_enabled?'经 H-MEM 注入先前记忆':'选择工具与检索词'}</span></div><b>⇄</b><div><small>受控工具</small><strong>Python + PubMed</strong><span>执行、返回观察、再决策</span></div></div>
    <section><h2>运行真实案例</h2><p>目前仅开放两个已校验的公开案例及其预设研究问题。文献检索词会发给 PubMed；模型推理在本机运行。没有多 Agent 协作或自动科学审稿。</p>
      <div className="controls"><select aria-label="Agent 公开案例" value={example} disabled={active||busy} onChange={e=>setExample(e.target.value)}><option value="heart">UCI 心脏病：诊断指标与解释局限</option><option value="breast">UCI 乳腺癌：形态指标与解释局限</option></select><button onClick={start} disabled={active||busy||available!==true}>{active?'Agent 正在执行…':busy?'启动中…':'启动真实 Agent'}</button></div>
      <p className="muted">{available===null?'检查本机模型…':available?`已检测到 ${caps?.provider||'本机'} 模型 ${caps?.model||''}${caps?.memory_enabled?'，并启用 H-MEM 记忆召回':''}；每次运行会重新推理、计算和检索。`:'本机模型不可用。不会自动下载或切换到付费服务。'} 最多 10 轮模型调用、2 次文献搜索；网页启动的进程上限 450 秒。</p>
      {error&&<p role="alert" className="alert error">{error}</p>}
    </section>
    <section><h2>真实执行记录</h2>{history.length>0&&<select aria-label="历史 Agent 运行" value={run?.id||''} disabled={active} onChange={e=>void open(e.target.value).catch(e=>setError(String(e)))}>{history.map(h=><option key={h.id} value={h.id}>{h.example||'公开案例'} · {h.id.slice(0,8)} · {status[h.status]||h.status}</option>)}</select>}
      {run?<><p><strong>{status[run.status]||run.status}</strong> · {run.id}</p><p>{run.events[0]?.question}</p><p className="muted">{active?'下方随真实事件更新。':'以下是保存的真实运行记录，不是重新执行。'} 展开可核对工具输入与输出；不展示隐藏思维链。</p>
        {run.error&&<p role="alert">{run.error}</p>}
        {run.engineering_review&&<div className="alert error"><strong>开发时复核发现的问题（不是自动审稿结果）</strong><ul>{run.engineering_review.issues.map(issue=><li key={issue}>{issue}</li>)}</ul></div>}
        <ol className="timeline">{run.events.filter(e=>['memory_retrieved','memory_written','model_started','tool_started'].includes(e.kind)).map(e=>{
          if(e.kind==='memory_retrieved'){const mem=e.memories||[];return <li className="tool-card" key={e.seq}><strong>H-MEM 召回 {mem.length} 条记忆</strong><span className="badge">{mem.length?'已注入提示词':'无匹配'}</span><code>strategy={e.strategy} threshold={e.threshold}</code>{mem.length?mem.map(m=><p key={m.id}><code>{m.id}</code> 分数 {m.score}（{m.layer}）· {m.reason}</p>):<p>本次查询没有达到阈值的记忆。这不等于研究结论为空。</p>}</li>}
          if(e.kind==='memory_written'){return <li className="tool-card" key={e.seq}><strong>写入长期记忆</strong><span className="badge">{(e as {layer?:string}).layer||'long_term'}</span><code>{e.memory_id}</code><p>来源 {e.source}；下次会话可被召回。</p></li>}
          if(e.kind==='model_started'){const response=run.events.find(n=>n.seq===e.seq+1&&n.kind==='model_returned');return <li className="model-turn" key={e.seq}>第 {e.turn} 轮 · {e.model} 接收上下文，选择下一步 <time>{new Date(e.at).toLocaleTimeString()}</time>{response&&Array.isArray(response.calls)&&response.calls.length===0&&<p>本轮未发出工具调用；系统提示模型继续使用工具，消耗一次轮数预算。</p>}</li>}
          const next=run.events.find(n=>n.seq===e.seq+1&&n.kind==='tool_returned');
          return <li className="tool-card" key={e.seq}><strong>{labels[e.tool||'']||e.tool}</strong><span className="badge">{next?next.status==='ok'?'工具已返回':'调用被拒绝':'执行中'}</span><code>{e.tool}</code>{next&&<p>{observation(next.result)}</p>}<details open={e.tool==='search_pubmed'||next?.status==='rejected'}><summary>模型传入的参数</summary><pre>{JSON.stringify(e.arguments,null,2)}</pre></details>{next&&<details><summary>真实工具输出 · {next.duration_ms} ms</summary><pre>{JSON.stringify(next.result,null,2)}</pre></details>}</li>
        })}</ol><a href={'/api/agent/runs/'+run.id} target="_blank" rel="noreferrer">查看完整 JSON 记录 ↗</a></>:<p>点击启动后查看模型调用、工具参数和执行结果。</p>}
    </section>
    {run?.report&&<section><h2>结果：计算事实与模型解释分开展示</h2><h3>Python 计算的指标</h3><div className="agent-metrics">{Object.entries(run.report.computed_metrics).map(([k,v])=><div key={k}><small>{k}</small><strong>{v.toFixed(4)}</strong></div>)}</div><h3>模型选择讨论的特征</h3><p>{run.report.selected_computed_factors.map(f=>f.feature).join('、')}</p><h3>模型解释草稿 · 尚未通过科学语义核验</h3><pre className="draft">{run.report.model_draft}</pre><p className="muted">程序只检查特征名和引用身份，未验证草稿中的每个数字或科学判断。应以工具输出为准，不能将此草稿用作医疗建议。</p><h3>实际检索并打开的文献</h3>{run.report.references.length?run.report.references.map(r=><p key={r.pmid}><a href={r.url} target="_blank" rel="noreferrer">PMID {r.pmid} · {r.title}</a></p>):<p>没有可引用的已读摘要；不生成替代引用。</p>}<h3>解释边界</h3><ul>{run.report.limitations.map(l=><li key={l}>{l}</li>)}</ul></section>}
  </main>
}
