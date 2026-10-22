# 公开数据实际验证记录

日期：2026-10-22；VERIFIED 本地 FastAPI + 独立 worker + SQLite + Markdown 报告导出。聚合机器可读结果见 [public-data-results.json](public-data-results.json)。原始行、详细切分和报告留在忽略的 `data/public/` 和 `data/runs/`。

| 案例 | 分析行数 | 训练 / 留出测试 | Balanced accuracy | ROC AUC | 结果 |
|---|---:|---:|---:|---:|---|
| UCI Cleveland | 303 | 227 / 76 | 0.847387 | 0.936585 | completed_with_warnings；报告已导出 |
| UCI WDBC | 569 | 426 / 143 | 0.956709 | 0.997484 | completed_with_warnings；报告已导出 |

两者 majority baseline balanced accuracy 均为 0.5。固定 seed=42；没有根据留出集反复选模型。三折训练 CV、训练内填补/编码、100 棵树随机森林、留出集 8 次置换；方法细节以 backend/analysis.py 为准。仅为本次历史样本的工程验收，不能解释为临床准确率、外部泛化或因果发现。

本轮外部文献查询关闭，结论没有被文献验证。API 记录仍标记为 `user_upload`，公开来源信息保存在下载 manifest 中；界面尚未自动导入数据字典或 manifest，下一步需补充该产品能力。

## 质量观察

- Cleveland：目标 0=164、1=139；`ca` 缺失 4、`thal` 缺失 2。原始 `num` 已从特征中移除；七个分类字段以字符串编码。
- WDBC：B=357、M=212；没有缺失值；ID 已移除。形态特征之间存在关联，重要性不代表独立机制。
- 源 zip 使用固定 SHA-256 校验；报告里的输入 SHA-256 与准备后的 CSV 实际内容一致。

## 执行记录

```bash
uv run --frozen python scripts/fetch_public_data.py all
uv run --frozen pytest -q
npm --prefix frontend run build
./scripts/start.sh
# 第二终端
uv run --frozen python -m scripts.smoke_public_data
cd frontend
npx playwright test
```

结果：18 项 pytest 通过（8.38 秒），前端构建通过，1 项浏览器 E2E 通过（11.4 秒）。pytest 有一条 Starlette/httpx 弃用警告，未造成失败；没有以此宣称零警告。浏览器流程使用合成数据；两个真实公开数据案例通过 API 检查。GitHub CI 的最终结果以 PR 的 Checks 记录为准。
