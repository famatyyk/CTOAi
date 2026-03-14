#!/usr/bin/env bash
# =============================================================================
# gs-startup-sequence.sh  —  CTOA Ordered Startup After GS Reset
#
# Called by gs-reset.sh Phase 4.
# Services are started in strict bottom-up dependency order with readiness probes.
# Exit 0 = all started  |  Exit 1 = fatal failure
# =============================================================================
set -euo pipefail

CTOA_DIR="/opt/ctoa"
LOG="$CTOA_DIR/logs/gs-reset.log"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [GS-STARTUP] $*" | tee -a "$LOG"; }
die() { log "FATAL: $*"; exit 1; }

wait_active() {
  local svc="$1" maxwait="${2:-30}" elapsed=0
  while [ "$elapsed" -lt "$maxwait" ]; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      log "$svc is ACTIVE."
      return 0
    fi
    sleep 2; elapsed=$(( elapsed + 2 ))
  done
  die "$svc did not become active within ${maxwait}s"
}

start_svc() {
  local svc="$1" wait="${2:-30}"
  log "Starting $svc …"
  systemctl start "$svc" || die "Failed to start $svc"
  # Oneshot services don't stay "active"; skip the probe for them
  case "$svc" in
    *.timer) ;;
    *) wait_active "$svc" "$wait" ;;
  esac
}

# =============================================================================
# LAYER 0 — Database (everything depends on it)
# =============================================================================
log "--- Layer 0: Database"
start_svc ctoa-db.service 60

# =============================================================================
# LAYER 1 — Core monitoring & health
# =============================================================================
log "--- Layer 1: Health / monitoring"
start_svc ctoa-health-live.service 20

# =============================================================================
# LAYER 2 — Mobile console  (auth token must refresh before agents use it)
# =============================================================================
log "--- Layer 2: Mobile console"
start_svc ctoa-mobile-console.service 20
# token rotation timer: just enable the schedule, not blocking
systemctl start ctoa-mobile-token-rotation.timer || log "WARNING: could not start mobile-token-rotation.timer"

# =============================================================================
# LAYER 3 — MythibIA news pipeline
# =============================================================================
log "--- Layer 3: MythibIA news"
start_svc ctoa-mythibia-news-api.service 30
systemctl start ctoa-mythibia-news-watcher.timer || log "WARNING: could not start mythibia-news-watcher.timer"

# =============================================================================
# LAYER 4 — Core runner
# =============================================================================
log "--- Layer 4: Core runner timer"
systemctl start ctoa-runner.timer || die "Failed to start ctoa-runner.timer"
log "ctoa-runner.timer armed."

# =============================================================================
# LAYER 5 — Reports & retention
# =============================================================================
log "--- Layer 5: Reports and retention"
systemctl start ctoa-report.timer       || log "WARNING: could not start ctoa-report.timer"
systemctl start ctoa-retention-cleanup.timer || log "WARNING: could not start ctoa-retention-cleanup.timer"

# =============================================================================
# LAYER 6 — Lab runner
# =============================================================================
log "--- Layer 6: Lab runner"
systemctl start ctoa-lab-runner.timer || log "WARNING: could not start ctoa-lab-runner.timer"

# =============================================================================
# LAYER 7 — Auto-trainer
# =============================================================================
log "--- Layer 7: Auto-trainer"
systemctl start ctoa-auto-trainer.timer || log "WARNING: could not start ctoa-auto-trainer.timer"

# =============================================================================
# LAYER 8 — Agents orchestrator  (last, depends on all layers above)
# =============================================================================
log "--- Layer 8: Agents orchestrator"
systemctl start ctoa-agents-orchestrator.timer || die "Failed to start ctoa-agents-orchestrator.timer"
log "ctoa-agents-orchestrator.timer armed."

# =============================================================================
# SUMMARY
# =============================================================================
log ""
log "Startup sequence complete."
log "Active CTOA units:"
systemctl list-units 'ctoa-*' --no-pager --no-legend 2>&1 | tee -a "$LOG"
exit 0
