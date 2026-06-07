from x64dbg_automate import X64DbgClient
print('probe_begin', flush=True)
c=X64DbgClient('C:/Users/zycie/AppData/Local/Microsoft/WinGet/Packages/x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe/release/x64/x64dbg.exe')
sid=c.start_session()
print('sid', sid, flush=True)
target='C:/Users/zycie/AppData/Roaming/KingsValeLauncher/client/otclient_gl.exe'
cmd=f'init "{target}"'
print('cmd', cmd, flush=True)
ok=c.cmd_sync(cmd)
print('cmd_ok', ok, flush=True)
print('wait_dbg', c.wait_until_debugging(20), flush=True)
print('is_debugging', c.is_debugging(), 'is_running', c.is_running(), flush=True)
print('probe_end', flush=True)
