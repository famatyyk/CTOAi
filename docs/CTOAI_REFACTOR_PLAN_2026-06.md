# CTOAi Refactor Plan (2026-06)

## 1) Executive Summary

This repository should not be refactored in one big rewrite. The highest ROI path is a phased refactor focused on reliability, modularity, and release speed.

Top recommendation:

- Primary development focus: hybrid runtime + orchestration reliability in `runner/hybrid_bot` and governance-safe boundaries in `runner/`.
- Product growth focus: Azure Activity Log interpretation quality pipeline (`evals/` + prompt variants + strict dataset discipline).

## 2) Current Snapshot (evidence-driven)

| Signal | Observation | Implication |
| --- | --- | --- |
| Repository scale | ~45k files in workspace | Full rewrite is high risk |
| Test surface | 143 test files in `tests/` | Refactor must be incremental with guardrails |
| Runtime hotspots | TODO markers and repeated `_utcnow()` helpers in `runner/hybrid_bot` | Shared utility and consistency refactor is overdue |
| API surface concentration | `mobile_console/app.py` is a very large multi-responsibility module | Split into bounded routers/services |
| Governance constraints | Canonical status flow and gate order are strict | Do not break transition semantics |

## 3) Refactor Priorities

Scoring model:

- Impact (1-5)
- Risk if unchanged (1-5)
- Refactor effort (1-5, lower is better)
- Priority score = Impact + Risk - Effort

| Area | Impact | Risk if unchanged | Effort | Priority score | Why now |
| --- | --- | --- | --- | --- | --- |
| `runner/hybrid_bot` modular cleanup | 5 | 5 | 3 | 7 | Core runtime correctness and maintainability |
| `mobile_console/app.py` decomposition | 5 | 4 | 4 | 5 | Faster feature delivery and safer API changes |
| Prompt/eval product hardening (`evals/`) | 4 | 4 | 2 | 6 | Clear product differentiation and quality uplift |
| Tool scoring/policy tuning (`scoring/`, `policies/`) | 4 | 3 | 3 | 4 | Better deterministic decisions |
| Documentation and runbook pruning | 3 | 2 | 2 | 3 | Better onboarding and lower cognitive load |

## 4) Best Place for Growth

## Recommendation: Build a product-grade Azure Activity Intelligence lane

Why this is the best growth vector now:

- Existing momentum already exists in prompt variants and run artifacts.
- Strong alignment with auditable, fact-first behavior already encoded in the repo.
- Can generate measurable KPI improvements quickly with frozen datasets and controlled prompt releases.

| Growth direction | Strategic value | Time to value | Defensibility |
| --- | --- | --- | --- |
| Azure Activity Intelligence (agent eval + runbook quality) | High | Fast (1-2 sprints) | High |
| Generic bot capability expansion | Medium | Medium | Medium |
| Broad UX expansion before backend cleanup | Medium | Slow | Low |

## 5) Target Architecture Changes

| Current state | Target state | Refactor action |
| --- | --- | --- |
| Repeated time helper implementation across modules | One shared time utility package | Introduce shared clock utility and migrate imports |
| Large orchestration classes with mixed responsibilities | Thin orchestrator + isolated domain services | Extract state, action, and telemetry services |
| Monolithic API app module | Router-based module boundaries | Split endpoints by domain and keep services pure |
| Mixed test intent (unit + integration overlap) | Layered test pyramid and explicit contract tests | Add focused unit suites near hotspots |
| Prompt variant results scattered by run | Stable eval protocol with comparators | Enforce frozen dataset and metric gates |

## 6) 6-Sprint Execution Plan

| Sprint | Objective | Deliverables | Exit criteria |
| --- | --- | --- | --- |
| S1 | Baseline and guardrails | Complexity map, dependency map, baseline KPIs, ADR-001 | Baseline approved, no regressions |
| S2 | Hybrid bot foundation cleanup | Shared clock utility, extraction of action/state boundaries | All hybrid tests green; no behavior drift |
| S3 | Hybrid bot modularization | Vision/action/metrics interfaces hardened | Integration tests green, lower coupling |
| S4 | Mobile console decomposition | Router split + service boundaries + API contract snapshots | API contract tests stable |
| S5 | Eval/product hardening | Frozen dataset v1, metric dashboard, variant promotion gate | Metric deltas visible and reproducible |
| S6 | Governance tightening | Deterministic evidence checks, release checklist automation | Sprint validate + CI gate clean |

## 7) Risk Register

| Risk | Probability | Impact | Mitigation |
| --- | --- | --- | --- |
| Hidden coupling in `mobile_console/app.py` | High | High | Slice by endpoint domain with contract snapshots first |
| Runtime behavior drift in bot loop | Medium | High | Add characterization tests before extraction |
| Gate policy regression | Medium | High | Keep status transitions untouched; validate per sprint task |
| Refactor fatigue / scope creep | High | Medium | Strict sprint scope and ADR per major decision |

## 8) KPI Table

| KPI | Baseline source | Target after 6 sprints |
| --- | --- | --- |
| Time to ship minor change | CI + sprint evidence logs | -30% |
| Mean recovery time after regression | Issue + validator history | -40% |
| Hybrid runtime bug density | `tests/test_hybrid_bot.py` + incidents | -35% |
| Mobile API change lead time | PR cycle metrics | -25% |
| Eval quality (coverage/precision/grounding) | `evals/runs/*` summaries | +15-25% |

## 9) Immediate Next Actions (first 72h)

| Day | Action | Owner |
| --- | --- | --- |
| Day 1 | Freeze baseline metrics and run current sprint validate | Core Architect + QA |
| Day 2 | Create module boundary ADRs for `runner/hybrid_bot` and `mobile_console` | Core Architect |
| Day 3 | Implement first extraction PR: shared clock utility + migration in hybrid modules | Code Smith |

## 10) Definition of Done for Refactor PRs

| Rule | Check |
| --- | --- |
| No status-flow semantics change | Governance tests and sprint validator pass |
| Deterministic outputs preserved | Evidence artifacts reproducible |
| Scope isolation | PR touches only declared module boundaries |
| Tests updated minimally | Unit/integration tests pass without unrelated refactors |
| Docs linked, not duplicated | References to canonical docs are present |
