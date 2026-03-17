# CTOA Agent Training Masterplan

## Cel
Wzmocnic pipeline: zwiad internetowy -> ingest do DB -> generacja -> walidacja -> feedback do promptow.

## Agent 1: Scout
- Misja: wykrywanie endpointow i sygnatur API serwerow.
- Trening:
  - rozszerzanie listy probe paths per profil silnika,
  - lepsze rozpoznanie fallback engine,
  - retry/backoff i timeout tuning.
- KPI:
  - endpoint discovery rate,
  - false-positive rate,
  - median scout time.

## Agent 2: Ingest
- Misja: pobranie i normalizacja game_data.
- Trening:
  - mapowanie data_type na stabilny schema contract,
  - deduplikacja i priorytet zrodel,
  - degradacja kontrolowana przy partial data.
- KPI:
  - data completeness per server,
  - schema validity,
  - ingest success ratio.

## Agent 3: Brain
- Misja: planowanie taskow i priorytetow templatingu.
- Trening:
  - adaptacyjne kolejkowanie wg danych i jakosci,
  - dynamiczne limity dzienne,
  - anty-duplikacja taskow.
- KPI:
  - useful queue ratio,
  - queue-to-generated conversion,
  - waste (queued but obsolete).

## Agent 4: Generator
- Misja: render modulow Lua/Python.
- Trening:
  - twardsze output contracts,
  - edge-case snippets i defensive coding,
  - contextual generation z game_data.
- KPI:
  - first-pass generation success,
  - syntax pass rate,
  - avg lines per validated module.

## Agent 5: Validator
- Misja: quality gate i scoring.
- Trening:
  - rozszerzenie testow semantycznych,
  - mocniejszy scoring za stabilnosc runtime,
  - wykrywanie anti-patternow.
- KPI:
  - validation precision,
  - regression catch rate,
  - score stability over time.

## Agent 6: Publisher
- Misja: release gate i pakiety launcher day.
- Trening:
  - lepszy release-risk scoring,
  - quality-aware packaging,
  - rollback metadata i audit trail.
- KPI:
  - release success ratio,
  - post-release incident rate,
  - rollback readiness.

## Agent 7: Prompt Forge (trener promptow)
- Misja: tuning promptow na bazie telemetry i wynikow walidacji.
- Trening:
  - A/B prompt variants,
  - feedback loop z failed_modules/test_log,
  - token-cost vs quality optimizer.
- KPI:
  - quality lift po iteracji,
  - token efficiency,
  - prompt drift control.

## Agent 8: Tool Advisor
- Misja: dobieranie narzedzi/modeli do typu zadania.
- Trening:
  - rankingi per task class,
  - SLA-aware routing,
  - privacy/cost constraints.
- KPI:
  - tool win-rate,
  - cost per successful task,
  - latency per task.

## Agent 9: Orchestrator
- Misja: synchronizacja calosci i odporność na awarie.
- Trening:
  - policy-based retries,
  - concurrency windows,
  - graceful degradation.
- KPI:
  - pipeline completion rate,
  - mean cycle time,
  - error containment index.

## Agent 10: Governance/Queen
- Misja: decyzje GO/NO-GO i polityki.
- Trening:
  - risk scoring i priorytetyzacja,
  - audit discipline,
  - explicit escalation matrix.
- KPI:
  - decision accuracy,
  - policy compliance,
  - incident escalation time.

## Rytm operacyjny
1. Zwiad: co 30-60 min seed + scout.
2. Trening promptow: co 6h na podstawie intel report.
3. Review KPI: daily.
4. Hard gate: weekly, tylko po trendzie quality > 90.
