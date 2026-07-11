from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts" / "ops" / "bot" / "deploy.sh"


def _script_text() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def test_bot_vps_deploy_validates_remote_user_host_and_dir() -> None:
    script = _script_text()

    assert "validate_remote_user()" in script
    assert "validate_remote_host()" in script
    assert "validate_deploy_dir()" in script
    assert 'DEPLOY_DIR="${BOT_DEPLOY_DIR:-/opt/tibia-bot}"' in script
    assert '[[ "$value" != /opt/* ]]' in script
    assert '[[ "$value" == *".."* || "$value" == *"//"*' in script
    assert "validate_remote_user \"$VPS_USER\"" in script
    assert "validate_remote_host \"$VPS_IP\"" in script
    assert "validate_deploy_dir \"$DEPLOY_DIR\"" in script


def test_bot_vps_deploy_uses_ssh_end_of_options_and_quoted_remote_path() -> None:
    script = _script_text()

    assert "quote_remote_path()" in script
    assert 'REMOTE_DEPLOY_DIR="$(quote_remote_path "$DEPLOY_DIR")"' in script
    assert 'ssh -- "$REMOTE" "install -d -m 0750 -- $REMOTE_DEPLOY_DIR"' in script
    assert 'ssh "$REMOTE" "mkdir -p $DEPLOY_DIR"' not in script


def test_bot_vps_deploy_uses_guarded_rsync_and_scp_targets() -> None:
    script = _script_text()

    assert "rsync -az --delete" in script
    assert "  -e ssh \\" in script
    assert '  -- . "$REMOTE:$DEPLOY_DIR/"' in script
    assert 'scp -- .env.bot "$REMOTE:$DEPLOY_DIR/.env"' in script
    assert "scp .env.bot" not in script.replace('scp -- .env.bot "$REMOTE:$DEPLOY_DIR/.env"', "")


def test_bot_vps_deploy_remote_block_receives_deploy_dir_as_argument() -> None:
    script = _script_text()

    assert "ssh -- \"$REMOTE\" bash -s -- \"$DEPLOY_DIR\" <<'REMOTE_SCRIPT'" in script
    assert 'DEPLOY_DIR="$1"' in script
    assert 'cd "$DEPLOY_DIR/bot/infra"' in script
    assert "ssh \"$REMOTE\" bash <<REMOTE_SCRIPT" not in script
    assert "cd $DEPLOY_DIR/bot/infra" not in script
