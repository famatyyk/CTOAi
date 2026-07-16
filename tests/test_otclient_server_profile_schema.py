from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "otclient-server-profile.schema.json"


def _profile() -> dict[str, object]:
    return {
        "schema_version": "ctoa-ots-server-profile-v1",
        "profile_id": "solteria-main",
        "display_name": "Solteria",
        "adapter": "redemption-mehah",
        "endpoints": [{"host": "game.example.test", "login_port": 7171, "game_port": 7172}],
        "protocol": {"client_version": 1400, "extended_opcodes": True, "cef_login": False},
        "trust": {"tls_required": True, "public_key_sha256": "a" * 64},
        "credential_ref": "ctoa-vault://ots/solteria-main/default",
    }


def test_public_server_profile_schema_is_valid_and_accepts_no_secret_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(_profile())) == []

    for forbidden in ("password", "account", "token", "private_key", "session"):
        forged = deepcopy(_profile())
        forged[forbidden] = "must-not-be-stored"
        assert list(validator.iter_errors(forged)), forbidden


def test_server_profile_fails_closed_on_unknown_adapter_or_unpinned_key() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    unknown = _profile()
    unknown["adapter"] = "random-fork"
    assert list(validator.iter_errors(unknown))

    unpinned = _profile()
    unpinned["trust"] = {"tls_required": True, "public_key_sha256": ""}
    assert list(validator.iter_errors(unpinned))
