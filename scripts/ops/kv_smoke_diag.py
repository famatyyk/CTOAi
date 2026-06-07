from x64dbg_automate import X64DbgClient
print('diag_begin', flush=True)
c=X64DbgClient('C:/Users/zycie/AppData/Local/Microsoft/WinGet/Packages/x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe/release/x64/x64dbg.exe')
print('client_created', flush=True)
sid=c.start_session()
print('session_started', sid, flush=True)
print('waiting_cmd_ready', flush=True)
print('cmd_ready', c.wait_cmd_ready(30), flush=True)
target='C:/Users/zycie/AppData/Roaming/KingsValeLauncher/client/otclient_gl.exe'
cwd='C:/Users/zycie/AppData/Roaming/KingsValeLauncher/client'
ok=c.load_executable(target, '', cwd, wait_timeout=90)
print('load_executable', ok, flush=True)
print('is_debugging', c.is_debugging(), 'is_running', c.is_running(), flush=True)
r=c.get_regs()
print('last_error', getattr(r,'last_error',None), flush=True)
print('diag_end', flush=True)
