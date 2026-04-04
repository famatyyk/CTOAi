param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Arg1,

    [Parameter(Position = 2)]
    [string]$Arg2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VpsScript = Join-Path $Root "scripts/ops/ctoa-vps.ps1"
$CommandDictionaryFile = Join-Path $Root "schemas/ctoa-command-dictionary.json"

function Get-CliVpsHost {
    $explicit = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST_CLI", "Process")
    if ([string]::IsNullOrWhiteSpace($explicit)) {
        $explicit = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST_CLI", "User")
    }
    if ([string]::IsNullOrWhiteSpace($explicit)) {
        return "46.225.110.52"
    }
    return $explicit
}

function Get-PythonExe {
    $venvPython = Join-Path $Root ".venv/Scripts/python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Get-UvicornExe {
    $venvUvicorn = Join-Path $Root ".venv/Scripts/uvicorn.exe"
    if (Test-Path $venvUvicorn) {
        return $venvUvicorn
    }
    return "uvicorn"
}

function Invoke-FromRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @()
    )

    Push-Location $Root
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-FromRootCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @()
    )

    Push-Location $Root
    try {
        try {
            $output = (& $FilePath @Arguments 2>&1 | Out-String)
            $exit = $LASTEXITCODE
        }
        catch {
            $output = ($_ | Out-String)
            $exit = 1
        }

        return @{
            ok = ($exit -eq 0)
            exit_code = $exit
            output = $output.TrimEnd()
        }
    }
    finally {
        Pop-Location
    }
}

function Get-CommandDictionary {
    if (-not (Test-Path $CommandDictionaryFile)) {
        return @{
            version = "missing"
            source = "missing"
            commands = @()
        }
    }

    try {
        $raw = Get-Content -Path $CommandDictionaryFile -Raw
        $payload = $raw | ConvertFrom-Json
        return @{
            version = [string]$payload.version
            source = [string]$payload.source
            commands = @($payload.commands)
        }
    }
    catch {
        return @{
            version = "invalid"
            source = "invalid"
            commands = @()
        }
    }
}

function Show-Help {
        $dict = Get-CommandDictionary
        $dictCount = @($dict.commands).Count

    @"
CTOAi CLI (MVP)

Usage:
  .\\ctoa.ps1 help
    .\\ctoa.ps1 menu
    .\\ctoa.ps1 dev
    .\\ctoa.ps1 ops
    .\\ctoa.ps1 prod
    .\\ctoa.ps1 status
  .\\ctoa.ps1 up
  .\\ctoa.ps1 test
  .\\ctoa.ps1 val <sprint>
  .\\ctoa.ps1 nightly [sprint]
  .\\ctoa.ps1 doctor
  .\\ctoa.ps1 vps <action>
    .\\ctoa.ps1 runner <status|restart|logs>
    .\\ctoa.ps1 report <status|restart|now|logs>
    .\\ctoa.ps1 mobile <status|restart|logs>
    .\\ctoa.ps1 logs <runner|health|agents|report|mobile>
  .\\ctoa.ps1 dash snap
    .\\ctoa.ps1 report now

Short aliases:
  h = help
    m = menu
    s = status
  t = test
  v = val
  n = nightly
  d = doctor
    dev = local dev profile
    ops = operator profile
    prod = release/profile gate

Examples:
    .\\ctoa.ps1 menu
    .\\ctoa.ps1 dev
    .\\ctoa.ps1 ops
    .\\ctoa.ps1 prod
    .\\ctoa.ps1 status
  .\\ctoa.ps1 up
  .\\ctoa.ps1 test
  .\\ctoa.ps1 val 029
  .\\ctoa.ps1 nightly 029
    .\\ctoa.ps1 runner status
    .\\ctoa.ps1 report restart
    .\\ctoa.ps1 mobile logs
  .\\ctoa.ps1 vps ValidateServices
  .\\ctoa.ps1 dash snap
  .\\ctoa.ps1 report now
"@ | Write-Host

        Write-Host ("Shared dictionary: version={0}, commands={1}" -f $dict.version, $dictCount) -ForegroundColor DarkGray
}

function Resolve-Sprint {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Sprint is required. Example: .\\ctoa.ps1 val 029"
    }

    if ($Value -notmatch "^\d{1,3}$") {
        throw "Invalid sprint '$Value'. Use digits only, e.g. 29 or 029."
    }

    return ([int]$Value).ToString("000")
}

function Invoke-ValidateSprint {
    param([string]$Sprint)

    $s = Resolve-Sprint $Sprint
    $python = Get-PythonExe
    $script = Join-Path $Root ("scripts/ops/sprint{0}_validate.py" -f $s)
    $jsonOut = Join-Path $Root ("runtime/ci-artifacts/sprint-{0}-validation.json" -f $s)

    if (-not (Test-Path $script)) {
        throw "Validator not found: $script"
    }

    Invoke-FromRoot -FilePath $python -Arguments @(
        $script,
        "--run-tests",
        "--json-out",
        $jsonOut
    )
}

function Invoke-Nightly {
    param([string]$Sprint = "029")

    $s = Resolve-Sprint $Sprint
    $python = Get-PythonExe
    $script = Join-Path $Root "scripts/ops/nightly_stability.py"
    $jsonOut = Join-Path $Root ("runtime/ci-artifacts/nightly-stability-sprint-{0}.json" -f $s)

    Invoke-FromRoot -FilePath $python -Arguments @(
        $script,
        "--sprint",
        $s,
        "--json-out",
        $jsonOut
    )
}

function Invoke-Up {
    $uvicorn = Get-UvicornExe
    Invoke-FromRoot -FilePath $uvicorn -Arguments @(
        "mobile_console.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8787",
        "--reload"
    )
}

function Invoke-Test {
    $python = Get-PythonExe
    Invoke-FromRoot -FilePath $python -Arguments @(
        "-m",
        "pytest",
        "tests/",
        "--ignore=tests/e2e",
        "-v"
    )
}

function Invoke-Doctor {
    $python = Get-PythonExe

    Write-Host "[doctor] core integrity" -ForegroundColor Cyan
    Invoke-FromRoot -FilePath $python -Arguments @("scripts/ops/core_guard.py", "--check")

    Write-Host "[doctor] runtime freeze" -ForegroundColor Cyan
    Invoke-FromRoot -FilePath $python -Arguments @("scripts/ops/runtime_path_guard.py")

    Write-Host "[doctor] sprint-029" -ForegroundColor Cyan
    Invoke-ValidateSprint -Sprint "029"
}

function Invoke-DevProfile {
    Write-Host "[dev] starting mobile console dev profile" -ForegroundColor Cyan
    Invoke-Up
}

function Invoke-OpsProfile {
    Write-Host "[ops] running operational health profile" -ForegroundColor Cyan
    Invoke-Doctor
}

function Invoke-ProdProfile {
    $python = Get-PythonExe

    Write-Host "[prod] update gate" -ForegroundColor Cyan
    Invoke-FromRoot -FilePath $python -Arguments @("scripts/ops/ctoa_update_gate.py")

    Write-Host "[prod] sprint-029 validation" -ForegroundColor Cyan
    Invoke-ValidateSprint -Sprint "029"
}

function Invoke-VpsAction {
    param(
        [string]$Action,
        [string[]]$ActionArgs = @()
    )

    if (-not (Test-Path $VpsScript)) {
        throw "VPS script not found: $VpsScript"
    }

    if ([string]::IsNullOrWhiteSpace($Action)) {
        throw "VPS action is required. Example: .\\ctoa.ps1 vps ValidateServices"
    }

    $invokeArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $VpsScript,
        "-Action",
        $Action
    ) + $ActionArgs

    $previousHost = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST", "Process")
    $previousRetries = [Environment]::GetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", "Process")
    $previousRetryDelay = [Environment]::GetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", "Process")
    [Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", (Get-CliVpsHost), "Process")
    [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", "2", "Process")
    [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", "2", "Process")
    try {
        Invoke-FromRoot -FilePath "powershell" -Arguments $invokeArgs
    }
    finally {
        [Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", $previousHost, "Process")
        [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", $previousRetries, "Process")
        [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", $previousRetryDelay, "Process")
    }
}

function Invoke-VpsActionCapture {
    param(
        [string]$Action,
        [string[]]$ActionArgs = @()
    )

    if (-not (Test-Path $VpsScript)) {
        return @{
            ok = $false
            exit_code = 1
            output = ("VPS script not found: {0}" -f $VpsScript)
        }
    }

    if ([string]::IsNullOrWhiteSpace($Action)) {
        return @{
            ok = $false
            exit_code = 1
            output = "VPS action is required"
        }
    }

    $invokeArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $VpsScript,
        "-Action",
        $Action
    ) + $ActionArgs

    $previousHost = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST", "Process")
    $previousRetries = [Environment]::GetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", "Process")
    $previousRetryDelay = [Environment]::GetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", "Process")
    [Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", (Get-CliVpsHost), "Process")
    [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", "2", "Process")
    [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", "2", "Process")
    try {
        return Invoke-FromRootCapture -FilePath "powershell" -Arguments $invokeArgs
    }
    finally {
        [Environment]::SetEnvironmentVariable("CTOA_VPS_HOST", $previousHost, "Process")
        [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_ATTEMPTS", $previousRetries, "Process")
        [Environment]::SetEnvironmentVariable("CTOA_SSH_RETRY_DELAY_SECONDS", $previousRetryDelay, "Process")
    }
}

function Invoke-RunnerCommand {
    param([string]$Subcommand)

    $mode = (Get-ValueOrDefault -Value $Subcommand -Fallback "status").ToLowerInvariant()
    switch ($mode) {
        "status" { Invoke-VpsAction -Action "ShowPipelineProgress"; break }
        "restart" { Invoke-VpsAction -Action "HealService" -ActionArgs @("-ServiceName", "ctoa-runner"); break }
        "logs" { Invoke-VpsAction -Action "ReportErrorDetails"; break }
        default { throw "Unknown runner subcommand '$Subcommand'. Use status|restart|logs" }
    }
}

function Invoke-ReportCommand {
    param([string]$Subcommand)

    $mode = (Get-ValueOrDefault -Value $Subcommand -Fallback "status").ToLowerInvariant()
    switch ($mode) {
        "status" { Invoke-VpsAction -Action "InspectReportEnv"; break }
        "restart" { Invoke-VpsAction -Action "HealService" -ActionArgs @("-ServiceName", "ctoa-report"); break }
        "logs" { Invoke-VpsAction -Action "ReportErrorDetails"; break }
        "now" { Invoke-ReportNow; break }
        default { throw "Unknown report subcommand '$Subcommand'. Use status|restart|now|logs" }
    }
}

function Invoke-MobileCommand {
    param([string]$Subcommand)

    $mode = (Get-ValueOrDefault -Value $Subcommand -Fallback "status").ToLowerInvariant()
    switch ($mode) {
        "status" { Invoke-VpsAction -Action "ValidateServices"; break }
        "restart" { Invoke-VpsAction -Action "HealService" -ActionArgs @("-ServiceName", "ctoa-mobile-console"); break }
        "logs" { Invoke-VpsAction -Action "TailMobileLogs"; break }
        default { throw "Unknown mobile subcommand '$Subcommand'. Use status|restart|logs" }
    }
}

function Invoke-LogsCommand {
    param([string]$Target)

    $name = (Get-ValueOrDefault -Value $Target -Fallback "runner").ToLowerInvariant()
    switch ($name) {
        "runner" { Invoke-VpsAction -Action "ReportErrorDetails"; break }
        "agents" { Invoke-VpsAction -Action "TailAgents"; break }
        "health" { Invoke-VpsAction -Action "ShowSystemHealth"; break }
        "report" { Invoke-VpsAction -Action "ReportErrorDetails"; break }
        "mobile" { Invoke-VpsAction -Action "TailMobileLogs"; break }
        default { throw "Unknown logs target '$Target'. Use runner|health|agents|report|mobile" }
    }
}

function Invoke-StatusSnapshot {
    $python = Get-PythonExe

    $core = Invoke-FromRootCapture -FilePath $python -Arguments @("scripts/ops/core_guard.py", "--check")
    $runtime = Invoke-FromRootCapture -FilePath $python -Arguments @("scripts/ops/runtime_path_guard.py")
    $sprint029 = Invoke-FromRootCapture -FilePath $python -Arguments @(
        "scripts/ops/sprint029_validate.py",
        "--run-tests",
        "--json-out",
        "runtime/ci-artifacts/sprint-029-validation.json"
    )

    $vpsValidate = Invoke-VpsActionCapture -Action "ValidateServices"

    $dashboardToken = [Environment]::GetEnvironmentVariable("CTOA_MOBILE_TOKEN", "Process")
    if ([string]::IsNullOrWhiteSpace($dashboardToken)) {
        $dashboardToken = [Environment]::GetEnvironmentVariable("CTOA_MOBILE_TOKEN", "User")
    }

    try {
        $dashboardHeaders = @{}
        if (-not [string]::IsNullOrWhiteSpace($dashboardToken)) {
            $dashboardHeaders["X-CTOA-TOKEN"] = $dashboardToken
        }

        $dashboardResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8787/api/health" -Method Get -TimeoutSec 5 -Headers $dashboardHeaders
        $dashboard = @{
            ok = $true
            exit_code = 0
            output = ($dashboardResponse | ConvertTo-Json -Compress)
        }
    }
    catch {
        $dashboardMessage = $_.Exception.Message
        if (
            [string]::IsNullOrWhiteSpace($dashboardToken) -and
            ($dashboardMessage -match "401" -or $dashboardMessage -match "403")
        ) {
            $dashboard = @{
                ok = $true
                exit_code = 0
                output = "AUTH_REQUIRED: API reachable but token not provided"
            }
        }
        else {
            $dashboard = @{
                ok = $false
                exit_code = 1
                output = ("ERROR: {0}" -f $dashboardMessage)
            }
        }
    }

    $dict = Get-CommandDictionary

    $isOk = $core.ok -and $runtime.ok -and $sprint029.ok -and $vpsValidate.ok -and $dashboard.ok
    $payload = [ordered]@{
        timestamp = (Get-Date).ToString("s")
        ok = $isOk
        command_dictionary = [ordered]@{
            version = $dict.version
            source = $dict.source
            count = @($dict.commands).Count
        }
        local = [ordered]@{
            core_guard = $core
            runtime_freeze = $runtime
            sprint_029 = $sprint029
        }
        vps = [ordered]@{
            validate_services = $vpsValidate
        }
        dashboard = [ordered]@{
            health_api = $dashboard
        }
    }

    ($payload | ConvertTo-Json -Depth 6) | Write-Output
}

function Invoke-DashboardSnapshot {
    Invoke-VpsAction -Action "DashboardSnapshot"
}

function Invoke-ReportNow {
    Invoke-VpsAction -Action "ReportViaServiceEnv"
}

function Get-ValueOrDefault {
    param(
        [string]$Value,
        [string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Fallback
    }
    return $Value
}

function Show-Menu {
    Write-Host "" 
    Write-Host "CTOAi CLI Menu" -ForegroundColor Cyan
    Write-Host "  1. Help"
    Write-Host "  2. Dev profile"
    Write-Host "  3. Ops profile"
    Write-Host "  4. Prod profile"
    Write-Host "  5. Run tests"
    Write-Host "  6. Validate sprint-029"
    Write-Host "  7. Nightly sprint-029"
    Write-Host "  8. Status snapshot (local+VPS+dashboard)"
    Write-Host "  9. Runner status"
    Write-Host " 10. Report restart"
    Write-Host " 11. Mobile status"
    Write-Host " 12. Logs runner"
    Write-Host " 13. VPS ValidateServices"
    Write-Host " 14. Dashboard snapshot"
    Write-Host " 15. Report now"
    Write-Host "  0. Exit"
    Write-Host ""

    $choice = Read-Host "Select option"
    switch ($choice) {
        "1" { Show-Help; break }
        "2" { Invoke-DevProfile; break }
        "3" { Invoke-OpsProfile; break }
        "4" { Invoke-ProdProfile; break }
        "5" { Invoke-Test; break }
        "6" { Invoke-ValidateSprint -Sprint "029"; break }
        "7" { Invoke-Nightly -Sprint "029"; break }
        "8" { Invoke-StatusSnapshot; break }
        "9" { Invoke-RunnerCommand -Subcommand "status"; break }
        "10" { Invoke-ReportCommand -Subcommand "restart"; break }
        "11" { Invoke-MobileCommand -Subcommand "status"; break }
        "12" { Invoke-LogsCommand -Target "runner"; break }
        "13" { Invoke-VpsAction -Action "ValidateServices"; break }
        "14" { Invoke-DashboardSnapshot; break }
        "15" { Invoke-ReportNow; break }
        "0" { return }
        default { throw "Unknown menu option '$choice'." }
    }
}

switch ($Command.ToLowerInvariant()) {
    "help" { Show-Help; break }
    "h" { Show-Help; break }

    "menu" { Show-Menu; break }
    "m" { Show-Menu; break }

    "status" { Invoke-StatusSnapshot; break }
    "s" { Invoke-StatusSnapshot; break }

    "dev" { Invoke-DevProfile; break }
    "ops" { Invoke-OpsProfile; break }
    "prod" { Invoke-ProdProfile; break }

    "up" { Invoke-Up; break }

    "test" { Invoke-Test; break }
    "t" { Invoke-Test; break }

    "val" { Invoke-ValidateSprint -Sprint $Arg1; break }
    "v" { Invoke-ValidateSprint -Sprint $Arg1; break }

    "nightly" { Invoke-Nightly -Sprint (Get-ValueOrDefault -Value $Arg1 -Fallback "029"); break }
    "n" { Invoke-Nightly -Sprint (Get-ValueOrDefault -Value $Arg1 -Fallback "029"); break }

    "doctor" { Invoke-Doctor; break }
    "d" { Invoke-Doctor; break }

    "vps" { Invoke-VpsAction -Action $Arg1; break }

    "runner" { Invoke-RunnerCommand -Subcommand $Arg1; break }
    "report" {
        if ((Get-ValueOrDefault -Value $Arg1 -Fallback "").ToLowerInvariant() -eq "now") {
            Invoke-ReportNow
            break
        }
        Invoke-ReportCommand -Subcommand $Arg1
        break
    }
    "mobile" { Invoke-MobileCommand -Subcommand $Arg1; break }
    "logs" { Invoke-LogsCommand -Target $Arg1; break }

    "dash" {
        if ((Get-ValueOrDefault -Value $Arg1 -Fallback "").ToLowerInvariant() -eq "snap") {
            Invoke-DashboardSnapshot
            break
        }
        throw "Unknown dash action '$Arg1'. Use: .\\ctoa.ps1 dash snap"
    }

    default {
        throw "Unknown command '$Command'. Run: .\\ctoa.ps1 help"
    }
}
