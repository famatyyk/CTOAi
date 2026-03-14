#!/usr/bin/env bash
# =============================================================================
# gs-reset.sh  —  CTOA Global Save Reset (VPS only)
# Runs every day at 06:00 UTC via ctoa-gs-reset.timer
#
# Sequence:
#   Phase 1 – SHUTDOWN:   stop all CTOA services in reverse-dependency order
#   Phase 2 – REST:       60-second memory/IO pause  (like Tibia GS save window)
#   Phase 3 – COHERENCE:  file integrity check before any service is restarted
#   Phase 4 – STARTUP:    bring services up in strict dependency order
#   Phase 5 – INJECT:     push new Lua modules into MythibIA client folder
#   Phase 6 – VALIDATE:   commanding agent queries server API for 100% OK signal
#
# Exit codes:  0 = success | 1 = startup failure | 2 = coherence failure
#              3 = validation failure | 4 = inject failure
# =============================================================================
set -euo pipefail

CTOA_DIR="/opt/ctoa"
LOG_DIR="$CTOA_DIR/logs"
LOG="$LOG_DIR/gs-reset.log"
MYTHIBIA_MOD_DIR="${MYTHIBIA_MOD_DIR:-/opt/mythibia/modules}"
GS_TIMEOUT_WAIT="${GS_TIMEOUT_WAIT:-60}"     # seconds to rest between stop and start
API_CHECK_RETRIES="${API_CHECK_RETRIES:-5}"
API_HEALTH_URL="${API_HEALTH_URL:-${API_CHECK_URL:-http://127.0.0.1:8890/health}}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8890}"
GS_REQUIRE_API_VALIDATION="${GS_REQUIRE_API_VALIDATION:-false}"

mkdir -p "$LOG_DIR"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [GS-RESET] $*" | tee -a "$LOG"; }
log_section() { log ""; log "==== $* ===="; }
die() { log "FATAL: $*"; exit "${2:-1}"; }

# ---------------------------------------------------------------------------
# PHASE 1 — SHUTDOWN  (reverse dependency order)
# ---------------------------------------------------------------------------
log_section "PHASE 1 — SHUTDOWN"

STOP_ORDER=(
  ctoa-agents-orchestrator.timer
  ctoa-agents-orchestrator.service
  ctoa-auto-trainer.timer
  ctoa-auto-trainer.service
  ctoa-lab-runner.timer
  ctoa-lab-runner.service
  ctoa-report.timer
  ctoa-report.service
  ctoa-retention-cleanup.timer
  ctoa-retention-cleanup.service
  ctoa-mythibia-news-watcher.timer
  ctoa-mythibia-news-watcher.service
  ctoa-mythibia-news-api.service
  ctoa-runner.timer
  ctoa-runner.service
  ctoa-mobile-token-rotation.timer
  ctoa-mobile-token-rotation.service
  ctoa-mobile-console.service
  ctoa-health-live.service
  ctoa-db.service
)

for svc in "${STOP_ORDER[@]}"; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    log "Stopping $svc …"
    systemctl stop "$svc" || log "WARNING: could not stop $svc (may already be stopped)"
  else
    log "Skip (inactive): $svc"
  fi
done

log "All services stopped."

# ---------------------------------------------------------------------------
# PHASE 2 — REST  (memory/IO pause — the GS window)
# ---------------------------------------------------------------------------
log_section "PHASE 2 — REST ($GS_TIMEOUT_WAIT seconds)"
log "Sleeping for $GS_TIMEOUT_WAIT seconds — global save window …"
sleep "$GS_TIMEOUT_WAIT"
log "Rest complete."

# ---------------------------------------------------------------------------
# PHASE 3 — COHERENCE CHECK
# ---------------------------------------------------------------------------
log_section "PHASE 3 — COHERENCE CHECK"
bash "$CTOA_DIR/scripts/ops/gs-coherence-check.sh" 2>&1 | tee -a "$LOG"
COHERENCE_EXIT="${PIPESTATUS[0]}"
if [ "$COHERENCE_EXIT" -ne 0 ]; then
  die "Coherence check FAILED (exit $COHERENCE_EXIT). Aborting startup." 2
fi
log "Coherence check PASSED."

# ---------------------------------------------------------------------------
# PHASE 4 — STARTUP  (strict dependency order)
# ---------------------------------------------------------------------------
log_section "PHASE 4 — STARTUP"
bash "$CTOA_DIR/scripts/ops/gs-startup-sequence.sh" 2>&1 | tee -a "$LOG"
STARTUP_EXIT="${PIPESTATUS[0]}"
if [ "$STARTUP_EXIT" -ne 0 ]; then
  die "Startup sequence FAILED (exit $STARTUP_EXIT)." 1
fi
log "All services started."

# ---------------------------------------------------------------------------
# PHASE 5 — MODULE INJECT
# ---------------------------------------------------------------------------
log_section "PHASE 5 — LUA MODULE INJECT"
bash "$CTOA_DIR/scripts/ops/gs-module-inject.sh" 2>&1 | tee -a "$LOG"
INJECT_EXIT="${PIPESTATUS[0]}"
if [ "$INJECT_EXIT" -ne 0 ]; then
  die "Module inject FAILED (exit $INJECT_EXIT)." 4
fi
log "Module inject PASSED."

# ---------------------------------------------------------------------------
# PHASE 6 — API VALIDATION  (commanding agent checks server 100% OK)
# ---------------------------------------------------------------------------
log_section "PHASE 6 — API VALIDATION"

CANDIDATE_HEALTH_URLS=(
  "$API_HEALTH_URL"
  "http://127.0.0.1:8890/health"
  "http://127.0.0.1:8890/api/health"
  "http://127.0.0.1:7777/health"
  "http://127.0.0.1:7777/api/health"
)

ATTEMPTS=0
SUCCESS=false
SELECTED_HEALTH_URL=""
while [ "$ATTEMPTS" -lt "$API_CHECK_RETRIES" ]; do
  ATTEMPTS=$(( ATTEMPTS + 1 ))
  for url in "${CANDIDATE_HEALTH_URLS[@]}"; do
    log "API health check attempt $ATTEMPTS/$API_CHECK_RETRIES → $url"
    HTTP_CODE=$(curl --silent --max-time 10 --output /dev/null \
      --write-out "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
      SUCCESS=true
      SELECTED_HEALTH_URL="$url"

      case "$url" in
        */api/health) API_BASE_URL="${url%/health}" ;;
        */health) API_BASE_URL="${url%/health}" ;;
      esac

      log "Server responded 200 OK at $SELECTED_HEALTH_URL."
      break 2
    fi
    log "Got HTTP $HTTP_CODE from $url."
  done
  log "No healthy API endpoint detected yet; waiting 10 s before retry …"
  sleep 10
done

if [ "$SUCCESS" != "true" ]; then
  if [ "$GS_REQUIRE_API_VALIDATION" = "true" ]; then
    die "API validation FAILED after $API_CHECK_RETRIES attempts." 3
  fi
  log "WARNING: API validation failed after $API_CHECK_RETRIES attempts; continuing (GS_REQUIRE_API_VALIDATION=false)."
  log "===== GS RESET CYCLE COMPLETE WITH WARNINGS — $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
  exit 0
fi

# Post GS validation via python commanding agent
log "Running commanding agent API compliance check (API_BASE_URL=$API_BASE_URL) …"
cd "$CTOA_DIR"
source .venv/bin/activate || true
API_BASE_URL="$API_BASE_URL" API_HEALTH_URL="${SELECTED_HEALTH_URL:-$API_HEALTH_URL}" \
python3 scripts/ops/gs-api-validator.py 2>&1 | tee -a "$LOG"
VALIDATOR_EXIT="${PIPESTATUS[0]}"
if [ "$VALIDATOR_EXIT" -ne 0 ]; then
  die "Commanding agent API check FAILED (exit $VALIDATOR_EXIT)." 3
fi

log ""
log "===== GS RESET CYCLE COMPLETE — $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
exit 0
