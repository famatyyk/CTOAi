from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROTATE_SCRIPT = ROOT / "deploy" / "vps" / "rotate-mobile-token.sh"


def _script_text() -> str:
    return ROTATE_SCRIPT.read_text(encoding="utf-8")


def test_mobile_token_rotation_uses_private_temp_files() -> None:
    script = _script_text()

    assert "/tmp/ctoa_new_mobile_token" not in script
    assert 'TMP_TOKEN_FILE="$(mktemp "${TMPDIR:-/tmp}/ctoa-mobile-token.XXXXXX")"' in script
    assert 'TMP_ENV_FILE="$(mktemp "${ENV_FILE}.XXXXXX")"' in script
    assert 'TMP_HISTORY_FILE="$(mktemp "${TOKEN_HISTORY_FILE}.XXXXXX")"' in script
    assert 'TMP_HISTORY_FILE="${TOKEN_HISTORY_FILE}.tmp"' not in script
    assert "trap cleanup EXIT" in script
    assert "umask 077" in script


def test_mobile_token_rotation_does_not_hardcode_temp_paths_in_python() -> None:
    script = _script_text()

    assert "Path('/tmp/ctoa_new_mobile_token')" not in script
    assert "Path('/opt/ctoa/.env.tmp')" not in script
    assert "Path(os.environ['TMP_TOKEN_FILE'])" in script
    assert "Path(os.environ['TMP_ENV_FILE'])" in script
    assert "export TMP_TOKEN_FILE TMP_ENV_FILE" in script


def test_mobile_token_rotation_installs_secret_with_root_only_permissions() -> None:
    script = _script_text()

    assert 'install -d -m 0700 "${SECRETS_DIR}"' in script
    assert 'install -m 0600 -o root -g root "${TMP_TOKEN_FILE}" "${TOKEN_FILE}"' in script
    assert 'chmod 600 "${TOKEN_HISTORY_FILE}"' in script
