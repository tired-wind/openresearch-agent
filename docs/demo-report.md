# OpenResearch Agent — Research report

## Research question
Which synthetic factors predict outcome, and what literature should be reviewed?

## Dataset and provenance
Source: synthetic_demo_not_clinical. SHA-256: d34a30279fb7048be992b7ba7df1fb10b41f021ee8fdd05628bb7bba3e595676.
Observed 320 rows and 9 columns. Analyzed 320 rows; train 240, test 80.

## Methodology
classification target: outcome. Model: RandomForest (100 trees, max_depth=6, min_samples_leaf=3). Seed: 42.
Preprocessing fitted on training rows only. Three-fold training CV and separate 25% holdout. Exact duplicate rows removed before splitting.
CV scoring: balanced_accuracy; mean 0.659152, fold SD 0.065336. Negative RMSE scores use higher-is-better convention.
Positive class (binary only): 1.

## Model evaluation [computation: analysis-1]
- balanced_accuracy: 0.642258
- f1_macro: 0.629630
- baseline_balanced_accuracy: 0.500000
- roc_auc: 0.776506
- average_precision: 0.695981

## Ranked predictive factors [computation]
| Factor | Permutation score decrease | Repeat SD | Evidence |
|---|---:|---:|---|
| bmi | 0.019641 | 0.035873 | factor-2 |
| sleep_hours | 0.018593 | 0.015247 | factor-5 |
| age | 0.001716 | 0.021918 | factor-1 |
| exercise_hours | -0.000667 | 0.049088 | factor-3 |
| smoking | -0.029987 | 0.012813 | factor-4 |
| noise_marker | -0.040761 | 0.023487 | factor-6 |

Importance is measured in the scoring metric units; negative values are retained. No causal direction is inferred.

## Excluded features [dataset observation]
- participant_id: Identifier, direct personal field or time field; review subject grouping and temporal design.
- target_copy: Exact target copy in training rows.

## Scientific evidence [retrieved sources]
Retrieval status: retrieved. Identifiers verified against fetched records; scientific support not established.
No source is automatically labeled supporting or conflicting. Search matches alone cannot establish either relationship.
- [Non-Invasive Prediction of Metabolic Syndrome Using Explainable Machine Learning.](https://pubmed.ncbi.nlm.nih.gov/42882228/) — Islam A Berdaweel, Sayer I Al-Azzam, Ghaith Al-Taani, Amal Albawaana, Salam Shannag, Ameera M Bataineh, Sireen Abdul Rahim Shilbayeh, Amjed Al Fahoum (2026); PMID 42882228; DOI 10.3390/diagnostics16193073. Access: abstract_only; relation: uncertain; evidence: pubmed-42882228.
- [Association of ophthalmic disease and physical activity in All of Us Research Program.](https://pubmed.ncbi.nlm.nih.gov/42858823/) — Nikhil Chatra, Amin Nabavi, Swarup S Swaminathan, Felipe A Medeiros, Siamak Yousefi (2026); PMID 42858823; DOI 10.1016/j.jshs.2026.101182. Access: abstract_only; relation: uncertain; evidence: pubmed-42858823.
- [Lifestyle interventions for cardiometabolic health in women with polycystic ovary syndrome: a systematic review and network meta-analysis.](https://pubmed.ncbi.nlm.nih.gov/42854088/) — Xinuan Zhang, Zhide Liang, Angelo Sabag, Rhiannon Patten, Yanyan Kang, Mingyue Yin, Kai Xu, Yujia Kuang, Mingda Li, Shunchang Li (2026); PMID 42854088; DOI 10.1093/humupd/dmag032. Access: abstract_only; relation: uncertain; evidence: pubmed-42854088.
- [Development and validation of a risk prediction model for postoperative frailty in breast cancer patients.](https://pubmed.ncbi.nlm.nih.gov/42799450/) — Ye Zhou, Lili Li, Lin Jiang, Lihua Zhou, Huan Qiu (2026); PMID 42799450; DOI 10.7717/peerj.21733. Access: abstract_only; relation: uncertain; evidence: pubmed-42799450.
- [The temporal relationship among socioeconomic vulnerability, dietary intake, and childhood obesity across six European countries: longitudinal results from the Feel4Diabetes-study.](https://pubmed.ncbi.nlm.nih.gov/42747589/) — Lubna Mahmood, Guiomar Masip, Luis A Moreno, Peter Schwarz, Lena Roth, Maxi Bretschneider, Ruben Willems, Greet Cardon, Violeta Iotova, Natalya Usheva, Tsvetalina Tankova, Eva Karaglani (2026); PMID 42747589; DOI 10.1007/s00431-026-07415-2. Access: abstract_only; relation: uncertain; evidence: pubmed-42747589.

## Uncertainty and limitations
- Predictive importance is not causal evidence and does not establish an association direction.
- Permutation repeat SD measures shuffle variability, not a confidence interval.
- Single random holdout; small-sample performance and rankings can be unstable.
- No temporal or grouped validation. Independent rows must be confirmed by the user.
- Leakage heuristics cannot detect all post-outcome variables; domain review is required.
- Feature rankings use the evaluation set and are exploratory; new validation is required before selecting/refitting features.
- No clinical validation, treatment advice, p-values or invented confidence intervals.

## Verification
Deterministic artifact checks. Not an independent scientific peer review or full-text citation verification.
- Review excluded columns for identifiers and target leakage.
- Read candidate papers and assess population, exposure and outcome before labeling support or contradiction.

## Reproducibility
Run ID: a8d7de8d-b625-4007-a179-5b3617fa6192. Dataset digest above. Dependency versions: {'pandas': '2.3.3', 'numpy': '2.5.4', 'scikit-learn': '1.9.1'}.
Persisted artifacts: plan.json, overview.json, analysis.json (including split indices), literature.json, review.json, provenance.json, report.md. No dataset rows were sent to a model.
Execution mode: deterministic research workflow; LLM and sponsor integrations not active. Hypotheses are not validated findings.
