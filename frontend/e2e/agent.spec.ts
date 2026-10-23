import {test,expect} from '@playwright/test';
import {writeFileSync} from 'node:fs';

test('Agent 页面在模型不可用时禁用启动，不伪造运行',async({page})=>{
 await page.route('**/api/agent/capabilities',r=>r.fulfill({json:{available:false}}));
 await page.route('**/api/agent/runs',r=>r.fulfill({json:[]}));
 await page.goto('/agent');
 await expect(page.getByRole('heading',{name:'看一次 Agent 如何工作'})).toBeVisible();
 await expect(page.getByRole('button',{name:'启动真实 Agent'})).toBeDisabled();
 await expect(page.getByText('本机模型不可用。',{exact:false})).toBeVisible();
});

test('真实本机模型：通过网页启动，查看工具调用及实际报告',async({page,request})=>{
 test.skip(!process.env.RUN_AGENT_E2E,'Requires existing local Ollama model and prepared public dataset; no automatic download.');
 test.setTimeout(480000);
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/agent');
 const started=page.waitForResponse(r=>r.url().endsWith('/api/agent/runs')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'启动真实 Agent'}).click();
 const response=await started;expect(response.status()).toBe(202);
 const {id}=await response.json();
 await expect.poll(async()=>{const r=await request.get('/api/agent/runs/'+id);return (await r.json()).status},{timeout:455000,intervals:[2000,4000]}).toBe('completed_draft');
 await expect(page.getByRole('heading',{name:'模型解释草稿 · 尚未通过科学语义核验'})).toBeVisible();
 const result=await (await request.get('/api/agent/runs/'+id)).json();
 expect(result.events.some((e:{kind:string})=>e.kind==='model_returned')).toBe(true);
 expect(result.events.some((e:{tool:string})=>e.tool==='search_pubmed')).toBe(true);
 expect(result.report.interpretation_status).toBe('unverified_model_draft');
 expect(errors).toEqual([]);
 writeFileSync('../data/acceptance/agent-live.json',JSON.stringify(result,null,2));
 await page.screenshot({path:'../data/screenshots/agent-live.png',fullPage:true});
 await page.reload();
 await expect(page.getByText(id,{exact:false}).first()).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'../data/screenshots/agent-mobile.png',fullPage:true});
 console.log('Verified actual Agent run:',id);
});
