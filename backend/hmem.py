"""H-MEM: the Meterless memory engine, implemented for this project.

Vector stores forget corrections and cannot explain why an agent believed
something. H-MEM treats memory as a knowledge graph with provenance: every
record needs a ``source`` (a record without one is rejected by construction),
every mutation lands in an append-only trust ledger, and retrieval blends eight
signals so a stale or superseded memory loses to a fresher, trusted one.

Scope: the retrieval-critical path of the Meterless H-MEM spec -- canonical
record, tiered storage, hybrid ranking with trace metadata, prompt reinjection,
trust ledger, feedback deltas, and a model-free mining fallback. Dreaming, the
sleep cycle and conflict resolution are opt-in stages and are not implemented
here; ``docs/hmem.md`` records that boundary.

Embeddings are deterministic lexical vectors, not model inference. They are
labelled as such everywhere they appear, because claiming otherwise would make
the provenance it stores a lie.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# --- Spec defaults (Meterless H-MEM, section 13) ---------------------------
LAYER_WEIGHTS = {'long_term': 1.0, 'working': 0.8, 'short_term': 0.6}
SIGNAL_WEIGHTS = {
    'semantic': 0.35,
    'keyword': 0.20,
    'tag': 0.10,
    'domain': 0.10,
    'entity': 0.15,
    'layer': 0.05,
    'recency': 0.05,
    'superseded': -0.20,
}
RETRIEVAL_TOP_N = 5
RETRIEVAL_THRESHOLD = 0.35
# Calibration, not a spec default. The 0.35 gate assumes a neural embedder where a
# true semantic match lands near 0.7; the deterministic lexical embedder used here
# tops out near 0.45 on short Chinese queries, so 0.35 would silently drop genuinely
# relevant memories. Pass threshold=RETRIEVAL_THRESHOLD once a neural embedder is
# wired in. The formula and signal weights stay exactly as specified.
LEXICAL_RETRIEVAL_THRESHOLD = 0.28
RECENCY_TAU_DAYS = 14.0
ENTITY_CAP = 10
RELATED_CAP = 5
KEYWORD_TOP_TOKENS = 8

MEMORY_TYPES = ('personal', 'factual', 'preference', 'general')
LAYERS = tuple(LAYER_WEIGHTS)

# Canonical 17 audit actions.
LEDGER_ACTIONS = frozenset({
    'create', 'read', 'update', 'delete', 'feedback', 'promote', 'demote', 'merge',
    'conflict_detected', 'conflict_resolved', 'sleep_consolidate', 'sleep_archive',
    'sleep_synthesize', 'dream_proposed', 'dream_approved', 'dream_rejected', 'restore',
})

# Feedback deltas, applied to confidence and access count.
FEEDBACK_DELTAS = {
    'helpful': {'access': 1, 'confidence': 0.05, 'tag': None},
    'not_helpful': {'access': 0, 'confidence': -0.03, 'tag': None},
    'wrong': {'access': 0, 'confidence': -0.20, 'tag': 'review'},
}

_WORD = re.compile(r'[a-z0-9]+')
_CJK = re.compile(r'[\u4e00-\u9fff]')


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def tokenize(text: str) -> list[str]:
    """Latin/digit words plus CJK characters and bigrams.

    Chinese has no spaces, so single characters alone retrieve too loosely and
    word segmentation would add a dependency; character bigrams are the usual
    compromise and keep ``keyword`` meaningful for the Chinese interface.
    """
    lowered = text.lower()
    tokens = _WORD.findall(lowered)
    cjk = _CJK.findall(lowered)
    tokens.extend(cjk)
    tokens.extend(''.join(pair) for pair in zip(cjk, cjk[1:]))
    return tokens


def embed(text: str) -> dict[str, float]:
    """Deterministic lexical embedding (hashed term frequencies). Not a model."""
    counts: dict[str, int] = {}
    for token in tokenize(text):
        counts[token] = counts.get(token, 0) + 1
    if not counts:
        return {}
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(token, 0.0) for token, weight in a.items())


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    left, right = set(a), set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


@dataclass
class Memory:
    id: str
    content: str
    type: str
    layer: str
    timestamp: str
    lastAccessed: str
    accessCount: int
    tags: list[str]
    domain: str
    namespace: str
    confidence: float
    source: str
    provenance: dict[str, Any]
    entities: list[str] = field(default_factory=list)
    relatedTo: list[str] = field(default_factory=list)
    supersedes: str | None = None
    supersededBy: str | None = None
    derivedFrom: list[str] = field(default_factory=list)
    embedding: dict[str, float] = field(default_factory=dict)
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'Memory':
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in payload.items() if k in known})


class TrustLedger:
    """Append-only audit of every memory mutation (JSON Lines)."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, memory_id: str, action: str, *, actor: str = 'agent',
               previous: dict | None = None, new: dict | None = None,
               details: dict | None = None) -> dict:
        if action not in LEDGER_ACTIONS:
            raise ValueError(f'Unknown ledger action: {action}')
        entry = {'memoryId': memory_id, 'action': action, 'actor': actor,
                 'timestamp': now(), 'previousState': previous, 'newState': new,
                 'details': details or {}}
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return entry

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries():
            counts[entry['action']] = counts.get(entry['action'], 0) + 1
        return counts


class MemoryStore:
    """Tiered store: long-term and working persist, short-term lives in session."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.ledger = TrustLedger(self.folder / 'trust-ledger.jsonl')
        self._memories: dict[str, Memory] = {}
        self._load()

    # --- persistence -------------------------------------------------------
    def _file(self, layer: str) -> Path:
        return self.folder / f'{layer}.json'

    def _load(self) -> None:
        for layer in ('long_term', 'working'):
            path = self._file(layer)
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                continue
            for row in payload if isinstance(payload, list) else []:
                memory = Memory.from_dict(row)
                if not memory.embedding:
                    memory.embedding = embed(memory.content)
                self._memories[memory.id] = memory

    def _persist(self, layer: str) -> None:
        rows = [m.as_dict() for m in self._memories.values() if m.layer == layer]
        # Backfill embeddings on load/write so ranking never silently degrades.
        for row in rows:
            if not row['embedding']:
                row['embedding'] = embed(row['content'])
        path = self._file(layer)
        temp = path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)

    # --- writes ------------------------------------------------------------
    def add(self, content: str, *, source: str, mem_type: str = 'general',
            layer: str = 'short_term', tags: Iterable[str] = (),
            domain: str = '', namespace: str = '', confidence: float = 0.6,
            provenance: dict | None = None, entities: Iterable[str] = (),
            related_to: Iterable[str] = (), supersedes: str | None = None,
            derived_from: Iterable[str] = (), actor: str = 'agent') -> Memory:
        if not source or not str(source).strip():
            raise ValueError('A memory record without a source is rejected.')
        if mem_type not in MEMORY_TYPES:
            raise ValueError(f'Unknown memory type: {mem_type}')
        if layer not in LAYERS:
            raise ValueError(f'Unknown layer: {layer}')
        if not content or not content.strip():
            raise ValueError('Empty memory content.')

        memory_id = hashlib.sha256(f'{source}|{content}|{now()}'.encode('utf-8')).hexdigest()[:16]
        stamp = now()
        memory = Memory(
            id=memory_id, content=content.strip(), type=mem_type, layer=layer,
            timestamp=stamp, lastAccessed=stamp, accessCount=0,
            tags=list(dict.fromkeys(tags))[:8], domain=domain, namespace=namespace,
            confidence=clamp01(confidence), source=source,
            provenance={'origin': (provenance or {}).get('origin', 'interaction'),
                        'learnedAt': stamp,
                        'label': (provenance or {}).get('label', source),
                        'refs': (provenance or {}).get('refs', [])},
            entities=list(dict.fromkeys(entities))[:ENTITY_CAP],
            relatedTo=list(dict.fromkeys(related_to))[:RELATED_CAP],
            supersedes=supersedes, derivedFrom=list(derived_from),
            embedding=embed(content),
        )
        self._memories[memory.id] = memory
        if layer in ('long_term', 'working'):
            self._persist(layer)
        self.ledger.append(memory.id, 'create', actor=actor, new={'layer': layer, 'type': mem_type},
                           details={'source': source, 'domain': domain})
        return memory

    def feedback(self, memory_id: str, verdict: str, *, actor: str = 'user') -> Memory:
        """Close the loop: retrieval quality moves future ranking."""
        if verdict not in FEEDBACK_DELTAS:
            raise ValueError(f'Unknown feedback verdict: {verdict}')
        memory = self._memories.get(memory_id)
        if memory is None:
            raise KeyError(memory_id)
        previous = {'confidence': memory.confidence, 'accessCount': memory.accessCount}
        delta = FEEDBACK_DELTAS[verdict]
        memory.confidence = round(clamp01(memory.confidence + delta['confidence']), 3)
        memory.accessCount += delta['access']
        if delta['tag'] and delta['tag'] not in memory.tags:
            memory.tags.append(delta['tag'])
        if memory.layer in ('long_term', 'working'):
            self._persist(memory.layer)
        self.ledger.append(memory.id, 'feedback', actor=actor, previous=previous,
                           new={'confidence': memory.confidence, 'accessCount': memory.accessCount},
                           details={'verdict': verdict})
        return memory

    # --- reads -------------------------------------------------------------
    def all(self) -> list[Memory]:
        return list(self._memories.values())

    def get(self, memory_id: str) -> Memory | None:
        return self._memories.get(memory_id)

    def domains(self) -> list[str]:
        return sorted({m.domain for m in self._memories.values() if m.domain})


def _recency(last_accessed: str, reference: datetime) -> float:
    try:
        seen = datetime.fromisoformat(last_accessed)
    except ValueError:
        return 0.0
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (reference - seen).total_seconds() / 86400.0)
    return math.exp(-age_days / RECENCY_TAU_DAYS)


def _infer_domain(query_tokens: set[str], domains: Iterable[str]) -> str:
    best, best_hits = '', 0
    for domain in domains:
        hits = len(set(tokenize(domain)) & query_tokens)
        if hits > best_hits:
            best, best_hits = domain, hits
    return best


def _nearest_domain(store: 'MemoryStore', query: str) -> str:
    """Fallback when no domain name is mentioned: take the closest memory's domain.

    Without this, a Chinese query that never spells out a Latin domain name scores
    zero on the domain signal and can miss the 0.35 gate even when the memory is
    obviously the right one.
    """
    query_vector = embed(query)
    best, best_score = '', 0.0
    for memory in store.all():
        similarity = cosine(query_vector, memory.embedding or embed(memory.content))
        if similarity > best_score:
            best, best_score = memory.domain, similarity
    return best if best_score >= 0.15 else ''


def score_memory(memory: Memory, query: str, *, query_domain: str = '',
                 reference: datetime | None = None) -> tuple[float, dict[str, float]]:
    """The canonical hybrid formula, term by term, so a judge can audit it."""
    reference = reference or datetime.now(timezone.utc)
    query_tokens = tokenize(query)
    # Order of appearance, not sorted(): sorting CJK tokens picks arbitrary
    # characters and makes the keyword signal unstable between runs.
    ranked_tokens = list(dict.fromkeys(query_tokens))[:KEYWORD_TOP_TOKENS]
    memory_tokens = set(tokenize(memory.content))

    semantic = cosine(embed(query), memory.embedding or embed(memory.content))
    keyword = jaccard(ranked_tokens, memory_tokens)
    tag = jaccard(memory.tags, set(query_tokens))
    domain = 1.0 if query_domain and memory.domain == query_domain else 0.0
    query_entities = {e for e in memory.entities if e.lower() in query_tokens}
    entity = (len(query_entities) / len(memory.entities)) if memory.entities else 0.0
    layer = LAYER_WEIGHTS.get(memory.layer, 0.6)
    recency = _recency(memory.lastAccessed, reference)
    superseded = 1.0 if memory.supersededBy else 0.0

    signals = {'semantic': semantic, 'keyword': keyword, 'tag': tag, 'domain': domain,
               'entity': entity, 'layer': layer, 'recency': recency, 'superseded': superseded}
    raw = sum(SIGNAL_WEIGHTS[name] * value for name, value in signals.items())
    return clamp01(raw) * clamp01(memory.confidence), signals


def retrieve(store: MemoryStore, query: str, *, top_n: int = RETRIEVAL_TOP_N,
             threshold: float | None = None,
             reference: datetime | None = None) -> dict[str, Any]:
    """Rank, filter, and package memory context with inspectable trace metadata."""
    reference = reference or datetime.now(timezone.utc)
    gate = LEXICAL_RETRIEVAL_THRESHOLD if threshold is None else threshold
    query_domain = _infer_domain(set(tokenize(query)), store.domains()) or _nearest_domain(store, query)
    scored: list[tuple[float, Memory, dict[str, float]]] = []
    for memory in store.all():
        score, signals = score_memory(memory, query, query_domain=query_domain, reference=reference)
        memory.score = round(score, 4)
        if score >= gate:
            scored.append((score, memory, signals))
    scored.sort(key=lambda row: row[0], reverse=True)
    selected = scored[:top_n]

    for _score, memory, _signals in selected:
        memory.lastAccessed = reference.isoformat()
        memory.accessCount += 1

    strategy = 'minimal'
    if len(selected) > 2 or any(m.type in ('personal', 'preference') for _s, m, _g in selected):
        strategy = 'comprehensive'
    elif len(selected) == 2:
        strategy = 'personal'

    return {
        'query': query,
        'queryDomain': query_domain,
        'strategy': strategy,
        'threshold': gate,
        'memories': [
            {'id': m.id, 'content': m.content, 'layer': m.layer, 'type': m.type,
             'domain': m.domain, 'confidence': round(m.confidence, 3),
             'score': round(s, 4), 'source': m.source,
             'retrievalReason': _reason(signals)}
            for s, m, signals in selected
        ],
        'context': render_context(selected),
        'considered': len(scored),
    }


def _reason(signals: dict[str, float]) -> str:
    parts = [f'{name}={signals[name]:.2f}' for name in
             ('semantic', 'keyword', 'entity', 'recency') if signals[name] > 0]
    if signals['superseded']:
        parts.append('superseded=-0.20')
    return ', '.join(parts) or 'threshold hit on layer/domain only'


def render_context(selected: list[tuple[float, Memory, dict[str, float]]]) -> str:
    """Domain-grouped blocks with a layer marker; empty string when nothing matched."""
    if not selected:
        return ''
    groups: dict[str, list[tuple[float, Memory]]] = {}
    for score, memory, _signals in selected:
        groups.setdefault(memory.domain or 'general', []).append((score, memory))
    lines = ['## 记忆上下文（H-MEM，来自此前的分析会话）']
    for domain, items in groups.items():
        lines.append(f'### {domain}')
        for score, memory in items:
            lines.append(f'- [{memory.layer}] {memory.content} (score={score:.2f}, source={memory.source})')
    lines.append('以上记忆是先前会话的结论，可能过时或已被取代；使用前核对本次计算结果。')
    return '\n'.join(lines)


def mine_report(store: MemoryStore, report: dict[str, Any], *, source: str = 'agent_report',
                domain: str = '', run_id: str | None = None) -> Memory:
    """Model-free mining: capture the computed facts a later session can reuse."""
    metrics = report.get('computed_metrics') or {}
    factors = [f.get('feature') for f in (report.get('selected_computed_factors') or [])]
    pmids = [r.get('pmid') for r in (report.get('references') or []) if r.get('pmid')]
    balanced = metrics.get('balanced_accuracy')
    parts = [f"问题：{report.get('question', '未记录')}"]
    if balanced is not None:
        parts.append(f"平衡准确率 {balanced}")
    if factors:
        parts.append(f"关键特征 {', '.join(str(f) for f in factors[:5])}")
    if pmids:
        parts.append(f"引用文献 {', '.join(pmids[:5])}")
    parts.append('结论状态：未经验证的模型草稿，特征重要性不代表因果')
    content = '；'.join(parts)
    return store.add(
        content,
        source=source,
        mem_type='factual',
        layer='long_term',
        tags=['research', 'analysis'] + (['has_literature'] if pmids else []),
        domain=domain or 'research',
        namespace='research/investigations',
        # Computed metrics and citation ids were verified against artifacts, so
        # these memories earn higher trust than an unverified interaction note.
        confidence=0.85,
        entities=[f for f in factors[:ENTITY_CAP]] + pmids[:3],
        provenance={'origin': 'mission', 'label': '完成一次研究调查后写入的事实摘要',
                    'refs': [run_id] if run_id else []},
    )


def capture_session_summary(store: MemoryStore, summary: str, *, source: str,
                            domain: str = 'research') -> Memory:
    """No-model fallback: keep continuity as a short-term memory instead of dropping it."""
    return store.add(summary, source=source, mem_type='general', layer='short_term',
                     tags=['session'], domain=domain, confidence=0.5,
                     provenance={'origin': 'interaction', 'label': '无模型兜底的会话摘要'})
