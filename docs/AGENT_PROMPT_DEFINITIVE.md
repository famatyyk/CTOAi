# Enhanced Agent/Prompt Definitive

Single source of truth for agent roles, BRAVE(R) prompt lifecycle,
real-time training/skilling, and release quality evidence in CTOA.

## Scope

This document standardizes:

- agent role boundaries,
- prompt lifecycle and governance,
- real-time training and skilling loop,
- KPI and evidence requirements for GO/NO-GO.

For implementation detail, see:

- [Architecture](./ARCHITECTURE.md)
- [Agent Training Masterplan](./AGENT_TRAINING_MASTERPLAN.md)
- [Real-Time Module Creation](./REALTIME_MODULE_CREATION.md)
- [Sprint Governance](./SPRINT_GOVERNANCE.md)
- [Validation Checklist](./VALIDATION_CHECKLIST.md)

## Canonical Terminology

- **Agent:** a specialized execution role in the 10-agent operating model.
- **Prompt Forge:** the capability that tunes BRAVE(R) prompts
  from telemetry and failures.
- **Tool Advisor:** scoring/routing capability selecting tools
  based on relevance/cost/risk.
- **Wave-1:** automated gate (validation + CI + evidence completeness).
- **Wave-2:** manual approval gate with release sign-off.
- **Training Event:** one closed loop from telemetry capture
  to validated prompt/skill decision.
- **Skill Update:** a controlled change to agent behavior,
  templates, scoring, or routing policy.
- **Promotion Criteria:** explicit threshold that allows an update
  to move from candidate to baseline.

## Canonical Flow (Agent -> Prompt -> Scoring -> Governance)

1. Agent receives scoped task and required artifacts.
2. BRAVE(R) prompt is rendered with current baseline template.
3. Tool Advisor ranks and policy pack constrains available tools.
4. Agent executes and emits outputs + telemetry + confidence signals.
5. Validators score quality and create evidence artifacts.
6. Governance evaluates Wave-1/Wave-2 gates and decides GO/NO-GO.

## Real-Time Training & Skilling Loop

Cycle:
`telemetry -> failure analysis -> prompt update ->`
`A/B comparison -> validation -> rollout`

Cadence:

- Scout/ingest refresh: every **30-60 min**
- Prompt/skill tuning window: every **6h**
- KPI and drift review: **daily**
- Hard promotion gate: **weekly**
  (only with stable trend and no blocking regressions)

## Agent Roles (Canonical)

1. Scout — endpoint/signal discovery
2. Ingest — data normalization and schema quality
3. Brain — planning, prioritization, queue hygiene
4. Generator — artifact generation contracts
5. Validator — quality scoring and regression protection
6. Publisher — release packaging and rollback readiness
7. Prompt Forge — prompt lifecycle and A/B optimization
8. Tool Advisor — tool/model routing and cost/risk control
9. Orchestrator — pipeline coordination and resilience
10. Governance/Queen — GO/NO-GO, policy compliance, escalation

## KPI Template (All Agents)

Each agent update should report:

1. **Outcome KPI:** core task success metric (e.g., pass rate, discovery rate)
2. **Quality KPI:** error/false-positive/regression signal
3. **Efficiency KPI:** latency and/or cost per successful run
4. **Stability KPI:** trend consistency over time window

## Minimal Evidence for GO/NO-GO

Required per candidate update:

1. Task output artifacts (or explicit no-output rationale)
2. Validation results (test/validator status)
3. Delta comparison against previous baseline (quality/cost/latency)
4. Risk notes (known limitations, fallback/rollback path)
5. Decision log entry with owner and timestamp

Gate mapping:

- **Wave-1 PASS:** automated checks pass and evidence set is complete.
- **Wave-2 PASS:** manual sign-off confirms release fitness.

## Documentation Rollout Checklist

### Definition of Ready (DoR)

- Terminology aligned with this document
- Target metrics and promotion criteria explicitly defined
- Required evidence sources identified

### Definition of Done (DoD)

- Linked docs updated without duplicated conflicting instructions
- Wave-1/Wave-2 implications documented
- Validation/checklist references updated
- Change reviewed in sprint governance cadence

### Sprint Audit Cadence

- Run a docs consistency audit once per sprint closure.
- Verify source-of-truth links and remove stale duplicated guidance.
- Record audit result in sprint release notes.
