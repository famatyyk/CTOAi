# Sprint 005 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 to 2026-03-26  
**Status:** 🟢 ACTIVE  
**Theme:** Stabilization Window + Backlog Refresh

---

## Priorytety

1. 🔥 **P0: Backlog Refresh (sprint-002)**
   - Po zamknięciu 10/10 zadań potrzebny nowy wsad i reguły harmonogramu
   - Cel: gotowy backlog `sprint-002` + spójne priorytety P0/P1

2. ⚙️ **P1: Reliability Validation (7d)**
   - Potwierdzić stabilność: `ctoa-runner.timer`, `ctoa-report.timer`, `ctoa-health-live.service`, `ctoa-retention-cleanup.timer`
   - Cel: brak regresji po zmianach Track C (disk auto-action + CPU debounce)

3. 📝 **P1: Documentation Closeout (carry-over)**
   - Domknąć brakujące artefakty dokumentacyjne ze Sprint-004 Track D
   - Cel: operacyjne runbooki i checklista aktualna po zmianach runtime

4. 📈 **P2: KPI Reporting Pack**
   - Ustandaryzować metryki tygodniowe: disk, alert count, approval lead-time
   - Cel: gotowy raport do status issue i przeglądu operacyjnego

---

## Work Breakdown

### Track A: Backlog Refresh (P0)
- ✅ Dodany nowy backlog (`workflows/backlog-sprint-002.yaml`) z zadaniami CTOA-011..020
- ✅ `max_parallel_tasks=3` + reguły priorytetyzacji P0/P1/P2
- ✅ `runner.py` wspiera przełączenie backlogu przez `CTOA_BACKLOG_FILE` i reset stanu przy zmianie `backlog_id`
- ✅ VPS podpięty pod sprint-002 (`ctoa-runner.service`, `ctoa-report.service`)
- ✅ Pierwszy tick kontrolny wykonany

### Track B: Reliability Validation (P1)
- Przegląd statusów usług i timerów (daily checks)
- Weryfikacja logów: brak restart-loop, brak disk regressions > 80%
- Przegląd auto-cleanup cooldown i trigger frequency

### Track C: Documentation Closeout (P1)
- Dodać `docs/runbook-disk-emergency.md`
- Uzupełnić `docs/VALIDATION_CHECKLIST.md` o sprint runtime checks
- Aktualizacja mapy operacyjnej po wdrożonych timerach i monitoringu

### Track D: KPI Reporting (P2)
- Dodać stały format tygodniowego raportu KPI
- Oprzeć metryki o `runner/health_trend.py` + `runner/runner.py report`
- Zdefiniować progi eskalacji DEFCON 1-2

---

## Definition of Done

- Nowy backlog sprint-002 gotowy i załadowany bez błędów
- 7 dni stabilnej pracy usług bez krytycznych alertów disk/memory
- Runbook i checklista operacyjna zaktualizowane
- Raport KPI gotowy do publikacji cyklicznej

---

## Sprint-004 Closure Reference

- Sprint-004 closed at 100%: **10/10 RELEASED**
- Final state at close:
  - NEW: 0
  - IN_PROGRESS: 0
  - WAITING_APPROVAL: 0
  - RELEASED: 10

---

## Checkpoint (2026-03-12 18:53 UTC)

- Sprint-005 backlog aktywny na VPS: `backlog_id: sprint-002`
- Pierwszy tick uruchomił 3 zadania P0:
   - CTOA-011 `IN_PROGRESS`
   - CTOA-012 `IN_PROGRESS`
   - CTOA-013 `IN_PROGRESS`
- Status counts po ticku: NEW=7, IN_PROGRESS=3, WAITING_APPROVAL=0, RELEASED=0

## Checkpoint (2026-03-12 18:55 UTC)

- Wave #1 gotowa do approve po auto-przejściach (IN_PROGRESS→IN_QA→IN_CI_GATE→WAITING_APPROVAL)
- Approved: CTOA-011, CTOA-012, CTOA-013 → RELEASED
- Sprint progress: **30.0% (3/10)**
- Status counts: NEW=7, IN_PROGRESS=0, WAITING_APPROVAL=0, RELEASED=3

## Checkpoint (2026-03-12 18:57 UTC)

- Wave #2 activated: CTOA-014, CTOA-015, CTOA-016
- Standard cycle executed: IN_PROGRESS→IN_QA→IN_CI_GATE→WAITING_APPROVAL
- Approved: CTOA-014, CTOA-015, CTOA-016 → RELEASED
- Sprint progress: **60.0% (6/10)**
- Status counts: NEW=4, IN_PROGRESS=0, WAITING_APPROVAL=0, RELEASED=6

## Checkpoint (2026-03-12 19:01 UTC)

- Wave #3 activated: CTOA-017, CTOA-018, CTOA-019
- Standard cycle executed: IN_PROGRESS→IN_QA→IN_CI_GATE→WAITING_APPROVAL
- Approved: CTOA-017, CTOA-018, CTOA-019 → RELEASED
- Sprint progress: **90.0% (9/10)**
- Status counts: NEW=1, IN_PROGRESS=0, WAITING_APPROVAL=0, RELEASED=9

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 18:50 UTC  
**Planned End:** 2026-03-26 18:00 UTC
