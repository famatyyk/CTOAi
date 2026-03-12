# Sprint 006 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 to 2026-03-26  
**Status:** 🟢 ACTIVE  
**Theme:** Reliability Window + Operational Hardening

---

## Priorytety

1. 🔥 **P0: Backlog v3 Preparation**
   - Po zamknięciu sprint-002 na 100% przygotować kolejny wsad (`sprint-003`)
   - Cel: gotowy nowy backlog i bezpieczne przełączenie bez utraty historii

2. ⚙️ **P1: Reliability Validation (7-day window)**
   - Potwierdzić stabilność usług 24/7 i timerów po wszystkich zmianach
   - Cel: brak restart-loop, brak regresji disk/memory, spójne tick/report cadence

3. 📝 **P1: Documentation Closeout**
   - Domknąć operacyjne runbooki i checklisty zaległe po sprintach 004/005
   - Cel: dokumentacja zgodna z realnym stanem VPS + pipeline

4. 📈 **P2: KPI Automation**
   - Ustandaryzować i zautomatyzować weekly KPI (disk, alerts, approval lead-time)
   - Cel: gotowy, powtarzalny raport do issue status

---

## Work Breakdown

### Track A: Backlog v3 Prep (P0)
- ✅ Utworzony `workflows/backlog-sprint-003.yaml` (CTOA-021..030)
- ✅ Usługi `ctoa-runner.service` i `ctoa-report.service` przełączone na backlog sprint-003
- ✅ Kontrolny tick rollover + walidacja `backlog_id` na VPS

### Track B: Reliability Window (P1)
- Daily snapshot: `ctoa-runner.timer`, `ctoa-report.timer`, `ctoa-health-live.service`, `ctoa-retention-cleanup.timer`
- Weryfikacja logów dla restart loops i disk spikes
- Sprawdzenie zachowania cooldown dla disk auto-cleanup

### Track C: Documentation Closeout (P1)
- Dodać `docs/runbook-disk-emergency.md`
- Zaktualizować `docs/VALIDATION_CHECKLIST.md`
- Uzupełnić runbook operacyjny o procedurę sprint rollover

### Track D: KPI Automation (P2)
- Rozszerzyć format weekly KPI o approval lead-time
- Zintegrować `runner/health_trend.py` + `runner/runner.py report`
- Dodać jasne progi eskalacji DEFCON 1-2

---

## Definition of Done

- Backlog sprint-003 gotowy i aktywowany bez błędów
- 7 dni stabilnych metryk runtime bez krytycznych alertów
- Runbook i checklista operacyjna domknięte
- Weekly KPI generowany cyklicznie i publikowalny bez ręcznych poprawek

---

## Sprint-005 Closure Reference

- Sprint-005 closed at 100%: **10/10 RELEASED**
- Final state at close:
  - NEW: 0
  - IN_PROGRESS: 0
  - WAITING_APPROVAL: 0
  - RELEASED: 10

---

## Checkpoint (2026-03-12 19:18 UTC)

- Backlog rollover wykonany do `sprint-003`
- Backup poprzedniego stanu zachowany na VPS: `runtime/task-state-sprint-002-closed.yaml`
- Pierwszy tick kontrolny uruchomiony po przełączeniu
- Aktywna fala startowa P0:
   - CTOA-021 `IN_PROGRESS`
   - CTOA-022 `IN_PROGRESS`
   - CTOA-023 `IN_PROGRESS`
- Status counts po ticku: NEW=7, IN_PROGRESS=3, WAITING_APPROVAL=0, RELEASED=0

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 19:15 UTC  
**Planned End:** 2026-03-26 18:00 UTC
