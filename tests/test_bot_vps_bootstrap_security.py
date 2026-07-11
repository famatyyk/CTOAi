from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "ops" / "bot" / "bootstrap_vps.sh"


def _script_text() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8")


def test_bot_vps_bootstrap_does_not_pipe_remote_installers_to_shell() -> None:
    script = _script_text()

    assert "curl -fsSL https://get.docker.com | sh" not in script
    assert "| sh" not in script
    assert "| bash" not in script
    assert "apt-get install -y docker.io docker-compose-plugin" in script
    assert "do not execute remote installer scripts as root" in script


def test_bot_vps_bootstrap_requires_root_and_valid_local_user() -> None:
    script = _script_text()

    assert 'if [[ "${EUID:-$(id -u)}" -ne 0 ]]' in script
    assert 'BOT_VPS_USER="${BOT_VPS_USER:-ubuntu}"' in script
    assert '[[ ! "$BOT_VPS_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]' in script
    assert 'id "$BOT_VPS_USER"' in script
    assert 'usermod -aG docker "$BOT_VPS_USER"' in script
    assert 'chown -R ubuntu:ubuntu' not in script


def test_bot_vps_bootstrap_keeps_deploy_dir_under_opt() -> None:
    script = _script_text()

    assert 'BOT_DEPLOY_DIR="${BOT_DEPLOY_DIR:-/opt/tibia-bot}"' in script
    assert 'if [[ "$BOT_DEPLOY_DIR" != /opt/* ]]' in script
    assert 'install -d -m 0750 -o "$BOT_VPS_USER" -g "$BOT_VPS_USER" "$BOT_DEPLOY_DIR/data"' in script
    assert "mkdir -p /opt/tibia-bot/data" not in script


def test_bot_vps_bootstrap_does_not_expose_grafana_by_default() -> None:
    script = _script_text()

    assert 'BOT_ALLOW_PUBLIC_GRAFANA="${BOT_ALLOW_PUBLIC_GRAFANA:-false}"' in script
    assert 'if [[ "$BOT_ALLOW_PUBLIC_GRAFANA" == "true" ]]' in script
    assert 'ufw allow 3000/tcp' in script
    assert 'Grafana port 3000 left closed' in script
    assert 'ufw allow 3000/tcp   # Grafana' not in script
