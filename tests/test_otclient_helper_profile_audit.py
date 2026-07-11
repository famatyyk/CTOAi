import json
from pathlib import Path

from scripts.ops import otclient_helper_profile_audit as audit


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "otclient-helper-config.schema.json"
PROFILE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua"
SMOKE_SCRIPT = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_helper_config_schema_documents_safe_boot_defaults():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["title"] == "OTClient Helper HELPER_CONFIG"
    assert schema["properties"]["schema_version"]["const"] == "ctoa-helper-profile-v1"
    assert "schema_version" in schema["required"]
    assert schema["properties"]["enabled"]["const"] is False
    assert schema["properties"]["safe_boot_runtime_disabled"]["const"] is True
    tools = schema["properties"]["tools"]["properties"]
    for key in [
        "auto_attack",
        "auto_exeta",
        "auto_haste",
        "spell_rotation",
        "rune_enabled",
        "cavebot_enabled",
        "cavebot_movement_enabled",
        "timer_enabled",
    ]:
        assert tools[key]["const"] is False


def test_profile_audit_passes_repo_safe_boot_profile():
    result = audit.audit_profile(PROFILE, SCHEMA)

    assert result.status == "passed"
    assert result.findings == []


def test_profile_audit_blocks_unsafe_migrated_profile(tmp_path: Path):
    profile = tmp_path / "ctoa_ek_profile.lua"
    profile.write_text(
        """
return {
    name = "old unsafe",
    enabled = true,
    safe_boot_runtime_disabled = false,
    tools = {
        auto_attack = true,
        auto_exeta = true,
        auto_haste = true,
        spell_rotation = true,
        rune_enabled = true,
        cavebot_enabled = true,
        cavebot_movement_enabled = true,
        timer_enabled = true,
        feature_flags = {
            experimental_cavebot = true,
            experimental_loot = true,
            experimental_combat = true,
        },
    },
}
""".strip(),
        encoding="utf-8",
    )

    result = audit.audit_profile(profile, SCHEMA)
    findings = {item.key: item.reason for item in result.findings}

    assert result.status == "blocked"
    assert "schema_version" in findings
    assert "safe_boot_runtime_disabled" in findings
    assert "auto_attack" in findings
    assert "cavebot_movement_enabled" in findings
    assert "experimental_combat" in findings


def test_profile_audit_atomic_writer_uses_unique_temp_and_fsync(tmp_path: Path):
    out = tmp_path / "profile_audit.json"

    audit.write_json_atomic(out, {"status": "passed"})

    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "passed"
    assert list(tmp_path.glob(".*.tmp")) == []

    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert ".{path.name}.{os.getpid()}.tmp" not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source


def test_validate_dev_runs_profile_audit_before_pytest():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "otclient_helper_profile_audit.py --profile scripts\\lua\\otclient\\ctoa_ek_profile.lua --json-out $profileAuditPath" in script
    assert "profile_audit.json" in script
    assert script.index("helper profile safe migration audit") < script.index("pytest helper/API contracts")


def test_solteria_helper_test_env_atomic_json_uses_guid_temp_cleanup():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert '".{0}.{1}.tmp"' not in script
    assert "[Guid]::NewGuid().ToString('N')" in script
    assert "Remove-Item -LiteralPath $tmp -Force" in script
