"""Run a secret-safe local operations audit for CTOAi Engine Brain."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner import process_safety  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "AI" / "generated"
WINDOWS_GIT = Path(r"C:\Program Files\Git\cmd\git.exe")
WARP_CLI = Path(r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe")


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str


def run_cmd(command: list[str], *, timeout: int = 15, cwd: Path = ROOT, env: dict[str, str] | None = None) -> CommandResult:
    try:
        if not command:
            return CommandResult(False, 127, "", "empty command")
        executable = process_safety.resolve_executable(command[0])
        result = process_safety.run_trusted(
            [executable, *command[1:]],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except process_safety.ExecutableUnavailableError as exc:
        return CommandResult(False, 127, "", str(exc))
    except process_safety.ProcessTimeoutExpired as exc:
        return CommandResult(False, 124, exc.stdout or "", exc.stderr or "timeout")
    return CommandResult(result.returncode == 0, result.returncode, result.stdout.strip(), result.stderr.strip())


def safe_lines(value: str, limit: int = 20) -> list[str]:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return lines[:limit]


def status(ok: bool, warning: bool = False) -> str:
    if ok and not warning:
        return "ok"
    if ok and warning:
        return "warn"
    return "fail"


def check_git() -> dict[str, Any]:
    plain_git = shutil.which("git")
    git_path = plain_git or (str(WINDOWS_GIT) if WINDOWS_GIT.exists() else "")
    payload: dict[str, Any] = {
        "plain_git_on_path": bool(plain_git),
        "git_path": git_path,
    }
    if not git_path:
        payload["status"] = "fail"
        payload["message"] = "git not found"
        return payload

    root = run_cmd([git_path, "rev-parse", "--show-toplevel"])
    branch = run_cmd([git_path, "branch", "--show-current"])
    head = run_cmd([git_path, "rev-parse", "HEAD"])
    dirty = run_cmd([git_path, "status", "--short"])
    remotes = run_cmd([git_path, "remote", "-v"])
    dirty_lines = safe_lines(dirty.stdout, 500)

    payload.update(
        {
            "status": status(root.ok and branch.ok and head.ok and dirty.ok),
            "root": root.stdout.replace("\\", "/") if root.ok else "",
            "branch": branch.stdout if branch.ok else "",
            "head": head.stdout if head.ok else "",
            "dirty_count": len(dirty_lines),
            "dirty_sample": dirty_lines[:25],
            "remotes": safe_lines(remotes.stdout, 20),
        }
    )
    if not payload["plain_git_on_path"]:
        payload["status"] = "warn"
        payload["message"] = "plain git is missing from PATH; fallback path works"
    return payload


def parse_docker_ports(ports: str) -> list[str]:
    broad: list[str] = []
    for part in ports.split(","):
        item = part.strip()
        host_part = item.split("->", 1)[0].rsplit(":", 1)[0]
        if _is_unspecified_host(host_part):
            broad.append(item)
    return broad


def _is_unspecified_host(host_ip: str) -> bool:
    normalized = host_ip.strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        return ipaddress.ip_address(normalized).is_unspecified
    except ValueError:
        return False


def docker_status(*, version_ok: bool, compose_ok: bool, ps_ok: bool, has_broad_binds: bool) -> str:
    if not compose_ok:
        return "fail"
    if not version_ok or not ps_ok:
        return "warn"
    return status(True, warning=has_broad_binds)


def check_docker() -> dict[str, Any]:
    docker = shutil.which("docker")
    if not docker:
        return {"status": "fail", "docker_on_path": False, "message": "docker not found"}

    version = run_cmd([docker, "version", "--format", "{{json .}}"], timeout=20)
    compose = run_cmd([docker, "compose", "version"], timeout=20)
    ps = run_cmd([docker, "ps", "--format", "{{json .}}"], timeout=20)

    containers: list[dict[str, Any]] = []
    broad_binds: list[dict[str, Any]] = []
    for line in safe_lines(ps.stdout, 200):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = row.get("Names") or row.get("Name") or ""
        ports = row.get("Ports") or ""
        broad = parse_docker_ports(ports)
        containers.append({"name": name, "status": row.get("Status", ""), "ports": ports})
        for bind in broad:
            broad_binds.append({"container": name, "bind": bind})

    configured_broad_binds = docker_config_broad_binds(docker)
    return {
        "status": docker_status(
            version_ok=version.ok,
            compose_ok=compose.ok,
            ps_ok=ps.ok,
            has_broad_binds=bool(broad_binds or configured_broad_binds),
        ),
        "docker_on_path": True,
        "version_ok": version.ok,
        "daemon_ok": version.ok and ps.ok,
        "compose": compose.stdout,
        "container_count": len(containers),
        "containers": containers,
        "broad_binds": broad_binds,
        "configured_broad_binds": configured_broad_binds,
    }


def docker_config_broad_binds(docker: str) -> list[dict[str, Any]]:
    compose_files: list[tuple[str, list[str]]] = [
        ("root", [docker, "compose", "config", "--format", "json"]),
        ("bot_infra", [docker, "compose", "-f", str(ROOT / "bot" / "infra" / "docker-compose.yml"), "config", "--format", "json"]),
    ]
    broad_binds: list[dict[str, Any]] = []
    for compose_name, command in compose_files:
        result = run_cmd(command, timeout=25)
        if not result.ok or not result.stdout:
            continue
        try:
            config = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        services = config.get("services", {})
        for service_name, service in services.items():
            for port in service.get("ports", []) or []:
                host_ip = str(port.get("host_ip", ""))
                if _is_unspecified_host(host_ip):
                    broad_binds.append(
                        {
                            "compose": compose_name,
                            "service": service_name,
                            "bind": f"{host_ip}:{port.get('published')}->{port.get('target')}/{port.get('protocol', 'tcp')}",
                        }
                    )
    return broad_binds


def powershell(script: str, timeout: int = 20) -> CommandResult:
    return run_cmd(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=timeout)


def check_vpn() -> dict[str, Any]:
    adapters = powershell(
        "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -or $_.InterfaceDescription -match 'VPN|WireGuard|TAP|TUN|OpenVPN|Wintun|Nord|Proton|Tailscale|ZeroTier|WARP' } | "
        "Select-Object Name,InterfaceDescription,Status | ConvertTo-Json -Compress",
    )
    warp_status = run_cmd([str(WARP_CLI), "status"], timeout=15) if WARP_CLI.exists() else CommandResult(False, 127, "", "warp-cli not found")
    adapter_payload: Any = []
    if adapters.ok and adapters.stdout:
        try:
            adapter_payload = json.loads(adapters.stdout)
            if isinstance(adapter_payload, dict):
                adapter_payload = [adapter_payload]
        except json.JSONDecodeError:
            adapter_payload = []
    warp_connected = "Connected" in warp_status.stdout
    return {
        "status": status(adapters.ok, warning=not warp_connected),
        "warp_cli": str(WARP_CLI) if WARP_CLI.exists() else "",
        "warp_connected": warp_connected,
        "warp_status": safe_lines(warp_status.stdout, 5),
        "adapters": adapter_payload,
    }


def check_vercel() -> dict[str, Any]:
    vercel = shutil.which("vercel") or shutil.which("vercel.cmd") or shutil.which("vercel.ps1")
    project_file = ROOT / "web" / ".vercel" / "project.json"
    project: dict[str, Any] = {}
    if project_file.exists():
        try:
            raw = json.loads(project_file.read_text(encoding="utf-8"))
            settings = raw.get("settings", {})
            project = {
                "project_name": raw.get("projectName", ""),
                "framework": settings.get("framework", ""),
                "node_version": settings.get("nodeVersion", ""),
                "has_project_id": bool(raw.get("projectId")),
                "has_org_id": bool(raw.get("orgId")),
            }
        except json.JSONDecodeError:
            project = {"project_file_error": "invalid json"}

    if not vercel:
        return {"status": "warn", "vercel_on_path": False, "project": project}

    version = run_cmd([vercel, "--version"], timeout=20)
    whoami = run_cmd([vercel, "whoami"], timeout=20)
    return {
        "status": status(version.ok and bool(project), warning=not whoami.ok),
        "vercel_on_path": True,
        "version": version.stdout,
        "account": whoami.stdout if whoami.ok else "",
        "project": project,
    }


def check_vscode() -> dict[str, Any]:
    code = shutil.which("code") or shutil.which("code.cmd")
    settings_file = ROOT / ".vscode" / "settings.json"
    extensions_file = ROOT / ".vscode" / "extensions.json"
    extension_root = Path.home() / ".vscode" / "extensions"
    openai_dirs = sorted([path.name for path in extension_root.glob("openai.chatgpt-*")]) if extension_root.exists() else []
    listed_extensions: list[str] = []
    if code:
        ext_result = run_cmd([code, "--list-extensions", "--show-versions"], timeout=25)
        listed_extensions = [line for line in safe_lines(ext_result.stdout, 500) if re.search(r"openai|codex|github|docker|vercel|python|remote", line, re.I)]

    interpreter = ""
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8-sig"))
            interpreter = settings.get("python.defaultInterpreterPath", "")
        except json.JSONDecodeError:
            interpreter = "invalid settings json"

    recommendations: list[str] = []
    if extensions_file.exists():
        try:
            recommendations = list(json.loads(extensions_file.read_text(encoding="utf-8-sig")).get("recommendations", []))
        except json.JSONDecodeError:
            recommendations = []

    active_openai = [ext for ext in listed_extensions if ext.lower().startswith("openai.chatgpt@")]
    return {
        "status": status(bool(active_openai) or bool(openai_dirs), warning=len(openai_dirs) > 1),
        "code_on_path": bool(code),
        "active_openai_extensions": active_openai,
        "openai_extension_dirs": openai_dirs,
        "relevant_extensions": listed_extensions[:80],
        "python_interpreter": interpreter,
        "recommendations": recommendations,
    }


def check_github() -> dict[str, Any]:
    gh = shutil.which("gh")
    if not gh:
        return {"status": "fail", "gh_on_path": False, "message": "gh not found"}

    env = os.environ.copy()
    if WINDOWS_GIT.exists():
        env["PATH"] = f"{WINDOWS_GIT.parent};{env.get('PATH', '')}"

    auth = run_cmd([gh, "auth", "status", "--hostname", "github.com"], timeout=20, env=env)
    repo = run_cmd(
        [gh, "repo", "view", "famatyyk/CTOAi", "--json", "nameWithOwner,defaultBranchRef,visibility,pushedAt,updatedAt,url"],
        timeout=25,
        env=env,
    )
    prs = run_cmd(
        [gh, "pr", "list", "--repo", "famatyyk/CTOAi", "--state", "open", "--limit", "30", "--json", "number,title,mergeStateStatus,reviewDecision,isDraft,url"],
        timeout=25,
        env=env,
    )
    runs = run_cmd(
        [gh, "run", "list", "--repo", "famatyyk/CTOAi", "--limit", "15", "--json", "status,conclusion,workflowName,createdAt,url"],
        timeout=25,
        env=env,
    )

    pr_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    repo_payload: dict[str, Any] = {}
    for result, target in ((repo, "repo"), (prs, "prs"), (runs, "runs")):
        if not result.ok or not result.stdout:
            continue
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        if target == "repo":
            repo_payload = parsed
        elif target == "prs":
            pr_rows = parsed
        elif target == "runs":
            run_rows = parsed

    dirty_prs = [row for row in pr_rows if row.get("mergeStateStatus") == "DIRTY"]
    failed_runs = [row for row in run_rows if row.get("conclusion") not in {"success", None}]
    return {
        "status": status(auth.ok and repo.ok and prs.ok and runs.ok, warning=bool(dirty_prs or failed_runs)),
        "gh_on_path": True,
        "auth_ok": auth.ok,
        "repo": repo_payload,
        "open_pr_count": len(pr_rows),
        "dirty_prs": dirty_prs,
        "recent_run_count": len(run_rows),
        "failed_recent_runs": failed_runs,
    }


def check_update_gate() -> dict[str, Any]:
    gate = ROOT / "scripts" / "ops" / "ctoa_update_gate.py"
    if not gate.exists():
        return {"status": "fail", "message": "ctoa_update_gate.py missing"}
    result = run_cmd([sys.executable, str(gate)], timeout=20)
    payload: dict[str, Any] = {"status": "fail", "returncode": result.returncode}
    if result.stdout:
        try:
            parsed = json.loads(result.stdout)
            payload.update(parsed)
            payload["status"] = "ok" if parsed.get("ok") else "fail"
        except json.JSONDecodeError:
            payload["message"] = "invalid gate json"
    return payload


def build_report() -> dict[str, Any]:
    checks = {
        "git": check_git(),
        "docker": check_docker(),
        "vpn": check_vpn(),
        "vercel": check_vercel(),
        "vscode": check_vscode(),
        "github": check_github(),
        "update_gate": check_update_gate(),
    }
    status_counts = {"ok": 0, "warn": 0, "fail": 0}
    for item in checks.values():
        item_status = str(item.get("status", "fail"))
        status_counts[item_status if item_status in status_counts else "fail"] += 1
    overall = "fail" if status_counts["fail"] else "warn" if status_counts["warn"] else "ok"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(ROOT),
        "overall_status": overall,
        "status_counts": status_counts,
        "checks": checks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    checks: dict[str, dict[str, Any]] = report["checks"]
    lines = [
        "# Engine Brain Environment Doctor",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Overall status: `{report['overall_status']}`",
        "",
        "| Check | Status | Key evidence |",
        "|---|---|---|",
    ]
    for name, payload in checks.items():
        evidence = ""
        if name == "git":
            evidence = f"branch={payload.get('branch', '')}; dirty={payload.get('dirty_count', '')}; path={payload.get('git_path', '')}"
        elif name == "docker":
            evidence = (
                f"containers={payload.get('container_count', 0)}; "
                f"running_broad={len(payload.get('broad_binds', []))}; "
                f"configured_broad={len(payload.get('configured_broad_binds', []))}"
            )
        elif name == "vpn":
            evidence = f"warp_connected={payload.get('warp_connected', False)}"
        elif name == "vercel":
            project = payload.get("project", {})
            evidence = f"version={payload.get('version', '')}; project={project.get('project_name', '') if isinstance(project, dict) else ''}"
        elif name == "vscode":
            evidence = f"openai={payload.get('active_openai_extensions', [])}; old_dirs={len(payload.get('openai_extension_dirs', []))}"
        elif name == "github":
            evidence = f"open_prs={payload.get('open_pr_count', 0)}; dirty_prs={len(payload.get('dirty_prs', []))}; failed_runs={len(payload.get('failed_recent_runs', []))}"
        elif name == "update_gate":
            evidence = f"gate={payload.get('status', '')}; product={payload.get('product', '')}; version={payload.get('version', '')}"
        lines.append(f"| `{name}` | `{payload.get('status', 'fail')}` | {evidence} |")

    docker_binds = checks.get("docker", {}).get("broad_binds", [])
    if docker_binds:
        lines.extend(["", "## Docker Broad Binds", ""])
        lines.append("These are currently running container binds. Recreate the stack to apply compose bind changes.")
        lines.append("")
        for bind in docker_binds:
            lines.append(f"- `{bind.get('container')}`: `{bind.get('bind')}`")

    configured_docker_binds = checks.get("docker", {}).get("configured_broad_binds", [])
    if configured_docker_binds:
        lines.extend(["", "## Docker Configured Broad Binds", ""])
        for bind in configured_docker_binds:
            lines.append(f"- `{bind.get('compose')}/{bind.get('service')}`: `{bind.get('bind')}`")

    dirty_prs = checks.get("github", {}).get("dirty_prs", [])
    if dirty_prs:
        lines.extend(["", "## GitHub Dirty PRs", ""])
        for pr in dirty_prs:
            lines.append(f"- `#{pr.get('number')}` {pr.get('title')} - {pr.get('url')}")

    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "ENV_DOCTOR.json"
    md_path = out_dir / "ENV_DOCTOR.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {
        "json": str(json_path.relative_to(ROOT)) if json_path.is_relative_to(ROOT) else str(json_path),
        "markdown": str(md_path.relative_to(ROOT)) if md_path.is_relative_to(ROOT) else str(md_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CTOAi Engine Brain environment doctor")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--no-write", action="store_true", help="Only print JSON; do not write artifacts")
    args = parser.parse_args()

    report = build_report()
    if not args.no_write:
        report["outputs"] = write_report(report, args.out_dir.resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["overall_status"] in {"ok", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
