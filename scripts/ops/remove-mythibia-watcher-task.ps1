param(
    [string]$TaskName = 'CTOA-Mythibia-Watcher',
    [string]$RunKeyName = 'CTOA-Mythibia-Watcher'
)

$ErrorActionPreference = 'Stop'

& schtasks /End /TN $TaskName | Out-Null
& schtasks /Delete /F /TN $TaskName | Out-Null

$runKeyPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (Get-ItemProperty -Path $runKeyPath -Name $RunKeyName -ErrorAction SilentlyContinue) {
    Remove-ItemProperty -Path $runKeyPath -Name $RunKeyName
}

Write-Output "[watcher-task] removed"
Write-Output "[watcher-task] name=$TaskName"
Write-Output "[watcher-task] run_key=$RunKeyName"
