import {test,expect} from '@playwright/test';

test('真实公开心脏病案例：来源、字段含义、报告与证据卡',async({page})=>{
 test.skip(!process.env.RUN_PUBLIC_E2E,'Explicit live UCI download test; not part of offline CI.');
 await page.goto('/');
 await page.getByRole('button',{name:'心脏病公开案例',exact:false}).click();
 await expect(page.getByText('内容指纹已核验',{exact:false})).toBeVisible({timeout:45000});
 await expect(page.getByRole('combobox',{name:'目标变量',exact:true})).toHaveValue('disease_present');
 await page.getByLabel('我已确认每行代表独立观测',{exact:false}).check();
 await page.getByRole('button',{name:'预览分析方案'}).click();
 await expect(page.getByText('可运行 · 请确认范围',{exact:true})).toBeVisible();
 await page.screenshot({path:'../data/screenshots/public-plan.png',fullPage:true});
 await page.getByRole('button',{name:'确认方案并开始分析',exact:false}).click();
 await page.getByRole('button',{name:'查看结论与依据',exact:false}).click({timeout:60000});
 await expect(page.getByText('模型评估来自 76 行留出测试数据。',{exact:false})).toBeVisible();
 await page.locator('.claim-card summary').first().click();
 await expect(page.getByText('analysis.json#/factors/0',{exact:true})).toBeVisible();
 await page.screenshot({path:'../data/screenshots/public-results.png',fullPage:true});
});
