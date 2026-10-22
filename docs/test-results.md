# Observed validation — 2026-10-22

## Automated tests

- `uv run pytest -q`: **15 passed**, 10.78 s. Real sklearn classification/regression, leakage exclusion, duplicate handling, malformed CSV, XLSX/formula/zip expansion, rare targets, actual subprocess/API/export flow, browser-origin/input rejection, retrieved-record parsing and explicit retrieval failures.
- First run: 3 failed / 12 passed due to numeric-looking string labels in current sklearn class weighting. Fixed using a training-fitted LabelEncoder and returning the original positive class; rerun above passed.
- One non-failing warning: Starlette's httpx-based TestClient is deprecated in the installed version. It does not invalidate these tests; plan migration if dependency updates require it.
- `npm run build`: **passed** with Next.js 16.4.2; production compilation, TypeScript checking and static page generation.
- `npx playwright test`: **1 passed**, 18.4 s using installed Google Chrome. Actual browser → API → subprocess → report; verifies target_copy exclusion, uncertainty labels, Markdown download, no JS exceptions and 390px layout without horizontal overflow. Desktop/mobile screenshots under ignored data/screenshots/.

## Live network + application run

Run `a8d7de8d-b625-4007-a179-5b3617fa6192` completed_with_warnings using the actual API and actual PubMed network requests. Synthetic rows: 320; train 240/test 80. Computed balanced accuracy 0.6422578185, baseline 0.5, F1 macro 0.6296296296, ROC-AUC 0.7765064836, average precision 0.6959807460. These are engineering fixture results, not clinical performance.

Five records fetched with abstracts: PMIDs 42882228, 42858823, 42854088, 42799450, 42747589. Candidate relevance and support remain uncertain. Full result: local data/demo-run.json. Human-readable exported artifact: docs/demo-report.md.

## Remaining unverified

Sponsor connectivity, LLM calls, authenticated resource contents, clinical applicability, semantic support/contradiction, public deployment security, multi-user/concurrent access, recovery across host shutdown, final video/slides and submission. Offline HTTP fixtures are used only in parser/failure tests and are not represented as live retrieval.
