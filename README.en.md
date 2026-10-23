> **2026-10-23 update:** A separate experimental `/agent` page now runs a real **LangGraph + Ollama / Qwen3.5 4B** tool loop over two verified public examples. The default workspace below remains deterministic. The local model chooses searches and tools; free-text interpretations remain unverified drafts. This is one agent, not a multi-agent scientific review system. See [engineering](docs/agent-engineering.md) and [observed demo](docs/agent-acceptance.md).

# OpenResearch Agent

[中文 README](README.md) · [GitHub repository](https://github.com/tired-wind/openresearch-agent)

**An Evidence-Grounded Multi-Agent Research System — local MVP foundation**

A research workspace for analysts who need to connect a tabular predictive analysis to inspectable computations and real literature records. The current build delivers a working deterministic vertical slice, not yet an autonomous multi-LLM system or a competition-compliant submission.

## What works now

- Upload UTF-8 CSV or values-only XLSX; inspect schema, missingness and duplicates.
- Explicit target and classification/regression selection; bounded execution plan and six visible workflow stages.
- Train-only imputation/encoding; training-set three-fold CV, 25% holdout, dummy baseline, appropriate metrics and permutation importance.
- Exclude identifiers, constants and simple target proxies; report remaining leakage risks.
- Opt-in real PubMed search and abstract retrieval; source IDs, URLs, access scope and uncertainty retained. No fabricated support/contradiction labels.
- SQLite execution state; immutable-by-convention run artifacts; Markdown report and JSON evidence export.
- Responsive Next.js dashboard, real backend subprocess execution, explicit failures and timeouts.

The natural-language question provides report context; it does not yet drive LLM planning or automatically select the target. The user explicitly selects target, task and literature query. Planner/critic are deterministic components. `backend/providers.py` defines an extension contract only; the separate `backend/agent_runtime.py` now implements a live local Ollama adapter.

## Quick start

Clone `tired-wind/openresearch-agent` after accepting a collaborator invitation, then run the commands below from its root.

Requirements: Python 3.12, uv, Node 24 and npm. No GPU, Docker, model weights or API keys needed for the local demo.

```bash
uv sync --frozen --python 3.12
npm --prefix frontend ci
npm --prefix frontend run build
./scripts/start.sh
```

Open http://127.0.0.1:3018 . API docs: http://127.0.0.1:8018/docs . Both bind to loopback. `Ctrl-C` stops the launcher and its children. Existing processes on these ports are not killed. Development: use `uv run uvicorn backend.app:app --host 127.0.0.1 --port 8018` and, in another terminal, `npm --prefix frontend run dev`.

Optional configuration: copy `.env.example` to `.env`. The launcher loads it through `uv run --env-file .env`. Keep secrets local; no credential is currently used by the analysis worker. `OPENRESEARCH_DATA_DIR` chooses local storage. Sponsor endpoints are intentionally absent until verified.

## Run the demo

1. Choose **心脏病公开案例 · 303 行** (verified UCI) or **使用合成数据演示** (synthetic); the target is selected automatically.
2. Review source and variable definitions, then confirm independent observations.
3. Optionally enable PubMed and review the public search text. Only that query is sent externally.
4. Click **预览分析方案** (preview), then **确认方案并开始分析** (confirm and run). Unsupported purposes/designs are blocked. Expand claim cards, inspect snippets, refresh to restore the report, and export evidence.

The 320-row synthetic fixture deliberately includes `target_copy` and `participant_id` to demonstrate exclusion. It is CC0 and regenerated with `uv run python scripts/generate_demo.py`. Its coefficients and labels are invented for engineering tests; no clinical finding follows from them. A real executed example is in [docs/demo-report.md](docs/demo-report.md).

## Architecture and workflow

Next.js/TypeScript → FastAPI/Pydantic → one bounded Python worker → pandas/scikit-learn + opt-in PubMed → deterministic critic → persisted report. SQLite stores states; local files store uploads/artifacts. Stages: planner → data → model → literature → critic → report. No Redis, vector database or distributed queue. See [architecture](docs/architecture.md).

## Sponsor status and rules

**Not yet submission-compliant.** Verified rules require both Zetaris and Meterless integrations and Cursor development, plus GitHub source, a 1–4 minute video and slides. NVIDIA integration is encouraged where useful. No sponsor runtime integration is claimed; local Ollama inference is demonstrated separately. User reports Resources login, but current tools cannot read that authenticated session. Meterless H-MEM's public reference is explicitly a deterministic prototype with mock hash embeddings; it has not been presented as real inference or integrated here.

See [resource audit](docs/resource-audit.md), [rules compliance](docs/rules-compliance.md), [environment audit](docs/environment-audit.md), [delivery plan](docs/development-plan.md) and [submission checklist](docs/submission-checklist.md).

## Validation

```bash
uv run pytest -q
npm --prefix frontend run build
# Start both servers first; uses installed Google Chrome, no browser download.
cd frontend && npx playwright test
```

Observed on Oct 22 after the public-data update: 46 backend tests passed; Next.js production build/typecheck passed; three local browser workflows passed (two offline CI cases plus one explicitly enabled live UCI case), including desktop/mobile layout, actual analysis and report download. Separate live network smoke retrieved 5 PubMed abstracts and completed a report. Offline tests use clearly scoped HTTP fixtures for failure/record parsing; the live smoke is independent. See [test evidence](docs/test-results.md).

## Limits and data handling

- Local single-user prototype; **do not expose publicly**. No account authentication, authorization, tenant isolation, automated retention or hardened upload gateway yet.
- Files: <=5 MiB, <=5,000 rows, <=60 columns; first XLSX sheet only, no formulas/external links. At least 60 usable distinct rows for modeling; classification 2–10 classes, >=8 rows/class.
- Only independent observations. No temporal/grouped validation, external validation, hyperparameter search, causal inference, significance testing or clinical decision support.
- Holdout rankings are exploratory; correlated features and small samples can distort importance. Shuffle SD is not a CI. Feature screening occurs on outer training data; training CV is conditional on that screen, while holdout remains separate.
- Source existence is checked via retrieval; semantic relevance, support and contradiction are not automatically established. Full text is not fetched. Network failure is explicit and never replaced with fake citations.
- Question, schema, raw uploads and run outputs stay under ignored `data/`; only an opt-in literature query leaves the machine. No arbitrary LLM-generated code executes. Model credentials are removed from worker environment.
- One worker at a time, up to four active/queued jobs, 150-second subprocess deadline. Server restart marks unfinished jobs failed; no automatic resume. Refreshing the UI restores the remembered run; local history lists the latest 20 runs. Unfinished computation is not resumed after a server restart.
- No previous product code copied. Standard libraries are reused with locked versions in `uv.lock` / `package-lock.json`. This repository is separate from the parent personal workspace, which must never be published with it.

Cleanup after stopping servers: delete only this project's `data/` to remove uploads and results. Delete its `.venv/` and `frontend/node_modules/` to remove dependencies; restore them using the commands above. No global packages or models were installed.

## Collaboration

The repository is now public. A write-access invitation has been sent to `znh3012107`; acceptance is pending. The maintainer owns delivery, without depending on a second reviewer. Main requires PRs, the `verify` CI check, an up-to-date branch and resolved conversations; force pushes/deletion are disabled and administrators are included. Required approvals are zero. See [CONTRIBUTING](CONTRIBUTING.md) and the [issue backlog](https://github.com/tired-wind/openresearch-agent/issues). No project-level open-source license has been selected.

## Public data

Run `uv run --frozen python scripts/fetch_public_data.py all` to prepare verified CC BY 4.0 UCI Cleveland (303 rows) and WDBC (569 rows) datasets under ignored `data/public/`. With the application running, `uv run --frozen python -m scripts.smoke_public_data` validates both through the API and report export. Raw data is not committed. See [source audit](docs/data-source-audit.md) and [actual validation](docs/public-data-validation.md). UK Biobank new applications are currently paused; NHANES requires survey-aware methods. Neither is silently substituted into the current independent-row pipeline.

## Chinese product acceptance increment

The main UI now offers verified public examples, typed plan preview with unsupported-scope gates, input fingerprints, expandable computation/abstract evidence cards and history recovery. Literal snippet matches stay unassessed; no semantic support/contradiction or LLM autonomy is claimed. See [product acceptance](docs/product-acceptance.md) for observed tests and the live PubMed run. Main UI/plan/claims are Chinese; the report retains English methodology plus Chinese plan/evidence sections.
