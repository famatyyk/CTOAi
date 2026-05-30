# Azure Activity Agent Eval Dataset Template

File:
- evals/azure-activity-agent-eval-dataset.template.jsonl

Format:
- JSONL (one test case per line)

Required top-level fields per case:
- case_id
- category
- priority
- input
- expected

Recommended workflow:
1. Copy template to evals/azure-activity-agent-eval-dataset.jsonl
2. Add real production-like cases (anonymized)
3. Keep expected.must_include and expected.labels strict and auditable
4. Evaluate prompt variants against the same frozen dataset
5. Promote only variants with metric improvement and no safety regressions

Starter metrics:
- required_fields_coverage_rate
- high_impact_detection_precision
- high_impact_detection_recall
- facts_vs_inference_compliance_rate
- next_step_grounding_rate
