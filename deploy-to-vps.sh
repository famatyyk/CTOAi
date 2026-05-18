#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./deploy-to-vps.sh <vps_host> <ssh_user> <ssh_key_path> [image_tag] [image_repo]

Arguments:
  vps_host      VPS host (example: 116.202.96.250)
  ssh_user      SSH user (example: ctoa)
  ssh_key_path  Path to SSH private key (example: ~/.ssh/ctoa_vps_ed25519)
  image_tag     Optional image tag (default: latest)
  image_repo    Optional image repository prefix (example: docker.io/famatyyk/ctoa-toolkit)

Behavior:
  - Always builds local image ctoa-toolkit:<image_tag>
  - If image_repo is provided: tags + pushes image, then VPS pulls from registry
  - If image_repo is not provided: streams local image directly to VPS over SSH
USAGE
}

if [[ $# -lt 3 || $# -gt 5 ]]; then
  usage
  exit 1
fi

VPS_HOST="$1"
SSH_USER="$2"
SSH_KEY_PATH="$3"
IMAGE_TAG="${4:-latest}"
IMAGE_REPO="${5:-}"

LOCAL_IMAGE="ctoa-toolkit:${IMAGE_TAG}"
REMOTE_IMAGE="${LOCAL_IMAGE}"

if [[ -n "${IMAGE_REPO}" ]]; then
  if [[ "${IMAGE_REPO}" == *:* ]]; then
    REMOTE_IMAGE="${IMAGE_REPO}"
  else
    REMOTE_IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"
  fi
fi

if [[ ! -f "${SSH_KEY_PATH}" ]]; then
  echo "[deploy] SSH key not found: ${SSH_KEY_PATH}" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] Docker is required on local machine." >&2
  exit 1
fi

SSH_OPTS=(
  -i "${SSH_KEY_PATH}"
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=8
)
SSH_TARGET="${SSH_USER}@${VPS_HOST}"

echo "[deploy] Building local image: ${LOCAL_IMAGE}"
docker build -t "${LOCAL_IMAGE}" .

if [[ -n "${IMAGE_REPO}" ]]; then
  echo "[deploy] Tagging image as: ${REMOTE_IMAGE}"
  docker tag "${LOCAL_IMAGE}" "${REMOTE_IMAGE}"

  echo "[deploy] Pushing image to registry"
  docker push "${REMOTE_IMAGE}"

  echo "[deploy] Pulling image on VPS"
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "docker pull ${REMOTE_IMAGE} || sudo -n docker pull ${REMOTE_IMAGE}"
else
  echo "[deploy] No registry provided. Streaming image directly to VPS over SSH"
  docker save "${LOCAL_IMAGE}" | gzip | ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "gunzip | (docker load || sudo -n docker load)"
fi

echo "[deploy] Restarting ctoa-runner on VPS"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- "${REMOTE_IMAGE}" <<'REMOTE_SCRIPT'
set -euo pipefail

IMAGE="$1"

if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  SUDO=(sudo -n)
else
  SUDO=()
fi

run_root() {
  if [[ ${#SUDO[@]} -gt 0 ]]; then
    "${SUDO[@]}" "$@"
  else
    "$@"
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy:vps] Docker not found on VPS." >&2
  exit 1
fi

run_root mkdir -p /opt/ctoa/config /opt/ctoa/runtime /opt/ctoa/logs

if run_root docker ps -a --format '{{.Names}}' | grep -Fxq ctoa-runner; then
  run_root docker rm -f ctoa-runner
fi

env_args=(-e CTOA_ENV=prod -e CTOA_MOBILE_FULL_ACCESS=false -e CTOA_MOBILE_TOKEN=change-me-on-vps)
if run_root test -f /opt/ctoa/.env; then
  env_args=(--env-file /opt/ctoa/.env)
else
  echo "[deploy:vps] /opt/ctoa/.env not found, using fallback token. Set CTOA_MOBILE_TOKEN in /opt/ctoa/.env."
fi

run_root docker run -d \
  --name ctoa-runner \
  --restart unless-stopped \
  -p 8787:8787 \
  -v /opt/ctoa/config:/opt/ctoa/config \
  -v /opt/ctoa/runtime:/opt/ctoa/runtime \
  -v /opt/ctoa/logs:/opt/ctoa/logs \
  "${env_args[@]}" \
  "${IMAGE}"

run_root docker ps --filter name=ctoa-runner --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
REMOTE_SCRIPT

echo "[deploy] Done. Service should be reachable on http://${VPS_HOST}:8787"
