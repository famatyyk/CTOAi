# Sprint 003 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 to 2026-03-26 (2 weeks)  
**Status:** 🟢 ACTIVE  
**Theme:** Stabilization + Capacity + Approval Flow

---

## Priorytety

1. 🔥 **P0: Disk Pressure Mitigation (VPS)**
   - Obecny alert: disk usage ~98.88%
   - Cel: zejść poniżej 80% i utrzymać trend stabilny

2. ⚙️ **P1: Ops Reliability**
   - Ustabilizować live health stream + retencję logów
   - Zmniejszyć noise alertów i doprecyzować progi

3. ✅ **P1: Approval Throughput**
   - Skrócić czas `WAITING_APPROVAL`
   - Uporządkować kolejkę zadań P0 i kryteria akceptacji

4. 📈 **P2: Sprint Observability**
   - Czytelny tygodniowy report KPI
   - Widoczność SLA i ryzyk operacyjnych

---

## Work Breakdown

### Track A: Capacity Recovery (P0)
- Audyt zajętości: `/opt/ctoa`, logi, cache, artefakty
- Bezpieczne cleanupy (stare logi/backupy)
- Logrotate + limity retencji
- Weryfikacja po cleanupie: disk < 80%

### Track B: Monitoring Hardening (P1)
- Uporządkowanie progów alertów
- Spięcie alertów z akcjami operacyjnymi
- Snapshot trendów (24h/7d)

### Track C: Flow & Approval (P1)
- Przegląd zadań `WAITING_APPROVAL`
- Reguły priorytetyzacji P0/P1
- Skrócenie lead-time approval

### Track D: Documentation Delta (P2)
- Krótkie runbooki „disk emergency”
- Aktualizacja checklisty operacyjnej

---

## Definition of Done

- Disk usage VPS stabilnie < 80%
- `ctoa-health-live.service` działa ciągle bez restart-loop
- Czas `WAITING_APPROVAL` skrócony względem stanu bazowego
- Raport tygodniowy zawiera KPI: disk, alert count, approval lead-time

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 18:00 UTC  
**Planned End:** 2026-03-26 18:00 UTC
