#!/usr/bin/env bash
# AGENT 9: DEVOPS MASTER — VPS Deploy Script
# Usage: ./deploy.sh [VPS_IP] [VPS_USER]
# Requires: ssh key auth configured, Docker installed on VPS
set -euo pipefail

VPS_IP="${1:-${BOT_VPS_IP:?'Set BOT_VPS_IP env var or pass as arg'}}"
VPS_USER="${2:-${BOT_VPS_USER:-ubuntu}}"
REMOTE="$VPS_USER@$VPS_IP"
DEPLOY_DIR="/opt/tibia-bot"
REPO_URL="https://github.com/famatyyk/CTOAi.git"

echo "=== AGENT 9: DEVOPS MASTER — Deploying Tibia Bot ==="
echo "Target: $REMOTE:$DEPLOY_DIR"

# 1. Ensure remote dir exists
ssh "$REMOTE" "mkdir -p $DEPLOY_DIR"

# 2. Sync code (rsync faster than full clone)
rsync -az --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='data/*.db' \
  --exclude='data/*.log' \
  . "$REMOTE:$DEPLOY_DIR/"

# 3. Copy env file if exists locally
if [[ -f ".env.bot" ]]; then
  scp .env.bot "$REMOTE:$DEPLOY_DIR/.env"
fi

# 4. Remote: build and restart
ssh "$REMOTE" bash <<REMOTE_SCRIPT
  set -euo pipefail
  cd $DEPLOY_DIR/bot/infra

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
