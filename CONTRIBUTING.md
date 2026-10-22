# 开发与维护约定

本项目由维护者统一推进实现、验证、合并和交付。朋友按需参与，不作为关键路径或必需审核人。Codex 在本会话执行获授权的工作，不代表无人值守的持续运行服务。

## 最短工作流程

1. 在 [Issues](https://github.com/tired-wind/openresearch-agent/issues) 选一个任务，确认验收条件。一次只推进一个主要任务。
2. 从最新 `main` 建分支，如 `feat/2-analysis-plan`。已有未提交修改先保存，禁止用 reset/force-push 覆盖别人的工作。
3. 实现小而完整的改动，写明实际测试结果，再提交 PR。
4. CI 必须通过；维护者检查 diff、数据边界和验收条件后 squash merge。无需等待朋友批准。
5. 只有验收完成才关闭 Issue；外部依赖失败标记 blocked，不能靠模拟结果通过验收。

任务流：`status:ready` → `status:in-progress` → `status:review` → Closed；受阻时使用 `status:blocked`，同一任务只保留一个状态标签。标签和状态需在工作时更新，未配置自动调度机器人。

## 分支保护目标与边界

`main` 要求 PR、`verify` 检查通过且分支跟上 main、对话已解决；禁止强推和删除，管理员同样受规则约束。PR 必需批准人数为 0，以允许单维护者推进。此设置保留审查记录，但不等于独立人工同行审查。实际启用状态以 GitHub Settings → Branches 为准。

仓库当前公开；代码公开不等于已经选择开源许可证。未经用户决定，不添加项目级授权许可证。外部数据保留各自许可证和署名要求。

## 本地验证

```bash
uv sync --frozen --python 3.12
uv run --frozen pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
./scripts/start.sh
# 第二个终端，macOS 本地使用已安装的 Chrome：
cd frontend
npx playwright test
```

CI 使用 Ubuntu、Python 3.12、Node 24 和 Playwright Chromium；不依赖本机 Chrome、付费 API 或真实患者数据。端到端检查使用明确标记的合成数据。公开数据联网下载和真实赞助商连接是单独的验收证据，不伪装成每次 CI 都验证过。

## 证据与凭据

- 统计值只能来自工具结果；文献必须能追溯到真实检索记录。
- 不把相关、预测重要性和因果效应混用；方法不适用时明确拒绝或解释。
- 不提交 `.env`、密钥、原始患者明细、`data/` 或模型大文件。下载脚本、哈希和聚合验证结果可提交。
- GitHub Issue/PR 中只放非敏感复现信息；服务凭据在本地设置。
- 不在公开 CI 开放远程付费服务调用，不运行不可信文本生成的代码。

## 每次交付汇报

说明完成的行为、实际测试、仍未解决的阻塞、下一个具体任务。维护者负责记录；用户只需处理必须本人操作的登录、付费决定、Cursor 开发和最终参赛提交。
