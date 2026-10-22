"""Computed claims and literal source anchors; no fabricated semantic judgments."""
import hashlib
import math
import re
from backend.catalog import feature_info

def statement(label: str, value: float) -> str:
    return (f'打乱 {label} 后，测试评分平均下降 {value:.4f}。' if value > 0 else
            f'{label} 的置换评分变化为 {value:.4f}，本次未观察到正的重要性。')


def anchors(feature: str, profile: dict | None, records: list[dict]) -> list[dict]:
    terms = feature_info(profile, feature)['terms']
    found = []
    for paper in records:
        abstract = paper.get('abstract', '')
        for term in terms:
            match = re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', abstract, re.I)
            if not match:
                continue
            start, end = max(0, match.start() - 75), min(len(abstract), match.end() + 125)
            found.append({'source_id': paper['evidence_id'], 'pmid': paper['pmid'], 'url': paper['url'],
                          'matched_term': term, 'start': start, 'end': end, 'quote': abstract[start:end],
                          'abstract_sha256': hashlib.sha256(abstract.encode()).hexdigest(),
                          'relation': 'unassessed', 'access': paper['access'],
                          'scope': '仅摘要词语命中；尚未核对人群、研究设计、变量定义和结论方向。'})
            break
        if len(found) == 3:
            break
    return found


def build_claims(analysis: dict, literature: dict, profile: dict | None) -> list[dict]:
    claims = []
    for i, factor in enumerate(analysis['factors']):
        info = feature_info(profile, factor['feature'])
        value, sd = factor['importance'], factor['repeat_std']
        snippets = anchors(factor['feature'], profile, literature['records'])
        claims.append({
            'id': f'claim-{i+1}', 'feature': factor['feature'], 'label': info['label'],
            'statement': statement(info['label'], value),
            'category': 'computation', 'evidence_id': factor['evidence_id'],
            'artifact': 'analysis.json', 'pointer': f'/factors/{i}',
            'value': value, 'repeat_std': sd, 'metric': analysis['importance_scoring'],
            'n_test': analysis['n_test'], 'literature_status': 'unassessed' if snippets else 'insufficient',
            'anchors': snippets,
            'limitations': ['评分变化描述模型对变量的依赖，不代表提高该变量会改变疾病风险。',
                            '重复打乱的标准差不是置信区间；相关特征可能分摊重要性。',
                            '文献相关性及支持/冲突需要内容审查；没有原文线索时不作外部支持结论。'],
        })
    return claims


def verify_claims(claims: list[dict], analysis: dict, literature: dict) -> dict:
    records = {p['evidence_id']: p for p in literature['records']}
    if len(claims) != len(analysis['factors']):
        raise ValueError('Claim coverage does not match computed factors.')
    for i, (claim, factor) in enumerate(zip(claims, analysis['factors'])):
        if (claim['id'] != f'claim-{i+1}' or claim['feature'] != factor['feature'] or claim['evidence_id'] != factor['evidence_id']
            or claim['artifact'] != 'analysis.json' or claim['pointer'] != f'/factors/{i}'
            or claim['metric'] != analysis['importance_scoring'] or claim['n_test'] != analysis['n_test']):
            raise ValueError('Claim points to the wrong computation.')
        if (not math.isfinite(claim['value']) or claim['value'] != factor['importance'] or claim['repeat_std'] != factor['repeat_std']):
            raise ValueError('Claim numbers differ from tool output.')
        if claim['statement'] != statement(claim['label'], factor['importance']) or claim['category'] != 'computation':
            raise ValueError('Claim wording differs from the bounded computation statement.')
        expected = 'unassessed' if claim['anchors'] else 'insufficient'
        if claim['literature_status'] != expected:
            raise ValueError('No automatic support or contradiction judgments are permitted.')
        for anchor in claim['anchors']:
            paper = records.get(anchor['source_id'])
            if not paper or anchor['pmid'] != paper['pmid'] or anchor['url'] != paper['url']:
                raise ValueError('Claim cites an unretrieved source.')
            abstract = paper.get('abstract', '')
            start, end = anchor['start'], anchor['end']
            if (not 0 <= start < end <= len(abstract) or anchor['quote'] != abstract[start:end]
                or anchor['abstract_sha256'] != hashlib.sha256(abstract.encode()).hexdigest()
                or anchor['relation'] != 'unassessed' or anchor['access'] != paper['access']):
                raise ValueError('Citation excerpt does not match retrieved evidence.')
    return {'status': 'verified', 'claims_checked': len(claims), 'anchors_checked': sum(len(c['anchors']) for c in claims),
            'scope': '数值、来源标识与摘要原文位置核验；不等于科学支持判定或独立同行评审。'}
