#!/usr/bin/env bash
# AGENT 9: One-time VPS bootstrap for Oracle Cloud Free Tier (Ubuntu 22.04 ARM)
# Run as: bash bootstrap_vps.sh
set -euo pipefail

echo "=== AGENT 9: VPS Bootstrap ==="

# Update + essentials
apt-get update && apt-get upgrade -y
apt-get install -y git curl rsync ufw fail2ban

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
systemctl enable docker

# Docker Compose plugin
apt-get install -y docker-compose-plugin

# Firewall: allow SSH, Grafana only
ufw allow 22/tcp
ufw allow 3000/tcp   # Grafana
ufw --force enable

# Create bot dir
mkdir -p /opt/tibia-bot/data
chown -R ubuntu:ubuntu /opt/tibia-bot

echo "=== Bootstrap complete! ==="
echo "Next: run deploy.sh from your local machine"
echo "  BOT_VPS_IP=<your-ip> ./scripts/ops/bot/deploy.sh"
