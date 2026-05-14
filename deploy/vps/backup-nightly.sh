#!/usr/bin/env bash
set -euo pipefail

umask 077

BACKUP_ROOT="/opt/ctoa/backups"
CONFIG_DIR="$BACKUP_ROOT/config"
DB_DIR="$BACKUP_ROOT/db"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CONFIG_ARCHIVE="$CONFIG_DIR/ctoa-config-$STAMP.tar.gz"
DB_ARCHIVE="$DB_DIR/ctoa-db-$STAMP.sql.gz"

mkdir -p "$CONFIG_DIR" "$DB_DIR" /opt/ctoa/logs

# Collect operational config files that are critical for service recovery.
declare -a CONFIG_PATHS=()
for path in /opt/ctoa/.env /etc/ssh/sshd_config /etc/fail2ban/jail.d/ctoa-sshd.local /etc/sudoers.d/90-ctoa-admin; do
  if [[ -e "$path" ]]; then
    CONFIG_PATHS+=("$path")
  fi
done

for pattern in /etc/ssh/sshd_config.d/* /etc/systemd/system/ctoa-*.service /etc/systemd/system/ctoa-*.timer; do
  for match in $pattern; do
    if [[ -e "$match" ]]; then
      CONFIG_PATHS+=("$match")
    fi
  done
done

if [[ ${#CONFIG_PATHS[@]} -eq 0 ]]; then
  echo "[backup] no config files found to archive"
  exit 1
fi

tar -czf "$CONFIG_ARCHIVE" "${CONFIG_PATHS[@]}"
chmod 600 "$CONFIG_ARCHIVE"

if [[ -f /opt/ctoa/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /opt/ctoa/.env
  set +a
fi

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ctoa_mobile}"
DB_USER="${DB_USER:-ctoa_mobile}"

if [[ -n "${DB_PASSWORD:-}" ]]; then
  export PGPASSWORD="$DB_PASSWORD"
fi

if ! pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip -9 > "$DB_ARCHIVE"; then
  rm -f "$DB_ARCHIVE"
  echo "[backup] database dump failed"
  exit 1
fi
chmod 600 "$DB_ARCHIVE"

unset PGPASSWORD || true

# Retention policy: DB 7 days, config archives 30 days.
find "$DB_DIR" -type f -name "ctoa-db-*.sql.gz" -mtime +7 -delete || true
find "$CONFIG_DIR" -type f -name "ctoa-config-*.tar.gz" -mtime +30 -delete || true

echo "[backup] config archive: $CONFIG_ARCHIVE"
echo "[backup] db archive: $DB_ARCHIVE"
echo "[backup] retention applied (db=7d, config=30d)"
