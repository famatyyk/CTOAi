# CTOA Agent Training Masterplan

This masterplan defines the operational training and skilling rhythm
for the 10-agent system.

Primary source of truth:

- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)

## Goal

Strengthen the end-to-end pipeline:
`scout -> ingest -> planning -> generation -> validation -> governance`
with a closed real-time learning loop and explicit promotion gates.

## Real-Time Training & Skilling Cycle

`telemetry -> failure analysis -> prompt update ->`
`A/B comparison -> validation -> rollout`

- **Training Event:** one complete cycle
  from telemetry capture to validated decision.
- **Skill Update:** controlled change to prompts,
  scoring/routing, or agent execution behavior.
- **Promotion Criteria:** minimum threshold
  to move a candidate update into baseline.

## Operating Cadence

1. Scout and ingest refresh: every **30-60 min**
2. Prompt/skill tuning window: every **6h**
3. KPI trend review: **daily**
4. Hard promotion gate: **weekly**
   (only with stable quality trend and no critical regressions)

## Agent-by-Agent Focus

### 1) Scout

- Mission: discover endpoints and target signals.
- Training focus: probe-path coverage, fallback detection, retry/backoff tuning.

### 2) Ingest

- Mission: fetch and normalize source data.
- Training focus: schema contract stability,
  dedup/prioritization, partial-data degradation.

### 3) Brain

- Mission: queue and priority planning.
- Training focus: adaptive ordering, dynamic limits, anti-duplication.

### 4) Generator

- Mission: generate Lua/Python modules with output contracts.
- Training focus: edge-case handling,
  defensive generation, contextual rendering.

### 5) Validator

- Mission: quality gate and regression detection.
- Training focus: semantic checks,
  runtime stability scoring, anti-pattern detection.

### 6) Publisher

- Mission: release packaging and rollback readiness.
- Training focus: release-risk scoring, quality-aware packaging, audit metadata.

### 7) Prompt Forge

- Mission: optimize BRAVE(R) prompts from outcomes and failures.
- Training focus: A/B variants,
  failed-module feedback loops, token-quality optimization.

### 8) Tool Advisor

- Mission: route tool/model choices by task class.
- Training focus: ranked routing policies,
  SLA-awareness, privacy/cost constraints.

### 9) Orchestrator

- Mission: coordinate execution and error containment.
- Training focus: policy retries, concurrency windows, graceful degradation.

### 10) Governance/Queen

- Mission: GO/NO-GO and policy compliance decisions.
- Training focus: risk scoring, escalation discipline, evidence completeness.

## KPI Template (Required for Every Agent)

For each training event, report at least:

1. **Outcome KPI** (success ratio for mission objective)
2. **Quality KPI** (regression/false-positive/error signal)
3. **Efficiency KPI** (latency and/or cost per successful run)
4. **Stability KPI** (trend consistency across review window)

## Promotion Criteria (Baseline Admission)

A skill update can be promoted only when:

1. Quality trend is stable or improving vs baseline.
2. No critical regressions are detected by validators.
3. Evidence pack is complete
   (artifacts, validation, delta, risk note, decision log).
4. Governance confirms Wave-1 PASS and Wave-2 sign-off.

## Evidence Sources

- Execution telemetry and run summaries
- Validator outputs and test results
- A/B comparison report
- Governance decision log

Cross-reference for release-gate behavior:

- [Sprint Governance](./SPRINT_GOVERNANCE.md)
- [Validation Checklist](./VALIDATION_CHECKLIST.md)
