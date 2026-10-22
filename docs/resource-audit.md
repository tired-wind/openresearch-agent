# Resource audit

Audit date: 2026-10-22, Singapore. VERIFIED / UNVERIFIED / BLOCKED refer separately to documentation and usable access.

## Authenticated event resources

https://hackathon.genai.works/resources returned HTTP 307 to `/sign-in?next=%2Fresources` using unauthenticated HTTP. User reports logging in inside the app. The current toolset cannot read that browser session; browser cookies were not extracted. **BLOCKED:** authenticated resource inventory. Minimum action: supply non-secret page text/screenshots or documentation links. Never share keys in chat; use ignored local `.env`.

The public event HTML lists NVIDIA, Zetaris, SpaceX AI (links to x.ai), and Meterless. Rules also require Cursor development. Hackathon credit quantities, redemption, expiration, workshop schedule and support entitlements remain **UNVERIFIED**. Public event promises resources/workshops/support but no usable allocations were established.

| Resource / official documentation | Intended role / interface | Auth and credits / limits | Complexity / relevance / access |
|---|---|---|---|
| Zetaris: https://kbase.zetaris.com/knowledge/overview-of-connecting-to-zetaris ; https://kbase.zetaris.com/knowledge/zetaris-api-release | VERIFIED query/federation platform; JDBC, ODBC, REST documented. Detailed API documentation links require access. | Tenant, endpoint, auth contract, credits and rate limits UNVERIFIED. | Medium/high; meaningful dataset query + provenance. BLOCKED connectivity. Do not invent SQL/API endpoints. |
| Meterless: https://github.com/Meterless/Meterless ; https://meterless.ai/ ; https://www.meterless.ai/engines.html | VERIFIED public context/memory engines and Nightshift. Website describes OpenAI-compatible local service; illustrative address is not our endpoint. | Public repository readable without auth. Actual Nightshift installation, configured models, credits and limits UNVERIFIED. Cloud models use user-supplied paid-provider keys. | Medium; memory/evidence continuity or model serving. Source accessible; runtime UNVERIFIED. No large model downloads approved. |
| NVIDIA Nemotron: https://developer.nvidia.com/topics/ai/Nemotron ; https://nvidia.github.io/NeMo-Retriever/extraction/api-keys/ | VERIFIED models and hosted NIM authentication documentation; potential structured planner/critic. | NVIDIA build key for hosted calls; NGC key is distinct. No key detected. Hackathon allocation/rate limits UNVERIFIED. | Low/medium for hosted adapter once model contract/access verified; BLOCKED live use. Local CUDA deployment unsuitable for this Mac. |
| NVIDIA compute / NIM: https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html | VERIFIED self-hosted GPU runtime documentation. | GPU access/credits UNVERIFIED. | High; avoid local NVIDIA runtime on ARM Mac. |
| SpaceX AI / xAI: https://x.ai/ | VERIFIED sponsor link in event HTML. | API entitlement, credits, SDK/version and quotas UNVERIFIED. | Optional; no implementation planned pending resource access. |
| Cursor: https://cursor.com/ | Required development tool per event rules. | User account/license UNVERIFIED; standard app path absent. | Must use for a real development contribution and document honestly. |
| PubMed: https://www.ncbi.nlm.nih.gov/books/NBK25501/ | Scientific records through NCBI E-utilities. | Public access; no key assumed. Conservative <=2 requests/sec, bounded requests. | Low; selected first literature source; live endpoint test to be recorded. |
| OpenAlex: https://docs.openalex.org/how-to-use-the-api/api-overview | Additional scientific record source. | Documentation redirect inaccessible in web tool; current key/quota policy UNVERIFIED. | Deferred until policy/API access verified. |

## Credentials and integration decision

Only credential **names/presence** checked in the inherited process. `DEEPSEEK_API_KEY` present; validity, balance, model access UNVERIFIED. No Zetaris, Meterless, NVIDIA or NGC credential variables detected. No paid call made; no unrelated secret files inspected.

Recommended sponsor path, conditional on access: Zetaris supplies an explicitly selected read-only research table with query provenance; Meterless provides persistent research context or a verified inference service; optional NVIDIA Nemotron performs structured planning/critique. These are design proposals, not completed integrations. Local deterministic analysis remains available with explicit no-LLM status; no silent fake responses.

Meterless's engine landing page contains dates different from the event page; use the event page for the deadline. Do not treat website marketing examples as tested endpoints.

## Follow-up verification

- VERIFIED live PubMed ESearch and EFetch on 2026-10-22: five real records with abstracts; see test-results.md. No API key or paid call used.
- VERIFIED Meterless H-MEM docs at https://github.com/Meterless/Meterless/blob/main/docs/engines/hmem.md and https://github.com/Meterless/Meterless/blob/main/engines/hmem/reference/README.md : implementation specification plus an explicitly non-production TypeScript reference. Reference uses mock hash embeddings and no network. It is not a ready hosted inference SDK. Do not count reading this source or copying a hash mock as a completed sponsor integration. Actual Nightshift access and hackathon-approved integration expectations remain pending.
