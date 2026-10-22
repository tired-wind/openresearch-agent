# Rules compliance audit

Audited 2026-10-22 (Asia/Singapore). Labels: VERIFIED = primary source checked; UNVERIFIED = not established; BLOCKED = requires access or action.

Source: https://hackathon.genai.works/event/open-agent-hackathon-2026#rules . Expanded sections were read from the public HTML's serialized Next.js data; the initial rendered page only exposed section 1. Extraction and HTML digest: `rules-source.json`.

| Topic | Status | Finding / project action |
|---|---|---|
| Eligibility | VERIFIED | Worldwide, age 16+, one account; organizer/judging-sponsor employees cannot win cash. User eligibility/registration remains UNVERIFIED. |
| Team | VERIFIED | 1–5 people, one team per person; membership locks at first submission. |
| Track | VERIFIED | Exactly one primary track; choose Track 02. |
| Build window | VERIFIED | 2026-10-22 00:00 UTC through 2026-10-27 23:45 UTC. Pre-window components must be disclosed. |
| Reuse / AI code | VERIFIED | Open-source libraries and generated code permitted; disclose existing product code. Fresh application here; no previous project code copied. |
| Models / paid APIs | VERIFIED | Closed-source APIs allowed. Permission to use does not establish credits or payment authorization. |
| Mandatory technology | VERIFIED | Both Zetaris and Meterless required; Cursor development required. NVIDIA use encouraged where useful. |
| Submission assets | VERIFIED | GitHub source + setup README; 1–4 minute video; slide deck; explain sponsor use, Cursor use and NVIDIA contribution. |
| Deployment / repo visibility | UNVERIFIED | No explicit hosted-deployment or public-versus-private repository requirement in inspected sections; check authenticated submission form. |
| IP | VERIFIED | Builder retains ownership; submission grants promotional use of demo/screenshots/description to organizer and relevant sponsor. |
| Judging | VERIFIED | Impact 30, technical 20, innovation 15, demo 15, UX 10, sponsor 10; >=3 judges; tie-break impact then submission time. |

Deadline: **2026-10-28 07:45 Singapore time**. Registration closes **2026-10-23 07:59 Singapore time**. Internal submission target: Oct 27 18:00 SGT.

## Submission gates

- BLOCKED: Zetaris authenticated API and actual integration.
- BLOCKED: Meterless integration must be implemented and demonstrated; public source access alone does not count.
- BLOCKED: actual Cursor development not evidenced (Cursor.app not found at standard path).
- UNVERIFIED: registration, team, eligibility, authenticated resources and submission form fields.
- VERIFIED: private GitHub collaboration repository created at https://github.com/tired-wind/openresearch-agent . Final visibility requirements remain UNVERIFIED; video and slides are not yet prepared.

A functioning local analysis pipeline is not yet a competition-compliant submission. Recheck rules before submission; organizers may update them. Do not describe Codex work as Cursor work.
