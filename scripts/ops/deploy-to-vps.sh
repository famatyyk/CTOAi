#!/bin/bash
# Automated deployment script for CTOA Toolkit to VPS
# Usage: ./scripts/ops/deploy-to-vps.sh <VPS_HOST> <SSH_USER> <SSH_KEY_PATH> [IMAGE_TAG]

set -e

# Configuration
VPS_HOST="${1:-116.202.96.250}"
SSH_USER="${2:-ctoa}"
SSH_KEY="${3:-$HOME/.ssh/ctoa_vps_ed25519}"
IMAGE_TAG="${4:-v1.14.0}"
DOCKER_IMAGE="ctoa-toolkit:${IMAGE_TAG}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-localhost}"  # Change to Docker Hub if needed
CONTAINER_NAME="ctoa-runner"
REMOTE_DIR="/opt/ctoa"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== CTOA Deployment Script ===${NC}"
echo "VPS Host:     $VPS_HOST"
echo "SSH User:     $SSH_USER"
echo "Image Tag:    $IMAGE_TAG"
echo "Registry:     $DOCKER_REGISTRY"
echo ""

# Verify SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH key not found: $SSH_KEY${NC}"
    exit 1
fi

# Step 1: Build Docker image locally
echo -e "${YELLOW}Step 1: Building Docker image locally...${NC}"
docker build -t ${DOCKER_IMAGE} .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image built successfully${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# Step 2: Test SSH connection
echo -e "${YELLOW}Step 2: Testing SSH connection...${NC}"
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" "echo 'SSH OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ SSH connection failed${NC}"
    echo "Command: ssh -i '$SSH_KEY' ${SSH_USER}@${VPS_HOST}"
    exit 1
fi

# Step 3: Create remote directories
echo -e "${YELLOW}Step 3: Creating remote directories...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" << 'REMOTE'
    sudo mkdir -p /opt/ctoa/{config,logs,runtime,secrets}
    sudo chown -R ctoa:ctoa /opt/ctoa
REMOTE

# Step 4: Copy Docker image to VPS (tar method - no registry needed)
echo -e "${YELLOW}Step 4: Transferring Docker image to VPS...${NC}"
docker save ${DOCKER_IMAGE} | gzip | ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" "gunzip | docker load"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image transferred${NC}"
else
    echo -e "${RED}❌ Image transfer failed${NC}"
    exit 1
fi

# Step 5: Stop and remove old container
echo -e "${YELLOW}Step 5: Stopping old container...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" << 'REMOTE'
    docker stop ctoa-runner 2>/dev/null || true
    docker rm ctoa-runner 2>/dev/null || true
REMOTE

# Step 6: Start new container
echo -e "${YELLOW}Step 6: Starting new container...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" << REMOTE
    docker run -d \
      --name ctoa-runner \
      --restart unless-stopped \
      -p 8787:8787 \
      -v /opt/ctoa/config:/opt/ctoa/config \
      -v /opt/ctoa/logs:/opt/ctoa/logs \
      -v /opt/ctoa/runtime:/opt/ctoa/runtime \
      -e CTOA_ENV=prod \
      -e CTOA_MOBILE_TOKEN=\$(cat /opt/ctoa/.env 2>/dev/null | grep CTOA_MOBILE_TOKEN | cut -d= -f2) \
      ${DOCKER_IMAGE}
REMOTE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container started${NC}"
else
    echo -e "${RED}❌ Container start failed${NC}"
    exit 1
fi

# Step 7: Verify deployment
echo -e "${YELLOW}Step 7: Verifying deployment...${NC}"
sleep 5
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" "curl -f http://localhost:8787/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check pending (container may still be starting)${NC}"
fi

# Step 8: Show logs
echo -e "${YELLOW}Step 8: Recent logs:${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${VPS_HOST}" "docker logs --tail 20 ctoa-runner" 2>/dev/null || echo "Logs not available yet"

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo "VPS:        https://${VPS_HOST}:8787"
echo "View logs:  ssh -i '${SSH_KEY}' ${SSH_USER}@${VPS_HOST} docker logs -f ctoa-runner"
echo ""
