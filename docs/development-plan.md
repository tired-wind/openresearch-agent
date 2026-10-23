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

## Initial next actions (superseded by the updates below)

Finish local vertical slice; execute automated integration and leakage/input tests; run actual API and frontend; persist a demo report. In parallel with user login, resolve sponsor resource documentation. Update test evidence here after execution.

## Milestone update — Oct 22

M0 public/environment audits complete; authenticated resources remain BLOCKED. M1 complete and tested. M2 real PubMed retrieval and provenance complete; semantic support/contradiction assessment pending. M3 deterministic bounded stage machine/critic complete; multi-LLM orchestration pending verified provider access. M5 initial responsive workspace, trace, results and export complete. M4 sponsor integrations BLOCKED. M6 test suite/build/browser flow complete for this slice; submission assets not complete.

Observed results: 15 backend tests passed; frontend build passed; 1 browser E2E passed; separate live API+PubMed run completed. See test-results.md. Next task: obtain non-secret authenticated resource contents, verify Zetaris tenant contract and Meterless runtime, implement genuine sponsor use and a grounded semantic review layer. Do not claim readiness to submit yet.

## GitHub collaboration update — Oct 22

Created private repository https://github.com/tired-wind/openresearch-agent for source collaboration. Added clone/branch/PR guidance to the README. Excluded local datasets, run artifacts, secrets and dependencies. Collaborator invitations and branch protection are not configured. This does not resolve sponsor or submission requirements.

## Current management and public-data update — Oct 22

Live audit now confirms the repository is public; preserved its current visibility. Sent `znh3012107` a write-access invitation. The user requested sole-maintainer delivery, so no dependency or compulsory review is assigned to the friend.

Enabled main protection: PR required, `verify` status required with strict branch freshness, conversations resolved, no force push/delete, administrators included, zero required external approvals. Configured squash merging and automatic merged-branch deletion. Added CI, PR/Issue templates and Chinese CONTRIBUTING guide. Actual CI execution is recorded in the setup PR; local checks passed (18 pytest, frontend build, 1 browser workflow).

Created six scoped Issues and a milestone due Oct 27 10:00 UTC (18:00 Singapore). Credentials/access remain the external blocker in #1. Ready tasks represent work that can begin with local contracts; full semantic/provider completion still depends on #1. This is a maintained backlog, not an unattended scheduling service.

Downloaded licensed UCI Cleveland and WDBC, added checksum-pinned preparation and API smoke scripts, and verified both through report export. See data-source-audit.md and public-data-validation.md. UK Biobank new applications are paused; NHANES needs survey-aware methods. No restricted data or paid service was acquired.

Next concrete implementation: #2 typed research plan and dataset semantics, followed by #3 claim-to-evidence records and bounded verification. Prioritize the real evidence chain and mandatory sponsor connectivity over additional agent roles or larger datasets. User intervention is limited to unavailable authenticated resources, real Cursor participation and final submission.

## Reviewable Chinese product increment — Oct 22

Implemented typed rule-based plan preview, unsupported-design/purpose gates, data/request fingerprints, checksum-identified examples and curated field labels. Added computed claim records with literal abstract anchors and tamper rejection, a Chinese interface, run history and refresh recovery. Updated exports and product acceptance instructions. These deliver concrete portions of #2, #3, #4 and #5; they do not complete provider-driven reasoning or scientific support assessment.

Verified: 46 backend tests, production frontend build, 3 local browser tests (including live UCI), and a live PubMed/API run with 4 retrieved publications and 15 verified snippet locations. See product-acceptance.md. Conventional CI intentionally excludes live UCI/PubMed reliance; its 2 browser checks are distinct from the live tests.

Next: verify sponsor/runtime contracts (#1), then implement constrained semantic proposals and population/exposure/outcome comparison. Preserve the current working examples and explicit uncertainty while doing so. Do not close the full planning/evidence issues merely because the deterministic substrate is ready.


## Agent runtime correction — 2026-10-23

The user correctly identified that stage labels and test counts did not demonstrate an Agent. Studied PilotDeck AgentLoop and OpenWorker Engine/ProviderClient source, then implemented a separate LangGraph + native Ollama runtime with five allowlisted research tools, event records, bounded model/tool feedback, public-data checks and an interactive `/agent` page. Kept the existing deterministic analysis as the reliable computation layer.

Real CLI and browser runs now exist. The first exposed a scientific field-meaning error; preserved it with an explicit engineering review. The second demonstrated search refinement after an empty result and correction after rejected feature names. Model prose remains an unverified draft. See agent-acceptance.md for actual calls and limitations, not just test totals.

Next priority: structured claim/source assessment, semantic field and population matching, and a reproducible evaluation set with expected refusal/uncertainty outcomes. Full #2 and #3 remain open. Sponsors and competition compliance are still blocked separately; the local Agent is not a sponsor integration.

Validation completed for this increment: backend control/API/analysis regressions passed (53 tests); frontend production build passed; default browser checks passed (3, with 2 live checks deliberately skipped); the separately enabled real Agent browser flow passed. The latter observed a real model correcting a rejected submission. Scientific interpretation defects remain documented and open.


## Two-person handoff review — 2026-10-23

Reviewed znh3012107's pushed znh/dev branch and Windows development log; no PR existed at inspection. Preserved the branch and assembled integrate/znh-sponsor-adapters from its commits. Added explicit CLI provider/env-file/memory selection, web-worker dotenv isolation, model identity/truncation rejection, conservative SQL checks, and a beginner GitHub collaboration guide. Contributor Windows service runs remain reported evidence, not maintainer Mac reproductions or full competition compliance. No cloud inference, Docker install or model download was performed in this review. Dashboard sponsor configuration and actual Zetaris analysis input remain open.
