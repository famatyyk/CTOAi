param(
    [string]$Repo = 'famatyyk/CTOAi'
)

$runs = Invoke-RestMethod -Uri ('https://api.github.com/repos/{0}/actions/runs?per_page=30' -f $Repo) -Headers @{ 'User-Agent' = 'CTOAi-Agent' }
$last = $runs.workflow_runs | Where-Object { $_.name -eq 'CTOA Pipeline' } | Select-Object -First 1

if (-not $last) {
    Write-Output 'No CTOA Pipeline runs found'
    exit 0
}

if ($last.conclusion -ne 'failure') {
    Write-Output ('Last pipeline is {0} (id {1}) - no failed step to show' -f $last.conclusion, $last.id)
    Write-Output $last.html_url
    exit 0
}

$jobs = Invoke-RestMethod -Uri ('https://api.github.com/repos/{0}/actions/runs/{1}/jobs?per_page=100' -f $Repo, $last.id) -Headers @{ 'User-Agent' = 'CTOAi-Agent' }
$failed = $jobs.jobs | Where-Object { $_.conclusion -eq 'failure' } | Select-Object -First 1

if (-not $failed) {
    Write-Output ('Run {0} failed but no failed job found' -f $last.id)
    Write-Output $last.html_url
    exit 0
}

Write-Output ('Run ID: {0}' -f $last.id)
Write-Output ('Workflow: {0}' -f $last.name)
Write-Output ('Failed Job: {0}' -f $failed.name)
Write-Output ('Job URL: {0}' -f $failed.html_url)
