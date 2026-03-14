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

start_optional_timer() {
  local timer="$1" label="$2"
  if ! systemctl list-unit-files --type=timer --no-legend | awk '{print $1}' | grep -Fxq "$timer"; then
    log "INFO: optional timer not installed: $label ($timer)"
    return 0
  fi
  if systemctl start "$timer"; then
    log "$timer armed."
  else
    log "WARNING: optional timer failed to start: $label ($timer)"
  fi
}

db_endpoint_ready() {
  # Prefer pg_isready when available; fallback to TCP probe.
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1
    return $?
  fi

  # /dev/tcp works in bash; timeout avoids hanging.
  timeout 2 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/5432' >/dev/null 2>&1
  return $?
}

# =============================================================================
# LAYER 0 — Database (everything depends on it)
# =============================================================================
log "--- Layer 0: Database"
if db_endpoint_ready; then
  log "DB endpoint already reachable on 127.0.0.1:5432."
  systemctl reset-failed ctoa-db.service >/dev/null 2>&1 || true
else
  if ! systemctl start ctoa-db.service; then
    log "INFO: ctoa-db.service did not start cleanly; checking endpoint 127.0.0.1:5432 …"
    if db_endpoint_ready; then
      log "Existing DB endpoint is reachable. Continuing startup with external/already-running DB."
      systemctl reset-failed ctoa-db.service >/dev/null 2>&1 || true
    else
      die "Failed to start ctoa-db.service and no DB endpoint reachable on 127.0.0.1:5432"
    fi
  else
    wait_active ctoa-db.service 60
  fi
fi

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
# token rotation timer: optional, non-blocking
start_optional_timer ctoa-mobile-token-rotation.timer mobile-token-rotation

# =============================================================================
# LAYER 3 — MythibIA news pipeline
# =============================================================================
log "--- Layer 3: MythibIA news"
start_svc ctoa-mythibia-news-api.service 30
start_optional_timer ctoa-mythibia-news-watcher.timer mythibia-news-watcher

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
start_optional_timer ctoa-report.timer ctoa-report
start_optional_timer ctoa-retention-cleanup.timer ctoa-retention-cleanup

# =============================================================================
# LAYER 6 — Lab runner
# =============================================================================
log "--- Layer 6: Lab runner"
start_optional_timer ctoa-lab-runner.timer ctoa-lab-runner

# =============================================================================
# LAYER 7 — Auto-trainer
# =============================================================================
log "--- Layer 7: Auto-trainer"
start_optional_timer ctoa-auto-trainer.timer ctoa-auto-trainer

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
systemctl list-units 'ctoa-*' --state=active --no-pager --no-legend 2>&1 | tee -a "$LOG"
exit 0
