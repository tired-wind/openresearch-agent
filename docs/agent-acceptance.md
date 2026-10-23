# 真实 Agent 验收记录

更新：2026-10-23，新加坡时间。结论：**模型—工具循环已实际跑通；科研解释质量仍未通过验收。** 不用自动化测试数量替代后者。

## 环境与执行路径

- LangGraph 1.2.16；本机 Ollama / 既有 Qwen3.5 4B；未下载新模型，未使用付费 API。
- Next.js `/agent` → FastAPI 子进程 → LangGraph model/tools 节点 → Python 和真实 PubMed。
- UCI Cleveland 303 行、13 个候选特征和二值目标；prepared.csv SHA-256：`3b46ae4de8e2a18070e923c7071c71c0f6987e6879ba26a8d6b4b27bdd484c73`。
- 复跑可得到不同模型选择、文献或失败结果；这不是预录的工具脚本。

## 网页实跑：29577ba7-03ac-422c-9f4a-27b013778e59

实际事件时间：2026-10-23 10:23:55–10:25:27（SGT，原日志为 UTC）。约 92 秒。九轮模型响应，八次工具调用；含一次无工具响应及一次被拒绝的提交。

| 顺序 | 模型真实动作 | 程序返回与后续行为 |
|---|---|---|
| 1 | `inspect_dataset({})` | 读取字段定义、缺失信息与数据局限 |
| 2 | `analyze_dataset({})` | 实际训练 227 行、留出 76 行；平衡准确率 0.8473867596，基线 0.5，ROC AUC 0.9365853659 |
| 3 | 一轮仅返回文字，没有工具 | 系统要求使用工具，消耗一轮预算；没有把文字当作执行结果 |
| 4 | 搜索 `fluoroscopy coronary vessels exercise ECG ST depression slope angina prediction heart disease` | PubMed 返回 0 条 |
| 5 | 模型改搜 `thallium perfusion exercise stress test ST segment slope coronary artery disease diagnosis` | 返回 2 条真实记录 |
| 6–7 | 读取 PMID 17964962、9605049 | 各自返回真实摘要、标题、作者、年份、链接 |
| 8 | 提交特征名为中文描述的草稿 | 程序拒绝：这些字符串不在实际计算字段中 |
| 9 | 改用 `ca`、`thal`、`slope` 再次提交 | 身份检查通过；保存 `completed_draft`，科学语义仍为 `not_verified` |

这次能证明：模型看到了空检索结果后更换查询，看到了参数错误后纠正字段名。两处反馈循环由实际模型响应驱动，不是前端动画。

原始本机文件：

- `data/agent-runs/29577ba7-03ac-422c-9f4a-27b013778e59/trace.json`
- 同目录 `analysis.json`、`search-1.json`、`search-2.json`、`messages.json`、`report.json`
- `data/acceptance/agent-live.json`：浏览器验收时读取的 API 快照
- `data/screenshots/agent-live.png`、`agent-mobile.png`：实际页面截图

完整产物保留本机，不纳入公开 Git；另提供[真实调用记录节选](../demo/recorded-agent-trace.json)，省略论文摘要和重复字段详情，明确标注为历史记录，不用作运行时替代输出。

## 质量问题仍然存在

最初 CLI 运行 `a5d35ce9-84b7-416f-a2ba-b3f846e5813d` 把 `ca` 误读成钙化血管数，进而改变了检索词。依据 [UCI 字段说明](https://archive.ics.uci.edu/dataset/45/heart+disease)，已经在数据字典和提示中明确其为透视检查中显影的主要血管数。原错例未删除，页面单独展示开发时复核意见。

第二次网页运行纠正了 `ca`，但仍有不能接受为科研结论的地方：

- 模型把 thallium-201 写为“钍-201”；应为铊-201，存在专业术语翻译错误。
- 文献中的 ST/HR slope 和 UCI 的 `slope`（运动峰值 ST 段斜率类别）不是同一测量。不能仅因名称相似就认定论文直接支持该特征。
- [PMID 17964962](https://pubmed.ncbi.nlm.nih.gov/17964962/) 讨论特定女性样本，[PMID 9605049](https://pubmed.ncbi.nlm.nih.gov/9605049/) 讨论使用地高辛的患者。样本人群、检查与本数据的适用关系未建立。

以上为开发时逐项阅读后的复核，不是当前程序已具备的自动语义判断能力。已写入独立的 engineering-review.json，保留原始模型输出。页面将草稿与 Python 数字分开显示，不把引用身份校验说成科学支持校验。

## 验证方法及其边界

- 真实浏览器操作已完成：点击启动、实时事件、实际报告、刷新恢复与手机宽度检查。该测试显式使用本机模型及 PubMed；默认 CI 不调用模型或外部科学 API。
- 离线控制测试验证：未知工具被拒绝、错误回传后可纠正、伪造 PMID 不能提交、无文献时不补引用、循环预算生效、截断调用不执行。
- 原有固定分析入口也需回归，避免新 Agent 破坏已可用的计算路径。

复跑命令：

```bash
uv run pytest -q
npm --prefix frontend run build
./scripts/start.sh
# 另一终端，已有 Ollama 模型与公开数据：
cd frontend
RUN_AGENT_E2E=1 npx playwright test e2e/agent.spec.ts
```

下一验收标准：主张结构化；给出原文片段；区分测量、人群、结局是否匹配；有证据缺口时明确拒绝“支持”标签。在这之前，仅将当前版本作为可检查执行过程的 Agent 原型。
