#!/usr/bin/env bash
# =============================================================================
# gs-module-inject.sh  —  CTOA Lua Bot Module Injector
#
# Called by gs-reset.sh Phase 5.
# Discovers all *.lua modules under scripts/lua/modules/  (new additions land here)
# and under scripts/lua/  (core modules).
# Each module must live in its own sub-folder and have an init.lua entry point.
# Copies/syncs them into MYTHIBIA_MOD_DIR so the client picks them up on next load.
#
# Folder contract:
#   scripts/lua/<module-name>/init.lua       <- injected as-is
#   scripts/lua/<module-name>/<other>.lua    <- bundled alongside init.lua
#   scripts/lua/<legacy>.lua                 <- single-file legacy modules
#
# Exit 0 = success | Exit 4 = partial or full failure
# =============================================================================
set -euo pipefail

CTOA_DIR="/opt/ctoa"
SRC_LUA_DIR="$CTOA_DIR/scripts/lua"
MYTHIBIA_MOD_DIR="${MYTHIBIA_MOD_DIR:-/opt/mythibia/modules}"
LOG="$CTOA_DIR/logs/gs-reset.log"
INJECT_LOG="$CTOA_DIR/logs/gs-inject.log"
FAIL=0

log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [GS-INJECT] $*" | tee -a "$LOG" | tee -a "$INJECT_LOG"; }
fail() { log "FAIL: $*"; FAIL=$(( FAIL + 1 )); }
pass() { log "PASS: $*"; }

mkdir -p "$MYTHIBIA_MOD_DIR"
mkdir -p "$(dirname "$INJECT_LOG")"

# ---------------------------------------------------------------------------
# Inject folder-based modules (each has own sub-folder with init.lua)
# ---------------------------------------------------------------------------
log "Scanning folder-based modules in $SRC_LUA_DIR …"
find "$SRC_LUA_DIR" -mindepth 2 -maxdepth 2 -name "init.lua" | sort | while IFS= read -r init_file; do
  mod_dir="$(dirname "$init_file")"
  mod_name="$(basename "$mod_dir")"
  dest="$MYTHIBIA_MOD_DIR/$mod_name"

  log "Injecting module: $mod_name → $dest"
  mkdir -p "$dest"
  # rsync-style: copy all .lua files from module dir, preserving timestamps
  if ! cp -u "$mod_dir"/*.lua "$dest/" 2>/dev/null; then
    fail "Could not inject module: $mod_name"
  else
    pass "Module injected: $mod_name ($(ls -1 "$dest"/*.lua 2>/dev/null | wc -l) files)"
  fi
done

# ---------------------------------------------------------------------------
# Inject legacy single-file modules (direct *.lua in scripts/lua/)
# ---------------------------------------------------------------------------
log "Scanning legacy single-file modules in $SRC_LUA_DIR …"
find "$SRC_LUA_DIR" -maxdepth 1 -name "*.lua" | sort | while IFS= read -r lua_file; do
  mod_name="$(basename "$lua_file" .lua)"
  dest_dir="$MYTHIBIA_MOD_DIR/$mod_name"
  mkdir -p "$dest_dir"
  if ! cp -u "$lua_file" "$dest_dir/init.lua" 2>/dev/null; then
    fail "Could not inject legacy module: $mod_name"
  else
    pass "Legacy module injected: $mod_name → $dest_dir/init.lua"
  fi
done

# ---------------------------------------------------------------------------
# Refresh hash registry after inject
# ---------------------------------------------------------------------------
HASH_REGISTRY="$CTOA_DIR/core/module-hashes.sha256"
find "$SRC_LUA_DIR" -name "*.lua" | sort | xargs sha256sum > "$HASH_REGISTRY" 2>/dev/null || true
log "Hash registry updated: $HASH_REGISTRY"

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
if [ "$FAIL" -gt 0 ]; then
  log "INJECT FAILED — $FAIL module(s) could not be injected."
  exit 4
fi
log "All modules injected successfully."
exit 0
