#!/usr/bin/env bash
# AGENT 9: One-time VPS bootstrap for Oracle Cloud Free Tier (Ubuntu 22.04 ARM)
# Run as: bash bootstrap_vps.sh
set -euo pipefail

echo "=== AGENT 9: VPS Bootstrap ==="

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "ERROR: bootstrap_vps.sh must run as root." >&2
  exit 1
fi

BOT_VPS_USER="${BOT_VPS_USER:-ubuntu}"
BOT_DEPLOY_DIR="${BOT_DEPLOY_DIR:-/opt/tibia-bot}"
BOT_ALLOW_PUBLIC_GRAFANA="${BOT_ALLOW_PUBLIC_GRAFANA:-false}"
BOT_GRAFANA_CIDR="${BOT_GRAFANA_CIDR:-}"

if [[ ! "$BOT_VPS_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
  echo "ERROR: BOT_VPS_USER must be a valid local Linux username." >&2
  exit 1
fi

if ! id "$BOT_VPS_USER" >/dev/null 2>&1; then
  echo "ERROR: BOT_VPS_USER does not exist: $BOT_VPS_USER" >&2
  exit 1
fi

if [[ "$BOT_DEPLOY_DIR" != /opt/* ]]; then
  echo "ERROR: BOT_DEPLOY_DIR must stay under /opt." >&2
  exit 1
fi

# Update + essentials
apt-get update && apt-get upgrade -y
apt-get install -y git curl rsync ufw fail2ban

# Docker. Use distro packages; do not execute remote installer scripts as root.
apt-get install -y docker.io docker-compose-plugin
usermod -aG docker "$BOT_VPS_USER"
systemctl enable docker

# Firewall: allow SSH. Grafana must be explicitly exposed.
ufw allow 22/tcp
if [[ "$BOT_ALLOW_PUBLIC_GRAFANA" == "true" ]]; then
  if [[ -n "$BOT_GRAFANA_CIDR" ]]; then
    ufw allow from "$BOT_GRAFANA_CIDR" to any port 3000 proto tcp
  else
    ufw allow 3000/tcp
  fi
else
  echo "Grafana port 3000 left closed. Set BOT_ALLOW_PUBLIC_GRAFANA=true to expose it."
fi
ufw --force enable

# Create bot dir
install -d -m 0750 -o "$BOT_VPS_USER" -g "$BOT_VPS_USER" "$BOT_DEPLOY_DIR/data"

echo "=== Bootstrap complete! ==="
echo "Next: run deploy.sh from your local machine"
echo "  BOT_VPS_IP=<your-ip> ./scripts/ops/bot/deploy.sh"
