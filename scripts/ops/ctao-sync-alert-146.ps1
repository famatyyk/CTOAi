param(
    [string]$Repo = 'famatyyk/CTOAi',
    [int]$IssueNumber = 146
)

$gh = 'C:\Program Files\GitHub CLI\gh.exe'
if (-not (Test-Path $gh)) {
    $gh = 'C:\Users\zycie\AppData\Local\Programs\GitHub CLI\gh.exe'
}
if (-not (Test-Path $gh)) {
    Write-Error 'gh CLI not found'
    exit 1
}

$runs = Invoke-RestMethod -Uri ('https://api.github.com/repos/{0}/actions/runs?per_page=20' -f $Repo) -Headers @{ 'User-Agent' = 'CTOAi-Agent' }
$last = $runs.workflow_runs | Where-Object { $_.name -eq 'CTOA Pipeline' } | Select-Object -First 1
if (-not $last) {
    Write-Error 'No CTOA Pipeline run found'
    exit 1
}

if ($last.conclusion -eq 'success') {
    & $gh issue close $IssueNumber --repo $Repo --comment ('Auto-closed because pipeline run {0} is success.' -f $last.id) | Out-Host
}
else {
    & $gh issue reopen $IssueNumber --repo $Repo | Out-Host
}

& $gh issue view $IssueNumber --repo $Repo --json number,state,url | Out-Host
