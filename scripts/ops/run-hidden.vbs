If WScript.Arguments.Count = 0 Then
  WScript.Quit 1
End If

Dim scriptPath
scriptPath = WScript.Arguments.Item(0)

Dim shell
Set shell = CreateObject("WScript.Shell")

Dim cmd
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"

shell.Run cmd, 0, False
