# Sprint 007 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 to 2026-03-26  
**Status:** 🟢 ACTIVE  
**Theme:** Documentation Completion + KPI Automation

---

## Priorytety

1. 🔥 **P0: Documentation Closeout**
   - Domknąć zaległe runbooki i checklisty operacyjne
   - Cel: pełna zgodność dokumentacji z realnym stanem VPS

2. ⚙️ **P1: KPI Automation Hardening**
   - Ustabilizować generowanie tygodniowych metryk operacyjnych
   - Cel: automatyczny, powtarzalny raport bez ręcznych poprawek

3. 🧪 **P1: Reliability Guardrails**
   - Doprecyzować kontrole driftu dla usług i timerów
   - Cel: szybkie wykrycie regresji konfiguracji 24x7

4. 📈 **P2: Sprint Governance**
   - Uspójnić reguły start/close sprintu i rollover state
   - Cel: standardowy playbook na kolejne sprinty

---

## Work Breakdown

### Track A: Documentation Completion (P0)
- Dodać docs/runbook-disk-emergency.md
- Uzupełnić docs/VALIDATION_CHECKLIST.md o runtime checks
- Zweryfikować zgodność z deploy/vps/SETUP.md i docs/ARCHITECTURE.md

### Track B: KPI Automation (P1)
- Rozszerzyć runner/weekly_report.py o stały układ KPI
- Spiąć runner/health_trend.py z weekly output
- Dodać metrykę approval lead-time (avg, p95)

### Track C: Reliability Guardrails (P1)
- Dodać check driftu usług i timerów (runner/report/health/retention)
- Wprowadzić czytelny status pass/fail do raportu
- Dopisać szybki command path w scripts/ops/ctoa-vps.ps1

### Track D: Governance (P2)
- Ustandaryzować sprint closure gate (release count + brak waiting approvals)
- Utrwalić procedurę backupu state przy backlog rollover
- Przygotować szablon kickoff/closure do reużycia

---

## Definition of Done

- Runbook disk emergency i checklista operacyjna domknięte
- Weekly KPI generuje komplet metryk bez błędów
- Drift checks usług działają i raportują czytelny wynik
- Sprint governance playbook gotowy do reużycia

---

## Sprint-006 Closure Reference

- Sprint-006 closed at 100%: 10/10 RELEASED
- Final state at close:
  - NEW: 0
  - IN_PROGRESS: 0
  - WAITING_APPROVAL: 0
  - RELEASED: 10

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 19:30 UTC  
**Planned End:** 2026-03-26 18:00 UTC
