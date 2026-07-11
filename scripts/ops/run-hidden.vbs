If WScript.Arguments.Count = 0 Then
  WScript.Quit 1
End If

Dim scriptPath
scriptPath = WScript.Arguments.Item(0)

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

Dim runnerDir
Dim scriptsDir
Dim repoRoot
runnerDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptsDir = fso.GetParentFolderName(runnerDir)
repoRoot = fso.GetParentFolderName(scriptsDir)

scriptPath = fso.GetAbsolutePathName(scriptPath)

If LCase(fso.GetExtensionName(scriptPath)) <> "ps1" Then
  WScript.Quit 2
End If

If Not fso.FileExists(scriptPath) Then
  WScript.Quit 3
End If

If Left(LCase(scriptPath), Len(LCase(repoRoot & "\"))) <> LCase(repoRoot & "\") Then
  WScript.Quit 4
End If

Dim shell
Set shell = CreateObject("WScript.Shell")

Dim cmd
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"

shell.Run cmd, 0, False
