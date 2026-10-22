# 公开科研数据审计

核实日期：2026-10-22。VERIFIED 表示官方页面或实际下载已核验；UNVERIFIED 表示本项目尚未取得或验证；BLOCKED 表示当前存在访问或方法障碍。官网规则可能变化，正式研究前重新核验。

## 选型结论

当前主演示使用 **UCI Heart Disease 的 processed.cleveland.data**，WDBC 作为独立第二案例。两个小数据集能在本机运行，公开页面均列出 CC BY 4.0。现阶段产品价值是可检查的分析与证据链，不能把经典基准实验描述成新的医学发现。

NHANES 适合作为后续更真实的公共卫生研究案例，但需先增加数据字典、队列构建、复杂抽样和适用性检查。UK Biobank 和完整 MIMIC-IV 不进入本次交付关键路径。

| 来源 | 官方核验事实 | 本项目状态 | 决定 |
|---|---|---|---|
| [UK Biobank](https://www.ukbiobank.ac.uk/use-our-data/apply-for-access/) | 研究申请当前暂停，官网计划 2026 年末恢复；需要合资格研究者和公共利益健康研究 | VERIFIED 规则；BLOCKED 新申请；个人历史权限 UNVERIFIED | 很可能是用户本科使用的平台，但不能确定；不下载受控数据 |
| [UCI Heart Disease](https://archive.ics.uci.edu/dataset/45/heart+disease) | Cleveland 303 行、13 个预测字段；缺失值；CC BY 4.0 | VERIFIED 官方下载、字典、哈希和 CSV 转换 | 第一演示案例 |
| [UCI WDBC](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic) | 569 行、30 个细胞核形态学特征；CC BY 4.0 | VERIFIED 官方下载、字典、哈希和 CSV 转换 | 第二案例/备用 |
| [CDC NHANES 2017–2018](https://wwwn.cdc.gov/nchs/nhanes/search/DataPage.aspx?Component=Demographics&Cycle=2017-2018) | 提供公开 XPT 数据和 codebook | VERIFIED 文档；数据未下载、当前分析方法适配 UNVERIFIED | 后续升级，不能直接宣传为美国人群结论 |
| [MIMIC-IV / MIT 访问说明](https://mimic.mit.edu/docs/faq/how-to-get-access.html) | PhysioNet 认证、CITI 培训、协议等访问要求 | VERIFIED 文档；BLOCKED 未认证 | 当前不引入 |
| [UCI Heart Failure Clinical Records](https://archive.ics.uci.edu/dataset/519/heart+failure+clinical+records) | 299 行、12 个特征，含随访时间和死亡结局；CC BY 4.0 | VERIFIED 页面；未下载；生存分析支持 UNVERIFIED | 用于后续方法边界设计，暂不做普通死亡分类演示 |

## UK Biobank：不是随意下载的公开 CSV

申请页目前明确暂停新申请，意向恢复时间不是承诺。根据[费用页](https://www.ukbiobank.ac.uk/use-our-data/fees/)，普通前三年 Tier 1/2/3 为 £3,000/£6,000/£9,000，另有符合条件学生等优惠；不能假定本团队符合优惠。RAP 计算等另收费。本项目没有申请、开通、付款，也没有验证用户旧研究项目的授权。曾在本科使用不意味着能将旧数据带到个人公开仓库。页面中的过去活动额度不视作现在可领取。

## Cleveland：字段含义与使用边界

来源 DOI：10.24432/C52P4X；署名：Janosi, Steinbrunn, Pfisterer & Detrano (1989)，以当前 UCI 页面引用为准。

压缩包 `WARNING` 明确指出 `cleveland.data` 损坏，`processed.cleveland.data` 可用于 14 字段场景；脚本只使用后者。只读取指定成员，不解压整个归档。

| 字段 | 字典含义 / 转换 |
|---|---|
| age | 年龄（年） |
| sex | 原编码 0/1；保留为名义类别，不扩大其含义 |
| cp | 胸痛类型 1/2/3/4，保留类别 |
| trestbps | 入院静息血压 mm Hg |
| chol | 血清胆固醇 mg/dl |
| fbs | 空腹血糖是否 >120 mg/dl；不是连续血糖值 |
| restecg | 静息心电图类别 0/1/2 |
| thalach | 达到的最大心率 |
| exang | 运动诱发心绞痛类别 0/1 |
| oldpeak | 运动相对静息的 ST 段压低 |
| slope | 运动峰值 ST 段斜率类别 1/2/3 |
| ca | 荧光检查着色的主要血管数；缺失保留 |
| thal | 3 正常、6 固定缺损、7 可逆缺损；缺失保留 |
| num → disease_present | 原标签 0 为无、1–4 为有；二值化后必须移除 num，防止标签泄漏 |

七个类别字段加字段名前缀，避免 CSV 再读取时被当成连续数值；`?` 转成缺失，由分析管线在训练折内填补。未筛掉缺失行。逐次运行在 `manifest.json` 记录来源、哈希、变换、缺失、类别数和 Python/pandas 版本。

允许的演示问题：“在这个已接受检查的历史样本中，哪些测量帮助区分已记录的疾病状态，解释有哪些不确定性？”许多变量来自诊断检查；不能将其说成未来发病风险、初诊前可获得的预测因素或治疗效果。小样本、旧队列、选择偏倚和特征相关性限制解释。数据字典表述独立患者案例，但无法用去标识化表独立证明没有所有潜在个体关联；smoke 测试采用基准数据的一行一例假设。

## WDBC：第二案例

来源 DOI：10.24432/C5DW2B；UCI 引用：Wolberg, Mangasarian, Street & Street (1993)。数据是乳腺肿块细针穿刺图像的细胞核形态特征，不是生活方式风险因素。移除 ID；保留 M=恶性、B=良性。按原始字典命名十种形态的 mean / se / worst 三组；worst 是三个最大值的均值。强相关尺寸指标可能稀释置换重要性，单字段排名不代表独立机制。

## NHANES 与其他候选的主要障碍

[NHANES 权重教程](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx)说明复杂多阶段抽样、过度抽样和非应答调整。需要通过 SEQN 合并人口学/检查/实验室表，定义年龄和队列，检查跳题/缺失编码，并选择适当 interview/exam/subsample 权重、分层和 PSU。当前独立行分类器不等价于 survey-aware 推断，未经适配不作总体代表性结论。

完整 MIMIC 要每位实际接触数据的人分别满足访问要求；不共享账号或将受控记录上传 GitHub。参见 [PhysioNet FAQ](https://physionet.org/about/faqs/)。我们没有取得数据授权，也没有将其发送给任何模型。

心衰数据的 `time` 是随访长度，基线预测不能使用事后随访信息。单纯删除 time 仍未解决不同随访时长、删失和预测时点问题；先设计生存分析或固定时间窗，再考虑模型。

## 复现与数据存储

```bash
uv run --frozen python scripts/fetch_public_data.py all
# 先在另一个终端运行 ./scripts/start.sh，再执行：
uv run --frozen python -m scripts.smoke_public_data
```

准备后的 CSV 位于 `data/public/uci-heart/prepared.csv` 和 `data/public/uci-breast/prepared.csv`，可在界面上传，目标分别为 `disease_present` 和 `diagnosis`。下载总共约 180 KB，不需要新依赖或模型。脚本限 1 MiB、30 秒，固定 SHA-256；上游变更时失败并要求重新核验，不静默接受新数据。

原始 zip、字典、CSV、manifest 和 API 报告均留在已忽略的 `data/`。版本库只放脚本、测试和聚合验证记录。CC BY 4.0 要求署名、许可链接与修改说明；这些记录随 manifest 保留。数据许可不等于项目代码许可。
