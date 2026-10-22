"""Bounded scope checks and explicit plans; no LLM reasoning is claimed."""
import hashlib
import json
import re
from typing import Literal
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: UUID
    target: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=10, max_length=1500)
    task: Literal['auto', 'classification', 'regression'] = 'auto'
    intent: Literal['prediction', 'causal_effect', 'future_risk', 'survival'] = 'prediction'
    study_design: Literal['independent', 'repeated', 'temporal', 'survey'] = 'independent'
    independent_rows: bool = False
    allow_literature: bool = False
    literature_query: str = Field(default='', max_length=300)
    plan_fingerprint: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    @field_validator('question', mode='before')
    @classmethod
    def strip_question(cls, value):
        return value.strip() if isinstance(value, str) else value


class Check(BaseModel):
    code: str
    status: Literal['pass', 'warning', 'blocked']
    message: str
    action: str


class AnalysisPlan(BaseModel):
    version: str = '1'
    mode: str = 'deterministic_scope_checks'
    status: Literal['ready', 'blocked']
    question: str
    target: str
    task: str
    dataset_sha256: str
    fingerprint: str
    checks: list[Check]
    steps: list[str]
    limitations: list[str]
    external_query: str | None
    max_review_rounds: int = 1


def build_plan(request: ResearchRequest, frame: pd.DataFrame, raw: bytes, profile: dict | None) -> AnalysisPlan:
    checks: list[Check] = []
    def add(code, status, message, action=''):
        checks.append(Check(code=code, status=status, message=message, action=action))
    if request.target not in frame:
        add('target', 'blocked', '目标字段不存在。', '重新选择数据中已有的目标字段。')
        clean = frame.iloc[:0]
        task = request.task
    else:
        clean = frame.drop_duplicates().dropna(subset=[request.target])
        y = clean[request.target]
        task = request.task if request.task != 'auto' else ('classification' if not pd.api.types.is_numeric_dtype(y) or y.nunique() <= 10 else 'regression')
        add('target', 'pass', f'将 {request.target} 作为目标，执行{"分类" if task == "classification" else "回归"}。')
        if len(clean) < 60:
            add('sample_size', 'blocked', f'去重并排除缺失目标后只有 {len(clean)} 行；至少需要 60 行。', '使用更充分的数据；不要复制样本凑数。')
        elif task == 'classification' and (not 2 <= y.nunique() <= 10 or y.astype(str).value_counts().min() < 8):
            add('classes', 'blocked', '分类需要 2–10 类，且每类至少 8 行。', '检查目标含义和各类别样本量。')
        elif task == 'regression' and (not pd.api.types.is_numeric_dtype(y) or y.nunique() < 10):
            add('numeric_target', 'blocked', '回归需要至少 10 个不同数值的数值目标。', '检查任务类型和目标。')
        else:
            add('sample_size', 'pass', f'预计使用 {len(clean)} 行；保留独立测试集。')
    if request.study_design != 'independent' or not request.independent_rows:
        add('design', 'blocked', '当前方法仅支持独立观测；尚未提供重复个体、时间序列或复杂抽样验证。', '确认一行一例且观测独立；否则需要专门的切分和评估方法。')
    else:
        add('design', 'pass', '采用用户确认的独立观测假设；程序无法证明这个假设。')
    if request.intent != 'prediction':
        add('intent', 'blocked', '当前工具不能估计因果效应、未来风险或生存结局。', '将问题限定为当前样本的预测表现，或先扩展研究设计。')
    # Conservative language flags supplement explicit purpose selection, not a semantic model.
    patterns = r'因果效应|导致|治疗效果|未来|生存分析|\bcausal\s+effect|\bcauses?\b|\btreatment\s+effect|\bfuture\s+risk|\bsurvival\s+analysis'
    if re.search(patterns, request.question, re.I):
        add('question_scope', 'blocked', '问题中出现可能超出当前预测方法的因果、未来或生存表述。', '这是保守的关键词检查；请改写为样本内预测问题，或选择适当研究方法。')
    else:
        add('question_scope', 'warning', '问题通过基础范围检查；这不代表系统已理解全部科学意图。', '检查目标、字段含义和分析方案；复杂语义仍需研究者审查。')
    columns = {str(c).lower() for c in frame}
    if {'sdmvpsu', 'sdmvstra'} & columns or any(c.startswith(('wtmec', 'wtint')) for c in columns):
        add('survey_fields', 'blocked', '检测到 NHANES 常见抽样设计字段，不能套用独立行分析。', '使用权重、分层和 PSU 感知的分析方法。')
    if {'time', 'death_event'} <= columns:
        add('follow_up', 'blocked', '检测到随访时间与死亡结局；随机分类可能包含事后信息。', '先定义预测时点、固定时间窗与删失处理。')
    if profile:
        add('source', 'pass', f'文件内容哈希与已核验的 {profile["label"]} 一致。')
    else:
        add('source', 'warning', '数据来源和字段语义尚未独立验证。', '自行确认来源授权及每个特征在预测时点是否可用。')
    if request.allow_literature and len(request.literature_query.strip()) < 3:
        add('literature_query', 'blocked', '启用检索时需要明确的公开检索词。', '填写不含个人信息的检索词。')
    limits = ['这是预定义规则生成的方案，未使用大模型自主规划。', '变量筛查仅在训练数据中执行；无法发现所有业务泄漏。',
              '随机留出集评估与特征重要性不能证明因果或临床有效性。', '论文词语命中只是待审查线索，不自动证明支持或反驳。']
    if profile:
        limits += profile['limitations']
    dataset_sha = hashlib.sha256(raw).hexdigest()
    identity = {'request': request.model_dump(mode='json', exclude={'plan_fingerprint'}), 'dataset_sha256': dataset_sha, 'plan_version': '1'}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return AnalysisPlan(status='blocked' if any(c.status == 'blocked' for c in checks) else 'ready',
        question=request.question, target=request.target, task=task, dataset_sha256=dataset_sha, fingerprint=fingerprint,
        checks=checks, limitations=limits, external_query=request.literature_query if request.allow_literature else None,
        steps=['检查缺失、重复行、目标和研究范围。', '按固定种子划分 75% 训练集与 25% 测试集；分类时分层。',
               '在训练数据内填补与编码；三折交叉验证并与简单基线比较。', '在留出测试集计算指标和置换重要性；保留负值及不稳定性。',
               '按明确检索词获取 PubMed 记录；为相关词命中保存摘要原文位置。' if request.allow_literature else '不进行外部检索；文献支持状态保留为证据不足。',
               '核对结论数值与原文引用，保存可追溯证据卡和报告。'])
