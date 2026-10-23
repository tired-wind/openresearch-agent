"""Trusted, checksum-identified public examples. User filenames never establish provenance."""
import hashlib

HEART_FIELDS = {
    'age': ('年龄（年）', ['age']), 'sex': ('原数据性别编码', ['sex']),
    'cp': ('胸痛类型', ['chest pain', 'angina']),
    'trestbps': ('入院静息血压（mm Hg）', ['blood pressure']),
    'chol': ('血清胆固醇（mg/dl）', ['cholesterol']),
    'fbs': ('空腹血糖是否超过 120 mg/dl', ['fasting blood glucose', 'fasting blood sugar']),
    'restecg': ('静息心电图类别', ['electrocardiogram', 'electrocardiographic']),
    'thalach': ('达到的最大心率', ['heart rate']),
    'exang': ('运动诱发心绞痛', ['exercise-induced angina', 'angina']),
    'oldpeak': ('运动相对静息的 ST 段压低', ['ST depression', 'ST-segment depression']),
    'slope': ('运动峰值 ST 段斜率类别', ['ST segment', 'ST-segment']),
    'ca': ('透视检查中显影的主要血管数（0–3）；不是冠状动脉钙化评分', ['fluoroscopy', 'coronary vessels']),
    'thal': ('灌注检查结果类别', ['perfusion', 'thallium']),
    'disease_present': ('已记录的心脏病状态（0 无 / 1 有）', []),
}
CATALOG = {
    'heart': {
        'label': '心脏病公开案例', 'rows': 303, 'target': 'disease_present',
        'prepared_sha256': '3b46ae4de8e2a18070e923c7071c71c0f6987e6879ba26a8d6b4b27bdd484c73',
        'source_url': 'https://archive.ics.uci.edu/dataset/45/heart+disease',
        'attribution': 'Janosi, Steinbrunn, Pfisterer & Detrano (1989), UCI, DOI:10.24432/C52P4X',
        'license': 'CC BY 4.0',
        'question': '在这个历史诊断样本中，哪些检查指标有助于区分已记录的心脏病状态？这些解释有哪些局限？',
        'query': 'coronary artery disease diagnosis exercise electrocardiography perfusion',
        'limitations': ['历史诊断样本；部分特征来自诊断检查，不能据此声称预测未来发病。',
                        '小样本及选择偏倚限制推广；特征重要性不是因果效应。'],
        'fields': {k: {'label': v[0], 'terms': v[1]} for k, v in HEART_FIELDS.items()},
    },
    'breast': {
        'label': '乳腺癌诊断公开案例', 'rows': 569, 'target': 'diagnosis',
        'prepared_sha256': '2b96892b20da5730655b83f6961cafcfb29091c3f09ab50a4206ad6f7761079e',
        'source_url': 'https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic',
        'attribution': 'Wolberg, Mangasarian, Street & Street (1993), UCI, DOI:10.24432/C5DW2B',
        'license': 'CC BY 4.0',
        'question': '哪些细胞核形态指标有助于区分样本中已记录的良性和恶性诊断？相关特征会怎样限制解释？',
        'query': 'breast cancer fine needle aspiration nuclear morphology diagnosis',
        'limitations': ['特征来自细针穿刺图像，不能解释成生活方式风险因素。',
                        '形态指标之间相关，单个特征排名不代表独立机制。'],
        'fields': {'diagnosis': {'label': '诊断（B 良性 / M 恶性）', 'terms': []}},
    },
}
for feature, label in {'radius': '半径', 'texture': '纹理', 'perimeter': '周长', 'area': '面积',
                       'smoothness': '平滑度', 'compactness': '紧密度', 'concavity': '凹陷程度',
                       'concave_points': '凹点数', 'symmetry': '对称性', 'fractal_dimension': '分形维数'}.items():
    for suffix, summary in [('mean', '均值'), ('se', '标准误'), ('worst', '三个最大值均值')]:
        CATALOG['breast']['fields'][f'{feature}_{suffix}'] = {'label': f'{label} · {summary}', 'terms': [feature.replace('_', ' ')]}


def identify(raw: bytes) -> dict | None:
    sha = hashlib.sha256(raw).hexdigest()
    return next(({'id': key, **value} for key, value in CATALOG.items() if value['prepared_sha256'] == sha), None)


def feature_info(profile: dict | None, name: str) -> dict:
    if profile and name in profile['fields']:
        return profile['fields'][name]
    # Unknown shorthand is not expanded into an invented medical meaning.
    return {'label': name, 'terms': [name.replace('_', ' ')] if len(name) >= 4 else []}
