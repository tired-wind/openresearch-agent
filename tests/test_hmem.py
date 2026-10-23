"""H-MEM contracts: mandatory provenance, the eight-signal formula, trial ledger."""
from datetime import datetime, timedelta, timezone

import pytest

from backend import hmem


def test_record_without_source_is_rejected(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    with pytest.raises(ValueError):
        store.add('some fact', source='')
    with pytest.raises(ValueError):
        store.add('some fact', source='   ')


def test_added_record_carries_provenance_and_ledger_entry(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    memory = store.add('心脏病数据集的平衡准确率为 0.64', source='agent_report',
                       mem_type='factual', layer='long_term', domain='research',
                       entities=['balanced_accuracy'])
    assert memory.provenance['origin'] == 'interaction'
    assert memory.provenance['learnedAt']
    assert memory.embedding
    actions = [e['action'] for e in store.ledger.entries()]
    assert actions == ['create']


def test_unknown_type_and_layer_are_rejected(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    with pytest.raises(ValueError):
        store.add('x', source='s', mem_type='speculation')
    with pytest.raises(ValueError):
        store.add('x', source='s', layer='forever')


def test_ledger_rejects_unregistered_action(tmp_path):
    ledger = hmem.TrustLedger(tmp_path / 'ledger.jsonl')
    with pytest.raises(ValueError):
        ledger.append('id', 'not_a_real_action')
    ledger.append('id', 'create')
    assert ledger.stats() == {'create': 1}


def test_formula_is_the_weighted_sum_times_confidence(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    memory = store.add('心脏数据集的平衡准确率 0.6423，关键特征 thalach',
                       source='agent_report', mem_type='factual', layer='long_term',
                       tags=['research'], domain='research', entities=['thalach'],
                       confidence=0.8)
    score, signals = hmem.score_memory(memory, '平衡准确率是多少 thalach', query_domain='research')
    raw = sum(hmem.SIGNAL_WEIGHTS[name] * value for name, value in signals.items())
    assert score == pytest.approx(hmem.clamp01(raw) * 0.8, abs=1e-9)
    assert signals['superseded'] == 0.0


def test_layer_weight_orders_long_term_above_short_term(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    content = '模型的平衡准确率是 0.64'
    short = store.add(content, source='s', layer='short_term', confidence=0.8)
    long = store.add(content, source='s', layer='long_term', confidence=0.8)
    query = '平衡准确率 0.64'
    short_score, _ = hmem.score_memory(short, query)
    long_score, _ = hmem.score_memory(long, query)
    assert long_score > short_score
    # The gap is exactly the layer weight difference before clamping.
    assert long_score - short_score == pytest.approx(
        hmem.SIGNAL_WEIGHTS['layer'] * (hmem.LAYER_WEIGHTS['long_term'] - hmem.LAYER_WEIGHTS['short_term']),
        abs=5e-3)


def test_superseded_record_is_penalised_but_kept(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    content = '最佳模型是随机森林'
    active = store.add(content, source='s', layer='long_term', confidence=0.8)
    stale = store.add(content, source='s', layer='long_term', confidence=0.8)
    stale.supersededBy = active.id
    query = '最佳模型 随机森林'
    assert hmem.score_memory(stale, query)[0] < hmem.score_memory(active, query)[0]
    assert stale in store.all()  # penalised, never deleted


def test_recency_decay_lowers_old_memories(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    fresh = store.add('实验结论 平衡准确率 0.64', source='s', layer='long_term', confidence=0.8)
    old = store.add('实验结论 平衡准确率 0.64', source='s', layer='long_term', confidence=0.8)
    old.lastAccessed = (datetime.now(timezone.utc) - timedelta(days=42)).isoformat()
    query = '实验结论 平衡准确率'
    assert hmem.score_memory(old, query)[0] < hmem.score_memory(fresh, query)[0]


def test_retrieval_filters_by_threshold_and_caps_results(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    for index in range(8):
        hmem.mine_report(store, {
            'question': f'第 {index} 次心脏病数据分析',
            'computed_metrics': {'balanced_accuracy': 0.60 + index / 100},
            'selected_computed_factors': [{'feature': 'thalach'}],
            'references': [],
        }, domain='research', run_id=f'run-{index}')
    result = hmem.retrieve(store, '心脏病数据分析 平衡准确率')
    assert 0 < len(result['memories']) <= hmem.RETRIEVAL_TOP_N
    assert all(row['score'] >= result['threshold'] for row in result['memories'])
    assert result['memories'] == sorted(result['memories'], key=lambda r: r['score'], reverse=True)


def test_spec_threshold_is_stricter_than_the_lexical_calibration(tmp_path):
    """The formula is unchanged; only the gate is calibrated for lexical embeddings."""
    assert hmem.RETRIEVAL_THRESHOLD == 0.35
    assert hmem.LEXICAL_RETRIEVAL_THRESHOLD < hmem.RETRIEVAL_THRESHOLD
    store = hmem.MemoryStore(tmp_path)
    hmem.mine_report(store, {'question': '心脏病数据分析', 'computed_metrics': {'balanced_accuracy': 0.64},
                             'selected_computed_factors': [{'feature': 'thalach'}], 'references': []},
                     domain='research')
    calibrated = hmem.retrieve(store, '心脏病 分析')
    strict = hmem.retrieve(store, '心脏病 分析', threshold=hmem.RETRIEVAL_THRESHOLD)
    assert len(strict['memories']) <= len(calibrated['memories'])
    assert strict['threshold'] == 0.35


def test_unrelated_query_returns_no_context(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    store.add('心脏病数据集的平衡准确率为 0.64', source='s', layer='long_term', confidence=0.8)
    result = hmem.retrieve(store, 'quantum chromodynamics lattice spacing')
    assert result['memories'] == []
    assert result['context'] == ''


def test_reinjection_is_domain_grouped_with_layer_markers(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    hmem.mine_report(store, {
        'question': '心脏病数据集的特征与诊断是否相关？',
        'computed_metrics': {'balanced_accuracy': 0.6423},
        'selected_computed_factors': [{'feature': 'thalach'}],
        'references': [{'pmid': '12345678'}],
    }, domain='research')
    store.add('用户要求报告用中文撰写', source='user_correction', mem_type='preference',
              layer='long_term', domain='preferences', tags=['language', '中文'],
              entities=['中文'], confidence=0.95)
    result = hmem.retrieve(store, '心脏病数据集的特征与准确率，报告用中文')
    assert '## 记忆上下文' in result['context']
    assert '### research' in result['context']
    assert '[long_term]' in result['context']
    assert result['strategy'] == 'comprehensive'
    assert all('retrievalReason' in row for row in result['memories'])


def test_feedback_deltas_match_the_spec(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    memory = store.add('一条可检验的事实', source='s', layer='long_term', confidence=0.5)

    store.feedback(memory.id, 'helpful')
    assert memory.confidence == pytest.approx(0.55)
    assert memory.accessCount == 1

    store.feedback(memory.id, 'not_helpful')
    assert memory.confidence == pytest.approx(0.52)

    store.feedback(memory.id, 'wrong')
    assert memory.confidence == pytest.approx(0.32)
    assert 'review' in memory.tags
    assert store.ledger.stats()['feedback'] == 3


def test_feedback_rejects_unknown_verdict(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    memory = store.add('事实', source='s')
    with pytest.raises(ValueError):
        store.feedback(memory.id, 'meh')


def test_persistence_round_trip_keeps_long_term_and_ledger(tmp_path):
    first = hmem.MemoryStore(tmp_path)
    memory = first.add('持久化的事实 平衡准确率 0.64', source='agent_report',
                       layer='long_term', domain='research', confidence=0.8)
    second = hmem.MemoryStore(tmp_path)
    restored = second.get(memory.id)
    assert restored is not None
    assert restored.content == memory.content
    assert restored.embedding  # backfilled on load
    assert len(second.ledger.entries()) >= 1


def test_cjk_tokenizer_emits_bigrams():
    tokens = hmem.tokenize('平衡准确率')
    assert '平衡' in tokens and '准确' in tokens


def test_mine_report_produces_a_long_term_factual_memory(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    report = {
        'question': '这些特征与心脏病是否相关？',
        'computed_metrics': {'balanced_accuracy': 0.6423},
        'selected_computed_factors': [{'feature': 'thalach'}, {'feature': 'cp'}],
        'references': [{'pmid': '12345678'}],
    }
    memory = hmem.mine_report(store, report, domain='research', run_id='run-1')
    assert memory.layer == 'long_term'
    assert memory.type == 'factual'
    assert '0.6423' in memory.content
    assert 'thalach' in memory.content
    assert memory.provenance['refs'] == ['run-1']
    assert 'has_literature' in memory.tags


def test_model_free_fallback_capture_stays_short_term(tmp_path):
    store = hmem.MemoryStore(tmp_path)
    memory = hmem.capture_session_summary(store, '本次会话只做了数据检查，未建模', source='session')
    assert memory.layer == 'short_term'
    assert memory.confidence == 0.5
