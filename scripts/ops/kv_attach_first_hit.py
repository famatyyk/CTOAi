from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner import process_safety  # noqa: E402
from x64dbg_automate import X64DbgClient  # noqa: E402
from x64dbg_automate.events import EventType  # noqa: E402

TARGET = Path(r"C:\Users\zycie\AppData\Roaming\KingsValeLauncher\client\otclient_gl.exe")
CWD = Path(r"C:\Users\zycie\AppData\Roaming\KingsValeLauncher\client")
X64DBG = r"C:\Users\zycie\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x64\x64dbg.exe"
REPORT_PATH = Path("artifacts/enc3/kingsvale-first-hit-attach.json")


def run_attach_first_hit() -> dict[str, object]:
    out: dict[str, object] = {"flow": "attach_first_hit", "errors": []}
    target = process_safety.resolve_executable(str(TARGET))
    proc = process_safety.start_trusted([target], cwd=str(CWD))
    out["target_pid"] = proc.pid
    time.sleep(1.0)
    client = X64DbgClient(X64DBG)
    sid = client.start_session_attach(proc.pid)
    out["session_pid"] = sid
    out["is_debugging"] = bool(client.is_debugging())
    breakpoints = []
    breakpoints.append(["CreateFileW", client.set_breakpoint("CreateFileW")])
    breakpoints.append(["ReadFile", client.set_breakpoint("ReadFile")])
    breakpoints.append(["NtReadFile", client.set_breakpoint("NtReadFile")])
    breakpoints.append(["RtlDecompressBuffer", client.set_breakpoint("RtlDecompressBuffer")])
    breakpoints.append(["0x005D5900", client.set_breakpoint(0x005D5900)])
    breakpoints.append(["0x005DEA30", client.set_breakpoint(0x005DEA30)])
    out["breakpoints"] = breakpoints
    client.go()
    event = client.wait_for_debug_event(EventType.EVENT_BREAKPOINT, 60)
    out["hit"] = str(event)
    regs = client.get_regs()
    out["regs"] = {
        "rip": regs.rip,
        "rsp": regs.rsp,
        "rax": regs.rax,
        "rbx": regs.rbx,
        "rcx": regs.rcx,
        "rdx": regs.rdx,
    }
    return out


def main() -> int:
    out = run_attach_first_hit()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
