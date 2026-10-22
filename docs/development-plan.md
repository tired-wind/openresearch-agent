# Delivery plan

Time zone: Asia/Singapore. Official deadline Oct 28 07:45; aim to submit Oct 27 18:00. One functioning vertical slice takes priority over added agents.

| Milestone | Date | Acceptance / status |
|---|---|---|
| 0 Audit | Oct 22 | Public rules/environment verified; resource access BLOCKED. Three audit docs written. |
| 1 Vertical slice | Oct 22 | CSV/XLSX upload, quality checks, split-safe model, permutation importance, persisted report; implement and test now. |
| 2 Literature | Oct 22–23 | Real PubMed records, stable IDs, explicit abstract-only uncertainty; no inferred support from title alone. |
| 3 Orchestration | Oct 23–24 | Persisted finite stage machine and critic; bounded operations. Provider-driven semantics conditional on verified access. |
| 4 Sponsors | Oct 23–25 | Mandatory Zetaris + Meterless live connectivity, adapters, regression tests, demonstrable value; Cursor contribution evidenced. BLOCKED credentials/contracts. |
| 5 Product | Oct 24–26 | Responsive workspace, execution trace, metrics, factors, literature and report export. |
| 6 Submission | Oct 26–27 | Full tests, browser walkthrough, GitHub repo, 1–4 min video, slides, sponsor evidence and final rules check. |

## Decision log

- Implement deterministic parameterized tools before any LLM integration; no arbitrary generated Python.
- Use explicit stage state and SQLite, without LangGraph initially: sequential bounded tasks do not justify another orchestration dependency.
- Next.js/TypeScript frontend + FastAPI/Pydantic + pandas/sklearn. Plain CSS minimizes setup; Tailwind is optional.
- Local predictor supports independent-row classification/regression only. Grouped or temporal data require a later split strategy and are flagged.
- Retrieved papers are candidates; automated support/contradiction is deferred until actual evidence review exists.
- Do not claim multi-LLM-agent autonomy, sponsor compliance or clinical validity from this initial deterministic build.

## Next concrete actions

Finish local vertical slice; execute automated integration and leakage/input tests; run actual API and frontend; persist a demo report. In parallel with user login, resolve sponsor resource documentation. Update test evidence here after execution.

## Milestone update — Oct 22

M0 public/environment audits complete; authenticated resources remain BLOCKED. M1 complete and tested. M2 real PubMed retrieval and provenance complete; semantic support/contradiction assessment pending. M3 deterministic bounded stage machine/critic complete; multi-LLM orchestration pending verified provider access. M5 initial responsive workspace, trace, results and export complete. M4 sponsor integrations BLOCKED. M6 test suite/build/browser flow complete for this slice; submission assets not complete.

Observed results: 15 backend tests passed; frontend build passed; 1 browser E2E passed; separate live API+PubMed run completed. See test-results.md. Next task: obtain non-secret authenticated resource contents, verify Zetaris tenant contract and Meterless runtime, implement genuine sponsor use and a grounded semantic review layer. Do not claim readiness to submit yet.

## GitHub collaboration update — Oct 22

Created private repository https://github.com/tired-wind/openresearch-agent for source collaboration. Added clone/branch/PR guidance to the README. Excluded local datasets, run artifacts, secrets and dependencies. Collaborator invitations and branch protection are not configured. This does not resolve sponsor or submission requirements.
