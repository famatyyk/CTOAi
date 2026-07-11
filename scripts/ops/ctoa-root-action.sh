#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
if [[ -z "$action" ]]; then
  echo "Missing wrapper action" >&2
  exit 64
fi

case "$action" in
  validate-services)
    systemctl start ctoa-runner.service
    systemctl start ctoa-report.service || true
    systemctl status ctoa-runner.service --no-pager -l | sed -n '1,12p' || true
    systemctl status ctoa-report.service --no-pager -l | sed -n '1,20p' || true
    if [[ -f /opt/ctoa/logs/runner.log ]]; then
      tail -n 40 /opt/ctoa/logs/runner.log
    else
      echo runner.log-not-present
    fi
    ;;

  inspect-report-env)
    grep -n '^GITHUB_PAT=' /opt/ctoa/.env | sed 's/=.*/=***set***/' || echo PAT-not-set
    systemctl restart ctoa-report.service
    journalctl -u ctoa-report.service -n 12 --no-pager
    ;;

  healthcheck-one-shot)
    mkdir -p /opt/ctoa/logs
    marker="ONE_SHOT_HEALTHCHECK_$(date -u +%Y%m%dT%H%M%SZ)"
    echo "$marker" >> /opt/ctoa/logs/runner.log

    echo "=== ValidateServices ==="
    systemctl start ctoa-runner.service
    systemctl start ctoa-report.service || true
    systemctl status ctoa-runner.service --no-pager -l | sed -n '1,12p' || true
    systemctl status ctoa-report.service --no-pager -l | sed -n '1,20p' || true
    if [[ -f /opt/ctoa/logs/runner.log ]]; then
      tail -n 40 /opt/ctoa/logs/runner.log
    else
      echo runner.log-not-present
    fi

    echo
    echo "=== DashboardSnapshot ==="
    systemctl status ctoa-mobile-console.service --no-pager -l | sed -n '1,20p' || true
    echo
    echo "=== Dashboard health ==="
    health_out="$(mktemp "${TMPDIR:-/tmp}/ctoa-health.XXXXXX")"
    trap 'rm -f "$health_out"' EXIT
    http_code=$(curl -sS -o "$health_out" -w "%{http_code}" http://127.0.0.1:8787/api/health || true)
    if [[ "$http_code" = "200" ]]; then
      cat "$health_out"
    elif [[ "$http_code" = "401" || "$http_code" = "403" ]]; then
      echo "dashboard-health-auth-required"
    else
      echo "dashboard-health-unavailable (http=$http_code)"
    fi

    echo
    echo "=== InspectReportEnv ==="
    grep -n '^GITHUB_PAT=' /opt/ctoa/.env | sed 's/=.*/=***set***/' || echo PAT-not-set
    systemctl restart ctoa-report.service
    journalctl -u ctoa-report.service -n 12 --no-pager

    echo
    echo "=== Secret Sanity ==="
    if [[ -f /opt/ctoa/logs/runner.log ]]; then
      segment="$(awk -v m="$marker" 'found{print} index($0,m){found=1}' /opt/ctoa/logs/runner.log)"
      if printf '%s\n' "$segment" | grep -q '\[report\] GITHUB_PAT is not set'; then
        echo "FAIL: GITHUB_PAT is still not set for report publish"
        exit 2
      fi
    fi

    echo "PASS: one-shot health check complete"
    ;;

  worktree-drycheck)
    /opt/ctoa/deploy/vps/worktree-nightly-drycheck.sh
    ;;

  install-worktree-drycheck-cron)
    mkdir -p /opt/ctoa/logs
    cron_line='20 2 * * * /opt/ctoa/deploy/vps/worktree-nightly-drycheck.sh >> /opt/ctoa/logs/worktree-drycheck.log 2>&1'
    current_cron="$(crontab -l 2>/dev/null || true)"
    {
      printf '%s\n' "$current_cron" | grep -Fv '/opt/ctoa/deploy/vps/worktree-nightly-drycheck.sh' || true
      printf '%s\n' "$cron_line"
    } | sed '/^[[:space:]]*$/d' | crontab -
    echo "installed-cron: $cron_line"
    crontab -l | grep -F '/opt/ctoa/deploy/vps/worktree-nightly-drycheck.sh'
    ;;

  *)
    echo "Unsupported wrapper action: $action" >&2
    exit 64
    ;;
esac
