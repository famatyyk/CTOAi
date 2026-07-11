#!/usr/bin/env bash
# AGENT 9: DEVOPS MASTER — VPS Deploy Script
# Usage: ./deploy.sh [VPS_IP] [VPS_USER]
# Requires: ssh key auth configured, Docker installed on VPS
set -euo pipefail

VPS_IP="${1:-${BOT_VPS_IP:?'Set BOT_VPS_IP env var or pass as arg'}}"
VPS_USER="${2:-${BOT_VPS_USER:-ubuntu}}"
DEPLOY_DIR="${BOT_DEPLOY_DIR:-/opt/tibia-bot}"

validate_remote_user() {
  local value="$1"
  if [[ ! "$value" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
    echo "ERROR: VPS user must be a valid Linux username: $value" >&2
    exit 1
  fi
}

validate_remote_host() {
  local value="$1"
  if [[ ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$ ]]; then
    echo "ERROR: VPS host must be a hostname or IPv4 address without shell metacharacters: $value" >&2
    exit 1
  fi
  if [[ "$value" == *".."* ]]; then
    echo "ERROR: VPS host must not contain empty labels: $value" >&2
    exit 1
  fi
}

validate_deploy_dir() {
  local value="$1"
  if [[ "$value" != /opt/* ]]; then
    echo "ERROR: BOT_DEPLOY_DIR must stay under /opt: $value" >&2
    exit 1
  fi
  if [[ "$value" == *".."* || "$value" == *"//"* || ! "$value" =~ ^/opt/[A-Za-z0-9._/-]+$ ]]; then
    echo "ERROR: BOT_DEPLOY_DIR contains unsupported path characters: $value" >&2
    exit 1
  fi
}

quote_remote_path() {
  printf '%q' "$1"
}

validate_remote_user "$VPS_USER"
validate_remote_host "$VPS_IP"
validate_deploy_dir "$DEPLOY_DIR"

REMOTE="$VPS_USER@$VPS_IP"
REMOTE_DEPLOY_DIR="$(quote_remote_path "$DEPLOY_DIR")"

echo "=== AGENT 9: DEVOPS MASTER — Deploying Tibia Bot ==="
echo "Target: $REMOTE:$DEPLOY_DIR"

# 1. Ensure remote dir exists
ssh -- "$REMOTE" "install -d -m 0750 -- $REMOTE_DEPLOY_DIR"

# 2. Sync code (rsync faster than full clone)
rsync -az --delete \
  -e ssh \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='data/*.db' \
  --exclude='data/*.log' \
  -- . "$REMOTE:$DEPLOY_DIR/"

# 3. Copy env file if exists locally
if [[ -f ".env.bot" ]]; then
  scp -- .env.bot "$REMOTE:$DEPLOY_DIR/.env"
fi

# 4. Remote: build and restart
ssh -- "$REMOTE" bash -s -- "$DEPLOY_DIR" <<'REMOTE_SCRIPT'
  set -euo pipefail
  DEPLOY_DIR="$1"
  cd "$DEPLOY_DIR/bot/infra"

  echo "[AGENT 9] Pulling latest images..."
  docker compose pull --quiet prometheus 2>/dev/null || true

  echo "[AGENT 9] Building bot image..."
  docker compose build bot

  echo "[AGENT 9] Restarting stack..."
  docker compose up -d --remove-orphans

  echo "[AGENT 9] Health check..."
  sleep 5
  docker compose ps
  echo "[AGENT 9] Deploy complete!"
REMOTE_SCRIPT

echo "=== Deploy finished. Prometheus: http://$VPS_IP:9090 ==="
