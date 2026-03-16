from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType


BREAKPOINTS = {
    0x005D5900: "FUN_005d5900",
    0x005D63A0: "FUN_005d63a0",
    0x005DEA30: "FUN_005dea30",
    0x005CF2B0: "FUN_005cf2b0",
    0x005CD050: "FUN_005cd050",
    0x005CEB30: "FUN_005ceb30",
}


def _hexdump(data: bytes, width: int = 16) -> str:
    lines: list[str] = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        asc_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{i:04X}  {hex_part:<47}  {asc_part}")
    return "\n".join(lines)


def _safe_read(client: X64DbgClient, address: int, size: int) -> str:
    try:
        if not client.check_valid_read_ptr(address):
            return ""
        data = client.read_memory(address, size)
        if not data:
            return ""
        return _hexdump(data)
    except Exception:
        return ""


def _render_markdown(
    binary_path: str,
    timeout_seconds: int,
    hit_events: list[dict],
    errors: list[str],
    started_at: float,
) -> str:
    elapsed = int(time.time() - started_at)
    lines: list[str] = []
    lines.append("# ENC3 Dynamic Pass (x64dbg-automate)")
    lines.append("")
    lines.append(f"- Binary: `{binary_path}`")
    lines.append(f"- TimeoutSeconds: `{timeout_seconds}`")
    lines.append(f"- ElapsedSeconds: `{elapsed}`")
    lines.append(f"- BreakpointHitCount: `{len(hit_events)}`")
    lines.append("")
    lines.append("## Breakpoint Map")
    lines.append("")
    for addr, name in BREAKPOINTS.items():
        lines.append(f"- `0x{addr:08X}` `{name}`")
    lines.append("")

    if errors:
        lines.append("## Errors")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("## Hit Log")
    lines.append("")
    if not hit_events:
        lines.append("No ENC3 breakpoints hit during the run window.")
        return "\n".join(lines) + "\n"

    for idx, event in enumerate(hit_events, start=1):
        lines.append(f"### Hit {idx}")
        lines.append("")
        lines.append(f"- Address: `0x{event['address']:08X}`")
        lines.append(f"- Symbol: `{event['symbol']}`")
        lines.append(f"- Timestamp: `{event['timestamp']}`")
        lines.append(f"- HitCount: `{event.get('hit_count', 0)}`")
        lines.append("")
        lines.append("#### Registers")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(event.get("registers", {}), indent=2))
        lines.append("```")

        mem = event.get("memory_samples", {})
        if mem:
            lines.append("")
            lines.append("#### Memory Samples")
            lines.append("")
            for key, dump in mem.items():
                if not dump:
                    continue
                lines.append(f"- Pointer: `{key}`")
                lines.append("```text")
                lines.append(dump)
                lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ENC3 dynamic pass with x64dbg-automate")
    parser.add_argument(
        "--binary",
        default=r"C:\Users\zycie\AppData\Roaming\Mythibia\MythibiaV2\mythibia_dx-1773218163.exe",
        help="Path to Mythibia executable",
    )
    parser.add_argument(
        "--current-dir",
        default=r"C:\Users\zycie\AppData\Roaming\Mythibia\MythibiaV2",
        help="Working directory for debuggee",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="How long to wait for breakpoint hits",
    )
    parser.add_argument(
        "--x64dbg-path",
        default=r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x64\x64dbg.exe",
        help="Path to x64dbg.exe",
    )
    parser.add_argument(
        "--out-md",
        default=r"C:\Users\zycie\CTOAi\artifacts\enc3\enc3-dynamic-pass-log.md",
        help="Output markdown report",
    )
    parser.add_argument(
        "--out-json",
        default=r"C:\Users\zycie\CTOAi\artifacts\enc3\enc3-dynamic-pass-log.json",
        help="Output JSON raw log",
    )
    args = parser.parse_args()

    out_md = Path(args.out_md)
    out_json = Path(args.out_json)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    started_at = time.time()
    errors: list[str] = []
    hit_events: list[dict] = []
    launched_pid: int | None = None
    launched_target_pid: int | None = None

    client = X64DbgClient(args.x64dbg_path)
    try:
        loaded = False
        try:
            # Preferred path: let the plugin issue `init` directly.
            client.start_session(args.binary, current_dir=args.current_dir)
            loaded = True
        except Exception as exc:
            errors.append(f"primary load path failed: {exc}")
            # Fallback path: launch x64dbg with target file as CLI arg, then attach.
            # This avoids plugin-side init failures seen on some targets/builds.
            proc = subprocess.Popen(
                [args.x64dbg_path, args.binary],
                cwd=args.current_dir,
            )
            launched_pid = proc.pid
            client.attach_session(launched_pid)
            if not client.wait_until_debugging(20):
                # Fallback #2: start target normally and attach debugger by PID.
                target_proc = subprocess.Popen(
                    [args.binary],
                    cwd=args.current_dir,
                )
                launched_target_pid = target_proc.pid
                client.terminate_session()
                client = X64DbgClient(args.x64dbg_path)
                client.start_session_attach(launched_target_pid)
            loaded = True

        if loaded:
            for addr in BREAKPOINTS:
                ok = client.set_breakpoint(addr)
                if not ok:
                    errors.append(f"set_breakpoint failed for 0x{addr:08X}")

            client.go()
            deadline = time.time() + args.timeout_seconds
            while time.time() < deadline:
                event = client.wait_for_debug_event(EventType.EVENT_BREAKPOINT, timeout=2)
                if event is None:
                    continue

                bp = event.event_data
                addr = int(getattr(bp, "addr", 0))
                symbol = BREAKPOINTS.get(addr, "UNKNOWN")
                regs_obj = client.get_regs()
                if hasattr(regs_obj, "model_dump"):
                    regs = regs_obj.model_dump()
                elif isinstance(regs_obj, dict):
                    regs = regs_obj
                else:
                    regs = dict(regs_obj)

                memory_samples: dict[str, str] = {}
                for reg_name in ("eax", "ebx", "ecx", "edx", "esi", "edi", "esp", "ebp"):
                    ptr = int(regs.get(reg_name, 0))
                    if ptr <= 0:
                        continue
                    dump = _safe_read(client, ptr, 64)
                    if dump:
                        memory_samples[f"{reg_name}=0x{ptr:08X}"] = dump

                hit_events.append(
                    {
                        "timestamp": int(time.time()),
                        "address": addr,
                        "symbol": symbol,
                        "hit_count": int(getattr(bp, "hitCount", 0)),
                        "registers": regs,
                        "memory_samples": memory_samples,
                    }
                )

                if len(hit_events) >= 24:
                    break
                client.go()

    except Exception as exc:
        errors.append(f"runtime exception: {exc}")
    finally:
        try:
            if client.is_debugging():
                client.unload_executable()
        except Exception:
            pass
        try:
            client.terminate_session()
        except Exception:
            pass
        if launched_pid is not None:
            try:
                subprocess.run(
                    [
                        "taskkill",
                        "/PID",
                        str(launched_pid),
                        "/F",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except Exception:
                pass
        if launched_target_pid is not None:
            try:
                subprocess.run(
                    [
                        "taskkill",
                        "/PID",
                        str(launched_target_pid),
                        "/F",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except Exception:
                pass

    out_json.write_text(
        json.dumps(
            {
                "binary": args.binary,
                "current_dir": args.current_dir,
                "timeout_seconds": args.timeout_seconds,
                "started_at": int(started_at),
                "hits": hit_events,
                "errors": errors,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out_md.write_text(
        _render_markdown(args.binary, args.timeout_seconds, hit_events, errors, started_at),
        encoding="utf-8",
    )

    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    print(f"hits={len(hit_events)} errors={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
