# Sprint 003 Plan - CTOA AI Toolkit
**Sprint Period:** 2026-03-12 (early close: 2026-03-12)  
**Status:** ✅ CLOSED  
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

### Track A: Capacity Recovery (P0) ✅ DONE
- ✅ Pip cache cleanup 8.3GB: disk 99% → 73%
- ✅ Logrotate (daily, 14 copies)
- ✅ `ctoa-retention-cleanup.timer` (daily 03:15 UTC) + `cleanup-retention.sh`
- ✅ Retention service manual run: status=0/SUCCESS

### Track B: Monitoring Hardening (P1) ✅ DONE
- ✅ CPU alert debounce: `run_watch()` fires CPU alert only after 3 consecutive high samples (~30s); single spikes suppressed
- ✅ `--cpu-sustain-samples` CLI flag added (default: 3, tunable without code change)
- ↪ Alert→action wiring: **carry-over → Sprint-004 Track C**
- ↪ Snapshot trendów (24h/7d): **carry-over → Sprint-004 Track C**

### Track C: Flow & Approval (P1) ↪ CARRY-OVER
- Przegląd zadań `WAITING_APPROVAL` — odkryte: CTOA-001/002/003 (3x P0, stuck od 09:30)
- Mechanizm approval zidentyfikowany: `runner.py approve --task CTOA-XXX`
- **Pełna realizacja → Sprint-004 Track A (P0)**

### Track D: Documentation Delta (P2) ↪ CARRY-OVER
- Runbooki „disk emergency": **Sprint-004 Track D**
- Aktualizacja checklisty operacyjnej: **Sprint-004 Track D**

---

## Definition of Done

- Disk usage VPS stabilnie < 80%
- `ctoa-health-live.service` działa ciągle bez restart-loop
- Czas `WAITING_APPROVAL` skrócony względem stanu bazowego
- Raport tygodniowy zawiera KPI: disk, alert count, approval lead-time

---

## Checkpoint (2026-03-12)

- P0 mitigation executed: safe cleanup of pip caches and temporary pip artifacts on VPS.
- Disk usage improved from 99% to 73% on `/dev/sda1`.
- Live monitor confirms status moved from ALERT to OK for disk threshold.
- Retention hardening deployed: logrotate (14 days) + `ctoa-retention-cleanup.timer` (daily 03:15 UTC) active.
- CPU debounce deployed (commit `662e67a`): sustained 3-sample check prevents false-positive ALERT on brief spikes.

## Closure Notes (2026-03-12)

**Delivered:**
- P0 disk crisis resolved (99% → 73%), retention hardening deployed and validated
- CPU alert debounce (3-sample sustain, ~30s) eliminates false-positive STATUS=ALERT from short spikes
- ctoa-health-live.service: stable 5h+, logrotate + cleanup timer: active
- SSH/ops access fixed (fallback defaults in ctoa-vps.ps1)

**Carry-over to Sprint-004:**
- CTOA-001/002/003 still in WAITING_APPROVAL (approval mechanism discovered: `runner.py approve`)
- Alert→action wiring, trend snapshots, runbooks

---

## Execution

**Mode:** STRATEGOS (autonomicznie)  
**Escalate only on:** DEFCON 1-2, budget >10%, blokada decyzji

**Start:** 2026-03-12 18:00 UTC  
**Closed:** 2026-03-12 18:30 UTC (early close — P0/P1 delivered, carry-over to S-004)
