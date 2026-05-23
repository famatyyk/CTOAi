#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper to keep legacy path working.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

exec "${ROOT_DIR}/deploy-to-vps.sh" "$@"
