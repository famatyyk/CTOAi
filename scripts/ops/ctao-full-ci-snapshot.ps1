param(
    [string]$Repo = 'famatyyk/CTOAi'
)

$wanted = @(
    'CTOA Pipeline',
    'CTOA Smoke Must Pass',
    'CTOA Runtime Smoke E2E 8001',
    'Build and deploy Python app to Azure Web App - CTOAi'
)

$runs = Invoke-RestMethod -Uri ('https://api.github.com/repos/{0}/actions/runs?per_page=60' -f $Repo) -Headers @{ 'User-Agent' = 'CTOAi-Agent' }

foreach ($name in $wanted) {
    $run = $runs.workflow_runs | Where-Object { $_.name -eq $name } | Select-Object -First 1
    if ($null -eq $run) {
        Write-Output ('{0}: not found' -f $name)
        continue
    }
    Write-Output ('{0} => status={1}; conclusion={2}; run={3}; updated={4}' -f $name, $run.status, $run.conclusion, $run.id, $run.updated_at)
}
