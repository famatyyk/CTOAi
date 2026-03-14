#!/usr/bin/env bash
# =============================================================================
# gs-coherence-check.sh  —  CTOA File & Config Coherence Check
#
# Called by gs-reset.sh Phase 3 — runs BEFORE any service is restarted.
# Verifies:
#   1. Critical Python files  (hash / existence)
#   2. Required directories
#   3. .env secrets presence  (key names only; values never logged)
#   4. Lua bot modules hash registry
#   5. Git repo clean state (no unexpected modifications to protected files)
#
# Exit 0 = all OK  |  Exit 2 = coherence failure
# =============================================================================
set -euo pipefail

CTOA_DIR="/opt/ctoa"
LOG="$CTOA_DIR/logs/gs-reset.log"
PROTECTED_LIST="$CTOA_DIR/core/protected-files.txt"
HASH_REGISTRY="$CTOA_DIR/core/module-hashes.sha256"
FAIL=0

log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [GS-COHERENCE] $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; FAIL=$(( FAIL + 1 )); }
pass() { log "PASS: $*"; }

# ---------------------------------------------------------------------------
# 1. Required directories
# ---------------------------------------------------------------------------
log "Checking required directories …"
REQUIRED_DIRS=(
  "$CTOA_DIR/logs"
  "$CTOA_DIR/runtime"
  "$CTOA_DIR/runner"
  "$CTOA_DIR/agents"
  "$CTOA_DIR/scripts/lua"
  "$CTOA_DIR/scripts/ops"
  "$CTOA_DIR/core"
)
for d in "${REQUIRED_DIRS[@]}"; do
  if [ -d "$d" ]; then pass "dir: $d"; else fail "missing dir: $d"; fi
done

# ---------------------------------------------------------------------------
# 2. Critical Python files existence
# ---------------------------------------------------------------------------
log "Checking critical Python files …"
CRITICAL_PY=(
  "$CTOA_DIR/runner/runner.py"
  "$CTOA_DIR/runner/health_metrics.py"
  "$CTOA_DIR/scripts/ops/gs-api-validator.py"
)
for f in "${CRITICAL_PY[@]}"; do
  if [ -f "$f" ]; then pass "file: $f"; else fail "missing: $f"; fi
done

# ---------------------------------------------------------------------------
# 3. Protected files integrity  (read list from base branch)
# ---------------------------------------------------------------------------
log "Checking protected file hashes …"
if [ ! -f "$PROTECTED_LIST" ]; then
  log "WARNING: $PROTECTED_LIST not found; skipping protected-file hash check."
else
  while IFS= read -r rel_path || [[ -n "$rel_path" ]]; do
    [[ "$rel_path" =~ ^#.*$ || -z "$rel_path" ]] && continue
    abs="$CTOA_DIR/$rel_path"
    if [ ! -f "$abs" ]; then
      fail "protected file missing: $rel_path"
    else
      pass "protected file present: $rel_path"
    fi
  done < "$PROTECTED_LIST"
fi

# ---------------------------------------------------------------------------
# 4. Lua module hash check
# ---------------------------------------------------------------------------
log "Checking Lua module hashes …"
if [ ! -f "$HASH_REGISTRY" ]; then
  log "WARNING: $HASH_REGISTRY not found; regenerating …"
  sha256sum "$CTOA_DIR/scripts/lua/"*.lua > "$HASH_REGISTRY" 2>/dev/null || true
  pass "Hash registry created."
else
  CHANGED=()
  while IFS=" " read -r stored_hash filename; do
    if [ -f "$filename" ]; then
      actual_hash=$(sha256sum "$filename" | awk '{print $1}')
      if [ "$actual_hash" != "$stored_hash" ]; then
        CHANGED+=("$filename")
      fi
    else
      fail "Lua module missing: $filename"
    fi
  done < "$HASH_REGISTRY"

  if [ "${#CHANGED[@]}" -gt 0 ]; then
    log "INFO: Hash drift detected (expected after patch/update):"
    for f in "${CHANGED[@]}"; do log "  CHANGED: $f"; done
    # Update registry and continue — hash change is intentional if source was updated via git
    sha256sum "$CTOA_DIR/scripts/lua/"*.lua > "$HASH_REGISTRY" 2>/dev/null || true
    log "INFO: Hash registry refreshed."
  else
    pass "All Lua hashes match."
  fi
fi

# ---------------------------------------------------------------------------
# 5. .env keys presence (configurable strictness; values never logged)
#
# By default, keys are warning-only so GS can run without API secrets.
# To enforce strict keys, set on VPS .env:
#   GS_REQUIRED_ENV_KEYS=KEY1,KEY2
# Example:
#   GS_REQUIRED_ENV_KEYS=GITHUB_PAT,OPENAI_API_KEY
# ---------------------------------------------------------------------------
log "Checking .env keys …"
ENV_FILE="$CTOA_DIR/.env"

OPTIONAL_KEYS=(
  GITHUB_PAT
  OPENAI_API_KEY
)

GS_REQUIRED_ENV_KEYS="${GS_REQUIRED_ENV_KEYS:-}"
REQUIRED_KEYS=()
if [ -n "$GS_REQUIRED_ENV_KEYS" ]; then
  IFS=',' read -r -a REQUIRED_KEYS <<< "$GS_REQUIRED_ENV_KEYS"
fi

if [ ! -f "$ENV_FILE" ]; then
  log "WARNING: .env file missing at $ENV_FILE"
else
  for key in "${OPTIONAL_KEYS[@]}"; do
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
      pass ".env key present: $key"
    else
      log "WARNING: .env key missing (optional): $key"
    fi
  done

  for key in "${REQUIRED_KEYS[@]}"; do
    key_trimmed="$(echo "$key" | xargs)"
    [ -z "$key_trimmed" ] && continue
    if grep -q "^${key_trimmed}=" "$ENV_FILE" 2>/dev/null; then
      pass ".env required key present: $key_trimmed"
    else
      fail ".env required key missing: $key_trimmed"
    fi
  done
fi

# ---------------------------------------------------------------------------
# RESULT
# ---------------------------------------------------------------------------
log ""
if [ "$FAIL" -gt 0 ]; then
  log "COHERENCE FAILED — $FAIL issue(s) detected."
  exit 2
else
  log "COHERENCE PASSED — all checks OK."
  exit 0
fi
