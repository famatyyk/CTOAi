param(
    [Parameter(Position = 0)]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Arg1,

    [Parameter(Position = 2)]
    [string]$Arg2,

    [Parameter(Position = 3)]
    [string]$Arg3,

    [Parameter(Position = 4)]
    [string]$Arg4,

    [Parameter(Position = 5)]
    [string]$Arg5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VpsScript = Join-Path $Root "scripts/ops/ctoa-vps.ps1"
$CommandDictionaryFile = Join-Path $Root "schemas/ctoa-command-dictionary.json"
$ControlCenterOpenScript = Join-Path $Root "scripts/windows/open-control-center.ps1"

function Get-CliVpsHost {
    $explicit = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST_CLI", "Process")
    if ([string]::IsNullOrWhiteSpace($explicit)) {
        $explicit = [Environment]::GetEnvironmentVariable("CTOA_VPS_HOST_CLI", "User")
    }
    if ([string]::IsNullOrWhiteSpace($explicit)) {
        return "116.202.96.250"
    }
    return $explicit
}

function Get-PythonExe {
    $venvPython = Join-Path $Root ".venv/Scripts/python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    throw "Missing repo-local Python at $venvPython. Create the virtual environment with: python -m venv .venv"
}

function Resolve-ControlCenterUrl {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        throw "Control Center URL must not be empty."
    }

    if ($Candidate -match "\\") {
        throw "Control Center URL path must not include backslashes."
    }

    $decodedCandidate = [System.Uri]::UnescapeDataString($Candidate)
    $rawTraversalSegments = @($decodedCandidate -split "/" | Where-Object { $_ -eq "." -or $_ -eq ".." })
    if ($rawTraversalSegments.Count -gt 0) {
        throw "Control Center URL path must not contain traversal."
    }

    $uri = $null
    if (-not [System.Uri]::TryCreate($Candidate, [System.UriKind]::Absolute, [ref]$uri)) {
        throw "Control Center URL must be absolute."
    }

    if ($uri.Scheme -notin @("http", "https")) {
        throw "Control Center URL must use http:// or https://."
    }

    if (-not [string]::IsNullOrWhiteSpace($uri.UserInfo)) {
        throw "Control Center URL must not include credentials."
    }

    if (-not [string]::IsNullOrWhiteSpace($uri.Query) -or -not [string]::IsNullOrWhiteSpace($uri.Fragment)) {
        throw "Control Center URL must not include query strings or fragments."
    }

    $decodedPath = [System.Uri]::UnescapeDataString($uri.AbsolutePath)
    if ($decodedPath -match "\\") {
        throw "Control Center URL path must not include backslashes."
    }
    $traversalSegments = @($decodedPath -split "/" | Where-Object { $_ -eq "." -or $_ -eq ".." })
    if ($traversalSegments.Count -gt 0) {
        throw "Control Center URL path must not contain traversal."
    }

    $hostName = $uri.Host.ToLowerInvariant()
    $isLocalHost = $hostName -in @("localhost", "127.0.0.1", "::1")
    if ($uri.Scheme -eq "http" -and -not $isLocalHost) {
        throw "Non-local Control Center URLs must use https://."
    }

    return $uri.AbsoluteUri
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
    .\\ctoa.ps1 next
    .\\ctoa.ps1 cc
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
    .\\ctoa.ps1 otprofile "<opis profilu EK>"
    .\\ctoa.ps1 otpreview
    .\\ctoa.ps1 otmockup
    .\\ctoa.ps1 otdeploy approve-live
    .\\ctoa.ps1 otest
    .\\ctoa.ps1 otbg
    .\\ctoa.ps1 otp9
    .\\ctoa.ps1 otp9accept "accept P9 conditions shadow"
    .\\ctoa.ps1 otp10doctor [init]
    .\\ctoa.ps1 otp10preview
    .\\ctoa.ps1 otp10catalog
    .\\ctoa.ps1 otp10plan [equippedItem candidateItem container slot "plan P10 capture profile change"]
    .\\ctoa.ps1 otp10autoplan equippedItem candidateItem "plan P10 capture profile change"
    .\\ctoa.ps1 otp10apply planSha "zatwierdzam zastosowanie planu P10 <planSha>"
    .\\ctoa.ps1 otp10preflight
    .\\ctoa.ps1 otp10ready
    .\\ctoa.ps1 otp10refresh
    .\\ctoa.ps1 otp10
    .\\ctoa.ps1 otp10accept "accept P10 equipment shadow"
    .\\ctoa.ps1 otp11catalog
    .\\ctoa.ps1 brain <refresh|doctor|pack>

Short aliases:
  h = help
    nx = next
    cc = open Control Center
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
    .\\ctoa.ps1 next
    .\\ctoa.ps1 cc
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
  .\\ctoa.ps1 otprofile "EK monk, bez aoe na 1, exeta od 2 visible, potion F1 heal 80"
  .\\ctoa.ps1 otpreview
  .\\ctoa.ps1 otmockup
  .\\ctoa.ps1 otdeploy approve-live
  .\\ctoa.ps1 otest
  .\\ctoa.ps1 otbg
  .\\ctoa.ps1 otp9
  .\\ctoa.ps1 otp9accept "accept P9 conditions shadow"
  .\\ctoa.ps1 otp10doctor [init]
  .\\ctoa.ps1 otp10preview
  .\\ctoa.ps1 otp10catalog
  .\\ctoa.ps1 otp10plan 3051 3048 2 1 "plan P10 capture profile change"
  .\\ctoa.ps1 otp10autoplan 3051 3048 "plan P10 capture profile change"
  .\\ctoa.ps1 otp10apply <planSha> "zatwierdzam zastosowanie planu P10 <planSha>"
  .\\ctoa.ps1 otp10preflight
  .\\ctoa.ps1 otp10ready
  .\\ctoa.ps1 otp10refresh
  .\\ctoa.ps1 otp10
  .\\ctoa.ps1 otp10accept "accept P10 equipment shadow"
  .\\ctoa.ps1 otp11catalog
  .\\ctoa.ps1 brain refresh
  .\\ctoa.ps1 brain doctor
  .\\ctoa.ps1 brain pack
"@ | Write-Host

        Write-Host ("Shared dictionary: version={0}, commands={1}" -f $dict.version, $dictCount) -ForegroundColor DarkGray
}

function Get-GitExe {
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }

    $windowsGit = "C:\Program Files\Git\cmd\git.exe"
    if (Test-Path $windowsGit) {
        return $windowsGit
    }

    return ""
}

function Get-NpmExe {
    foreach ($name in @("npm.cmd", "npm")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $cmd.Source
        }
    }

    return ""
}

function Get-WorktreeSummary {
    $git = Get-GitExe
    if ([string]::IsNullOrWhiteSpace($git)) {
        return "git unavailable in PATH; use C:\Program Files\Git\cmd\git.exe if you need raw git."
    }

    Push-Location $Root
    try {
        $lines = @(& $git status --short 2>$null)
        if ($LASTEXITCODE -ne 0) {
            return "git status failed; run .\\ctoa.ps1 brain doctor before sync/push work."
        }
        if (@($lines).Count -eq 0) {
            return "clean"
        }
        return ("{0} changed/untracked paths" -f @($lines).Count)
    }
    finally {
        Pop-Location
    }
}

function Show-Next {
    $worktree = Get-WorktreeSummary

    Write-Host ""
    Write-Host "CTOAi next step" -ForegroundColor Cyan
    Write-Host ("Worktree: {0}" -f $worktree)
    Write-Host ""
    Write-Host "Do this now:" -ForegroundColor Cyan
    Write-Host "  1. Run .\ctoa.ps1 cc if you need the visual Control Center."
    Write-Host "  2. Open docs/INDEX.md if you need orientation."
    Write-Host "  3. Continue the current lane: Control Center + evidence/reporting + VPS parity."
    Write-Host ""
    Write-Host "Do not start a new lane until this is clean:" -ForegroundColor Yellow
    Write-Host "  - package current docs/env parity changes into one reviewable commit or PR"
    Write-Host "  - keep unrelated bot/UI changes out of that review unit"
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  .\ctoa.ps1 cc"
    Write-Host "  .\ctoa.ps1 status"
    Write-Host "  python -m pytest tests/test_vps_python_parity.py -q"
    Write-Host "  cd web; npm test -- --run src/lib/__tests__/controlCenterEvidence.test.ts"
}

function Open-ControlCenter {
    $url = [Environment]::GetEnvironmentVariable("CTOA_CONTROL_CENTER_URL", "Process")
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = [Environment]::GetEnvironmentVariable("CTOA_CONTROL_CENTER_URL", "User")
    }
    if ([string]::IsNullOrWhiteSpace($url)) {
        $url = "http://127.0.0.1:3000/control-center"
    }
    $url = Resolve-ControlCenterUrl -Candidate $url

    $responding = $false
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null
        $responding = $true
        Write-Host "Control Center is responding: $url" -ForegroundColor Cyan
    }
    catch {
        $webDir = Join-Path $Root "web"
        Write-Host "Control Center is not responding yet: $url" -ForegroundColor Yellow
        $npm = Get-NpmExe
        if ([string]::IsNullOrWhiteSpace($npm)) {
            Write-Host "npm was not found. Install Node.js or run from a shell where npm is available." -ForegroundColor Yellow
        }
        else {
            Write-Host "Starting web dev server in background: cd web; npm run dev"
            Start-Process -FilePath $npm -ArgumentList @("run", "dev") -WorkingDirectory $webDir -WindowStyle Hidden
            Start-Sleep -Seconds 3
        }

        try {
            Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
            $responding = $true
            Write-Host "Control Center started: $url" -ForegroundColor Cyan
        }
        catch {
            Write-Host "Control Center is still warming up. Browser will open now; refresh in a few seconds." -ForegroundColor Yellow
        }
    }

    if (Test-Path $ControlCenterOpenScript) {
        Invoke-FromRoot -FilePath "powershell" -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $ControlCenterOpenScript,
            "-Url",
            $url
        )
        return
    }

    Start-Process -FilePath $url
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
    $python = Get-PythonExe
    Invoke-FromRoot -FilePath $python -Arguments @(
        "-m",
        "uvicorn",
        "mobile_console.app:app",
        "--host",
        "127.0.0.1",
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

function Invoke-OtProfileBuilder {
    param(
        [string]$Request
    )

    if ([string]::IsNullOrWhiteSpace($Request)) {
        throw "Missing profile request. Example: .\\ctoa.ps1 otprofile `"EK monk, bez aoe na 1, exeta od 2 visible, potion F1 heal 80`""
    }

    $python = Get-PythonExe
    $script = Join-Path $Root "scripts/ops/ctoa_otprofile_builder.py"
    Invoke-FromRoot -FilePath $python -Arguments @($script, "--request", $Request)
}

function Invoke-OtHelperPreview {
    $python = Get-PythonExe
    $script = Join-Path $Root "scripts/ops/ctoa_helper_ui_preview.py"
    Invoke-FromRoot -FilePath $python -Arguments @($script)
    $preview = Join-Path $Root "runtime/otclient_ui_preview/ctoa_helper_preview.html"
    if (Test-Path $preview) {
        Start-Process -FilePath $preview
    }
}

function Invoke-OtHelperMockup {
    $python = Get-PythonExe
    $script = Join-Path $Root "scripts/ops/ctoa_helper_ui_mockup_v4.py"
    Invoke-FromRoot -FilePath $python -Arguments @($script)
    $mockup = Join-Path $Root "runtime/otclient_ui_preview/ctoa_helper_mockup_v4.html"
    if (Test-Path $mockup) {
        Start-Process -FilePath $mockup
    }
}

function Invoke-OtHelperDeploy {
    param([string]$Approval)

    if ($Approval -cne "approve-live") {
        throw "Live Helper promotion requires: .\ctoa.ps1 otdeploy approve-live"
    }

    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
    Invoke-FromRoot -FilePath $powershell -Arguments @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $wrapper,
        "-Action",
        "PromoteLiveCtoa",
        "-ApproveLiveDeploy"
    )
}

function Invoke-OtTestLoop {
    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
    Invoke-FromRoot -FilePath $powershell -Arguments @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $wrapper,
        "-Action",
        "ValidateDev"
    )
    Invoke-OtHelperPreview
}

function Invoke-OtBackgroundStatus {
    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
    Invoke-FromRoot -FilePath $powershell -Arguments @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $wrapper,
        "-Action",
        "BackgroundStatus",
        "-OperatorMode",
        "BackgroundNoScreen"
    )
}

function Invoke-OtConditionsShadowReplay {
    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
    $backgroundPath = Join-Path $Root "runtime\solteria_helper_dev\background_status.json"
    $observationStartedAt = [DateTime]::UtcNow.AddSeconds(-1)
    $backgroundResult = Invoke-FromRootCapture -FilePath $powershell -Arguments @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $wrapper,
        "-Action",
        "BackgroundStatus",
        "-OperatorMode",
        "BackgroundNoScreen"
    )
    if (-not [string]::IsNullOrWhiteSpace([string]$backgroundResult.output)) {
        Write-Output $backgroundResult.output
    }
    if ([int]$backgroundResult.exit_code -notin @(0, 1)) {
        throw "P9 Conditions shadow replay could not collect bounded P8 evidence (exit $($backgroundResult.exit_code))."
    }
    if (-not (Test-Path -LiteralPath $backgroundPath -PathType Leaf)) {
        throw "P9 Conditions shadow replay requires a current BackgroundNoScreen artifact: $backgroundPath"
    }
    $backgroundItem = Get-Item -LiteralPath $backgroundPath -Force
    if (
        ($backgroundItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $backgroundItem.LastWriteTimeUtc -lt $observationStartedAt
    ) {
        throw "P9 Conditions shadow replay rejects stale or reparse-point BackgroundNoScreen output."
    }

    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $recoveryScript = Join-Path $Root "scripts\ops\otclient_conditions_recovery_proof.py"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_conditions_shadow_replay.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P9 Conditions shadow replay requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P9 Conditions shadow replay tool is missing: $scriptPath"
    }
    if (-not (Test-Path -LiteralPath $recoveryScript -PathType Leaf)) {
        throw "P9 passive Recovery proof producer is missing: $recoveryScript"
    }

    $previousOperatorMode = $env:CTOA_OPERATOR_MODE
    try {
        $env:CTOA_OPERATOR_MODE = "background_no_screen"
        Invoke-FromRoot -FilePath $python -Arguments @($recoveryScript, "--allow-blocked")
        Invoke-FromRoot -FilePath $python -Arguments @($scriptPath)
    }
    finally {
        if ($null -eq $previousOperatorMode) {
            Remove-Item Env:CTOA_OPERATOR_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:CTOA_OPERATOR_MODE = $previousOperatorMode
        }
    }
}

function Invoke-OtEquipmentShadowReplay {
    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
    $backgroundPath = Join-Path $Root "runtime\solteria_helper_dev\background_status.json"
    $observationStartedAt = [DateTime]::UtcNow.AddSeconds(-1)
    $backgroundResult = Invoke-FromRootCapture -FilePath $powershell -Arguments @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $wrapper,
        "-Action",
        "BackgroundStatus",
        "-OperatorMode",
        "BackgroundNoScreen"
    )
    if (-not [string]::IsNullOrWhiteSpace([string]$backgroundResult.output)) {
        Write-Output $backgroundResult.output
    }
    if ([int]$backgroundResult.exit_code -notin @(0, 1)) {
        throw "P10 Equipment replay could not collect bounded P8 evidence (exit $($backgroundResult.exit_code))."
    }
    if (-not (Test-Path -LiteralPath $backgroundPath -PathType Leaf)) {
        throw "P10 Equipment replay requires a current BackgroundNoScreen artifact: $backgroundPath"
    }
    $backgroundItem = Get-Item -LiteralPath $backgroundPath -Force
    if (
        ($backgroundItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $backgroundItem.LastWriteTimeUtc -lt $observationStartedAt
    ) {
        throw "P10 Equipment replay rejects stale or reparse-point BackgroundNoScreen output."
    }

    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $snapshotScript = Join-Path $Root "scripts\ops\otclient_equipment_shadow_snapshot.py"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_shadow_replay.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 Equipment shadow replay requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 Equipment shadow replay tool is missing: $scriptPath"
    }
    if (-not (Test-Path -LiteralPath $snapshotScript -PathType Leaf)) {
        throw "P10 Equipment shadow snapshot producer is missing: $snapshotScript"
    }
    $previousOperatorMode = $env:CTOA_OPERATOR_MODE
    try {
        $env:CTOA_OPERATOR_MODE = "background_no_screen"
        $snapshotResult = Invoke-FromRootCapture -FilePath $python -Arguments @($snapshotScript)
        if (-not [string]::IsNullOrWhiteSpace([string]$snapshotResult.output)) {
            Write-Host ([string]$snapshotResult.output)
        }
        $replayResult = Invoke-FromRootCapture -FilePath $python -Arguments @($scriptPath, "--source", "operational")
        if (-not [string]::IsNullOrWhiteSpace([string]$replayResult.output)) {
            Write-Host ([string]$replayResult.output)
        }
        if (-not $snapshotResult.ok -or -not $replayResult.ok) {
            throw "P10 operational snapshot/replay remains fail-closed. Inspect the canonical ingest and replay reports."
        }
    }
    finally {
        if ($null -eq $previousOperatorMode) {
            Remove-Item Env:CTOA_OPERATOR_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:CTOA_OPERATOR_MODE = $previousOperatorMode
        }
    }
}

function Invoke-OtEquipmentObservationPreview {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_observation_preview.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 equipment observation preview requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 equipment observation preview tool is missing: $scriptPath"
    }
    $previousOperatorMode = $env:CTOA_OPERATOR_MODE
    try {
        $env:CTOA_OPERATOR_MODE = "background_no_screen"
        Invoke-FromRoot -FilePath $python -Arguments @($scriptPath, "--allow-blocked")
    }
    finally {
        if ($null -eq $previousOperatorMode) {
            Remove-Item Env:CTOA_OPERATOR_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:CTOA_OPERATOR_MODE = $previousOperatorMode
        }
    }
}

function Invoke-OtEquipmentCandidateCatalog {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_candidate_catalog.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 equipment candidate catalog requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 equipment candidate catalog tool is missing: $scriptPath"
    }
    $previousOperatorMode = $env:CTOA_OPERATOR_MODE
    try {
        $env:CTOA_OPERATOR_MODE = "background_no_screen"
        Invoke-FromRoot -FilePath $python -Arguments @($scriptPath, "--allow-blocked")
    }
    finally {
        if ($null -eq $previousOperatorMode) {
            Remove-Item Env:CTOA_OPERATOR_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:CTOA_OPERATOR_MODE = $previousOperatorMode
        }
    }
}

function Invoke-OtEquipmentCaptureProfileChangePlan {
    param(
        [string]$EquippedItemId,
        [string]$CandidateItemId,
        [string]$CandidateContainerId,
        [string]$CandidateSlotIndex,
        [string]$Confirmation,
        [switch]$RefreshPreview
    )
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_capture_profile_change_plan.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 capture-profile change plan requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 capture-profile change plan generator is missing: $scriptPath"
    }
    if ($RefreshPreview) {
        $powershell = (Get-Command powershell -ErrorAction Stop).Source
        $wrapper = Join-Path $Root "scripts/windows/solteria_helper_test_env.ps1"
        $backgroundPath = Join-Path $Root "runtime\solteria_helper_dev\background_status.json"
        $observationStartedAt = [DateTime]::UtcNow.AddSeconds(-1)
        $backgroundResult = Invoke-FromRootCapture -FilePath $powershell -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $wrapper,
            "-Action",
            "BackgroundStatus",
            "-OperatorMode",
            "BackgroundNoScreen"
        )
        if (-not [string]::IsNullOrWhiteSpace([string]$backgroundResult.output)) {
            Write-Output $backgroundResult.output
        }
        if ([int]$backgroundResult.exit_code -notin @(0, 1)) {
            throw "P10 autoplan could not collect bounded BackgroundNoScreen evidence (exit $($backgroundResult.exit_code))."
        }
        if (-not (Test-Path -LiteralPath $backgroundPath -PathType Leaf)) {
            throw "P10 autoplan requires a current BackgroundNoScreen artifact: $backgroundPath"
        }
        $backgroundItem = Get-Item -LiteralPath $backgroundPath -Force
        if (
            ($backgroundItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or
            $backgroundItem.LastWriteTimeUtc -lt $observationStartedAt
        ) {
            throw "P10 autoplan rejects stale or reparse-point BackgroundNoScreen output."
        }
    }
    $arguments = @($scriptPath, "--allow-blocked")
    if (-not [string]::IsNullOrWhiteSpace($EquippedItemId)) {
        $arguments += @("--equipped-item-id", $EquippedItemId)
    }
    if (-not [string]::IsNullOrWhiteSpace($CandidateItemId)) {
        $arguments += @("--candidate-item-id", $CandidateItemId)
    }
    if (-not [string]::IsNullOrWhiteSpace($CandidateContainerId)) {
        $arguments += @("--candidate-container-id", $CandidateContainerId)
    }
    if (-not [string]::IsNullOrWhiteSpace($CandidateSlotIndex)) {
        $arguments += @("--candidate-slot-index", $CandidateSlotIndex)
    }
    if (-not [string]::IsNullOrWhiteSpace($Confirmation)) {
        $arguments += @("--confirm", $Confirmation)
    }
    if ($RefreshPreview) {
        $arguments += "--refresh-preview"
    }
    Invoke-FromRoot -FilePath $python -Arguments $arguments
}

function Invoke-OtEquipmentCaptureProfileDoctor {
    param([string]$Action)
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_capture_profile_doctor.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 capture-profile doctor requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 capture-profile doctor is missing: $scriptPath"
    }
    $arguments = @($scriptPath)
    switch ((Get-ValueOrDefault -Value $Action -Fallback "").ToLowerInvariant()) {
        "" { }
        "init" { $arguments += "--init-local" }
        default { throw "Unknown otp10doctor action '$Action'. Use: .\\ctoa.ps1 otp10doctor [init]" }
    }
    Invoke-FromRoot -FilePath $python -Arguments $arguments
}

function Invoke-OtEquipmentCaptureProfileApply {
    param(
        [string]$PlanSha256,
        [string]$Confirmation
    )
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_capture_profile_apply.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 capture-profile apply requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 capture-profile apply tool is missing: $scriptPath"
    }
    if ([string]::IsNullOrWhiteSpace($PlanSha256)) {
        throw "otp10apply requires the reviewed plan SHA-256."
    }
    $arguments = @($scriptPath, "--plan-sha256", $PlanSha256)
    if (-not [string]::IsNullOrWhiteSpace($Confirmation)) {
        $arguments += @("--confirm", $Confirmation)
    }
    Invoke-FromRoot -FilePath $python -Arguments $arguments
}

function Invoke-OtEquipmentDependencyPreflight {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_dependency_preflight.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 dependency preflight requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 dependency preflight is missing: $scriptPath"
    }
    Invoke-FromRoot -FilePath $python -Arguments @($scriptPath)
}

function Invoke-OtEquipmentOperatorReadiness {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_operator_readiness.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 operator readiness requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 operator readiness tool is missing: $scriptPath"
    }
    Invoke-FromRoot -FilePath $python -Arguments @($scriptPath, "--allow-blocked")
}

function Invoke-OtEquipmentOperatorRefresh {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_operator_refresh.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 operator refresh requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 operator refresh orchestrator is missing: $scriptPath"
    }
    $previousOperatorMode = $env:CTOA_OPERATOR_MODE
    try {
        $env:CTOA_OPERATOR_MODE = "background_no_screen"
        Invoke-FromRoot -FilePath $python -Arguments @($scriptPath)
    }
    finally {
        if ($null -eq $previousOperatorMode) {
            Remove-Item Env:CTOA_OPERATOR_MODE -ErrorAction SilentlyContinue
        }
        else {
            $env:CTOA_OPERATOR_MODE = $previousOperatorMode
        }
    }
}

function Invoke-OtConditionsShadowAcceptance {
    param([string]$Confirmation)
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_conditions_shadow_acceptance.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P9 Conditions acceptance requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P9 Conditions acceptance tool is missing: $scriptPath"
    }
    $arguments = @($scriptPath)
    if (-not [string]::IsNullOrWhiteSpace($Confirmation)) {
        $arguments += @("--confirm", $Confirmation)
    }
    Invoke-FromRoot -FilePath $python -Arguments $arguments
}

function Invoke-OtEquipmentShadowAcceptance {
    param([string]$Confirmation)
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_equipment_shadow_acceptance.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P10 Equipment acceptance requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 Equipment acceptance tool is missing: $scriptPath"
    }
    $arguments = @($scriptPath)
    if (-not [string]::IsNullOrWhiteSpace($Confirmation)) {
        $arguments += @("--confirm", $Confirmation)
    }
    Invoke-FromRoot -FilePath $python -Arguments $arguments
}

function Invoke-OtHealFriendCandidateCatalog {
    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $Root "scripts\ops\otclient_heal_friend_candidate_catalog.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "P11 candidate catalog requires the trusted repo interpreter: $python"
    }
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P11 candidate catalog tool is missing: $scriptPath"
    }
    Invoke-FromRoot -FilePath $python -Arguments @($scriptPath, "--allow-blocked")
}

function Invoke-EngineBrain {
    param(
        [string]$Subcommand,
        [string]$Profile
    )

    $mode = (Get-ValueOrDefault -Value $Subcommand -Fallback "refresh").ToLowerInvariant()
    switch ($mode) {
        "refresh" {
            $python = Get-PythonExe
            Invoke-FromRoot -FilePath $python -Arguments @("scripts/ops/engine_brain_index.py")
            break
        }
        "doctor" {
            $python = Get-PythonExe
            Invoke-FromRoot -FilePath $python -Arguments @("scripts/ops/engine_brain_doctor.py")
            break
        }
        "pack" {
            $python = Get-PythonExe
            $args = @("scripts/ops/engine_brain_pack.py")
            if (-not [string]::IsNullOrWhiteSpace($Profile)) {
                $args += @("--profile", $Profile)
            }
            Invoke-FromRoot -FilePath $python -Arguments $args
            break
        }
        default { throw "Unknown brain subcommand '$Subcommand'. Use refresh|doctor|pack [all|control-central|helper|control-center|infra|security]" }
    }
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
    Write-Host "  1. Next recommended step"
    Write-Host "  2. Open Control Center"
    Write-Host "  3. Help"
    Write-Host "  4. Dev profile"
    Write-Host "  5. Ops profile"
    Write-Host "  6. Prod profile"
    Write-Host "  7. Run tests"
    Write-Host "  8. Validate sprint-029"
    Write-Host "  9. Nightly sprint-029"
    Write-Host " 10. Status snapshot (local+VPS+dashboard)"
    Write-Host " 11. Runner status"
    Write-Host " 12. Report restart"
    Write-Host " 13. Mobile status"
    Write-Host " 14. Logs runner"
    Write-Host " 15. VPS ValidateServices"
    Write-Host " 16. Dashboard snapshot"
    Write-Host " 17. Report now"
    Write-Host "  0. Exit"
    Write-Host ""

    $choice = Read-Host "Select option"
    switch ($choice) {
        "1" { Show-Next; break }
        "2" { Open-ControlCenter; break }
        "3" { Show-Help; break }
        "4" { Invoke-DevProfile; break }
        "5" { Invoke-OpsProfile; break }
        "6" { Invoke-ProdProfile; break }
        "7" { Invoke-Test; break }
        "8" { Invoke-ValidateSprint -Sprint "029"; break }
        "9" { Invoke-Nightly -Sprint "029"; break }
        "10" { Invoke-StatusSnapshot; break }
        "11" { Invoke-RunnerCommand -Subcommand "status"; break }
        "12" { Invoke-ReportCommand -Subcommand "restart"; break }
        "13" { Invoke-MobileCommand -Subcommand "status"; break }
        "14" { Invoke-LogsCommand -Target "runner"; break }
        "15" { Invoke-VpsAction -Action "ValidateServices"; break }
        "16" { Invoke-DashboardSnapshot; break }
        "17" { Invoke-ReportNow; break }
        "0" { return }
        default { throw "Unknown menu option '$choice'." }
    }
}

switch ($Command.ToLowerInvariant()) {
    "help" { Show-Help; break }
    "h" { Show-Help; break }

    "next" { Show-Next; break }
    "nx" { Show-Next; break }

    "cc" { Open-ControlCenter; break }
    "control-center" { Open-ControlCenter; break }

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

    "otprofile" { Invoke-OtProfileBuilder -Request $Arg1; break }
    "otpreview" { Invoke-OtHelperPreview; break }
    "otmockup" { Invoke-OtHelperMockup; break }
    "otdeploy" { Invoke-OtHelperDeploy -Approval $Arg1; break }
    "otest" { Invoke-OtTestLoop; break }
    "otbg" { Invoke-OtBackgroundStatus; break }
    "otp9" { Invoke-OtConditionsShadowReplay; break }
    "otp9accept" { Invoke-OtConditionsShadowAcceptance -Confirmation $Arg1; break }
    "otp10doctor" { Invoke-OtEquipmentCaptureProfileDoctor -Action $Arg1; break }
    "otp10preview" { Invoke-OtEquipmentObservationPreview; break }
    "otp10catalog" { Invoke-OtEquipmentCandidateCatalog; break }
    "otp10plan" { Invoke-OtEquipmentCaptureProfileChangePlan -EquippedItemId $Arg1 -CandidateItemId $Arg2 -CandidateContainerId $Arg3 -CandidateSlotIndex $Arg4 -Confirmation $Arg5; break }
    "otp10autoplan" { Invoke-OtEquipmentCaptureProfileChangePlan -EquippedItemId $Arg1 -CandidateItemId $Arg2 -Confirmation $Arg3 -RefreshPreview; break }
    "otp10apply" { Invoke-OtEquipmentCaptureProfileApply -PlanSha256 $Arg1 -Confirmation $Arg2; break }
    "otp10preflight" { Invoke-OtEquipmentDependencyPreflight; break }
    "otp10ready" { Invoke-OtEquipmentOperatorReadiness; break }
    "otp10refresh" { Invoke-OtEquipmentOperatorRefresh; break }
    "otp10" { Invoke-OtEquipmentShadowReplay; break }
    "otp10accept" { Invoke-OtEquipmentShadowAcceptance -Confirmation $Arg1; break }
    "otp11catalog" { Invoke-OtHealFriendCandidateCatalog; break }
    "brain" { Invoke-EngineBrain -Subcommand $Arg1 -Profile $Arg2; break }

    default {
        throw "Unknown command '$Command'. Run: .\\ctoa.ps1 help"
    }
}
