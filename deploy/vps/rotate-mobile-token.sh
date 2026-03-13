#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/opt/ctoa/.env"
SECRETS_DIR="/opt/ctoa/secrets"
TOKEN_FILE="${SECRETS_DIR}/mobile-token.txt"
TOKEN_HISTORY_FILE="${SECRETS_DIR}/mobile-token-history.log"
LOG_FILE="/opt/ctoa/logs/mobile-token-rotation.log"
TMP_TOKEN_FILE="/tmp/ctoa_new_mobile_token"

mkdir -p /opt/ctoa/logs "${SECRETS_DIR}"

if [ ! -f "${ENV_FILE}" ]; then
  touch "${ENV_FILE}"
fi

python3 - << 'PY' > "${TMP_TOKEN_FILE}"
import secrets
print(secrets.token_urlsafe(32))
PY

python3 - << 'PY'
from pathlib import Path

env_path = Path('/opt/ctoa/.env')
tmp_path = Path('/opt/ctoa/.env.tmp')
token_path = Path('/tmp/ctoa_new_mobile_token')
new_token = token_path.read_text(encoding='utf-8').strip()

lines = env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []
kv = {}
for line in lines:
    if '=' in line:
        k, v = line.split('=', 1)
        kv[k] = v

kv['CTOA_MOBILE_TOKEN'] = new_token
if 'CTOA_MOBILE_FULL_ACCESS' not in kv:
    kv['CTOA_MOBILE_FULL_ACCESS'] = 'false'

content = '\n'.join(f"{k}={v}" for k, v in kv.items()) + '\n'
tmp_path.write_text(content, encoding='utf-8')
tmp_path.replace(env_path)
PY

cp "${TMP_TOKEN_FILE}" "${TOKEN_FILE}"
chmod 600 "${TOKEN_FILE}"
chown root:root "${TOKEN_FILE}"

MASKED_TOKEN="$(python3 - << 'PY'
from pathlib import Path
t = Path('/tmp/ctoa_new_mobile_token').read_text(encoding='utf-8').strip()
if len(t) <= 12:
  print('***')
else:
  print(f"{t[:6]}...{t[-4:]}")
PY
)"

TOKEN_SHA256="$(python3 - << 'PY'
from pathlib import Path
import hashlib
t = Path('/tmp/ctoa_new_mobile_token').read_text(encoding='utf-8').strip().encode('utf-8')
print(hashlib.sha256(t).hexdigest())
PY
)"

printf "[%s] masked=%s sha256=%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${MASKED_TOKEN}" "${TOKEN_SHA256}" >> "${TOKEN_HISTORY_FILE}"

# Keep only the newest 180 history entries.
TMP_HISTORY_FILE="${TOKEN_HISTORY_FILE}.tmp"
tail -n 180 "${TOKEN_HISTORY_FILE}" > "${TMP_HISTORY_FILE}" || true
mv "${TMP_HISTORY_FILE}" "${TOKEN_HISTORY_FILE}"
chmod 600 "${TOKEN_HISTORY_FILE}"
chown root:root "${TOKEN_HISTORY_FILE}"

rm -f "${TMP_TOKEN_FILE}"

systemctl restart ctoa-mobile-console.service

printf "[%s] mobile token rotated; token saved to %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${TOKEN_FILE}" >> "${LOG_FILE}"
