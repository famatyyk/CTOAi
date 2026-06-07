import json
import time
from pathlib import Path
import subprocess
from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType
out={'flow':'attach_first_hit','errors':[]}
target=r'C:\\Users\\zycie\\AppData\\Roaming\\KingsValeLauncher\\client\\otclient_gl.exe'
cwd=r'C:\\Users\\zycie\\AppData\\Roaming\\KingsValeLauncher\\client'
x64=r'C:\\Users\\zycie\\AppData\\Local\\Microsoft\\WinGet\\Packages\\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\\release\\x64\\x64dbg.exe'
proc=subprocess.Popen([target], cwd=cwd)
out['target_pid']=proc.pid
time.sleep(1.0)
c=X64DbgClient(x64)
sid=c.start_session_attach(proc.pid)
out['session_pid']=sid
out['is_debugging']=bool(c.is_debugging())
bps=[]
bps.append(['CreateFileW',c.set_breakpoint('CreateFileW')])
bps.append(['ReadFile',c.set_breakpoint('ReadFile')])
bps.append(['NtReadFile',c.set_breakpoint('NtReadFile')])
bps.append(['RtlDecompressBuffer',c.set_breakpoint('RtlDecompressBuffer')])
bps.append(['0x005D5900',c.set_breakpoint(0x005D5900)])
bps.append(['0x005DEA30',c.set_breakpoint(0x005DEA30)])
out['breakpoints']=bps
c.go()
ev=c.wait_for_debug_event(EventType.EVENT_BREAKPOINT,60)
out['hit']=str(ev)
regs=c.get_regs()
out['regs']={'rip':regs.rip,'rsp':regs.rsp,'rax':regs.rax,'rbx':regs.rbx,'rcx':regs.rcx,'rdx':regs.rdx}
Path('artifacts/enc3').mkdir(parents=True,exist_ok=True)
Path('artifacts/enc3/kingsvale-first-hit-attach.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
