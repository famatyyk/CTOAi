from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "runtime" / "solteria_helper_dev"
PREVIEW = ROOT / "runtime" / "otclient_ui_preview"
BRIDGE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_recovery_bridge.lua"
SANDBOX = Path.home() / "AppData" / "Local" / "SolteriaCodexTest" / "client"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def latest_smokeall() -> Path | None:
    matches = sorted(PREVIEW.glob("solteria-helper-smokeall-inworld-*.json"), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def lua_trace() -> tuple[dict, str]:
    lua = shutil.which("lua")
    if not lua:
        return {}, "lua_not_found"
    probe = """
local bridge = dofile(arg[1])
local invoked = false
local trace = bridge.dispatch(
  {next_action = "plan_heal", spell = "exura gran"},
  {online = true, hp = 400, protection_zone = false},
  {now_ms = 5000, cooldown_ms = 1000, client_ready = true, sandbox = true, dry_run = true},
  function() invoked = true; return true end
)
print(table.concat({trace.status, trace.guard, trace.action, trace.result, tostring(trace.dispatch_allowed), tostring(trace.runtime_actions), tostring(invoked)}, "|"))
"""
    with tempfile.TemporaryDirectory(prefix="ctoa-recovery-bridge-") as temp_dir:
        probe_path = Path(temp_dir) / "probe.lua"
        probe_path.write_text(probe, encoding="utf-8")
        completed = subprocess.run(
            [lua, str(probe_path), str(BRIDGE)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    if completed.returncode != 0:
        return {}, "lua_probe_failed"
    fields = completed.stdout.strip().split("|")
    if len(fields) != 7:
        return {}, "lua_probe_invalid_output"
    return {
        "status": fields[0],
        "guard": fields[1],
        "action": fields[2],
        "result": fields[3],
        "dispatch_allowed": fields[4] == "true",
        "runtime_actions": fields[5] == "true",
        "executor_invoked": fields[6] == "true",
    }, ""


def main() -> int:
    manifest_path = DEV / "manifest.json"
    ready_path = DEV / "ready_check.json"
    module_attach_path = DEV / "module_attach_smoke.json"
    static_path = DEV / "recovery_bridge_static_smoke.json"
    smokeall_path = latest_smokeall()
    boot_log = SANDBOX / "ctoa_boot.log"
    local_log = SANDBOX / "ctoa_local.log"

    manifest = load_json(manifest_path)
    ready = load_json(ready_path)
    module_attach = load_json(module_attach_path)
    static = load_json(static_path)
    smokeall = load_json(smokeall_path) if smokeall_path else {}
    boot_text = boot_log.read_text(encoding="utf-8", errors="replace") if boot_log.is_file() else ""
    local_text = local_log.read_text(encoding="utf-8", errors="replace") if local_log.is_file() else ""
    trace, trace_error = lua_trace()

    checks = {
        "manifest_present": bool(manifest),
        "ready_check_in_world": ready.get("status") == "ready",
        "module_attach_passed": module_attach.get("status") == "passed",
        "smoke_attach_all_16_of_16": smokeall.get("covered_count") == 16
        and smokeall.get("expected_count") == 16
        and smokeall.get("missing") == [],
        "bridge_static_smoke_passed": static.get("status") == "passed",
        "bridge_loaded_in_sandbox": "Loaded: ctoa_helper_recovery_bridge" in boot_text,
        "runtime_remained_disarmed": "Runtime disarmed" in local_text,
        "dry_run_trace_ready": trace.get("status") == "ready"
        and trace.get("guard") == "passed"
        and trace.get("result") == "dry_run",
        "dry_run_did_not_dispatch": trace.get("dispatch_allowed") is False
        and trace.get("runtime_actions") is False
        and trace.get("executor_invoked") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "schema_version": "ctoa.recovery-bridge-sandbox-smoke.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failed else "blocked",
        "mode": "sandbox_in_world_dry_run",
        "checks": checks,
        "passed_count": sum(checks.values()),
        "check_count": len(checks),
        "failed": failed,
        "trace": trace,
        "trace_error": trace_error,
        "runtime_actions": False,
        "live_promotion": False,
        "sources": {
            "manifest": manifest_path.name,
            "ready_check": ready_path.name,
            "module_attach": module_attach_path.name,
            "smoke_attach_all": smokeall_path.name if smokeall_path else "missing",
            "bridge_static_smoke": static_path.name,
        },
        "next_action": (
            "Design the native sandbox executor and operator arming UI; keep live promotion disabled."
            if not failed
            else "Repair failed sandbox evidence and rerun RecoveryBridgeSandboxSmoke."
        ),
    }
    output = DEV / "recovery_bridge_sandbox_smoke.json"
    temp = output.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    print(f"[recovery-bridge-sandbox-smoke] JSON: {output}")
    print(f"[recovery-bridge-sandbox-smoke] Status: {report['status']} ({report['passed_count']}/{report['check_count']})")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
