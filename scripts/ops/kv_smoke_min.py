from x64dbg_automate import X64DbgClient
print('before')
c=X64DbgClient(r'C:\\Users\\zycie\\AppData\\Local\\Microsoft\\WinGet\\Packages\\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\\release\\x64\\x64dbg.exe')
print('created')
c.start_session(r'C:\\Users\\zycie\\AppData\\Roaming\\KingsValeLauncher\\client\\otclient_gl.exe', current_dir=r'C:\\Users\\zycie\\AppData\\Roaming\\KingsValeLauncher\\client')
print('started')
