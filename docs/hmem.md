# H-MEM integration

Meterless H-MEM is the **BUILD layer** engine. The event requires at least one
Meterless Engine implemented in a working feature, not merely mentioned. This
document records what was implemented, what was deliberately left out, and the
one place where a default was calibrated instead of copied.

Source spec: `github.com/Meterless/Meterless` → `engines/hmem/AGENTS.md`
(Apache 2.0). H-MEM ships as a specification plus a TypeScript reference, so it
was implemented here in Python rather than installed as a dependency.

## What is implemented

| Spec section | Implementation | Where |
|---|---|---|
| §2 Canonical memory record | `Memory` dataclass with lineage fields; **`source` is mandatory and enforced** | `backend/hmem.py` |
| §3 Tiered storage | `long_term` and `working` persist to JSON; `short_term` is session-only; embeddings backfilled on load | `MemoryStore` |
| §5 Enrichment | tags, domain, namespace, entities (cap 10), relatedTo (cap 5), supersedes | `MemoryStore.add` |
| §6.1 Hybrid ranking | the exact eight-signal formula and weights | `score_memory` |
| §6.2 Reinjection | domain-grouped blocks with layer markers + `retrievalReason`, per-memory score, strategy label | `retrieve`, `render_context` |
| §9.1 Trust ledger | append-only JSONL, all 17 canonical action types validated | `TrustLedger` |
| §9.2 Feedback deltas | helpful +0.05/+1 access, not_helpful −0.03, wrong −0.20 + `review` tag | `MemoryStore.feedback` |
| §4.3 No-model fallback | direct capture as a short-term memory instead of dropping content | `capture_session_summary` |
| §4 Mining for this domain | one finished investigation becomes one long-term factual memory | `mine_report` |

Ranking is implemented term by term:

```text
raw   = 0.35·semantic + 0.20·keyword + 0.10·tag + 0.10·domain
      + 0.15·entity   + 0.05·layer   + 0.05·recency − 0.20·superseded
score = clamp01(raw) × confidence
```

`tests/test_hmem.py` asserts that `score` equals that arithmetic exactly, so the
weights cannot drift from the spec unnoticed.

## Deliberately not implemented

Dreaming (§7), the sleep cycle (§8) and conflict resolution (§10) are opt-in
stages in the spec. They are out of scope for the event build window and are
**not claimed** here. Records still carry `supersededBy`, and the ranker already
applies the −0.20 penalty, so a later conflict resolver has somewhere to write.

## The one calibrated default

The spec's gate is `0.35` on the **final** score, which assumes a neural
embedder: a genuine semantic match lands near `0.7` on the semantic signal.

This build uses a deterministic lexical embedding (`embed()`: term frequencies
over Latin words plus CJK characters and bigrams). It is honest about not being
model inference, and it tops out near `0.45` on short Chinese queries. At a
`0.35` gate a genuinely relevant memory scored `0.3175` and was silently dropped.

So `LEXICAL_RETRIEVAL_THRESHOLD = 0.28` is used by default, with the reason in
the code, while `RETRIEVAL_THRESHOLD = 0.35` remains the spec reference:

```python
retrieve(store, query)                                    # calibrated, 0.28
retrieve(store, query, threshold=RETRIEVAL_THRESHOLD)     # spec gate, 0.35
```

`tests/test_hmem.py::test_spec_threshold_is_stricter_than_the_lexical_calibration`
pins both. If a neural embedder is wired in later, drop the calibration and pass
the spec gate.

## Wiring into the research loop

`backend/agent_runtime.py` gained:

- `NightshiftProvider` — the `Provider` protocol implemented against the local
  Nightshift runtime (OpenAI tool-calling translated to this runtime's
  Ollama-shaped history, with stable tool-call ids).
- `ResearchSession(..., memory=store)` — before the model runs, `recalled()`
  retrieves context and prepends it to the system prompt; after
  `finish_investigation`, the report is mined into long-term memory.

Two trace events make the memory auditable in `trace.json`:

- `memory_retrieved` — strategy, gate, query domain, per-memory score and
  `retrievalReason`
- `memory_written` — memory id, layer, tags, source

## Verify

```bash
python scripts/check_hmem.py     # two-session recall, provenance, ledger, negative control
python -m pytest tests/test_hmem.py -q
python scripts/run_agent.py --example heart --provider nightshift
```

`run_agent.py` writes a trace containing `memory_retrieved` on the second run
against the same `--memory-dir`, which is the cross-session evidence.

## Known limits

- Lexical embeddings cannot generalise: a reworded question may score below the
  gate where a neural embedder would match. This is a stated limitation, not a
  hidden one.
- No dreaming, sleep or conflict resolution (see above).
- Short-term memories are intentionally lost on process exit.


## Current opt-in entry point after integration review

Memory requires explicit `--memory-dir data/hmem`. Default CLI and web tasks do not enable it. Example on a machine with an already activated Nightshift service and approved model access:

```bash
uv run python -m scripts.run_agent --example heart --provider nightshift --env-file .env --model <exact-discovered-Nemotron-ID> --memory-dir data/hmem
```

Replace the placeholder, without angle brackets, with the actual discovered model ID. The runtime rejects a response served by a different model. `.env` is loaded only with `--env-file`; web workers forbid that option. Offline check_hmem.py demonstrates mechanics using illustrative inputs and a placeholder PMID, not retrieved scientific evidence or live sponsor/model execution.
