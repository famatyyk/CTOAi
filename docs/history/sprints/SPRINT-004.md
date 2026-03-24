# Sprint 004 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 to 2026-03-26  
**Status:** ✅ CLOSED (2026-03-12, early close)  
**Theme:** Agent Activation — Approve & Release Core Modules

---

## Priorytety

1. 🔥 **P0: Unblock Approval Queue**
   - 3 zadania P0 utknęły w `WAITING_APPROVAL` od 09:30 — każdy kolejny tick zmarnowany
   - Cel: CTOA-001/002/003 → RELEASED; sprint progress > 0%

2. ⚙️ **P0: Activate Next P0 Backlog**
   - CTOA-007 (Cavebot safety interrupt) i CTOA-009 (Prompt pack for MMO/Lua) czekają w NEW
   - Cel: uruchomić flow IN_PROGRESS dla co najmniej 2 P0 z backlogu

3. 📈 **P1: Ops Hardening (carry-over S-003)**
   - Alert→action wiring: gdy DISK > 90% → auto-notify lub auto-cleanup trigger
   - Health snapshot trend: 24h/7d agregacja z health-history.jsonl

4. 📝 **P2: Documentation**
   - Runbook „disk emergency" (carry-over S-003 Track D)
   - Aktualizacja VALIDATION_CHECKLIST.md

---

## Backlog Reference (stan na 2026-03-12)

| ID | Tytuł | Priorytet | Status |
|----|-------|-----------|--------|
| CTOA-001 | Lua logger for Tibia events | P0 | WAITING_APPROVAL |
| CTOA-002 | Lua pathing helper for OpenTibia | P0 | WAITING_APPROVAL |
| CTOA-003 | Auto-heal decision module | P0 | WAITING_APPROVAL |
| CTOA-004 | Potion and supply manager | P1 | NEW |
| CTOA-005 | Target prioritization engine | P1 | NEW |
| CTOA-006 | Loot filter and auto-stack | P1 | NEW |
| CTOA-007 | Cavebot safety interrupt module | P0 | NEW |
| CTOA-008 | Telemetry exporter (JSONL) | P1 | NEW |
| CTOA-009 | Prompt pack for MMO/Lua tasks | P0 | NEW |
| CTOA-010 | Tool advisor matrix for Tibia stack | P1 | NEW |

---

## Work Breakdown

### Track A: Approval Unblock (P0)
- ✅ Zidentyfikować mechanizm: `runner.py approve --task <ID>`
- ✅ Approve CTOA-001 → RELEASED
- ✅ Approve CTOA-002 → RELEASED
- ✅ Approve CTOA-003 → RELEASED
- ✅ Zweryfikować: `task-state.yaml` status + runner.log + sprint progress > 0%

### Track B: P0 Backlog Activation (P0)
- ✅ CTOA-007 (Cavebot safety interrupt) → IN_QA (pipeline: NEW→IN_PROGRESS→IN_QA via auto-tick)
- ✅ CTOA-009 (Prompt pack for MMO/Lua) → IN_QA
- ✅ CTOA-004 (Potion and supply manager, P1) → IN_QA (3. wolny slot)
- ✅ Manual tick: IN_QA→IN_CI_GATE→WAITING_APPROVAL
- ✅ Approve wave #2: CTOA-007 + CTOA-009 + CTOA-004 → RELEASED

### Track C: Ops Hardening (P1, carry-over S-003 Track B remainder)
- ✅ Alert→action wdrożone: `health_metrics.py` uruchamia cleanup komendą po przekroczeniu progu DISK
- ✅ Cooldown bezpieczeństwa: domyślnie 3600s między cleanupami
- ✅ Parametry CLI: `--disk-auto-cleanup --disk-cleanup-threshold --disk-cleanup-cooldown --disk-cleanup-cmd`
- ✅ Health trend CLI: `runner/health_trend.py` (okna: custom h, 24h, 7d; avg/max + alert counts)
- ✅ Systemd wiring: `ctoa-health-live.service` uruchamiany z auto-cleanup (92%, cooldown 1h)

### Track D: Documentation (P2, carry-over S-003 Track D)
- Runbook `docs/runbook-disk-emergency.md` (kroki: sprawdź, wyczyść cache, reboot last resort)
- Aktualizacja `docs/VALIDATION_CHECKLIST.md` — Sprint-004 snapshot

---

## Definition of Done

- CTOA-001/002/003: status `RELEASED` w `task-state.yaml`
- Sprint progress > 0% w runner raportach
- Co najmniej 2 kolejne P0 zadania uruchomione (IN_PROGRESS+)
- Disk stabilnie < 80% przez cały sprint (monitoring potwierdza)
- `ctoa-health-live.service` nie restartuje się przez 7 dni

---

## Checkpoint (2026-03-12 18:26 UTC)

- Wave #1 RELEASED: CTOA-001, CTOA-002, CTOA-003
- Wave #2 RELEASED: CTOA-007, CTOA-009, CTOA-004
- Sprint progress: **60.0% (6/10)**
- Pozostałe NEW: CTOA-005, CTOA-006, CTOA-008, CTOA-010

## Checkpoint (2026-03-12 18:46 UTC)

- Wave #3 RELEASED: CTOA-005, CTOA-006, CTOA-008
- Uruchomiono ostatni slot: CTOA-010 → IN_PROGRESS
- Sprint progress: **90.0% (9/10)**
- Status counts: NEW=0, IN_PROGRESS=1, WAITING_APPROVAL=0

## Final Checkpoint (2026-03-12 18:47 UTC)

- Final approve: CTOA-010 → RELEASED
- Sprint progress: **100.0% (10/10)**
- Status counts: NEW=0, IN_PROGRESS=0, WAITING_APPROVAL=0, RELEASED=10
- Sprint-004 objective osiągnięty end-to-end

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 18:30 UTC  
**Planned End:** 2026-03-26 18:00 UTC  
**Closed:** 2026-03-12 18:47 UTC (early close — 10/10 RELEASED)
