param(
    [string]$TaskName = 'CTOA-Mythibia-Watcher',
    [string]$RunKeyName = 'CTOA-Mythibia-Watcher'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-task-guard.ps1')

$TaskName = Assert-CtoaTaskName -TaskName $TaskName
$RunKeyName = Assert-CtoaRunKeyName -RunKeyName $RunKeyName

& schtasks /End /TN $TaskName | Out-Null
& schtasks /Delete /F /TN $TaskName | Out-Null

$runKeyPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (Get-ItemProperty -LiteralPath $runKeyPath -Name $RunKeyName -ErrorAction SilentlyContinue) {
    Remove-ItemProperty -LiteralPath $runKeyPath -Name $RunKeyName
}

Write-Output "[watcher-task] removed"
Write-Output "[watcher-task] name=$TaskName"
Write-Output "[watcher-task] run_key=$RunKeyName"
