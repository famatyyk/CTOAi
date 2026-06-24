#!/usr/bin/env python3
"""CTOAi local chat CLI with modes, slash commands, history, and simple RAG."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.llm_providers import get_provider
from scripts.ops.git_exec import run_git

MODE_PROMPTS: dict[str, str] = {
    "general": "General assistant mode: concise, practical, and implementation-first.",
    "architect": "Architect mode: focus on system boundaries, interfaces, migration safety, and tradeoffs.",
    "reviewer": "Reviewer mode: prioritize bugs, regressions, risks, and missing tests with actionable fixes.",
    "debugger": "Debugger mode: isolate root cause, propose repro steps, and suggest minimal safe fixes.",
    "security": "Security mode: identify attack surface, auth risks, secrets handling, and hardening actions.",
    "ops": "Ops mode: focus on reliability, deploy safety, observability, rollback, and runbooks.",
}

RAG_DIRS = ("docs", "runner")
RAG_GLOBS = ("*.md", "*.py", "*.yml", "*.yaml", "*.json", "*.ts", "*.tsx")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "have",
    "will",
    "what",
    "your",
    "please",
    "czy",
    "oraz",
    "jest",
    "jak",
    "dla",
    "sie",
    "tak",
    "to",
    "nie",
    "you",
}


@dataclass
class ChatConfig:
    temperature: float
    max_tokens: int
    base_system_prompt: str
    mode: str
    rag_enabled: bool
    safe_exec: bool
    history_path: Path


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_unified_diff(text: str) -> str:
    patterns = [
        r"```diff\s*(.*?)```",
        r"```patch\s*(.*?)```",
        r"```\s*(diff --git.*?|--- .*?\n\+\+\+ .*?)```",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if m:
            content = m.group(1).strip()
            if content:
                return content

    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("diff --git ") or line.startswith("--- "):
            start = i
            break
    if start is None:
        return ""
    return "\n".join(lines[start:]).strip()


def resolve_repo_path(path_arg: str) -> Path | None:
    target = Path(path_arg)
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if ROOT not in target.parents and target != ROOT:
        return None
    return target


def patch_dir() -> Path:
    d = ROOT / ".ctoa-local" / "chat-patches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w in STOPWORDS or w.isdigit() or w in seen:
            continue
        seen.add(w)
        result.append(w)
        if len(result) >= 8:
            break
    return result


def append_history(path: Path, role: str, content: str, extra: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"ts": now_iso(), "role": role, "content": content}
    if extra:
        payload.update(extra)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def rg_available() -> bool:
    return shutil.which("rg") is not None


def run_rg(pattern: str, roots: list[str], max_results: int = 80) -> list[str]:
    if not rg_available():
        return []

    cmd = ["rg", "--no-heading", "-n", "-S", "-m", "3"]
    for g in RAG_GLOBS:
        cmd.extend(["-g", g])
    cmd.append(pattern)
    cmd.extend(roots)
    try:
        out = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception:
        return []

    if out.returncode not in (0, 1):
        return []

    stdout = out.stdout or ""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return lines[:max_results]


def build_rag_context(prompt: str) -> str:
    keywords = extract_keywords(prompt)
    if not keywords:
        return ""

    hits_by_file: dict[str, dict[str, Any]] = {}
    for kw in keywords:
        for line in run_rg(kw, list(RAG_DIRS)):
            parts = line.split(":", 2)
            if len(parts) != 3:
                continue
            path, line_no, content = parts
            rec = hits_by_file.setdefault(path, {"score": 0, "lines": []})
            rec["score"] += 1
            if len(rec["lines"]) < 3:
                rec["lines"].append(f"{line_no}: {content}")

    if not hits_by_file:
        return ""

    ranked = sorted(
        hits_by_file.items(),
        key=lambda item: (item[1]["score"], len(item[1]["lines"])),
        reverse=True,
    )[:6]

    chunks: list[str] = []
    for path, data in ranked:
        chunks.append(f"[{path}]")
        chunks.extend(f"  {ln}" for ln in data["lines"])
    return "\n".join(chunks)


def compose_system_prompt(cfg: ChatConfig) -> str:
    mode_prompt = MODE_PROMPTS.get(cfg.mode, MODE_PROMPTS["general"])
    return f"{cfg.base_system_prompt}\n\nActive mode: {cfg.mode}\n{mode_prompt}"


def ask_model(provider: Any, cfg: ChatConfig, prompt: str) -> str:
    user_prompt = prompt
    if cfg.rag_enabled:
        context = build_rag_context(prompt)
        if context:
            user_prompt = (
                "Use repository evidence below when relevant. "
                "If unsure, state assumptions.\n\n"
                f"Repository context:\n{context}\n\nUser request:\n{prompt}"
            )
    return provider.complete(
        system_prompt=compose_system_prompt(cfg),
        user_prompt=user_prompt,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )


def read_file_snippet(path_arg: str, max_lines: int = 140) -> str:
    target = resolve_repo_path(path_arg)
    if target is None:
        return "[ctoa-chat] Refusing to read outside repository root."
    if not target.exists() or not target.is_file():
        return f"[ctoa-chat] File not found: {target}"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    output = [f"[ctoa-chat] Reading: {target.relative_to(ROOT).as_posix()} ({len(lines)} lines total)"]
    for idx, line in enumerate(lines[:max_lines], start=1):
        output.append(f"{idx:>4}: {line}")
    if len(lines) > max_lines:
        output.append(f"... truncated after {max_lines} lines ...")
    return "\n".join(output)


def git_status_summary() -> str:
    status = run_git(["status", "-sb"], cwd=ROOT, check=False).stdout.strip()
    branch = run_git(["branch", "--show-current"], cwd=ROOT, check=False).stdout.strip()
    ahead_behind = ""
    upstream = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=ROOT,
        check=False,
    )
    if upstream.returncode == 0:
        upstream_name = upstream.stdout.strip()
        counts = run_git(["rev-list", "--left-right", "--count", f"{upstream_name}...HEAD"], cwd=ROOT, check=False)
        if counts.returncode == 0:
            behind, ahead = [int(x) for x in counts.stdout.strip().split()]
            ahead_behind = f" (ahead={ahead}, behind={behind} vs {upstream_name})"
    return "\n".join(
        [
            f"[ctoa-chat] git branch: {branch}{ahead_behind}",
            "[ctoa-chat] git status -sb:",
            status or "(clean)",
        ]
    )


def staged_files() -> list[str]:
    out = run_git(["diff", "--cached", "--name-only"], cwd=ROOT, check=False).stdout or ""
    return [line.strip() for line in out.splitlines() if line.strip()]


def suggest_commit_message(files: list[str]) -> str:
    if not files:
        return "chore: update repository files"
    top = files[:3]
    summary = ", ".join(top)
    if len(files) > 3:
        summary += f" +{len(files)-3} more"
    return f"chore: update {summary}"


def _sanitize_test_tokens(tokens: list[str]) -> list[str]:
    safe: list[str] = []
    for token in tokens:
        if not re.fullmatch(r"[\w\-\./:\[\]=]+", token):
            raise ValueError(f"Unsupported token in /test: {token}")
        safe.append(token)
    return safe


def run_test_command(raw_args: str) -> str:
    tokens = shlex.split(raw_args) if raw_args.strip() else ["tests/test_suite.py", "-q"]
    safe_tokens = _sanitize_test_tokens(tokens)
    cmd = [sys.executable, "-m", "pytest", *safe_tokens]
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = completed.stdout.strip()
    err = completed.stderr.strip()
    lines = [f"[ctoa-chat] /test exit={completed.returncode}", f"[ctoa-chat] cmd: {' '.join(cmd)}"]
    if out:
        lines.append(out[-4000:])
    if err:
        lines.append("[stderr]")
        lines.append(err[-1000:])
    return "\n".join(lines)


def check_patch_path(patch: Path) -> tuple[bool, str]:
    rel = patch.relative_to(ROOT).as_posix()
    check = run_git(["apply", "--check", rel], cwd=ROOT, check=False)
    if check.returncode != 0:
        detail = (check.stderr or check.stdout).strip()
        return False, f"[ctoa-chat] Patch check failed for {rel}\n{detail}"
    return True, f"[ctoa-chat] Patch check passed: {rel}"


def apply_patch_file(path_arg: str) -> str:
    patch = resolve_repo_path(path_arg)
    if patch is None:
        return "[ctoa-chat] Refusing to apply patch outside repository root."
    if not patch.exists() or not patch.is_file():
        return f"[ctoa-chat] Patch file not found: {path_arg}"
    if patch.suffix.lower() not in {".patch", ".diff", ".txt"}:
        return f"[ctoa-chat] Unsupported patch extension: {patch.suffix}"

    ok, msg = check_patch_path(patch)
    rel = patch.relative_to(ROOT).as_posix()
    if not ok:
        return msg

    apply = run_git(["apply", "--index", "--recount", "--whitespace=fix", rel], cwd=ROOT, check=False)
    if apply.returncode != 0:
        detail = (apply.stderr or apply.stdout).strip()
        return f"[ctoa-chat] Patch apply failed for {rel}\n{detail}"
    return f"[ctoa-chat] Patch applied: {rel}"


def build_patch_prompt(request: str, cfg: ChatConfig) -> str:
    context = build_rag_context(request) if cfg.rag_enabled else ""
    parts = [
        "Generate a unified git patch for this repository.",
        "Return ONLY a patch in ```diff fenced block.",
        "Requirements:",
        "- modify only files inside repo",
        "- keep patch minimal and safe",
        "- include proper unified diff hunks",
        "",
        f"User request: {request}",
    ]
    if context:
        parts.extend(["", "Repository context:", context])
    return "\n".join(parts)


def generate_patch_from_chat(provider: Any, cfg: ChatConfig, request: str) -> tuple[str, Path]:
    response = provider.complete(
        system_prompt=compose_system_prompt(cfg),
        user_prompt=build_patch_prompt(request, cfg),
        temperature=min(cfg.temperature, 0.2),
        max_tokens=max(2048, cfg.max_tokens),
    )
    diff = extract_unified_diff(response)
    if not diff:
        raise ValueError("Model did not return a valid unified diff patch.")
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    file_name = f"pending-{ts}.patch"
    patch_path = patch_dir() / file_name
    patch_path.write_text(diff + "\n", encoding="utf-8")
    return response, patch_path


def patch_preview(path: Path, max_lines: int = 140) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = [f"[ctoa-chat] Patch preview: {path.relative_to(ROOT).as_posix()} ({len(lines)} lines)"]
    for i, line in enumerate(lines[:max_lines], start=1):
        out.append(f"{i:>4}: {line}")
    if len(lines) > max_lines:
        out.append(f"... truncated after {max_lines} lines ...")
    return "\n".join(out)


def commit_changes(message: str, *, stage_all: bool = False) -> str:
    if stage_all:
        add = run_git(["add", "-A"], cwd=ROOT, check=False)
        if add.returncode != 0:
            return f"[ctoa-chat] git add failed:\n{(add.stderr or add.stdout).strip()}"

    files = staged_files()
    if not files:
        return "[ctoa-chat] No staged changes to commit."

    res = run_git(["commit", "-m", message], cwd=ROOT, check=False)
    if res.returncode != 0:
        return f"[ctoa-chat] git commit failed:\n{(res.stderr or res.stdout).strip()}"
    body = res.stdout.strip() or res.stderr.strip()
    return f"[ctoa-chat] Commit created.\n{body}"


def grep_snippet(pattern: str, max_results: int = 40) -> str:
    lines = run_rg(pattern, list(RAG_DIRS), max_results=max_results)
    if not lines:
        return f"[ctoa-chat] No matches for pattern: {pattern}"
    return "[ctoa-chat] grep results:\n" + "\n".join(lines)


def history_tail(history_path: Path, count: int = 20) -> str:
    if not history_path.exists():
        return "[ctoa-chat] No history yet."
    lines = history_path.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = lines[-count:]
    output = ["[ctoa-chat] history tail:"]
    for raw in tail:
        try:
            row = json.loads(raw)
            output.append(f"- {row.get('ts', '?')} {row.get('role', '?')}: {row.get('content', '')[:180]}")
        except Exception:
            output.append(f"- {raw[:180]}")
    return "\n".join(output)


def print_help() -> None:
    print("[ctoa-chat] Commands:")
    print("  /help                    Show commands")
    print("  /mode                    Show available modes")
    print("  /mode <name>             Switch mode (general/architect/reviewer/debugger/security/ops)")
    print("  /rag on|off|status       Toggle simple repository RAG")
    print("  /safe on|off|status      Safe execution mode for mutating actions")
    print("  /read <path>             Read file snippet")
    print("  /grep <pattern>          Search docs/ and runner/")
    print("  /git status              Show git status summary")
    print("  /test [pytest args]      Run pytest (safe command)")
    print("  /apply_patch <file>      Apply local patch file (.patch/.diff/.txt)")
    print("  /apply_patch --from-chat <request>")
    print("                           Generate patch with model, preview it, then /confirm yes")
    print("  /confirm yes|no          Confirm or discard pending generated patch")
    print("  /commit --suggest        Suggest commit message from staged files")
    print("  /commit --all <message>  Stage all and commit (safe mode must be off)")
    print("  /commit <message>        Commit staged changes (safe mode must be off)")
    print("  /plan <topic>            Generate implementation plan using architect mode")
    print("  /history [n]             Show last n messages from session history")
    print("  /health                  Provider health check")
    print("  /exit or /quit           Exit chat")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CTOAi local chat CLI")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--system-prompt",
        default="You are CTOAi local assistant. Be concise, practical, and code-first.",
    )
    parser.add_argument("--once", default="")
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--mode", default="general", choices=sorted(MODE_PROMPTS.keys()))
    parser.add_argument(
        "--history-dir",
        default=str(ROOT / ".ctoa-local" / "chat-history"),
        help="Directory where session jsonl history is stored",
    )
    parser.add_argument("--no-rag", action="store_true", help="Disable repository context retrieval")
    parser.add_argument("--unsafe-exec", action="store_true", help="Allow mutating slash commands without /safe off")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session_id = datetime.now(UTC).strftime("session-%Y%m%dT%H%M%SZ")
    history_path = Path(args.history_dir).resolve() / f"{session_id}.jsonl"
    cfg = ChatConfig(
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        base_system_prompt=args.system_prompt,
        mode=args.mode,
        rag_enabled=not args.no_rag,
        safe_exec=not args.unsafe_exec,
        history_path=history_path,
    )
    pending_patch: Path | None = None

    try:
        provider = get_provider()
    except Exception as exc:
        print(f"[ctoa-chat] Provider init failed: {exc}")
        return 2

    print(f"[ctoa-chat] Provider: {provider.__class__.__name__}")
    print(f"[ctoa-chat] URL: {os.getenv('CTOA_LOCAL_MODEL_URL', '')}")
    print(f"[ctoa-chat] Model: {os.getenv('CTOA_LOCAL_MODEL_NAME', '')}")
    print(f"[ctoa-chat] Mode: {cfg.mode}")
    print(f"[ctoa-chat] RAG: {'on' if cfg.rag_enabled else 'off'} (docs/, runner/)")
    print(f"[ctoa-chat] Safe exec: {'on' if cfg.safe_exec else 'off'}")
    print(f"[ctoa-chat] History: {cfg.history_path}")

    if not provider.health():
        print("[ctoa-chat] Provider health check failed.")
        return 2

    if args.health_only:
        print("[ctoa-chat] Health check passed.")
        return 0

    def run_prompt(prompt: str, *, mode_override: str | None = None) -> int:
        local_cfg = cfg
        if mode_override:
            local_cfg = ChatConfig(
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                base_system_prompt=cfg.base_system_prompt,
                mode=mode_override,
                rag_enabled=cfg.rag_enabled,
                safe_exec=cfg.safe_exec,
                history_path=cfg.history_path,
            )
        append_history(cfg.history_path, "user", prompt, {"mode": local_cfg.mode})
        try:
            response = ask_model(provider, local_cfg, prompt)
        except Exception as exc:
            print(f"[ctoa-chat] Request failed: {exc}")
            append_history(cfg.history_path, "error", str(exc), {"mode": local_cfg.mode})
            return 3
        print(f"assistant> {response}")
        append_history(cfg.history_path, "assistant", response, {"mode": local_cfg.mode})
        return 0

    if args.once.strip():
        return run_prompt(args.once.strip())

    print("[ctoa-chat] Interactive mode. Type /help for commands.")
    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[ctoa-chat] Bye.")
            return 0
        if not raw:
            continue
        if raw in {"/exit", "/quit"}:
            print("[ctoa-chat] Bye.")
            return 0
        if raw == "/help":
            print_help()
            continue
        if raw == "/health":
            print("[ctoa-chat] OK" if provider.health() else "[ctoa-chat] FAIL")
            continue
        if raw == "/mode":
            print(f"[ctoa-chat] Current mode: {cfg.mode}")
            print("[ctoa-chat] Available modes: " + ", ".join(sorted(MODE_PROMPTS.keys())))
            continue
        if raw.startswith("/mode "):
            new_mode = raw.split(maxsplit=1)[1].strip().lower()
            if new_mode not in MODE_PROMPTS:
                print(f"[ctoa-chat] Unknown mode: {new_mode}")
                continue
            cfg.mode = new_mode
            print(f"[ctoa-chat] Mode switched to: {cfg.mode}")
            continue
        if raw.startswith("/rag"):
            parts = raw.split(maxsplit=1)
            arg = parts[1].strip().lower() if len(parts) > 1 else "status"
            if arg == "on":
                cfg.rag_enabled = True
            elif arg == "off":
                cfg.rag_enabled = False
            print(f"[ctoa-chat] RAG is {'on' if cfg.rag_enabled else 'off'}")
            continue
        if raw.startswith("/safe"):
            parts = raw.split(maxsplit=1)
            arg = parts[1].strip().lower() if len(parts) > 1 else "status"
            if arg == "on":
                cfg.safe_exec = True
            elif arg == "off":
                cfg.safe_exec = False
            print(f"[ctoa-chat] Safe exec is {'on' if cfg.safe_exec else 'off'}")
            continue
        if raw.startswith("/read "):
            path_arg = raw.split(maxsplit=1)[1].strip()
            print(read_file_snippet(path_arg))
            continue
        if raw.startswith("/grep "):
            pattern = raw.split(maxsplit=1)[1].strip()
            print(grep_snippet(pattern))
            continue
        if raw == "/git status":
            print(git_status_summary())
            continue
        if raw.startswith("/test"):
            arg_str = raw[len("/test") :].strip()
            try:
                print(run_test_command(arg_str))
            except ValueError as exc:
                print(f"[ctoa-chat] {exc}")
            continue
        if raw.startswith("/apply_patch "):
            if cfg.safe_exec:
                print("[ctoa-chat] /apply_patch blocked in safe mode. Use /safe off to allow mutating actions.")
                continue
            arg = raw.split(maxsplit=1)[1].strip()
            if arg.startswith("--from-chat"):
                req = arg[len("--from-chat") :].strip()
                if not req:
                    print("[ctoa-chat] Usage: /apply_patch --from-chat <request>")
                    continue
                try:
                    _, generated = generate_patch_from_chat(provider, cfg, req)
                except Exception as exc:
                    print(f"[ctoa-chat] Patch generation failed: {exc}")
                    continue
                print(patch_preview(generated))
                ok, msg = check_patch_path(generated)
                print(msg)
                if ok:
                    pending_patch = generated
                    print("[ctoa-chat] Pending patch ready. Run /confirm yes to apply or /confirm no to discard.")
                else:
                    pending_patch = None
                continue

            print(apply_patch_file(arg))
            continue
        if raw.startswith("/confirm"):
            if cfg.safe_exec:
                print("[ctoa-chat] /confirm blocked in safe mode. Use /safe off to allow mutating actions.")
                continue
            parts = raw.split(maxsplit=1)
            decision = parts[1].strip().lower() if len(parts) > 1 else ""
            if pending_patch is None:
                print("[ctoa-chat] No pending patch to confirm.")
                continue
            if decision in {"no", "cancel"}:
                print(f"[ctoa-chat] Pending patch discarded: {pending_patch.relative_to(ROOT).as_posix()}")
                pending_patch = None
                continue
            if decision != "yes":
                print("[ctoa-chat] Usage: /confirm yes|no")
                continue
            print(apply_patch_file(pending_patch.relative_to(ROOT).as_posix()))
            pending_patch = None
            continue
        if raw.startswith("/commit"):
            if cfg.safe_exec:
                print("[ctoa-chat] /commit blocked in safe mode. Use /safe off to allow mutating actions.")
                continue
            arg = raw[len("/commit") :].strip()
            if arg == "--suggest":
                files = staged_files()
                msg = suggest_commit_message(files)
                print(f"[ctoa-chat] Suggested commit message: {msg}")
                continue
            if arg.startswith("--all "):
                message = arg[len("--all ") :].strip()
                if not message:
                    print("[ctoa-chat] Usage: /commit --all <message>")
                    continue
                print(commit_changes(message, stage_all=True))
                continue
            if not arg:
                files = staged_files()
                if not files:
                    print("[ctoa-chat] No staged files. Stage manually or use /commit --all <message>.")
                else:
                    print("[ctoa-chat] Staged files:\n- " + "\n- ".join(files))
                    print("[ctoa-chat] Commit with: /commit <message>")
                continue
            print(commit_changes(arg, stage_all=False))
            continue
        if raw.startswith("/plan "):
            topic = raw.split(maxsplit=1)[1].strip()
            prompt = (
                "Create a decision-complete implementation plan with: "
                "summary, key changes, tests, assumptions.\n\nTopic:\n"
                f"{topic}"
            )
            run_prompt(prompt, mode_override="architect")
            continue
        if raw.startswith("/history"):
            parts = raw.split(maxsplit=1)
            n = 20
            if len(parts) > 1 and parts[1].strip().isdigit():
                n = int(parts[1].strip())
            print(history_tail(cfg.history_path, n))
            continue

        run_prompt(raw)


if __name__ == "__main__":
    raise SystemExit(main())
