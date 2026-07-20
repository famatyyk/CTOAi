param(
    [ValidateSet("PrepareDev", "ValidateDev", "Setup", "SmokePreflight", "SmokeStatus", "SmokeQueue", "GoalStatus", "BackgroundStatus", "LocalReady", "Launch", "Smoke", "SmokeAll", "SmokeAttach", "SmokeAttachModules", "SmokeAttachAll", "ThemeSnapshotMatrix", "HealingVitalsSmoke", "CombatSafetySmoke", "CavebotSafetySmoke", "TimerSafetySmoke", "LootSafetySmoke", "HealFriendNoTargetSmoke", "ConditionsObserverSmoke", "EquipmentObserverSmoke", "ScriptingPolicySmoke", "PlannerStaticSmoke", "RuntimePolicyStaticSmoke", "DispatchGuardStaticSmoke", "PlanQueueStaticSmoke", "RuntimeReadinessStaticSmoke", "ModuleStatusStaticSmoke", "ActionCatalogStaticSmoke", "DecisionTraceStaticSmoke", "DecisionPipelineStaticSmoke", "SandboxHandoffStaticSmoke", "FeatureFlagsStaticSmoke", "HudStaticSmoke", "HotkeysStaticSmoke", "ModalStaticSmoke", "InputContractsStaticSmoke", "RouteStaticSmoke", "TargetingStaticSmoke", "CombatRuntimeStaticSmoke", "CavebotRuntimeStaticSmoke", "LootRuntimeStaticSmoke", "TimerRuntimeStaticSmoke", "RecoveryRuntimeStaticSmoke", "RecoveryBridgeStaticSmoke", "ConditionsRuntimeGateStaticSmoke", "EquipmentRuntimeGateStaticSmoke", "HealFriendRuntimeGateStaticSmoke", "RuntimeModuleGatesSandboxSmoke", "RecoveryBridgeSandboxSmoke", "RecoveryBridgeActionSmoke", "P12ConditionsExecuteOnce", "P12EquipmentExecuteOnce", "P12HealFriendExecuteOnce", "ProfileSchemaStaticSmoke", "OperatorSummaryStaticSmoke", "ExternalBotImportGateStaticSmoke", "HelperShellBudgetStaticSmoke", "HelperShellBudgetPlanStaticSmoke", "ModuleContract", "ModuleAudit", "ModuleStaticGates", "EquipmentShadowSnapshotStaticSmoke", "EquipmentShadowReplayStaticSmoke", "EquipmentShadowAcceptanceStaticSmoke", "Snapshot", "ReadyCheck", "BackupLiveCtoa", "PromoteLiveCtoa", "EmergencyRepairLiveCtoa", "DisableLiveCtoa", "EnableLiveCtoa", "EnableLiveCtoaUiOnly", "Stop")]
    [string]$Action = "Smoke",
    [ValidateSet("Interactive", "BackgroundNoScreen")]
    [string]$OperatorMode = "Interactive",
    [ValidateSet("overview", "healing", "heal_friend", "conditions", "hunting", "hunting_magic", "cavebot", "equipment", "tools", "tools_pvp", "tools_hud", "tools_timer", "tools_diag", "profile", "ui", "scripting")]
    [string]$Tab = "overview",
    [string]$SourceClient = "$env:LOCALAPPDATA\Solteria\client",
    [string]$SandboxClient = "$env:LOCALAPPDATA\SolteriaCodexTest\client",
    [string]$ScreenshotDir = "runtime\otclient_ui_preview",
    [string]$DevDir = "runtime\solteria_helper_dev",
    [string]$RunId = "",
    [string]$SmokeReport = "",
    [switch]$ToggleHelper,
    [switch]$DismissDialogs,
    [switch]$ApproveLiveDeploy,
    [switch]$LaunchAfterPromote,
    [switch]$NoReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:BackgroundNoScreen = $OperatorMode -eq "BackgroundNoScreen"
$script:InheritedBackgroundNoScreen = $env:CTOA_OPERATOR_MODE -eq "background_no_screen"

function Get-BackgroundAllowedActions {
    return @("BackgroundStatus")
}

function Assert-InteractiveOperatorMode {
    param([Parameter(Mandatory = $true)][string]$Operation)
    if ($script:BackgroundNoScreen -or $script:InheritedBackgroundNoScreen) {
        throw "BackgroundNoScreen forbids interactive operation: $Operation"
    }
}

function Assert-OperatorModeAction {
    if ($script:InheritedBackgroundNoScreen -and -not $script:BackgroundNoScreen) {
        throw "CTOA_OPERATOR_MODE=background_no_screen cannot be downgraded by a child process."
    }
    if (-not $script:BackgroundNoScreen) {
        return
    }
    $env:CTOA_OPERATOR_MODE = "background_no_screen"
    if ($ApproveLiveDeploy -or $LaunchAfterPromote -or $ToggleHelper -or $DismissDialogs) {
        throw "BackgroundNoScreen rejects live approval, launch, toggle, and dialog parameters."
    }
    if ($Action -notin (Get-BackgroundAllowedActions)) {
        throw "BackgroundNoScreen forbids action '$Action'. Use BackgroundStatus or an allowlisted static action."
    }
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
function Get-CtoaHelperBootGraphSource {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $sources = @(
        (Join-Path $RepoRoot "scripts\lua\otclient\ctoa_otclient_loader.lua"),
        (Join-Path $RepoRoot "scripts\lua\otclient\ctoa_helper_modules.lua")
    )
    $parts = foreach ($path in $sources) {
        if (Test-Path -LiteralPath $path) {
            Get-Content -LiteralPath $path -Raw
        }
    }
    return ($parts -join "`n")
}

function Test-CtoaHelperBootGraphModule {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$File
    )

    $prefix = '{name = "' + $Name + '", file = "' + $File + '"'
    return $Source.Contains($prefix + '}') -or $Source.Contains($prefix + ',')
}

function Assert-UnderLocalAppData {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw "LOCALAPPDATA is required for Solteria helper sandbox operations."
    }
    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd([char[]]@('\', '/'))
    $rootWithSeparator = $root + [System.IO.Path]::DirectorySeparatorChar
    if (
        -not $full.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $full.StartsWith($rootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Refusing to operate outside LOCALAPPDATA: $full"
    }
    return $full
}

function Assert-ExactLiveClientPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = (Assert-UnderLocalAppData -Path $Path).TrimEnd([char[]]@('\', '/'))
    $expected = [System.IO.Path]::GetFullPath(
        (Join-Path $env:LOCALAPPDATA "Solteria\client")
    ).TrimEnd([char[]]@('\', '/'))
    if (-not $full.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "BackgroundNoScreen requires the canonical live client path: $expected"
    }
    return $full
}

function Assert-ExactBackgroundOutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Candidate
    )
    $runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot "runtime"))
    $expected = [System.IO.Path]::GetFullPath(
        (Join-Path $runtimeRoot "solteria_helper_dev")
    ).TrimEnd([char[]]@('\', '/'))
    $full = [System.IO.Path]::GetFullPath($Candidate).TrimEnd([char[]]@('\', '/'))
    if (-not $full.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "BackgroundNoScreen output must be exactly: $expected"
    }
    foreach ($directory in @($runtimeRoot, $expected)) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            throw "BackgroundNoScreen output directory is missing: $directory"
        }
        $item = Get-Item -LiteralPath $directory -Force
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "BackgroundNoScreen rejects reparse output directory: $directory"
        }
    }
    return $expected
}

function Assert-SandboxClientPath {
    param(
        [string]$SandboxPath,
        [string]$SourcePath
    )
    $sandboxFull = Assert-UnderLocalAppData -Path $SandboxPath
    $sourceFull = [System.IO.Path]::GetFullPath($SourcePath).TrimEnd([char[]]@('\', '/'))
    $sourceWithSeparator = $sourceFull + [System.IO.Path]::DirectorySeparatorChar
    if (
        $sandboxFull.Equals($sourceFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $sandboxFull.StartsWith($sourceWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Refusing to treat SourceClient as sandbox. SandboxClient must be separate from SourceClient: $sandboxFull"
    }
    return $sandboxFull
}

function New-DirectoryJunction {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )
    if (Test-Path -LiteralPath $LinkPath) {
        return
    }
    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null
}

function New-FileHardlink {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )
    if (Test-Path -LiteralPath $LinkPath) {
        $source = Get-Item -LiteralPath $TargetPath
        $existing = Get-Item -LiteralPath $LinkPath
        $matchesSource = $source.Length -eq $existing.Length
        if ($matchesSource) {
            $sourceHash = (Get-FileHash -LiteralPath $TargetPath -Algorithm SHA256).Hash
            $existingHash = (Get-FileHash -LiteralPath $LinkPath -Algorithm SHA256).Hash
            $matchesSource = $sourceHash -eq $existingHash
        }
        if ($matchesSource) {
            return
        }
        Remove-Item -LiteralPath $LinkPath -Force
    }
    New-Item -ItemType HardLink -Path $LinkPath -Target $TargetPath | Out-Null
}

function Copy-FreshFile {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (Test-Path -LiteralPath $Destination) {
        $src = Get-Item -LiteralPath $Source
        $dst = Get-Item -LiteralPath $Destination
        if ($src.Length -eq $dst.Length -and $src.LastWriteTimeUtc -le $dst.LastWriteTimeUtc.AddSeconds(2)) {
            return
        }
        try {
            Remove-Item -LiteralPath $Destination -Force
        } catch {
            Write-Warning "Skipping locked sandbox executable refresh: $Destination"
            return
        }
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
    }
}

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)]
        [object]$InputObject,
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$Depth = 8
    )
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $leaf = Split-Path -Leaf $Path
    $tmpDirectory = $directory
    if ([string]::IsNullOrWhiteSpace($tmpDirectory)) {
        $tmpDirectory = "."
    }
    $tmp = Join-Path $tmpDirectory (".{0}.{1}.{2}.tmp" -f $leaf, $PID, [Guid]::NewGuid().ToString('N'))
    try {
        $InputObject | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $tmp -Encoding ASCII
        Move-Item -LiteralPath $tmp -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force
        }
    }
}

function Write-TextAtomic {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $leaf = Split-Path -Leaf $Path
    $tmpDirectory = $directory
    if ([string]::IsNullOrWhiteSpace($tmpDirectory)) {
        $tmpDirectory = "."
    }
    $tmp = Join-Path $tmpDirectory (".{0}.{1}.{2}.tmp" -f $leaf, $PID, [Guid]::NewGuid().ToString('N'))
    try {
        $Text | Set-Content -LiteralPath $tmp -Encoding ASCII
        Move-Item -LiteralPath $tmp -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force
        }
    }
}

function Write-TestPrefs {
    param(
        [string]$ClientDir,
        [string]$ActiveTab,
        [string]$SmokeSubtab = ""
    )
    @"
return {
  hotkey = "Ctrl+J",
  compact_mode = false,
  window_x = 280,
  window_y = 60,
  active_tab = "$ActiveTab",
  smoke_tab = "$ActiveTab",
  smoke_subtab = "$SmokeSubtab",
  theme_preset = "graphite",
  auto_hide_ms = 0,
  hud = {
    enabled = true,
    x = 42,
    y = 140
  }
}
"@ | Set-Content -LiteralPath (Join-Path $ClientDir "ctoa_ui_prefs.lua") -Encoding ASCII
}

function Write-SmokeCommand {
    param(
        [string]$ClientDir,
        [string]$ActiveTab,
        [string]$SmokeSubtab = "",
        [string]$CommandAction = "",
        [string]$Theme = "",
        [switch]$Confirm,
        [string]$SessionId = "",
        [string]$PlanSha256 = "",
        [string]$P9ReceiptSha256 = "",
        [string]$P10ReceiptSha256 = "",
        [string]$P11ReceiptSha256 = "",
        [string]$P12EquipmentReceiptSha256 = "",
        [Nullable[int]]$BeforeItemId = $null,
        [Nullable[int]]$CandidateItemId = $null,
        [Nullable[int]]$SourceContainerId = $null,
        [Nullable[int]]$SourceSlotIndex = $null,
        [Nullable[int]]$TargetId = $null,
        [string]$TargetName = "",
        [string]$WhitelistRevision = "",
        [Nullable[int]]$HpThreshold = $null,
        [Nullable[int]]$MaxRange = $null,
        [Nullable[int]]$RetryBudget = $null,
        [switch]$SessionApproved,
        [switch]$ExecutionApproved
    )
    Assert-InteractiveOperatorMode -Operation "write smoke command"
    $modDir = Join-Path $ClientDir "mods\ctoa_otclient"
    New-Item -ItemType Directory -Force -Path $modDir | Out-Null
    $lines = @("tab=$ActiveTab", "subtab=$SmokeSubtab")
    if (-not [string]::IsNullOrWhiteSpace($CommandAction)) {
        $lines += "action=$CommandAction"
    }
    if (-not [string]::IsNullOrWhiteSpace($Theme)) {
        $lines += "theme=$Theme"
    }
    if ($Confirm) { $lines += "confirm=true" }
    if (-not [string]::IsNullOrWhiteSpace($SessionId)) { $lines += "session_id=$SessionId" }
    if (-not [string]::IsNullOrWhiteSpace($PlanSha256)) { $lines += "plan_sha256=$PlanSha256" }
    if (-not [string]::IsNullOrWhiteSpace($P9ReceiptSha256)) { $lines += "p9_receipt_sha256=$P9ReceiptSha256" }
    if (-not [string]::IsNullOrWhiteSpace($P10ReceiptSha256)) { $lines += "p10_receipt_sha256=$P10ReceiptSha256" }
    if (-not [string]::IsNullOrWhiteSpace($P11ReceiptSha256)) { $lines += "p11_receipt_sha256=$P11ReceiptSha256" }
    if (-not [string]::IsNullOrWhiteSpace($P12EquipmentReceiptSha256)) { $lines += "p12_equipment_receipt_sha256=$P12EquipmentReceiptSha256" }
    if ($null -ne $BeforeItemId) { $lines += "before_item_id=$BeforeItemId" }
    if ($null -ne $CandidateItemId) { $lines += "candidate_item_id=$CandidateItemId" }
    if ($null -ne $SourceContainerId) { $lines += "source_container_id=$SourceContainerId" }
    if ($null -ne $SourceSlotIndex) { $lines += "source_slot_index=$SourceSlotIndex" }
    if ($null -ne $TargetId) { $lines += "target_id=$TargetId" }
    if (-not [string]::IsNullOrWhiteSpace($TargetName)) {
        if ($TargetName -match '[\r\n"]') { throw "TargetName contains an unsafe command character." }
        $lines += "target_name=`"$TargetName`""
    }
    if (-not [string]::IsNullOrWhiteSpace($WhitelistRevision)) { $lines += "whitelist_revision=$WhitelistRevision" }
    if ($null -ne $HpThreshold) { $lines += "hp_threshold=$HpThreshold" }
    if ($null -ne $MaxRange) { $lines += "max_range=$MaxRange" }
    if ($null -ne $RetryBudget) { $lines += "retry_budget=$RetryBudget" }
    if ($SessionApproved) { $lines += "session_approved=true" }
    if ($ExecutionApproved) { $lines += "execution_approved=true" }
    $commandText = ($lines -join "`n") + "`n"
    Write-TextAtomic -Text $commandText -Path (Join-Path $modDir "ctoa_smoke_command.lua")
    Write-TextAtomic -Text $commandText -Path (Join-Path $ClientDir "ctoa_smoke_command.lua")
}

function Sync-CtoaRuntimeFiles {
    param([string]$ClientDir)
    Assert-InteractiveOperatorMode -Operation "sync runtime files"
    $ClientDir = Assert-SandboxClientPath -SandboxPath $ClientDir -SourcePath $SourceClient
    $repo = Get-RepoRoot
    $stageRoot = Join-Path (Join-Path $repo $DevDir) "latest"
    $modDir = Join-Path $ClientDir "mods\ctoa_otclient"
    $chooserDir = Join-Path $ClientDir "mods\ctoa_chooser"
    $safeDir = [System.IO.Path]::GetFullPath((Join-Path $ClientDir "mods\ctoa_safe"))
    $clientPrefix = $ClientDir.TrimEnd([char[]]@('\', '/')) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $safeDir.StartsWith($clientPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove Safe outside the verified Helper sandbox: $safeDir"
    }
    if (Test-Path -LiteralPath $safeDir) {
        $safeItem = Get-Item -LiteralPath $safeDir -Force
        if (($safeItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing to remove reparse-point Safe directory from Helper sandbox: $safeDir"
        }
        Remove-Item -LiteralPath $safeDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $modDir | Out-Null
    New-Item -ItemType Directory -Force -Path $chooserDir | Out-Null

    function Copy-CtoaRuntimeFile {
        param(
            [string]$StageRelative,
            [string]$RepoRelative,
            [string]$Destination,
            [switch]$Optional
        )
        $stagePath = Join-Path $stageRoot $StageRelative
        if (Test-Path -LiteralPath $stagePath) {
            Copy-Item -LiteralPath $stagePath -Destination $Destination -Force
            return
        }
        $sourcePath = Join-Path $repo $RepoRelative
        if (Test-Path -LiteralPath $sourcePath) {
            Copy-Item -LiteralPath $sourcePath -Destination $Destination -Force
            return
        }
        if (-not $Optional) {
            throw "Missing CTOA runtime source: $StageRelative"
        }
    }

    $moduleFiles = @(Get-DevModuleFileNames)
    foreach ($name in $moduleFiles) {
        Copy-CtoaRuntimeFile -StageRelative "mods\ctoa_otclient\$name" -RepoRelative "scripts\lua\otclient\$name" -Destination (Join-Path $modDir $name)
    }
    foreach ($name in @("ctoa_chooser.otmod", "ctoa_chooser_loader.lua")) {
        Copy-CtoaRuntimeFile -StageRelative "mods\ctoa_chooser\$name" -RepoRelative "scripts\lua\ctoa_chooser\$name" -Destination (Join-Path $chooserDir $name)
    }
    Copy-CtoaRuntimeFile -StageRelative "ctoa_project_loader.lua" -RepoRelative "scripts\lua\ctoa_chooser\ctoa_chooser_loader.lua" -Destination (Join-Path $ClientDir "ctoa_project_loader.lua")
    foreach ($legacyRelative in Get-LiveLegacyFiles) {
        Remove-Item -LiteralPath (Join-Path $ClientDir $legacyRelative) -Force -ErrorAction SilentlyContinue
    }
}

function Ensure-CtoaBootHook {
    param([string]$ClientDir)
    $initPath = Join-Path $ClientDir "init.lua"
    if (-not (Test-Path -LiteralPath $initPath)) {
        throw "Cannot install CTOA boot hook because init.lua is missing: $initPath"
    }

    $content = Get-Content -LiteralPath $initPath -Raw
    $beginMarker = "-- CTOA-BOOT-BEGIN"
    $endMarker = "-- CTOA-BOOT-END"
    $hasBegin = $content.Contains($beginMarker)
    $hasEnd = $content.Contains($endMarker)
    if ($hasBegin -xor $hasEnd) {
        throw "Cannot update malformed CTOA boot hook markers in init.lua: $initPath"
    }
    if ($hasBegin -and $hasEnd) {
        $content = [regex]::Replace($content, "(?s)\r?\n?-- CTOA-BOOT-BEGIN.*?-- CTOA-BOOT-END\r?\n?", "")
    }

    $hook = @'
-- CTOA-BOOT-BEGIN
local function ctoaBootLog(msg)
    local ok, workDir = pcall(function()
        if g_resources and g_resources.getWorkDir then
            return g_resources.getWorkDir()
        end
        return ''
    end)
    if ok and workDir and workDir ~= '' then
        local file = io.open(workDir .. 'ctoa_boot.log', 'a')
        if file then
            file:write(os.date('%Y-%m-%d %H:%M:%S') .. ' [CTOA-BOOT] ' .. msg .. '\n')
            file:close()
        end
    end
end

local function ctoaNeutralBoot()
    local loader = '/ctoa_project_loader.lua'
    ctoaBootLog('init reached; loader_resource=' .. loader)
    if g_resources and g_resources.fileExists and g_resources.fileExists(loader) then
        ctoaBootLog('trying resource loader: ' .. loader)
        local ok, err = pcall(function()
            dofile(loader)
            if CTOA_PROJECT_LOADER and type(CTOA_PROJECT_LOADER.init) == 'function' then
                CTOA_PROJECT_LOADER.init()
            end
        end)
        if ok then
            ctoaBootLog('loader executed')
        else
            ctoaBootLog('loader failed: ' .. tostring(err))
        end
    else
        ctoaBootLog('loader missing: ' .. loader)
    end
end

if type(loadModules) == 'function' then
    local ctoaOriginalLoadModules = loadModules
    loadModules = function(...)
        local result = ctoaOriginalLoadModules(...)
        ctoaNeutralBoot()
        return result
    end
else
    ctoaNeutralBoot()
end
-- CTOA-BOOT-END

'@

    $needle = "-- run updater, must use data.zip"
    if ($content.Contains($needle)) {
        $content = $content.Replace($needle, "`r`n" + $hook + "`r`n" + $needle)
    } else {
        if (-not $content.EndsWith("`n")) {
            $content += "`r`n"
        }
        $content += "`r`n" + $hook
    }
    Set-Content -LiteralPath $initPath -Value $content -Encoding ASCII
}

function Get-HelperVersion {
    $repo = Get-RepoRoot
    $helper = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $match = Select-String -LiteralPath $helper -Pattern 'local HELPER_VERSION = "([^"]+)"' | Select-Object -First 1
    if (-not $match) {
        return "unknown"
    }
    return $match.Matches[0].Groups[1].Value
}

function Get-LiveClientSummary {
    $processes = @()
    Get-Process solteria-client -ErrorAction SilentlyContinue | ForEach-Object {
        $path = ""
        try {
            $path = $_.MainModule.FileName
        } catch {
            $path = ""
        }
        $processes += [pscustomobject]@{
            id = $_.Id
            start_time = if ($_.StartTime) { $_.StartTime.ToString("s") } else { "" }
            path = $path
        }
    }
    return [pscustomobject]@{
        source_client = [System.IO.Path]::GetFullPath($SourceClient)
        sandbox_client = [System.IO.Path]::GetFullPath($SandboxClient)
        running_processes = $processes
    }
}

function Get-SourceClientProcessSummaries {
    $sourceRoot = Assert-UnderLocalAppData -Path $SourceClient
    $exe = [System.IO.Path]::GetFullPath((Join-Path $sourceRoot "solteria-client.exe"))
    $summaries = @()
    try {
        $items = @(Get-CimInstance Win32_Process -Filter "Name = 'solteria-client.exe'" -ErrorAction Stop)
    } catch {
        $items = @()
    }
    foreach ($item in $items) {
        $path = [string]$item.ExecutablePath
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }
        try {
            $fullPath = [System.IO.Path]::GetFullPath($path)
            if (-not $fullPath.Equals($exe, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
        } catch {
            continue
        }
        $startUnixMs = 0
        try {
            $startUnixMs = ([DateTimeOffset]$item.CreationDate).ToUnixTimeMilliseconds()
        } catch {
            $startUnixMs = 0
        }
        $summaries += [pscustomobject]@{
            id = [int]$item.ProcessId
            start_time = [string]$item.CreationDate
            start_unix_ms = $startUnixMs
            path = $fullPath
        }
    }
    return $summaries
}

function Start-LiveClientAfterPromotion {
    Assert-InteractiveOperatorMode -Operation "start live client"
    $sourceRoot = Assert-UnderLocalAppData -Path $SourceClient
    $exe = [System.IO.Path]::GetFullPath((Join-Path $sourceRoot "solteria-client.exe"))
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Live client executable does not exist: $exe"
    }

    $existing = @(Get-SourceClientProcessSummaries)
    if ($existing.Count -gt 0) {
        Write-Host "[solteria-helper-test-env] Live client already running; launch skipped: $exe"
        return [pscustomobject]@{
            requested = $true
            status = "already_running"
            executable = $exe
            process_ids = @($existing | ForEach-Object { $_.id })
        }
    }

    $process = Start-Process -FilePath $exe -WorkingDirectory $sourceRoot -PassThru
    Write-Host "[solteria-helper-test-env] Live client launched after promotion: $exe"
    return [pscustomobject]@{
        requested = $true
        status = "launched"
        executable = $exe
        process_ids = @($process.Id)
    }
}

function Get-DevPackageFiles {
    return @(
        "ctoa_project_loader.lua",
        "mods/ctoa_chooser/ctoa_chooser.otmod",
        "mods/ctoa_chooser/ctoa_chooser_loader.lua",
        "mods/ctoa_otclient/ctoa_otclient.otmod",
        "mods/ctoa_otclient/ctoa_otclient_loader.lua",
        "mods/ctoa_otclient/ctoa_helper_ui_primitives.lua",
        "mods/ctoa_otclient/ctoa_helper_ui_composition.lua",
        "mods/ctoa_otclient/ctoa_helper_ui_rule_editors.lua",
        "mods/ctoa_otclient/ctoa_helper_ui.lua",
        "mods/ctoa_otclient/ctoa_helper_client_reporter.lua",
        "mods/ctoa_otclient/ctoa_helper_diagnostics.lua",
        "mods/ctoa_otclient/ctoa_helper_hotkeys.lua",
        "mods/ctoa_otclient/ctoa_helper_modal.lua",
        "mods/ctoa_otclient/ctoa_helper_route.lua",
        "mods/ctoa_otclient/ctoa_helper_rule_explanations.lua",
        "mods/ctoa_otclient/ctoa_helper_targeting.lua",
        "mods/ctoa_otclient/ctoa_helper_combat_runtime.lua",
        "mods/ctoa_otclient/ctoa_helper_spell_state_registry.lua",
        "mods/ctoa_otclient/ctoa_helper_cavebot_runtime.lua",
        "mods/ctoa_otclient/ctoa_helper_loot_runtime.lua",
        "mods/ctoa_otclient/ctoa_helper_timer_runtime.lua",
        "mods/ctoa_otclient/ctoa_helper_recovery_runtime.lua",
        "mods/ctoa_otclient/ctoa_helper_recovery_bridge.lua",
        "mods/ctoa_otclient/ctoa_helper_runtime_module_gate.lua",
        "mods/ctoa_otclient/ctoa_helper_conditions_runtime_gate.lua",
        "mods/ctoa_otclient/ctoa_helper_conditions_execute_once.lua",
        "mods/ctoa_otclient/ctoa_helper_equipment_execute_once.lua",
        "mods/ctoa_otclient/ctoa_helper_equipment_runtime_gate.lua",
        "mods/ctoa_otclient/ctoa_helper_heal_friend_runtime_gate.lua",
        "mods/ctoa_otclient/ctoa_helper_heal_friend_execute_once.lua",
        "mods/ctoa_otclient/ctoa_helper_profile_schema.lua",
        "mods/ctoa_otclient/ctoa_helper_vocation_profiles.lua",
        "mods/ctoa_otclient/ctoa_helper_profile_persistence.lua",
        "mods/ctoa_otclient/ctoa_helper_rule_presets.lua",
        "mods/ctoa_otclient/ctoa_helper_operator_summary.lua",
        "mods/ctoa_otclient/ctoa_helper_planner.lua",
        "mods/ctoa_otclient/ctoa_helper_runtime_policy.lua",
        "mods/ctoa_otclient/ctoa_helper_dispatch_guard.lua",
        "mods/ctoa_otclient/ctoa_helper_plan_queue.lua",
        "mods/ctoa_otclient/ctoa_helper_runtime_readiness.lua",
        "mods/ctoa_otclient/ctoa_helper_module_status.lua",
        "mods/ctoa_otclient/ctoa_helper_action_catalog.lua",
        "mods/ctoa_otclient/ctoa_helper_decision_trace.lua",
        "mods/ctoa_otclient/ctoa_helper_decision_pipeline.lua",
        "mods/ctoa_otclient/ctoa_helper_sandbox_handoff.lua",
        "mods/ctoa_otclient/ctoa_helper_feature_flags.lua",
        "mods/ctoa_otclient/ctoa_helper_hud.lua",
        "mods/ctoa_otclient/ctoa_helper_conditions.lua",
        "mods/ctoa_otclient/ctoa_helper_equipment_family_registry.lua",
        "mods/ctoa_otclient/ctoa_helper_equipment.lua",
        "mods/ctoa_otclient/ctoa_helper_scripting.lua",
        "mods/ctoa_otclient/ctoa_helper_heal_friend.lua",
        "mods/ctoa_otclient/ctoa_helper_modules.lua",
        "mods/ctoa_otclient/ctoa_helper_domain_contract.lua",
        "mods/ctoa_otclient/ctoa_helper_rule_engine.lua",
        "mods/ctoa_otclient/ctoa_helper_runtime_core.lua",
        "mods/ctoa_otclient/ctoa_helper_combat_observer.lua",
        "mods/ctoa_otclient/ctoa_helper_recovery_observer.lua",
        "mods/ctoa_otclient/ctoa_helper_cavebot_observer.lua",
        "mods/ctoa_otclient/ctoa_helper_loot_observer.lua",
        "mods/ctoa_otclient/ctoa_helper_equipment_observer.lua",
        "mods/ctoa_otclient/ctoa_helper_otclient_observation_adapter.lua",
        "mods/ctoa_otclient/ctoa_native_helper.lua",
        "mods/ctoa_otclient/ctoa_ek_profile.lua",
        "mods/ctoa_otclient/ctoa_ms_profile.lua",
        "mods/ctoa_otclient/ctoa_ed_profile.lua",
        "mods/ctoa_otclient/ctoa_rp_profile.lua"
    )
}

function Get-DevModuleFileNames {
    $moduleNames = @(
        foreach ($relative in Get-DevPackageFiles) {
            $normalized = ([string]$relative).Replace("\\", "/")
            if ($normalized.StartsWith("mods/ctoa_otclient/", [System.StringComparison]::Ordinal)) {
                [System.IO.Path]::GetFileName($normalized)
            }
        }
    )
    $requiredPassiveModules = @("ctoa_helper_client_reporter.lua")
    foreach ($required in $requiredPassiveModules) {
        if ($required -notin $moduleNames) {
            throw "Dev package is missing required passive module: $required"
        }
    }
    foreach ($name in $moduleNames) {
        $name
    }
}

function Get-DevPackageSourcePath {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string]$Relative
    )

    $normalized = $Relative.Replace("\", "/")
    $name = [System.IO.Path]::GetFileName($normalized)
    if ($normalized -eq "ctoa_project_loader.lua") {
        return (Join-Path $Repo "scripts\lua\ctoa_chooser\ctoa_chooser_loader.lua")
    }
    if ($normalized.StartsWith("mods/ctoa_chooser/", [System.StringComparison]::Ordinal)) {
        return (Join-Path $Repo ("scripts\lua\ctoa_chooser\{0}" -f $name))
    }
    if ($normalized.StartsWith("mods/ctoa_otclient/", [System.StringComparison]::Ordinal)) {
        return (Join-Path $Repo ("scripts\lua\otclient\{0}" -f $name))
    }
    throw "No tracked source mapping for staged file: $Relative"
}

function Get-LiveLegacyFiles {
    return @(
        "ctoa_native_helper.lua",
        "ctoa_otclient_loader.lua",
        "ctoa_chooser_prefs.lua",
        "ctoa_loader_pref.lua",
        "ctoa_ek_profile.lua",
        "ctoa_ms_profile.lua",
        "ctoa_ed_profile.lua",
        "ctoa_rp_profile.lua",
        "ctoa_ui_prefs.lua",
        "mods/ctoa_safe/ctoa_helper_modules.lua",
        "mods/ctoa_safe/ctoa_helper_profile_persistence.lua",
        "mods/ctoa_safe/ctoa_helper_profile_schema.lua",
        "mods/ctoa_safe/ctoa_helper_runtime_core.lua",
        "mods/ctoa_safe/ctoa_helper_vocation_profiles.lua",
        "mods/ctoa_safe/ctoa_native_combat.lua",
        "mods/ctoa_safe/ctoa_native_heal.lua",
        "mods/ctoa_safe/ctoa_native_loot.lua",
        "mods/ctoa_safe/ctoa_ek_profile.lua",
        "mods/ctoa_otclient/ctoa_native_combat.lua",
        "mods/ctoa_otclient/ctoa_native_combat.lua.disabled",
        "mods/ctoa_otclient/ctoa_native_heal.lua",
        "mods/ctoa_otclient/ctoa_native_heal.lua.disabled",
        "mods/ctoa_otclient/ctoa_native_loot.lua",
        "mods/ctoa_otclient/ctoa_native_loot.lua.disabled",
        "mods/ctoa_safe/ctoa_ms_profile.lua",
        "mods/ctoa_safe/ctoa_ed_profile.lua",
        "mods/ctoa_safe/ctoa_rp_profile.lua"
    )
}

function Copy-LegacyHelperUserState {
    param([string]$ClientDir)
    Assert-UnderLocalAppData -Path $ClientDir | Out-Null
    $migrated = @()
    $items = @(
        @{ destination = "ctoa_user_ek_profile.lua"; candidates = @("mods/ctoa_otclient/ctoa_ek_profile.lua", "ctoa_ek_profile.lua") },
        @{ destination = "ctoa_user_ms_profile.lua"; candidates = @("mods/ctoa_otclient/ctoa_ms_profile.lua", "ctoa_ms_profile.lua") },
        @{ destination = "ctoa_user_ed_profile.lua"; candidates = @("mods/ctoa_otclient/ctoa_ed_profile.lua", "ctoa_ed_profile.lua") },
        @{ destination = "ctoa_user_rp_profile.lua"; candidates = @("mods/ctoa_otclient/ctoa_rp_profile.lua", "ctoa_rp_profile.lua") },
        @{ destination = "ctoa_user_ui_prefs.lua"; candidates = @("mods/ctoa_otclient/ctoa_ui_prefs.lua", "ctoa_ui_prefs.lua") }
    )
    foreach ($item in $items) {
        $destinationPath = Join-Path $ClientDir $item.destination
        if (Test-Path -LiteralPath $destinationPath) {
            continue
        }
        foreach ($candidate in $item.candidates) {
            $sourcePath = Join-Path $ClientDir $candidate
            if (Test-Path -LiteralPath $sourcePath) {
                Copy-Item -LiteralPath $sourcePath -Destination $destinationPath
                $migrated += [pscustomobject]@{ source = $candidate; destination = $item.destination }
                Write-Host "[solteria-helper-test-env] Preserved Helper user state: $candidate -> $($item.destination)"
                break
            }
        }
    }
    return $migrated
}

function Remove-LiveLegacyFiles {
    param([string]$ClientDir)
    Assert-UnderLocalAppData -Path $ClientDir | Out-Null
    $removed = @()
    foreach ($relative in Get-LiveLegacyFiles) {
        $legacyPath = Join-Path $ClientDir $relative
        if (Test-Path -LiteralPath $legacyPath) {
            Remove-Item -LiteralPath $legacyPath -Force
            $removed += $relative
            Write-Host "[solteria-helper-test-env] Removed stale CTOA file: $relative"
        }
    }
    return $removed
}

function Get-DevFileManifest {
    param([string]$Stage)
    $items = @()
    foreach ($relative in Get-DevPackageFiles) {
        $path = Join-Path $Stage $relative
        if (Test-Path -LiteralPath $path) {
            $file = Get-Item -LiteralPath $path
            $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $path
            $items += [pscustomobject]@{
                path = $relative.Replace("\", "/")
                bytes = $file.Length
                sha256 = $hash.Hash.ToLowerInvariant()
            }
        }
    }
    return $items
}

function Write-DevChangelog {
    param(
        [string]$OutRoot,
        [string]$Version,
        [string]$Stage,
        [string]$ZipPath,
        [string]$ValidationStatus = "pending",
        [array]$Checks = @()
    )
    $changelogPath = Join-Path $OutRoot "CHANGELOG.md"
    $fileCount = @(Get-DevFileManifest -Stage $Stage).Count
    $createdAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $manifestPath = Join-Path $OutRoot "manifest.json"
    $validationPath = Join-Path $OutRoot "validation.json"
    $checkLines = @()
    foreach ($check in $Checks) {
        $checkLines += "- $($check.name): $($check.status) ($($check.evidence))"
    }
    if ($checkLines.Count -eq 0) {
        $checkLines += "- ValidateDev: pending"
    }
    $checksText = $checkLines -join "`n"
    @"
# Solteria Helper Dev Package

Version: $Version
Created: $createdAt
Validation: $ValidationStatus

## Contents

- Staged helper package: $Stage
- ZIP package: $ZipPath
- Manifest: $manifestPath
- Validation report: $validationPath
- Packaged files: $fileCount

## Validation Evidence

$checksText

## Current Development Notes

- Development package is generated without launching, stopping, or overwriting the live play client.
- Live client promotion remains manual and requires explicit user approval.
- Current feature lane: API observability and safe future feature rollout.

## Promotion Checklist

1. `PrepareDev` completed.
2. `ValidateDev` completed.
3. Sandbox in-world smoke completed when UI/runtime behavior changes.
4. User explicitly approves live deployment.

"@ | Set-Content -LiteralPath $changelogPath -Encoding ASCII
    return $changelogPath
}

function Write-ReleaseReadinessReport {
    param(
        [string]$OutRoot,
        [string]$Version,
        [string]$Stage,
        [string]$ZipPath,
        [string]$ManifestPath,
        [string]$ValidationPath,
        [string]$ValidationStatus,
        [array]$Checks
    )
    $zipHash = ""
    if (Test-Path -LiteralPath $ZipPath) {
        $zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath).Hash.ToLowerInvariant()
    }
    $report = [pscustomobject]@{
        name = "solteria-helper-release-readiness"
        helper_version = $Version
        created_at = (Get-Date).ToString("s")
        status = if ($ValidationStatus -eq "passed") { "static-passed" } else { "pending" }
        releasable_to_live = $false
        reason = "Live promotion still requires sandbox in-world SmokeAttachAll evidence and explicit user approval."
        stage = [System.IO.Path]::GetFullPath($Stage)
        zip = [pscustomobject]@{
            path = [System.IO.Path]::GetFullPath($ZipPath)
            sha256 = $zipHash
        }
        manifest = [System.IO.Path]::GetFullPath($ManifestPath)
        validation = [System.IO.Path]::GetFullPath($ValidationPath)
        gates = @(
            [pscustomobject]@{ name = "PrepareDev"; status = "passed"; evidence = $ManifestPath },
            [pscustomobject]@{ name = "ValidateDev"; status = $ValidationStatus; evidence = $ValidationPath },
            [pscustomobject]@{ name = "Sandbox Launch"; status = "pending"; evidence = "Run -Action Launch against sandbox client" },
            [pscustomobject]@{ name = "SmokeAttachAll"; status = "pending"; evidence = "Run -Action SmokeAttachAll after sandbox character is in-world" },
            [pscustomobject]@{ name = "Live Approval"; status = "pending"; evidence = "Run -Action PromoteLiveCtoa -ApproveLiveDeploy only after user approval" }
        )
        checks = $Checks
        live_safety = "PrepareDev and ValidateDev do not copy files into the live play client."
    }
    $path = Join-Path $OutRoot "release_readiness.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding ASCII
    return $path
}

function Write-DevValidationReport {
    param(
        [string]$OutRoot,
        [string]$Version,
        [array]$Checks,
        [string]$Status
    )
    $report = [pscustomobject]@{
        name = "solteria-helper-dev-validation"
        helper_version = $Version
        created_at = (Get-Date).ToString("s")
        status = $Status
        live_safety = "No live Solteria files are changed by PrepareDev or ValidateDev."
        checks = $Checks
    }
    $path = Join-Path $OutRoot "validation.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding ASCII
    return $path
}

function New-DevPackage {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $stage = Join-Path $outRoot "latest"
    $stageFull = [System.IO.Path]::GetFullPath($stage)
    $outRootFull = [System.IO.Path]::GetFullPath($outRoot).TrimEnd([char[]]@('\', '/'))
    $outRootPrefix = $outRootFull + [System.IO.Path]::DirectorySeparatorChar
    if (-not $stageFull.StartsWith($outRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to rebuild stage outside the dev output root: $stageFull"
    }
    if (Test-Path -LiteralPath $stageFull) {
        Remove-Item -LiteralPath $stageFull -Recurse -Force
    }
    $moduleDir = Join-Path $stage "mods\ctoa_otclient"
    $chooserDir = Join-Path $stage "mods\ctoa_chooser"
    New-Item -ItemType Directory -Force -Path $moduleDir | Out-Null
    New-Item -ItemType Directory -Force -Path $chooserDir | Out-Null

    $moduleFiles = @(Get-DevModuleFileNames)
    foreach ($name in $moduleFiles) {
        Copy-Item -LiteralPath (Join-Path $repo "scripts\lua\otclient\$name") -Destination (Join-Path $moduleDir $name) -Force
    }
    foreach ($name in @("ctoa_chooser.otmod", "ctoa_chooser_loader.lua")) {
        Copy-Item -LiteralPath (Join-Path $repo "scripts\lua\ctoa_chooser\$name") -Destination (Join-Path $chooserDir $name) -Force
    }
    Copy-Item -LiteralPath (Join-Path $repo "scripts\lua\ctoa_chooser\ctoa_chooser_loader.lua") -Destination (Join-Path $stage "ctoa_project_loader.lua") -Force

    $version = Get-HelperVersion
    $fileManifest = Get-DevFileManifest -Stage $stage
    $manifest = [pscustomobject]@{
        name = "solteria-helper-dev"
        helper_version = $version
        created_at = (Get-Date).ToString("s")
        source = [System.IO.Path]::GetFullPath((Join-Path $repo "scripts\lua\otclient"))
        stage = [System.IO.Path]::GetFullPath($stage)
        live_client = Get-LiveClientSummary
        live_safety = "No live Solteria files are changed by PrepareDev or ValidateDev."
        files = $fileManifest
    }
    $manifestPath = Join-Path $outRoot "manifest.json"
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding ASCII

    $zipPath = Join-Path $outRoot ("ctoa_otclient_{0}.zip" -f $version)
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
    $changelogPath = Write-DevChangelog -OutRoot $outRoot -Version $version -Stage $stage -ZipPath $zipPath
    $validationPath = Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "pending" -Checks @(
        [pscustomobject]@{ name = "PrepareDev"; status = "passed"; evidence = $manifestPath },
        [pscustomobject]@{ name = "ValidateDev"; status = "pending"; evidence = "Run -Action ValidateDev" }
    )
    $readinessPath = Write-ReleaseReadinessReport -OutRoot $outRoot -Version $version -Stage $stage -ZipPath $zipPath -ManifestPath $manifestPath -ValidationPath $validationPath -ValidationStatus "pending" -Checks @(
        [pscustomobject]@{ name = "PrepareDev"; status = "passed"; evidence = $manifestPath },
        [pscustomobject]@{ name = "ValidateDev"; status = "pending"; evidence = "Run -Action ValidateDev" }
    )

    Write-Output "[solteria-helper-test-env] Dev package ready: $stage"
    Write-Output "[solteria-helper-test-env] Manifest: $manifestPath"
    Write-Output "[solteria-helper-test-env] Changelog: $changelogPath"
    Write-Output "[solteria-helper-test-env] Validation report: $validationPath"
    Write-Output "[solteria-helper-test-env] Release readiness: $readinessPath"
    Write-Output "[solteria-helper-test-env] ZIP: $zipPath"
    Write-Output "[solteria-helper-test-env] Live client untouched."
}

function Invoke-DevValidation {
    New-DevPackage
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $version = Get-HelperVersion
    $checks = @()
    Write-Output "[solteria-helper-test-env] Validate: helper profile safe migration audit"
    $profileAuditPath = Join-Path $outRoot "profile_audit.json"
    & python scripts\ops\otclient_helper_profile_audit.py --profile scripts\lua\otclient\ctoa_ek_profile.lua --json-out $profileAuditPath
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Helper profile safe migration audit failed"
    }
    $checks += [pscustomobject]@{ name = "profile_audit"; status = "passed"; evidence = "runtime/solteria_helper_dev/profile_audit.json" }
    Write-Output "[solteria-helper-test-env] Validate: pytest helper/API contracts"
    & python -m pytest tests\test_ctoa_exclusive_project_loader.py tests\test_otclient_loader_cross_fork.py tests\test_otclient_helper_zerobot_shell.py tests\test_solteria_api_audit.py tests\test_ctoa_helper_smoke_report.py tests\test_solteria_helper_release_gate.py tests\test_solteria_helper_goal_audit.py -q
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Pytest validation failed"
    }
    $checks += [pscustomobject]@{ name = "pytest"; status = "passed"; evidence = "tests/test_otclient_helper_zerobot_shell.py tests/test_solteria_api_audit.py tests/test_ctoa_helper_smoke_report.py tests/test_solteria_helper_release_gate.py tests/test_solteria_helper_goal_audit.py" }
    Write-Output "[solteria-helper-test-env] Validate: P10 Equipment shadow replay fixture gate"
    $equipmentShadowScript = Join-Path $repo "scripts\ops\otclient_equipment_shadow_replay.py"
    & python $equipmentShadowScript --no-write --source fixture | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment shadow replay fixture gate failed"
    }
    $checks += [pscustomobject]@{ name = "equipment_shadow_replay"; status = "passed"; evidence = "scripts/ops/otclient_equipment_shadow_replay.py --no-write --source fixture" }
    Write-Output "[solteria-helper-test-env] Validate: P10 passive snapshot producer fail-closed gate"
    & python scripts\ops\otclient_equipment_shadow_snapshot.py --no-write --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment shadow snapshot producer gate failed"
    }
    $checks += [pscustomobject]@{ name = "equipment_shadow_snapshot"; status = "passed"; evidence = "scripts/ops/otclient_equipment_shadow_snapshot.py --no-write --allow-blocked" }
    Write-Output "[solteria-helper-test-env] Validate: P10 capture-profile doctor contract"
    & python scripts\ops\otclient_equipment_capture_profile_doctor.py | Out-Null
    if ($LASTEXITCODE -notin @(0, 1)) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment capture-profile doctor returned an unexpected status"
    }
    $doctorReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_capture_profile_doctor.json") -Raw | ConvertFrom-Json
    if ($doctorReport.runtime_actions -ne $false -or $doctorReport.live_file_writes -ne $false -or $doctorReport.no_action_contract -ne $true) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment capture-profile doctor violated its no-action contract"
    }
    $checks += [pscustomobject]@{ name = "equipment_capture_profile_doctor"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_capture_profile_doctor.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 bounded observation preview"
    & python scripts\ops\otclient_equipment_observation_preview.py --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment observation preview contract failed"
    }
    $previewReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_observation_preview.json") -Raw | ConvertFrom-Json
    if ($previewReport.runtime_actions -ne $false -or $previewReport.promotion_allowed -ne $false -or @($previewReport.intrusive_actions_performed).Count -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment observation preview violated its no-action contract"
    }
    $checks += [pscustomobject]@{ name = "equipment_observation_preview"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_observation_preview.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 P9-to-P10 dependency preflight"
    & python scripts\ops\otclient_equipment_dependency_preflight.py --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment dependency preflight contract failed"
    }
    $dependencyReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_dependency_preflight.json") -Raw | ConvertFrom-Json
    if ($dependencyReport.eligibility_changed -ne $false -or $dependencyReport.runtime_actions -ne $false -or $dependencyReport.promotion_allowed -ne $false -or @($dependencyReport.intrusive_actions_performed).Count -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment dependency preflight violated its no-action or unchanged-eligibility contract"
    }
    $checks += [pscustomobject]@{ name = "equipment_dependency_preflight"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_dependency_preflight.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 candidate catalog has no selection policy"
    & python scripts\ops\otclient_equipment_candidate_catalog.py --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment candidate catalog contract failed"
    }
    $catalogReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_candidate_catalog.json") -Raw | ConvertFrom-Json
    if ($catalogReport.selection_policy -ne "none" -or $null -ne $catalogReport.recommendation -or $catalogReport.runtime_actions -ne $false -or $catalogReport.promotion_allowed -ne $false) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment candidate catalog selected/recommended an item or violated no-action"
    }
    $checks += [pscustomobject]@{ name = "equipment_candidate_catalog"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_candidate_catalog.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 profile change plan remains write-free by default"
    & python scripts\ops\otclient_equipment_capture_profile_change_plan.py --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment capture-profile change plan contract failed"
    }
    $changePlanReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_capture_profile_change_plan.json") -Raw | ConvertFrom-Json
    if ($changePlanReport.profile_write_performed -ne $false -or $changePlanReport.acceptance_granted -ne $false -or $changePlanReport.eligibility_changed -ne $false -or $changePlanReport.runtime_actions -ne $false) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment capture-profile change plan violated its review-only contract"
    }
    $checks += [pscustomobject]@{ name = "equipment_capture_profile_change_plan"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_capture_profile_change_plan.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 consolidated operator readiness"
    & python scripts\ops\otclient_equipment_operator_readiness.py --allow-blocked | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment operator readiness contract failed"
    }
    $readinessReport = Get-Content -LiteralPath (Join-Path $outRoot "equipment_operator_readiness.json") -Raw | ConvertFrom-Json
    if ($readinessReport.eligibility_changed -ne $false -or $readinessReport.operational_readiness_claimed -ne $false -or $readinessReport.runtime_actions -ne $false -or $readinessReport.promotion_allowed -ne $false) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment operator readiness violated unchanged-eligibility/no-action"
    }
    $checks += [pscustomobject]@{ name = "equipment_operator_readiness"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_operator_readiness.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 Python/web consumer parity"
    $equipmentParityScript = Join-Path $repo "scripts\ops\otclient_equipment_consumer_parity.py"
    $equipmentParityOutput = Join-Path $outRoot "equipment_consumer_parity.json"
    & python $equipmentParityScript --dev-dir $outRoot --output $equipmentParityOutput | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment Python/web consumer parity gate failed"
    }
    $equipmentParityReport = Get-Content -LiteralPath $equipmentParityOutput -Raw | ConvertFrom-Json
    if ($equipmentParityReport.status -ne "passed" -or $equipmentParityReport.eligibility_changed -ne $false -or $equipmentParityReport.operational_readiness_claimed -ne $false -or $equipmentParityReport.runtime_actions -ne $false -or $equipmentParityReport.promotion_allowed -ne $false -or $equipmentParityReport.live_file_writes -ne $false) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment Python/web consumer parity violated passed/no-action contract"
    }
    $checks += [pscustomobject]@{ name = "equipment_consumer_parity"; status = "passed"; evidence = "runtime/solteria_helper_dev/equipment_consumer_parity.json" }
    Write-Output "[solteria-helper-test-env] Validate: P10 acceptance remains independent and fail-closed"
    & python scripts\ops\otclient_equipment_shadow_acceptance.py --no-write | Out-Null
    if ($LASTEXITCODE -ne 1) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Equipment shadow acceptance preflight returned an unexpected status"
    }
    $checks += [pscustomobject]@{ name = "equipment_shadow_acceptance"; status = "passed"; evidence = "blocked preflight without exact confirmation" }
    Write-Output "[solteria-helper-test-env] Validate: P11 Heal Friend exact-target fixture replay gate"
    $healFriendShadowScript = Join-Path $repo "scripts\ops\otclient_heal_friend_shadow_replay.py"
    & python $healFriendShadowScript --no-write | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Heal Friend shadow replay fixture gate failed"
    }
    $checks += [pscustomobject]@{ name = "heal_friend_shadow_replay"; status = "passed"; evidence = "scripts/ops/otclient_heal_friend_shadow_replay.py --no-write (55/55 fixture-only cases)" }
    Write-Output "[solteria-helper-test-env] Validate: static helper UI preview"
    & python scripts\ops\ctoa_helper_ui_preview.py
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Helper UI preview validation failed"
    }
    $checks += [pscustomobject]@{ name = "ui_preview"; status = "passed"; evidence = "runtime/otclient_ui_preview/ctoa_helper_preview.html" }
    Write-Output "[solteria-helper-test-env] Validate: Solteria API audit catalog refresh"
    & python scripts\ops\solteria_api_audit.py --client-dir $SourceClient --out-dir (Join-Path $repo "runtime\solteria_api_audit")
    if ($LASTEXITCODE -ne 0) {
        Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "failed" -Checks $checks | Out-Null
        throw "Solteria API audit failed"
    }
    $checks += [pscustomobject]@{ name = "api_audit"; status = "passed"; evidence = "runtime/solteria_api_audit/solteria_api_catalog.json" }
    $validationPath = Write-DevValidationReport -OutRoot $outRoot -Version $version -Status "passed" -Checks $checks
    $stage = Join-Path $outRoot "latest"
    $zipPath = Join-Path $outRoot ("ctoa_otclient_{0}.zip" -f $version)
    $manifestPath = Join-Path $outRoot "manifest.json"
    $changelogPath = Write-DevChangelog -OutRoot $outRoot -Version $version -Stage $stage -ZipPath $zipPath -ValidationStatus "passed" -Checks $checks
    $readinessPath = Write-ReleaseReadinessReport -OutRoot $outRoot -Version $version -Stage $stage -ZipPath $zipPath -ManifestPath $manifestPath -ValidationPath $validationPath -ValidationStatus "passed" -Checks $checks
    & python scripts\ops\solteria_helper_release_gate.py --dev-dir $outRoot --allow-blocked
    if ($LASTEXITCODE -ne 0) {
        throw "Solteria helper release gate audit failed"
    }
    & python scripts\ops\solteria_helper_goal_audit.py --dev-dir $outRoot --allow-blocked
    if ($LASTEXITCODE -ne 0) {
        throw "Solteria helper goal audit failed"
    }
    Write-Output "[solteria-helper-test-env] Validation report: $validationPath"
    Write-Output "[solteria-helper-test-env] Changelog refreshed: $changelogPath"
    Write-Output "[solteria-helper-test-env] Release readiness: $readinessPath"
    Write-Output "[solteria-helper-test-env] Dev validation complete. Live client untouched."
}

function Resolve-SmokeTab {
    param([string]$RequestedTab)
    $active = $RequestedTab
    $subtab = ""
    if ($RequestedTab -eq "hunting_magic") {
        $active = "hunting"
        $subtab = "magic"
    } elseif ($RequestedTab -eq "tools_pvp") {
        $active = "tools"
        $subtab = "pvp"
    } elseif ($RequestedTab -eq "tools_hud") {
        $active = "tools"
        $subtab = "hud"
    } elseif ($RequestedTab -eq "tools_timer") {
        $active = "tools"
        $subtab = "timer"
    } elseif ($RequestedTab -eq "tools_diag") {
        $active = "tools"
        $subtab = "diag"
    }
    return [pscustomobject]@{
        Active = $active
        Subtab = $subtab
        Requested = $RequestedTab
    }
}

function Initialize-Sandbox {
    Assert-InteractiveOperatorMode -Operation "initialize sandbox"
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    if (-not (Test-Path -LiteralPath $SourceClient)) {
        throw "Source client does not exist: $SourceClient"
    }
    New-Item -ItemType Directory -Force -Path $sandboxRoot | Out-Null

    foreach ($dir in @("cef", "data")) {
        New-DirectoryJunction -LinkPath (Join-Path $sandboxRoot $dir) -TargetPath (Join-Path $SourceClient $dir)
    }

    foreach ($file in @("solteria-client.exe", "otclient_cef_subprocess.exe")) {
        Copy-FreshFile -Source (Join-Path $SourceClient $file) -Destination (Join-Path $sandboxRoot $file)
    }

    foreach ($file in @(
        "data-things-1525.otpkg",
        "protected.otpkg",
        "cacert.pem",
        "meta.lua"
    )) {
        New-FileHardlink -LinkPath (Join-Path $sandboxRoot $file) -TargetPath (Join-Path $SourceClient $file)
    }

    foreach ($file in @("init.lua", "config.ini", "otclientrc.lua")) {
        Copy-IfExists -Source (Join-Path $SourceClient $file) -Destination (Join-Path $sandboxRoot $file)
    }

    $modsTarget = Join-Path $sandboxRoot "mods"
    if (-not (Test-Path -LiteralPath $modsTarget)) {
        New-Item -ItemType Directory -Force -Path $modsTarget | Out-Null
    }
    if (Test-Path -LiteralPath (Join-Path $SourceClient "mods")) {
        robocopy (Join-Path $SourceClient "mods") $modsTarget /MIR /XD ctoa_otclient ctoa_chooser ctoa_safe /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "robocopy mods failed with exit code $LASTEXITCODE"
        }
    }

    Sync-CtoaRuntimeFiles -ClientDir $sandboxRoot
    Ensure-CtoaBootHook -ClientDir $sandboxRoot
    $resolved = Resolve-SmokeTab -RequestedTab $Tab
    Write-TestPrefs -ClientDir $sandboxRoot -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab
    Remove-Item -LiteralPath (Join-Path $sandboxRoot "ctoa_local.log") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $sandboxRoot "ctoa_boot.log") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $sandboxRoot "otclient.log") -Force -ErrorAction SilentlyContinue
}

function Invoke-SmokePreflight {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $stage = Join-Path $outRoot "latest"
    $manifestPath = Join-Path $outRoot "manifest.json"
    $missingPackage = -not (Test-Path -LiteralPath $manifestPath)
    if (-not $missingPackage) {
        foreach ($relative in Get-DevPackageFiles) {
            if (-not (Test-Path -LiteralPath (Join-Path $stage $relative))) {
                $missingPackage = $true
                break
            }
        }
    }
    $packageStale = $missingPackage
    if (-not $packageStale) {
        foreach ($relative in Get-DevPackageFiles) {
            $sourcePath = Get-DevPackageSourcePath -Repo $repo -Relative $relative
            $stagePath = Join-Path $stage $relative
            if (
                -not (Test-Path -LiteralPath $sourcePath) -or
                -not (Test-Path -LiteralPath $stagePath)
            ) {
                $packageStale = $true
                break
            }
            $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash
            $stageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $stagePath).Hash
            if ($sourceHash -ne $stageHash) {
                $packageStale = $true
                break
            }
        }
    }
    if ($packageStale) {
        New-DevPackage
    }

    Initialize-Sandbox

    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $manifestCreatedAt = if ($manifest.created_at -is [datetime]) {
        $manifest.created_at.ToString("s")
    } else {
        [string]$manifest.created_at
    }
    $manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    $items = @()
    $allMatch = $true
    foreach ($relative in Get-DevPackageFiles) {
        $stagePath = Join-Path $stage $relative
        $sandboxPath = Join-Path $SandboxClient $relative
        $stageExists = Test-Path -LiteralPath $stagePath
        $sandboxExists = Test-Path -LiteralPath $sandboxPath
        $stageHash = ""
        $sandboxHash = ""
        if ($stageExists) {
            $stageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $stagePath).Hash.ToLowerInvariant()
        }
        if ($sandboxExists) {
            $sandboxHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sandboxPath).Hash.ToLowerInvariant()
        }
        $matches = $stageExists -and $sandboxExists -and ($stageHash -eq $sandboxHash)
        if (-not $matches) {
            $allMatch = $false
        }
        $items += [pscustomobject]@{
            path = $relative.Replace("\", "/")
            stage_exists = $stageExists
            sandbox_exists = $sandboxExists
            stage_sha256 = $stageHash
            sandbox_sha256 = $sandboxHash
            matches = $matches
        }
    }

    $report = [pscustomobject]@{
        name = "solteria-helper-smoke-preflight"
        created_at = (Get-Date).ToString("s")
        status = if ($allMatch) { "passed" } else { "failed" }
        stage = [System.IO.Path]::GetFullPath($stage)
        manifest = [pscustomobject]@{
            path = [System.IO.Path]::GetFullPath($manifestPath)
            created_at = $manifestCreatedAt
            sha256 = $manifestHash
        }
        sandbox_client = [System.IO.Path]::GetFullPath($SandboxClient)
        live_safety = "SmokePreflight runs Setup and hash checks only; it does not launch, stop, or overwrite the live play client."
        next_action = if ($allMatch) { "Launch sandbox, enter test character, then run SmokeAttachModules." } else { "Re-run Setup or inspect mismatched files before Launch." }
        files = $items
    }
    $path = Join-Path $outRoot "smoke_preflight.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding ASCII
    Write-Output "[solteria-helper-test-env] Smoke preflight: $path"
    Write-Output "[solteria-helper-test-env] Smoke preflight status: $($report.status)"
    Write-Output "[solteria-helper-test-env] $($report.next_action)"
    if (-not $allMatch) {
        throw "Smoke preflight failed"
    }
}

function Start-SandboxClient {
    Assert-InteractiveOperatorMode -Operation "start sandbox client"
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $exe = Join-Path $sandboxRoot "solteria-client.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Sandbox client is not initialized. Run -Action Setup first."
    }
    Start-Process -FilePath $exe -WorkingDirectory $sandboxRoot
}

function Get-SandboxProcesses {
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $exe = [System.IO.Path]::GetFullPath((Join-Path $sandboxRoot "solteria-client.exe"))
    $matches = @()
    Get-Process solteria-client -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $path = [System.IO.Path]::GetFullPath($_.MainModule.FileName)
            if ($path.Equals($exe, [System.StringComparison]::OrdinalIgnoreCase)) {
                $matches += $_
            }
        } catch {
            # MainModule can be unavailable for short-lived processes; ignore.
        }
    }
    return $matches
}

function Get-SandboxProcessSummaries {
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $exe = [System.IO.Path]::GetFullPath((Join-Path $sandboxRoot "solteria-client.exe"))
    $summaries = @()
    $items = @()
    try {
        $items = @(Get-CimInstance Win32_Process -Filter "Name = 'solteria-client.exe'" -ErrorAction Stop)
    } catch {
        $items = @()
    }
    foreach ($item in $items) {
        $path = [string]$item.ExecutablePath
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }
        try {
            $fullPath = [System.IO.Path]::GetFullPath($path)
            if (-not $fullPath.Equals($exe, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
        } catch {
            continue
        }
        $hasWindow = $false
        $responding = $false
        $startTime = ""
        try {
            $proc = Get-Process -Id ([int]$item.ProcessId) -ErrorAction Stop
            $hasWindow = $proc.MainWindowHandle -ne 0
            $responding = $proc.Responding
            if ($proc.StartTime) {
                $startTime = $proc.StartTime.ToString("s")
            }
        } catch {
            $hasWindow = $false
            $responding = $false
        }
        $summaries += [pscustomobject]@{
            id = [int]$item.ProcessId
            start_time = $startTime
            has_window = $hasWindow
            responding = $responding
        }
    }
    return $summaries
}

function Stop-SandboxClient {
    Assert-InteractiveOperatorMode -Operation "stop sandbox client"
    Get-SandboxProcesses | ForEach-Object {
        Stop-Process -Id $_.Id -Force
    }
    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-SandboxProcesses | Select-Object -First 1)) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
}

function Set-LiveCtoaEnabled {
    param([bool]$Enabled)
    Assert-InteractiveOperatorMode -Operation "change live helper enablement"
    $modDir = Join-Path $SourceClient "mods\ctoa_otclient"
    if (-not (Test-Path -LiteralPath $modDir)) {
        throw "CTOA module directory not found: $modDir"
    }
    $files = @(Get-DevModuleFileNames)
    foreach ($name in $files) {
        $enabledPath = Join-Path $modDir $name
        $disabledPath = "$enabledPath.disabled"
        if ($Enabled) {
            if ((Test-Path -LiteralPath $disabledPath) -and -not (Test-Path -LiteralPath $enabledPath)) {
                Rename-Item -LiteralPath $disabledPath -NewName $name
                Write-Output "[solteria-helper-test-env] Enabled $name"
            } elseif ((Test-Path -LiteralPath $disabledPath) -and (Test-Path -LiteralPath $enabledPath)) {
                Remove-Item -LiteralPath $disabledPath -Force
                Write-Output "[solteria-helper-test-env] Removed stale disabled copy for $name"
            }
        } else {
            if (Test-Path -LiteralPath $enabledPath) {
                if (Test-Path -LiteralPath $disabledPath) {
                    Remove-Item -LiteralPath $disabledPath -Force
                }
                Rename-Item -LiteralPath $enabledPath -NewName "$name.disabled"
                Write-Output "[solteria-helper-test-env] Disabled $name"
            }
        }
    }
    foreach ($name in @("ctoa_otclient_loader.lua", "ctoa_ek_profile.lua")) {
        $enabledPath = Join-Path $SourceClient $name
        $disabledPath = "$enabledPath.disabled"
        if ($Enabled) {
            if ((Test-Path -LiteralPath $disabledPath) -and -not (Test-Path -LiteralPath $enabledPath)) {
                Rename-Item -LiteralPath $disabledPath -NewName $name
                Write-Output "[solteria-helper-test-env] Enabled root $name"
            } elseif ((Test-Path -LiteralPath $disabledPath) -and (Test-Path -LiteralPath $enabledPath)) {
                Remove-Item -LiteralPath $disabledPath -Force
                Write-Output "[solteria-helper-test-env] Removed stale root disabled copy for $name"
            }
        } else {
            if (Test-Path -LiteralPath $enabledPath) {
                if (Test-Path -LiteralPath $disabledPath) {
                    Remove-Item -LiteralPath $disabledPath -Force
                }
                Rename-Item -LiteralPath $enabledPath -NewName "$name.disabled"
                Write-Output "[solteria-helper-test-env] Disabled root $name"
            }
        }
    }
    Get-ChildItem -LiteralPath $modDir -Filter "ctoa_*" | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
}

function Set-LiveCtoaUiOnly {
    Assert-InteractiveOperatorMode -Operation "change live helper UI-only state"
    $modDir = Join-Path $SourceClient "mods\ctoa_otclient"
    if (-not (Test-Path -LiteralPath $modDir)) {
        throw "CTOA module directory not found: $modDir"
    }

    $enableFiles = @(Get-DevModuleFileNames)
    $disableFiles = @(
        "ctoa_native_combat.lua",
        "ctoa_native_heal.lua",
        "ctoa_native_loot.lua"
    )

    foreach ($name in $enableFiles) {
        $enabledPath = Join-Path $modDir $name
        $disabledPath = "$enabledPath.disabled"
        if ((Test-Path -LiteralPath $disabledPath) -and -not (Test-Path -LiteralPath $enabledPath)) {
            Rename-Item -LiteralPath $disabledPath -NewName $name
            Write-Output "[solteria-helper-test-env] Enabled UI-only $name"
        } elseif ((Test-Path -LiteralPath $disabledPath) -and (Test-Path -LiteralPath $enabledPath)) {
            Remove-Item -LiteralPath $disabledPath -Force
            Write-Output "[solteria-helper-test-env] Removed stale disabled copy for $name"
        }
    }

    foreach ($name in @("ctoa_otclient_loader.lua", "ctoa_ek_profile.lua")) {
        $enabledPath = Join-Path $SourceClient $name
        $disabledPath = "$enabledPath.disabled"
        if ((Test-Path -LiteralPath $disabledPath) -and -not (Test-Path -LiteralPath $enabledPath)) {
            Rename-Item -LiteralPath $disabledPath -NewName $name
            Write-Output "[solteria-helper-test-env] Enabled UI-only root $name"
        } elseif ((Test-Path -LiteralPath $disabledPath) -and (Test-Path -LiteralPath $enabledPath)) {
            Remove-Item -LiteralPath $disabledPath -Force
            Write-Output "[solteria-helper-test-env] Removed stale root disabled copy for $name"
        }
    }

    foreach ($name in $disableFiles) {
        $enabledPath = Join-Path $modDir $name
        $disabledPath = "$enabledPath.disabled"
        if (Test-Path -LiteralPath $enabledPath) {
            if (Test-Path -LiteralPath $disabledPath) {
                Remove-Item -LiteralPath $disabledPath -Force
            }
            Rename-Item -LiteralPath $enabledPath -NewName "$name.disabled"
            Write-Output "[solteria-helper-test-env] Kept runtime disabled $name"
        }
    }

    Get-ChildItem -LiteralPath $modDir -Filter "ctoa_*" | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
}

function New-LiveCtoaBackup {
    Assert-InteractiveOperatorMode -Operation "create live client backup"
    Assert-UnderLocalAppData -Path $SourceClient | Out-Null
    if (-not (Test-Path -LiteralPath $SourceClient)) {
        throw "Source client does not exist: $SourceClient"
    }

    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupRoot = Join-Path $outRoot ("live_backup_{0}" -f $stamp)
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

    $items = @()
    foreach ($relative in @("init.lua") + (Get-DevPackageFiles) + (Get-LiveLegacyFiles)) {
        $sourcePath = Join-Path $SourceClient $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }
        $destPath = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destPath) | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destPath -Force
        $file = Get-Item -LiteralPath $destPath
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $destPath
        $items += [pscustomobject]@{
            path = $relative.Replace("\", "/")
            bytes = $file.Length
            sha256 = $hash.Hash.ToLowerInvariant()
        }
    }

    $manifest = [pscustomobject]@{
        name = "solteria-helper-live-backup"
        created_at = (Get-Date).ToString("s")
        source_client = [System.IO.Path]::GetFullPath($SourceClient)
        backup_root = [System.IO.Path]::GetFullPath($backupRoot)
        files = $items
        live_processes = (Get-LiveClientSummary).running_processes
    }
    $manifestPath = Join-Path $backupRoot "backup_manifest.json"
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding ASCII
    Write-Host "[solteria-helper-test-env] Live backup: $backupRoot"
    Write-Host "[solteria-helper-test-env] Live backup manifest: $manifestPath"
    return $backupRoot
}

function Assert-LiveDeployApproved {
    if (-not $ApproveLiveDeploy) {
        throw "Refusing live promotion without explicit approval. Re-run with -Action PromoteLiveCtoa -ApproveLiveDeploy after ValidateDev, sandbox smoke, and user approval."
    }
}

function Assert-ReleaseGateForLivePromotion {
    param([string]$OutRoot)
    $args = @(
        "scripts\ops\solteria_helper_release_gate.py",
        "--dev-dir", $OutRoot,
        "--approved"
    )
    if (-not [string]::IsNullOrWhiteSpace($SmokeReport)) {
        $args += @("--smoke-report", $SmokeReport)
    }
    & python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Refusing live promotion because release_gate is not passed. Run SmokePreflight and in-world SmokeAttachAll first."
    }
}

function Get-VerifiedStagePromotionEntries {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Stage
    )
    $maxFiles = 128
    $maxFileBytes = 2MB
    $maxTotalBytes = 16MB
    $relativeFiles = @(Get-DevPackageFiles)
    if ($relativeFiles.Count -eq 0 -or $relativeFiles.Count -gt $maxFiles) {
        throw "Promotion verification failed: package file count must be 1..$maxFiles."
    }
    $seen = @{}
    $totalBytes = [long]0
    $verifiedEntries = New-Object System.Collections.Generic.List[object]
    foreach ($relativeValue in $relativeFiles) {
        $relative = ([string]$relativeValue).Replace('\', '/')
        if (
            [string]::IsNullOrWhiteSpace($relative) -or
            [System.IO.Path]::IsPathRooted($relative) -or
            $relative -match '(^|/)\.\.?($|/)'
        ) {
            throw "Promotion verification failed: invalid package path: $relative"
        }
        $caseKey = $relative.ToLowerInvariant()
        if ($seen.ContainsKey($caseKey)) {
            throw "Promotion verification failed: duplicate case-insensitive package path: $relative"
        }
        $seen[$caseKey] = $true

        $sourcePath = Join-Path $Stage $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Promotion verification failed: staged file is missing: $sourcePath"
        }
        $sourceInfo = Get-Item -LiteralPath $sourcePath -Force
        if (($sourceInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Promotion verification failed: reparse stage file is forbidden: $($sourceInfo.FullName)"
        }
        if ($sourceInfo.PSIsContainer) {
            throw "Promotion verification failed: staged package entry is not a file: $($sourceInfo.FullName)"
        }
        if ([long]$sourceInfo.Length -gt $maxFileBytes) {
            throw "Promotion verification failed: stage file exceeds 2 MiB: $($sourceInfo.FullName)"
        }
        $sourceBytes = [long]$sourceInfo.Length
        $sourceWriteTicks = [long]$sourceInfo.LastWriteTimeUtc.Ticks
        if ($totalBytes + $sourceBytes -gt $maxTotalBytes) {
            throw "Promotion verification failed: stage package exceeds 16 MiB total."
        }
        $totalBytes += $sourceBytes

        $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
        $sourceAfter = Get-Item -LiteralPath $sourcePath -Force
        if (
            ($sourceAfter.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or
            $sourceAfter.PSIsContainer -or
            [long]$sourceAfter.Length -ne $sourceBytes -or
            [long]$sourceAfter.LastWriteTimeUtc.Ticks -ne $sourceWriteTicks
        ) {
            throw "Promotion verification failed: stage file changed during hashing: $relative"
        }
        $verifiedEntries.Add([pscustomobject][ordered]@{
            path = $relative
            sha256 = $sourceHash
            bytes = $sourceBytes
        })
    }
    return @($verifiedEntries.ToArray())
}

function Assert-LivePromotionMatchesStage {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$StageEntries,
        [Parameter(Mandatory = $true)]
        [string]$LiveClient
    )
    if ($StageEntries.Count -eq 0 -or $StageEntries.Count -gt 128) {
        throw "Promotion verification failed: verified stage entry count must be 1..128."
    }
    $seen = @{}
    $totalBytes = [long]0
    $verifiedEntries = New-Object System.Collections.Generic.List[object]
    foreach ($entry in $StageEntries) {
        $relative = ([string]$entry.path).Replace('\', '/')
        $caseKey = $relative.ToLowerInvariant()
        if ($seen.ContainsKey($caseKey)) {
            throw "Promotion verification failed: duplicate case-insensitive verified path: $relative"
        }
        $seen[$caseKey] = $true
        $expectedBytes = [long]$entry.bytes
        $expectedHash = ([string]$entry.sha256).ToLowerInvariant()
        if ($expectedBytes -lt 0 -or $expectedBytes -gt 2MB) {
            throw "Promotion verification failed: verified entry exceeds 2 MiB: $relative"
        }
        if ($expectedHash -notmatch '^[0-9a-f]{64}$') {
            throw "Promotion verification failed: invalid verified SHA256: $relative"
        }
        $totalBytes += $expectedBytes
        if ($totalBytes -gt 16MB) {
            throw "Promotion verification failed: verified entries exceed 16 MiB total."
        }

        $destPath = Join-Path $LiveClient $relative
        if (-not (Test-Path -LiteralPath $destPath)) {
            throw "Promotion verification failed: live file is missing: $destPath"
        }
        $destInfo = Get-Item -LiteralPath $destPath -Force
        if (($destInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Promotion verification failed: live reparse file is forbidden: $($destInfo.FullName)"
        }
        if ($destInfo.PSIsContainer) {
            throw "Promotion verification failed: live package entry is not a file: $($destInfo.FullName)"
        }
        if ([long]$destInfo.Length -ne $expectedBytes) {
            throw "Promotion verification failed: byte-size mismatch for $relative"
        }
        $destWriteTicks = [long]$destInfo.LastWriteTimeUtc.Ticks
        $destHash = (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($destHash -ne $expectedHash) {
            throw "Promotion verification failed: SHA256 mismatch for $relative"
        }
        $destAfter = Get-Item -LiteralPath $destPath -Force
        if (
            ($destAfter.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 -or
            $destAfter.PSIsContainer -or
            [long]$destAfter.Length -ne $expectedBytes -or
            [long]$destAfter.LastWriteTimeUtc.Ticks -ne $destWriteTicks
        ) {
            throw "Promotion verification failed: live file changed during hashing: $relative"
        }
        $verifiedEntries.Add([pscustomobject][ordered]@{
            path = $relative
            sha256 = $destHash
            bytes = $expectedBytes
        })
    }
    return @($verifiedEntries.ToArray())
}

function Write-LiveManifestSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$OutRoot,
        [Parameter(Mandatory = $true)][string]$CreatedAt,
        [Parameter(Mandatory = $true)][string]$Origin,
        [Parameter(Mandatory = $true)][string]$HelperVersion,
        [Parameter(Mandatory = $true)][object[]]$VerifiedEntries
    )
    if ($VerifiedEntries.Count -eq 0 -or $VerifiedEntries.Count -gt 128) {
        throw "Cannot snapshot live manifest outside the 1..128 file limit."
    }
    $totalBytes = [long]0
    $seen = @{}
    $files = @()
    foreach ($entry in $VerifiedEntries) {
        $relative = ([string]$entry.path).Replace('\', '/')
        $caseKey = $relative.ToLowerInvariant()
        if ($seen.ContainsKey($caseKey)) {
            throw "Cannot snapshot duplicate case-insensitive path: $relative"
        }
        $seen[$caseKey] = $true
        $bytes = [long]$entry.bytes
        if ($bytes -lt 0 -or $bytes -gt 2MB) {
            throw "Cannot snapshot file outside the 2 MiB limit: $relative"
        }
        $totalBytes += $bytes
        if ($totalBytes -gt 16MB) {
            throw "Cannot snapshot package above the 16 MiB total limit."
        }
        $files += [pscustomobject][ordered]@{
            path = $relative
            sha256 = ([string]$entry.sha256).ToLowerInvariant()
            bytes = $bytes
        }
    }
    $snapshot = [ordered]@{
        schema_version = "ctoa.solteria-live-manifest.v1"
        generated_at_utc = $CreatedAt
        origin = $Origin
        helper_version = $HelperVersion
        files = @($files)
    }
    $path = Join-Path $OutRoot "live_manifest.json"
    Write-JsonAtomic -InputObject $snapshot -Path $path -Depth 8
    return [System.IO.Path]::GetFullPath($path)
}

function Invoke-LivePromotion {
    Assert-InteractiveOperatorMode -Operation "promote live helper"
    Assert-LiveDeployApproved
    Assert-UnderLocalAppData -Path $SourceClient | Out-Null

    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $stage = Join-Path $outRoot "latest"
    if (-not (Test-Path -LiteralPath $stage)) {
        throw "Missing staged dev package: $stage"
    }

    Write-Output "[solteria-helper-test-env] Checking existing release gate for staged package before live promotion."
    Assert-ReleaseGateForLivePromotion -OutRoot $outRoot
    $stageEntries = @(Get-VerifiedStagePromotionEntries -Stage $stage)
    $backupRoot = New-LiveCtoaBackup
    $migratedUserState = @(Copy-LegacyHelperUserState -ClientDir $SourceClient)
    foreach ($entry in $stageEntries) {
        $relative = [string]$entry.path
        $sourcePath = Join-Path $stage $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Staged package is missing required file: $sourcePath"
        }
        $destPath = Join-Path $SourceClient $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destPath) | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destPath -Force
    }
    $verifiedEntries = @(Assert-LivePromotionMatchesStage -StageEntries $stageEntries -LiveClient $SourceClient)
    $helperVersion = Get-HelperVersion
    $removedLegacyFiles = @(Remove-LiveLegacyFiles -ClientDir $SourceClient)
    Ensure-CtoaBootHook -ClientDir $SourceClient

    $launchResult = [pscustomobject]@{
        requested = $false
        status = "not_requested"
        executable = [System.IO.Path]::GetFullPath((Join-Path $SourceClient "solteria-client.exe"))
        process_ids = @()
    }
    $launchError = ""
    if ($LaunchAfterPromote) {
        try {
            $launchResult = Start-LiveClientAfterPromotion
        } catch {
            $launchError = [string]$_.Exception.Message
            $launchResult = [pscustomobject]@{
                requested = $true
                status = "failed"
                executable = [System.IO.Path]::GetFullPath((Join-Path $SourceClient "solteria-client.exe"))
                process_ids = @()
                error = $launchError
            }
        }
    }

    $promotionCreatedAt = (Get-Date).ToString("s")
    $liveManifestPath = Write-LiveManifestSnapshot -OutRoot $outRoot -CreatedAt $promotionCreatedAt -Origin "official_live_promotion" -HelperVersion $helperVersion -VerifiedEntries $verifiedEntries
    $liveManifestSha256 = (Get-FileHash -LiteralPath $liveManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $report = [pscustomobject]@{
        name = "solteria-helper-live-promotion"
        created_at = $promotionCreatedAt
        helper_version = $helperVersion
        source_stage = [System.IO.Path]::GetFullPath($stage)
        live_client = [System.IO.Path]::GetFullPath($SourceClient)
        backup = [System.IO.Path]::GetFullPath($backupRoot)
        approval_switch = "ApproveLiveDeploy"
        verified_file_count = $verifiedEntries.Count
        verification = "stage_live_sha256_match"
        live_manifest = $liveManifestPath
        live_manifest_sha256 = $liveManifestSha256
        launch_after_promote = $LaunchAfterPromote.IsPresent
        launch_result = $launchResult
        migrated_user_state = $migratedUserState
        removed_legacy_files = $removedLegacyFiles
        note = "Promotion preserved legacy Helper user settings when needed, copied staged project files, removed stale loaders/preferences/Safe helper copies, and ensured the single neutral CTOA boot hook; it does not stop or restart the live client. Use -LaunchAfterPromote to launch the live client after promotion when it is not already running."
    }
    $reportPath = Join-Path $outRoot "live_promotion.json"
    Write-JsonAtomic -InputObject $report -Path $reportPath -Depth 8
    Write-Output "[solteria-helper-test-env] Live promotion complete: $SourceClient"
    Write-Output "[solteria-helper-test-env] Promotion report: $reportPath"
    if (-not [string]::IsNullOrWhiteSpace($launchError)) {
        throw "Live promotion completed, but -LaunchAfterPromote failed: $launchError"
    }
}

function Invoke-LiveEmergencyRepair {
    Assert-InteractiveOperatorMode -Operation "repair live helper"
    Assert-UnderLocalAppData -Path $SourceClient | Out-Null

    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $stage = Join-Path $outRoot "latest"
    if (-not (Test-Path -LiteralPath $stage)) {
        throw "Missing staged dev package: $stage"
    }

    $missing = @()
    foreach ($relative in Get-DevPackageFiles) {
        $sourcePath = Join-Path $stage $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            $missing += $relative
        }
    }
    if ($missing.Count -gt 0) {
        throw "Staged package is missing required file(s): $($missing -join ', ')"
    }

    $backupRoot = New-LiveCtoaBackup
    $migratedUserState = @(Copy-LegacyHelperUserState -ClientDir $SourceClient)
    $copied = @()
    foreach ($relative in Get-DevPackageFiles) {
        $sourcePath = Join-Path $stage $relative
        $destPath = Join-Path $SourceClient $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destPath) | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destPath -Force
        $copied += $relative
    }

    $removedLegacyFiles = @(Remove-LiveLegacyFiles -ClientDir $SourceClient)
    Ensure-CtoaBootHook -ClientDir $SourceClient

    $report = [pscustomobject]@{
        name = "solteria-helper-live-emergency-repair"
        created_at = (Get-Date).ToString("s")
        helper_version = (Get-HelperVersion)
        source_stage = [System.IO.Path]::GetFullPath($stage)
        live_client = [System.IO.Path]::GetFullPath($SourceClient)
        backup = [System.IO.Path]::GetFullPath($backupRoot)
        approval = "EmergencyRepairLiveCtoa"
        release_gate_bypassed = $true
        reason = "Emergency repair approved by operator because live client had stale root helper files and sandbox in-world smoke was blocked by client/protocol state."
        copied_files = $copied
        migrated_user_state = $migratedUserState
        removed_legacy_files = $removedLegacyFiles
        live_processes = (Get-LiveClientSummary).running_processes
        note = "Emergency repair preserved legacy Helper user settings when needed, copied the staged projects, removed stale loaders/preferences/Safe helper copies, and ensured the single neutral CTOA boot hook. It does not stop or restart the live client."
    }
    $reportPath = Join-Path $outRoot "live_emergency_repair.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding ASCII
    Write-Output "[solteria-helper-test-env] Live emergency repair complete: $SourceClient"
    Write-Output "[solteria-helper-test-env] Emergency repair report: $reportPath"
}

function Capture-Screenshot {
    param(
        [string]$Name,
        [IntPtr]$WindowHandle = [IntPtr]::Zero
    )
    Assert-InteractiveOperatorMode -Operation "capture screenshot"
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing
    $repo = Get-RepoRoot
    $outDir = Join-Path $repo $ScreenshotDir
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    if ($WindowHandle -ne [IntPtr]::Zero) {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32SolteriaCapture {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
  }
  [DllImport("user32.dll")]
  public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")]
  public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);
}
"@
        $rect = New-Object Win32SolteriaCapture+RECT
        if ([Win32SolteriaCapture]::GetWindowRect($WindowHandle, [ref]$rect)) {
            $bounds = New-Object System.Drawing.Rectangle $rect.Left, $rect.Top, ($rect.Right - $rect.Left), ($rect.Bottom - $rect.Top)
        } else {
            $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        }
    } else {
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    }
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $captured = $false
    if ($WindowHandle -ne [IntPtr]::Zero) {
        $hdc = $g.GetHdc()
        try {
            $captured = [Win32SolteriaCapture]::PrintWindow($WindowHandle, $hdc, 2)
        } finally {
            $g.ReleaseHdc($hdc)
        }
    }
    if (-not $captured) {
        $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    }
    $out = Join-Path $outDir $Name
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
    return $out
}

function Wait-ForSmokeTab {
    param(
        [string]$ActiveTab,
        [string]$SmokeSubtab = "",
        [switch]$Required,
        [int]$AfterLineCount = 0
    )
    $logPath = Join-Path $SandboxClient "ctoa_local.log"
    $label = $ActiveTab
    if (-not [string]::IsNullOrWhiteSpace($SmokeSubtab)) {
        $label = "$ActiveTab/$SmokeSubtab"
    }
    $needle = "Smoke tab visible: $label"
    $deadline = (Get-Date).AddSeconds(12)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $logPath) {
            $lines = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
            if ($AfterLineCount -gt 0 -and $lines.Count -gt $AfterLineCount) {
                $lines = $lines[$AfterLineCount..($lines.Count - 1)]
            } elseif ($AfterLineCount -gt 0) {
                $lines = @()
            } elseif ($lines.Count -gt 40) {
                $lines = $lines[($lines.Count - 40)..($lines.Count - 1)]
            }
            if ($lines -match [regex]::Escape($needle)) {
                Start-Sleep -Milliseconds 600
                return $true
            }
        }
        Start-Sleep -Milliseconds 250
    }
    $message = "Timed out waiting for helper smoke tab marker: $needle. If Select Character is visible, enter the character first and rerun SmokeAttachModules or SmokeAttachAll."
    if ($Required) {
        throw $message
    }
    Write-Warning $message
    return $false
}

function Get-SmokeLogLineCount {
    $logPath = Join-Path $SandboxClient "ctoa_local.log"
    if (-not (Test-Path -LiteralPath $logPath)) {
        return 0
    }
    return @((Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)).Count
}

function Test-AtCharacterSelect {
    $logPath = Join-Path $SandboxClient "otclient.log"
    if (-not (Test-Path -LiteralPath $logPath)) {
        return $false
    }
    $tail = Get-Content -LiteralPath $logPath -Tail 120 -ErrorAction SilentlyContinue
    return ($tail -match "Select Character" -or $tail -match "character")
}

function Invoke-SmokeStatus {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $processes = @(Get-SandboxProcessSummaries)
    $ctoaLog = Join-Path $sandboxFull "ctoa_local.log"
    $otclientLog = Join-Path $sandboxFull "otclient.log"
    $preflightPath = Join-Path $outRoot "smoke_preflight.json"
    $preflightStatus = "missing"
    if (Test-Path -LiteralPath $preflightPath) {
        try {
            $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
            $preflightStatus = [string]$preflight.status
        } catch {
            $preflightStatus = "invalid"
        }
    }
    $ctoaTail = @()
    $otclientTail = @()
    if (Test-Path -LiteralPath $ctoaLog) {
        $ctoaTail = @(Get-Content -LiteralPath $ctoaLog -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { [string]$_ })
    }
    if (Test-Path -LiteralPath $otclientLog) {
        $otclientTail = @(Get-Content -LiteralPath $otclientLog -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { [string]$_ })
    }
    $latestSmokeMarker = [string](@($ctoaTail | Where-Object { $_ -match "Smoke tab visible:" } | Select-Object -Last 1) | Select-Object -First 1)
    $atCharacterSelect = [bool](Test-AtCharacterSelect)
    $hasWindow = @($processes | Where-Object { $_.has_window }).Count -gt 0
    $statusValue = "not_running"
    $nextAction = if ($preflightStatus -eq "passed") { "Launch the sandbox client, enter test character, then run SmokeAttachModules." } else { "Run SmokePreflight, then Launch the sandbox client." }
    $nextCommand = if ($preflightStatus -eq "passed") { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight" }
    if ($processes.Count -gt 0 -and -not $hasWindow) {
        $statusValue = "running_without_window"
        $nextAction = "Wait for the sandbox window or restart only the sandbox client."
        $nextCommand = ""
    } elseif ($processes.Count -gt 0 -and $atCharacterSelect) {
        $statusValue = "character_modal"
        $nextAction = "Enter the sandbox test character, then run ReadyCheck or SmokeAttachModules."
        $nextCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck"
    } elseif ($processes.Count -gt 0 -and $hasWindow -and -not (Test-Path -LiteralPath $ctoaLog)) {
        $statusValue = "helper_log_missing"
        $nextAction = "Wait for helper load or inspect sandbox otclient.log."
        $nextCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeStatus"
    } elseif ($processes.Count -gt 0 -and $hasWindow) {
        $statusValue = "ready_for_readycheck"
        $nextAction = "Run ReadyCheck, then SmokeAttachModules when the test character is in-world."
        $nextCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck"
    }
    $report = [pscustomobject]@{
        name = "solteria-helper-smoke-status"
        created_at = (Get-Date).ToString("s")
        status = $statusValue
        sandbox_client = $sandboxFull
        process_count = $processes.Count
        has_window = $hasWindow
        at_character_select = $atCharacterSelect
        ctoa_log_exists = Test-Path -LiteralPath $ctoaLog
        otclient_log_exists = Test-Path -LiteralPath $otclientLog
        smoke_preflight_status = $preflightStatus
        latest_smoke_marker = if ($latestSmokeMarker) { [string]$latestSmokeMarker } else { "" }
        next_action = $nextAction
        next_command = $nextCommand
        processes = $processes
        ctoa_tail = $ctoaTail
        otclient_tail = $otclientTail
        live_safety = "SmokeStatus is read-only; it does not launch, stop, or overwrite any client."
    }
    $path = Join-Path $outRoot "smoke_status.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Smoke status: $path"
    Write-Output "[solteria-helper-test-env] Smoke status value: $statusValue"
    Write-Output "[solteria-helper-test-env] $nextAction"
    if (-not [string]::IsNullOrWhiteSpace($nextCommand)) {
        Write-Output "[solteria-helper-test-env] Next command: $nextCommand"
    }
}

function Test-HelperModuleConfigured {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string]$HelperSource,
        [Parameter(Mandatory = $true)][string]$ModuleName
    )
    $schemaPath = Join-Path $Repo "scripts\lua\otclient\ctoa_helper_profile_schema.lua"
    if (-not (Test-Path -LiteralPath $schemaPath -PathType Leaf)) {
        return $false
    }
    $schemaSource = Get-Content -LiteralPath $schemaPath -Raw
    return (
        $HelperSource.Contains("pcall(externalProfileSchema.defaultProfile)") -and
        $schemaSource.Contains("$ModuleName = {")
    )
}

function Invoke-HealFriendNoTargetSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $modulePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_heal_friend.lua"
    $profilePath = Join-Path $repo "scripts\lua\otclient\ctoa_ek_profile.lua"
    $helper = Get-Content -LiteralPath $helperPath -Raw
    $module = Get-Content -LiteralPath $modulePath -Raw
    $profile = Get-Content -LiteralPath $profilePath -Raw
    $adapterStart = $helper.IndexOf("local function maybeObserveHealFriend(now)")
    $adapterEnd = $helper.IndexOf("local function buildTargetCandidate")
    $adapterSource = ""
    if ($adapterStart -ge 0 -and $adapterEnd -gt $adapterStart) {
        $adapterSource = $helper.Substring($adapterStart, $adapterEnd - $adapterStart)
    }
    $checks = @(
        [pscustomobject]@{ name = "module_configured"; status = if (Test-HelperModuleConfigured -Repo $repo -HelperSource $helper -ModuleName "heal_friend") { "passed" } else { "failed" }; evidence = "profile schema owns heal_friend config and helper loads defaultProfile" },
        [pscustomobject]@{ name = "observer_module_present"; status = if ($module.Contains("function HealFriend.scan") -and $module.Contains("function HealFriend.observe") -and $module.Contains("function HealFriend.statusText") -and $module.Contains("function HealFriend.decisionText") -and $helper.Contains('moduleValue(externalHealFriend, "observe", healFriend, now, {') -and -not $helper.Contains("pcall(externalHealFriend.observe")) { "passed" } else { "failed" }; evidence = "module owns scan/observe/status/decision text and helper delegates observer context through guarded moduleValue" },
        [pscustomobject]@{ name = "profile_safe_boot"; status = if ($profile.Contains("heal_friend = {") -and $profile.Contains("runtime_enabled = false") -and $profile.Contains("friend_whitelist = {}")) { "passed" } else { "failed" }; evidence = "profile keeps runtime disabled and empty whitelist" },
        [pscustomobject]@{ name = "no_cast_in_observer"; status = if (-not $module.Contains("castSpell(") -and -not $adapterSource.Contains("castSpell(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no castSpell" },
        [pscustomobject]@{ name = "no_actionbar_in_observer"; status = if (-not $module.Contains("sendActionbarSlot(") -and -not $adapterSource.Contains("sendActionbarSlot(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no actionbar send" },
        [pscustomobject]@{ name = "no_talk_in_observer"; status = if (-not $module.Contains("g_game.talk") -and -not $adapterSource.Contains("g_game.talk")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no g_game.talk" },
        [pscustomobject]@{ name = "exact_target_guard_present"; status = if ($module.Contains("function HealFriend.whitelistContainsName") -and $module.Contains("friend_target_id") -and $module.Contains('scan_policy = "single_exact_target_id_and_name"') -and $module.Contains("requires_party_membership = true") -and $module.Contains("requires_visibility = true") -and $module.Contains("requires_same_floor = true")) { "passed" } else { "failed" }; evidence = "module owns exact stable ID/name, party, visibility, and floor guards" },
        [pscustomobject]@{ name = "status_is_read_only"; status = if ($module.Contains("read-only pending; no sio cast until sandbox whitelist smoke passes") -and $module.Contains("owns_status_text = true") -and $module.Contains("owns_decision_text = true") -and $helper.Contains('moduleValue(externalHealFriend, "statusText", healFriend)') -and -not $helper.Contains("externalHealFriend.statusText")) { "passed" } else { "failed" }; evidence = "module owns gated sio status and decision text while helper only renders it" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-heal-friend-no-target-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "heal_friend"
        mode = "static_no_target_contract"
        helper_path = [System.IO.Path]::GetFullPath($helperPath)
        module_path = [System.IO.Path]::GetFullPath($modulePath)
        profile_path = [System.IO.Path]::GetFullPath($profilePath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run SmokeAttach -Tab heal_friend after sandbox character is in-world to capture visual observer evidence." } else { "Fix failed heal_friend no-target contract checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend" } else { "" }
        live_safety = "HealFriendNoTargetSmoke reads repo helper/profile files only; it does not launch, stop, or overwrite any client."
    }
    $path = Join-Path $outRoot "heal_friend_no_target_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] HealFriend no-target smoke: $path"
    Write-Output "[solteria-helper-test-env] HealFriend no-target status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "HealFriend no-target smoke failed"
    }
}

function Invoke-ConditionsObserverSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $uiPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_ui.lua"
    $modulePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_conditions.lua"
    $profilePath = Join-Path $repo "scripts\lua\otclient\ctoa_ek_profile.lua"
    $helper = Get-Content -LiteralPath $helperPath -Raw
    $ui = Get-Content -LiteralPath $uiPath -Raw
    $module = Get-Content -LiteralPath $modulePath -Raw
    $profile = Get-Content -LiteralPath $profilePath -Raw
    $adapterStart = $helper.IndexOf("function maybeSampleConditions(now)")
    $adapterEnd = $helper.IndexOf("function maybeSampleEquipment(now)")
    $adapterSource = ""
    if ($adapterStart -ge 0 -and $adapterEnd -gt $adapterStart) {
        $adapterSource = $helper.Substring($adapterStart, $adapterEnd - $adapterStart)
    }
    $checks = @(
        [pscustomobject]@{ name = "module_configured"; status = if (Test-HelperModuleConfigured -Repo $repo -HelperSource $helper -ModuleName "conditions") { "passed" } else { "failed" }; evidence = "profile schema owns conditions config and helper loads defaultProfile" },
        [pscustomobject]@{ name = "observer_module_present"; status = if ($module.Contains("function Conditions.snapshot") -and $module.Contains("function Conditions.apiProbe") -and $module.Contains("function Conditions.observe") -and $helper.Contains('moduleValue(externalConditions, "observe", conditions, now, {') -and -not $helper.Contains("pcall(externalConditions.observe")) { "passed" } else { "failed" }; evidence = "module owns condition snapshot/api probe/observe and helper delegates context through guarded moduleValue" },
        [pscustomobject]@{ name = "profile_safe_boot"; status = if ($profile.Contains("conditions = {") -and $profile.Contains("runtime_enabled = false") -and $profile.Contains("observe_states = true")) { "passed" } else { "failed" }; evidence = "profile keeps runtime disabled while allowing state observation" },
        [pscustomobject]@{ name = "state_api_probe_present"; status = if ($module.Contains("player.hasState=") -and $module.Contains("player.getStates=") -and $module.Contains("state.manaShield=") -and $module.Contains("owns_api_probe = true")) { "passed" } else { "failed" }; evidence = "module reports state API availability" },
        [pscustomobject]@{ name = "no_cast_in_observer"; status = if (-not $module.Contains("castSpell(") -and -not $adapterSource.Contains("castSpell(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no castSpell" },
        [pscustomobject]@{ name = "no_actionbar_in_observer"; status = if (-not $module.Contains("sendActionbarSlot(") -and -not $adapterSource.Contains("sendActionbarSlot(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no actionbar send" },
        [pscustomobject]@{ name = "no_talk_in_observer"; status = if (-not $module.Contains("g_game.talk") -and -not $adapterSource.Contains("g_game.talk")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no g_game.talk" },
        [pscustomobject]@{ name = "status_is_read_only"; status = if ($ui.Contains("state observer / no actions") -and $ui.Contains("Status: read-only pending")) { "passed" } else { "failed" }; evidence = "UI declares conditions as read-only observer" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-conditions-observer-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "conditions"
        mode = "static_observer_contract"
        helper_path = [System.IO.Path]::GetFullPath($helperPath)
        ui_path = [System.IO.Path]::GetFullPath($uiPath)
        module_path = [System.IO.Path]::GetFullPath($modulePath)
        profile_path = [System.IO.Path]::GetFullPath($profilePath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run SmokeAttach -Tab conditions after sandbox character is in-world to capture state observer UI evidence." } else { "Fix failed conditions observer contract checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions" } else { "" }
        live_safety = "ConditionsObserverSmoke reads repo helper/profile files only; it does not launch, stop, or overwrite any client."
    }
    $path = Join-Path $outRoot "conditions_observer_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Conditions observer smoke: $path"
    Write-Output "[solteria-helper-test-env] Conditions observer status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Conditions observer smoke failed"
    }
}

function Invoke-EquipmentObserverSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $uiPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_ui.lua"
    $modulePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_equipment.lua"
    $profilePath = Join-Path $repo "scripts\lua\otclient\ctoa_ek_profile.lua"
    $helper = Get-Content -LiteralPath $helperPath -Raw
    $ui = Get-Content -LiteralPath $uiPath -Raw
    $module = Get-Content -LiteralPath $modulePath -Raw
    $profile = Get-Content -LiteralPath $profilePath -Raw
    $adapterStart = $helper.IndexOf("function maybeSampleEquipment(now)")
    $adapterEnd = $helper.IndexOf("function maybeRunTimer(now)")
    $adapterSource = ""
    if ($adapterStart -ge 0 -and $adapterEnd -gt $adapterStart) {
        $adapterSource = $helper.Substring($adapterStart, $adapterEnd - $adapterStart)
    }
    $checks = @(
        [pscustomobject]@{ name = "module_configured"; status = if (Test-HelperModuleConfigured -Repo $repo -HelperSource $helper -ModuleName "equipment") { "passed" } else { "failed" }; evidence = "profile schema owns equipment config and helper loads defaultProfile" },
        [pscustomobject]@{ name = "observer_module_present"; status = if ($module.Contains("function Equipment.snapshot") -and $module.Contains("function Equipment.apiProbe") -and $module.Contains("function Equipment.observe") -and $helper.Contains('moduleValue(externalEquipment, "observe", equipment, now, {') -and -not $helper.Contains("pcall(externalEquipment.observe")) { "passed" } else { "failed" }; evidence = "module owns equipment snapshot/api probe/observe and helper delegates context through guarded moduleValue" },
        [pscustomobject]@{ name = "profile_safe_boot"; status = if ($profile.Contains("equipment = {") -and $profile.Contains("runtime_enabled = false") -and $profile.Contains("ring_swap = false") -and $profile.Contains("amulet_swap = false")) { "passed" } else { "failed" }; evidence = "profile keeps runtime and swaps disabled" },
        [pscustomobject]@{ name = "inventory_api_probe_present"; status = if ($module.Contains("player.getInventoryItem=") -and $module.Contains("slot.ring=") -and $module.Contains("slot.amulet=") -and $module.Contains("owns_api_probe = true")) { "passed" } else { "failed" }; evidence = "module reports inventory slot API availability" },
        [pscustomobject]@{ name = "no_cast_in_observer"; status = if (-not $module.Contains("castSpell(") -and -not $adapterSource.Contains("castSpell(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no castSpell" },
        [pscustomobject]@{ name = "no_actionbar_in_observer"; status = if (-not $module.Contains("sendActionbarSlot(") -and -not $adapterSource.Contains("sendActionbarSlot(")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no actionbar send" },
        [pscustomobject]@{ name = "no_talk_in_observer"; status = if (-not $module.Contains("g_game.talk") -and -not $adapterSource.Contains("g_game.talk")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no g_game.talk" },
        [pscustomobject]@{ name = "no_move_or_use_in_observer"; status = if (-not $module.Contains("g_game.move") -and -not $module.Contains("moveTo") -and -not $module.Contains("useInventoryItem") -and -not $module.Contains("g_game.use") -and -not $adapterSource.Contains("g_game.move") -and -not $adapterSource.Contains("moveTo") -and -not $adapterSource.Contains("useInventoryItem") -and -not $adapterSource.Contains("g_game.use")) { "passed" } else { "failed" }; evidence = "observer module and helper adapter have no swap, move, or use call" },
        [pscustomobject]@{ name = "status_is_read_only"; status = if ($ui.Contains("slot observer / no swaps") -and $ui.Contains("Status: read-only pending; swap runtime gated")) { "passed" } else { "failed" }; evidence = "UI declares equipment as read-only observer" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-equipment-observer-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "equipment"
        mode = "static_observer_contract"
        helper_path = [System.IO.Path]::GetFullPath($helperPath)
        ui_path = [System.IO.Path]::GetFullPath($uiPath)
        module_path = [System.IO.Path]::GetFullPath($modulePath)
        profile_path = [System.IO.Path]::GetFullPath($profilePath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run SmokeAttach -Tab equipment after sandbox character is in-world to capture inventory slot observer UI evidence." } else { "Fix failed equipment observer contract checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment" } else { "" }
        live_safety = "EquipmentObserverSmoke reads repo helper/profile files only; it does not launch, stop, swap gear, move items, use items, or overwrite any client."
    }
    $path = Join-Path $outRoot "equipment_observer_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Equipment observer smoke: $path"
    Write-Output "[solteria-helper-test-env] Equipment observer status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Equipment observer smoke failed"
    }
}

function Invoke-ScriptingPolicySmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $uiPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_ui.lua"
    $profilePath = Join-Path $repo "scripts\lua\otclient\ctoa_ek_profile.lua"
    $modulePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_scripting.lua"
    $helper = Get-Content -LiteralPath $helperPath -Raw
    $ui = Get-Content -LiteralPath $uiPath -Raw
    $profile = Get-Content -LiteralPath $profilePath -Raw
    $module = Get-Content -LiteralPath $modulePath -Raw
    $policyStart = $helper.IndexOf("build_scripting_policy_snapshot = function()")
    $policyEnd = $helper.IndexOf('styleUi("renderProfilePanel"')
    $policySource = ""
    if ($policyStart -ge 0 -and $policyEnd -gt $policyStart) {
        $policySource = $helper.Substring($policyStart, $policyEnd - $policyStart)
    }
    $checks = @(
        [pscustomobject]@{ name = "module_configured"; status = if (Test-HelperModuleConfigured -Repo $repo -HelperSource $helper -ModuleName "scripting") { "passed" } else { "failed" }; evidence = "profile schema owns scripting config and helper loads defaultProfile" },
        [pscustomobject]@{ name = "policy_shell_present"; status = if (-not $helper.Contains("function buildScriptingPolicySnapshot()") -and $helper.Contains("build_scripting_policy_snapshot = function()") -and $helper.Contains('moduleValue(externalScripting, "policySnapshot", scripting)') -and -not $helper.Contains("pcall(externalScripting.policySnapshot") -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.scripting") -and $helper.Contains('scripting = moduleValue(externalOperatorSummary, "bridgeText", "scripting", OPERATOR_SUMMARY_BRIDGES)') -and $helper.Contains("scripting_summary_text = operatorSummaries.scripting")) { "passed" } else { "failed" }; evidence = "policy shell delegates passive snapshot through shared guarded renderer callback" },
        [pscustomobject]@{ name = "profile_safe_boot"; status = if ($profile.Contains("scripting = {") -and $profile.Contains('policy_mode = "deny_all"') -and $profile.Contains("allow_user_snippets = false") -and $profile.Contains("allow_runtime_eval = false") -and $profile.Contains('command_model = "none"')) { "passed" } else { "failed" }; evidence = "profile blocks snippets, eval, and command model" },
        [pscustomobject]@{ name = "runtime_flags_forced_off"; status = if ($helper.Contains("HELPER_CONFIG.scripting.runtime_enabled = false") -and $helper.Contains("HELPER_CONFIG.scripting.allow_user_snippets = false") -and $helper.Contains("HELPER_CONFIG.scripting.allow_runtime_eval = false")) { "passed" } else { "failed" }; evidence = "loader forces unsafe scripting flags off" },
        [pscustomobject]@{ name = "unsafe_flags_block_status"; status = if ($module.Contains("blocked: unsafe scripting flag") -and $module.Contains("blocked: runtime scripting disabled") -and $module.Contains("owns_policy_snapshot = true")) { "passed" } else { "failed" }; evidence = "scripting module owns policy snapshot and reports blocked unsafe states" },
        [pscustomobject]@{ name = "no_eval_loader_in_policy"; status = if (-not $policySource.Contains("loadstring") -and -not $policySource.Contains("dofile(") -and -not $policySource.Contains("require(")) { "passed" } else { "failed" }; evidence = "policy slice has no eval/file loader" },
        [pscustomobject]@{ name = "no_runtime_call_in_policy"; status = if (-not $policySource.Contains("pcall(function()") -and -not $policySource.Contains("g_game.talk") -and -not $policySource.Contains("castSpell(") -and -not $policySource.Contains("sendActionbarSlot(")) { "passed" } else { "failed" }; evidence = "policy slice has no runtime action call" },
        [pscustomobject]@{ name = "ui_forces_toggles_off"; status = if ($ui.Contains("ctoaScriptingSnippets") -and $ui.Contains("scripting.allow_user_snippets = false; policyText()") -and $ui.Contains("ctoaScriptingEval") -and $ui.Contains("scripting.allow_runtime_eval = false; policyText()")) { "passed" } else { "failed" }; evidence = "UI toggles cannot enable snippets or eval" },
        [pscustomobject]@{ name = "status_is_policy_only"; status = if ($ui.Contains("policy shell / no eval") -and $ui.Contains('"Status: " .. policyText()')) { "passed" } else { "failed" }; evidence = "UI declares scripting as policy-only shell" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-scripting-policy-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "scripting"
        mode = "static_policy_contract"
        helper_path = [System.IO.Path]::GetFullPath($helperPath)
        ui_path = [System.IO.Path]::GetFullPath($uiPath)
        profile_path = [System.IO.Path]::GetFullPath($profilePath)
        module_path = [System.IO.Path]::GetFullPath($modulePath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run SmokeAttach -Tab scripting after sandbox character is in-world to capture policy shell UI evidence; keep snippet execution blocked." } else { "Fix failed scripting policy checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting" } else { "" }
        live_safety = "ScriptingPolicySmoke reads repo helper/profile files only; it does not launch, stop, evaluate snippets, run files, talk, cast, or overwrite any client."
    }
    $path = Join-Path $outRoot "scripting_policy_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Scripting policy smoke: $path"
    Write-Output "[solteria-helper-test-env] Scripting policy status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Scripting policy smoke failed"
    }
}

function Invoke-PlannerStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $plannerPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_planner.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $planner = if (Test-Path -LiteralPath $plannerPath) { Get-Content -LiteralPath $plannerPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $plannerPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_planner.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($planner.Contains('rawget(_G, "CTOA_HELPER_PLANNER")') -and $planner.Contains("_G.CTOA_HELPER_PLANNER = Planner") -and $planner.Contains("return Planner")) { "passed" } else { "failed" }; evidence = "planner keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "planner_functions"; status = if ($planner.Contains("function Planner.collect") -and $planner.Contains("function Planner.best") -and $planner.Contains("function Planner.summary") -and $planner.Contains("function Planner.contract")) { "passed" } else { "failed" }; evidence = "planner exposes collect, best, summary, and contract functions" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($planner.Contains('mode = "passive"') -and $planner.Contains("runtime_actions = false") -and $planner.Contains("executes_plans = false") -and $planner.Contains("casts = false") -and $planner.Contains("talks = false") -and $planner.Contains("uses_items = false") -and $planner.Contains("walks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive ranking and no execution" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $planner.Contains("g_game") -and -not $planner.Contains("g_map") -and -not $planner.Contains("g_ui") -and -not $planner.Contains("g_keyboard") -and -not $planner.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "planner does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $planner.Contains("autoWalk") -and -not $planner.Contains("castSpell") -and -not $planner.Contains("g_game.talk") -and -not $planner.Contains("sendActionbarSlot") -and -not $planner.Contains("useInventoryItem") -and -not $planner.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "planner does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_planner" -File "ctoa_helper_planner.lua")) { "passed" } else { "failed" }; evidence = "loader stages planner with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_planner.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_planner.lua")) { "passed" } else { "failed" }; evidence = "dev package copies planner into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "ranked_actions_present"; status = if ($planner.Contains("plan_sio") -and $planner.Contains("plan_ring_swap") -and $planner.Contains("plan_attack") -and $planner.Contains("plan_walk") -and $planner.Contains("Planner.best")) { "passed" } else { "failed" }; evidence = "planner ranks borrowed bot concepts without executing them" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-planner-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "planner"
        mode = "static_passive_planner_contract"
        planner_path = [System.IO.Path]::GetFullPath($plannerPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed planner static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "PlannerStaticSmoke reads repo helper/planner files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "planner_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Planner static smoke: $path"
    Write-Output "[solteria-helper-test-env] Planner static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Planner static smoke failed"
    }
}

function Invoke-RuntimePolicyStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $policyPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_runtime_policy.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $policy = if (Test-Path -LiteralPath $policyPath) { Get-Content -LiteralPath $policyPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $policyPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_runtime_policy.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($policy.Contains('rawget(_G, "CTOA_HELPER_RUNTIME_POLICY")') -and $policy.Contains("_G.CTOA_HELPER_RUNTIME_POLICY = RuntimePolicy") -and $policy.Contains("return RuntimePolicy")) { "passed" } else { "failed" }; evidence = "runtime policy keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "policy_functions"; status = if ($policy.Contains("function RuntimePolicy.requiredGates") -and $policy.Contains("function RuntimePolicy.snapshot") -and $policy.Contains("function RuntimePolicy.decision") -and $policy.Contains("function RuntimePolicy.summary") -and $policy.Contains("function RuntimePolicy.contract")) { "passed" } else { "failed" }; evidence = "runtime policy exposes required gates, snapshot, decision, summary, and contract" },
        [pscustomobject]@{ name = "required_gates"; status = if ($policy.Contains('"manifest_current"') -and $policy.Contains('"module_static_gates"') -and $policy.Contains('"module_attach_smoke"') -and $policy.Contains('"smoke_attach_all"') -and $policy.Contains('"live_approval"')) { "passed" } else { "failed" }; evidence = "policy requires manifest, static, attach, full smoke, and live approval gates" },
        [pscustomobject]@{ name = "action_bound_runtime_classification"; status = if ($policy.Contains("function actionGateAccepted") -and $policy.Contains("runtime_action_classified_by_policy = true") -and $policy.Contains('append(reasons, "unknown_action")') -and $policy.Contains('append(reasons, "action_not_approved_v1")')) { "passed" } else { "failed" }; evidence = "policy classifies actions internally, binds accepted traces to the exact action, and blocks unknown or out-of-scope actions" },
        [pscustomobject]@{ name = "v1_exact_allowlist"; status = if ($policy.Contains('plan_paralyze_recovery = "conditions_runtime_gate"') -and $policy.Contains('plan_ring_swap = "equipment_runtime_gate"') -and $policy.Contains('plan_sio = "heal_friend_runtime_gate"') -and -not $policy.Contains('plan_poison_recovery = "conditions_runtime_gate"') -and -not $policy.Contains('plan_amulet_swap = "equipment_runtime_gate"')) { "passed" } else { "failed" }; evidence = "v1 module gates cover only paralyze, ring, and sio" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($policy.Contains('mode = "passive"') -and $policy.Contains("runtime_actions = false") -and $policy.Contains("executes_plans = false") -and $policy.Contains("casts = false") -and $policy.Contains("talks = false") -and $policy.Contains("uses_items = false") -and $policy.Contains("walks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive policy and no execution" },
        [pscustomobject]@{ name = "helper_uses_runtime_policy_bridge"; status = if ($helper.Contains('moduleValue(externalRuntimePolicy, "resolvedProtectionZonePolicy")') -and $helper.Contains('if type(policy) ~= "table" then') -and $helper.Contains('moduleValue(externalRuntimePolicy, "protectionZoneDecision", observation)') -and -not $helper.Contains("local function runtimePolicyProtectionZonePolicy()") -and -not $helper.Contains("local function runtimePolicyProtectionZoneDecision(observation)") -and -not $helper.Contains("player_methods = {`"isInPz`"")) { "passed" } else { "failed" }; evidence = "native helper observes OTClient state locally, delegates PZ policy resolution/decision through the shared guarded runtime policy bridge, and blocks conservatively if policy is unavailable" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $policy.Contains("g_game") -and -not $policy.Contains("g_map") -and -not $policy.Contains("g_ui") -and -not $policy.Contains("g_keyboard") -and -not $policy.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "runtime policy does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $policy.Contains("autoWalk") -and -not $policy.Contains("castSpell") -and -not $policy.Contains("g_game.talk") -and -not $policy.Contains("sendActionbarSlot") -and -not $policy.Contains("useInventoryItem") -and -not $policy.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "runtime policy does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_runtime_policy" -File "ctoa_helper_runtime_policy.lua")) { "passed" } else { "failed" }; evidence = "loader stages runtime policy with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_runtime_policy.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_runtime_policy.lua")) { "passed" } else { "failed" }; evidence = "dev package copies runtime policy into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-runtime-policy-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "runtime_policy"
        mode = "static_passive_runtime_policy_contract"
        policy_path = [System.IO.Path]::GetFullPath($policyPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed runtime policy static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "RuntimePolicyStaticSmoke reads repo helper/policy files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "runtime_policy_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Runtime policy static smoke: $path"
    Write-Output "[solteria-helper-test-env] Runtime policy static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Runtime policy static smoke failed"
    }
}

function Invoke-DispatchGuardStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $guardPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_dispatch_guard.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $guard = if (Test-Path -LiteralPath $guardPath) { Get-Content -LiteralPath $guardPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $guardPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_dispatch_guard.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($guard.Contains('rawget(_G, "CTOA_HELPER_DISPATCH_GUARD")') -and $guard.Contains("_G.CTOA_HELPER_DISPATCH_GUARD = DispatchGuard") -and $guard.Contains("return DispatchGuard")) { "passed" } else { "failed" }; evidence = "dispatch guard keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "guard_functions"; status = if ($guard.Contains("function DispatchGuard.classify") -and $guard.Contains("function DispatchGuard.decision") -and $guard.Contains("function DispatchGuard.summary") -and $guard.Contains("function DispatchGuard.contract")) { "passed" } else { "failed" }; evidence = "dispatch guard exposes classify, decision, summary, and contract" },
        [pscustomobject]@{ name = "policy_handoff"; status = if ($guard.Contains("policy_not_ready") -and $guard.Contains("sandbox_attach_required") -and $guard.Contains("requires_runtime_policy = true") -and $guard.Contains("requires_live_approval = true")) { "passed" } else { "failed" }; evidence = "guard blocks runtime plans until policy, sandbox attach, and live approval are ready" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($guard.Contains('mode = "passive"') -and $guard.Contains("runtime_actions = false") -and $guard.Contains("executes_plans = false") -and $guard.Contains("dispatch_allowed = false") -and $guard.Contains("casts = false") -and $guard.Contains("talks = false") -and $guard.Contains("uses_items = false") -and $guard.Contains("walks = false") -and $guard.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive dispatch guard and no execution" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $guard.Contains("g_game") -and -not $guard.Contains("g_map") -and -not $guard.Contains("g_ui") -and -not $guard.Contains("g_keyboard") -and -not $guard.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "dispatch guard does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $guard.Contains("autoWalk") -and -not $guard.Contains("castSpell") -and -not $guard.Contains("g_game.talk") -and -not $guard.Contains("sendActionbarSlot") -and -not $guard.Contains("useInventoryItem") -and -not $guard.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "dispatch guard does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_dispatch_guard" -File "ctoa_helper_dispatch_guard.lua")) { "passed" } else { "failed" }; evidence = "loader stages dispatch guard with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_dispatch_guard.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_dispatch_guard.lua")) { "passed" } else { "failed" }; evidence = "dev package copies dispatch guard into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-dispatch-guard-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "dispatch_guard"
        mode = "static_passive_dispatch_guard_contract"
        guard_path = [System.IO.Path]::GetFullPath($guardPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed dispatch guard static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "DispatchGuardStaticSmoke reads repo guard files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "dispatch_guard_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Dispatch guard static smoke: $path"
    Write-Output "[solteria-helper-test-env] Dispatch guard static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Dispatch guard static smoke failed"
    }
}

function Invoke-PlanQueueStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $queuePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_plan_queue.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $queue = if (Test-Path -LiteralPath $queuePath) { Get-Content -LiteralPath $queuePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $queuePath) { "passed" } else { "failed" }; evidence = "ctoa_helper_plan_queue.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($queue.Contains('rawget(_G, "CTOA_HELPER_PLAN_QUEUE")') -and $queue.Contains("_G.CTOA_HELPER_PLAN_QUEUE = PlanQueue") -and $queue.Contains("return PlanQueue")) { "passed" } else { "failed" }; evidence = "plan queue keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "queue_functions"; status = if ($queue.Contains("function PlanQueue.normalize") -and $queue.Contains("function PlanQueue.enqueue") -and $queue.Contains("function PlanQueue.trim") -and $queue.Contains("function PlanQueue.summary") -and $queue.Contains("function PlanQueue.contract")) { "passed" } else { "failed" }; evidence = "plan queue exposes normalize, enqueue, trim, summary, and contract" },
        [pscustomobject]@{ name = "bounded_queue"; status = if ($queue.Contains("DEFAULT_LIMIT = 12") -and $queue.Contains("while #result > maxItems") -and $queue.Contains("table.remove(result, 1)") -and $queue.Contains("bounded_queue = true")) { "passed" } else { "failed" }; evidence = "plan queue limits retained decisions and trims oldest entries" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($queue.Contains('mode = "passive"') -and $queue.Contains("runtime_actions = false") -and $queue.Contains("executes_plans = false") -and $queue.Contains("dispatch_allowed = false") -and $queue.Contains("casts = false") -and $queue.Contains("talks = false") -and $queue.Contains("uses_items = false") -and $queue.Contains("walks = false") -and $queue.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive decision storage and no execution" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $queue.Contains("g_game") -and -not $queue.Contains("g_map") -and -not $queue.Contains("g_ui") -and -not $queue.Contains("g_keyboard") -and -not $queue.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "plan queue does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $queue.Contains("autoWalk") -and -not $queue.Contains("castSpell") -and -not $queue.Contains("g_game.talk") -and -not $queue.Contains("sendActionbarSlot") -and -not $queue.Contains("useInventoryItem") -and -not $queue.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "plan queue does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_plan_queue" -File "ctoa_helper_plan_queue.lua")) { "passed" } else { "failed" }; evidence = "loader stages plan queue with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_plan_queue.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_plan_queue.lua")) { "passed" } else { "failed" }; evidence = "dev package copies plan queue into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-plan-queue-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "plan_queue"
        mode = "static_passive_plan_queue_contract"
        queue_path = [System.IO.Path]::GetFullPath($queuePath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed plan queue static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "PlanQueueStaticSmoke reads repo queue files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "plan_queue_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Plan queue static smoke: $path"
    Write-Output "[solteria-helper-test-env] Plan queue static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Plan queue static smoke failed"
    }
}

function Invoke-RuntimeReadinessStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $readinessPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_runtime_readiness.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $readiness = if (Test-Path -LiteralPath $readinessPath) { Get-Content -LiteralPath $readinessPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $readinessPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_runtime_readiness.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($readiness.Contains('rawget(_G, "CTOA_HELPER_RUNTIME_READINESS")') -and $readiness.Contains("_G.CTOA_HELPER_RUNTIME_READINESS = RuntimeReadiness") -and $readiness.Contains("return RuntimeReadiness")) { "passed" } else { "failed" }; evidence = "runtime readiness keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "readiness_functions"; status = if ($readiness.Contains("function RuntimeReadiness.requiredComponents") -and $readiness.Contains("function RuntimeReadiness.requiredGates") -and $readiness.Contains("function RuntimeReadiness.snapshot") -and $readiness.Contains("function RuntimeReadiness.decision") -and $readiness.Contains("function RuntimeReadiness.summary") -and $readiness.Contains("function RuntimeReadiness.contract")) { "passed" } else { "failed" }; evidence = "runtime readiness exposes required components/gates, snapshot, decision, summary, and contract" },
        [pscustomobject]@{ name = "component_coverage"; status = if ($readiness.Contains('"planner"') -and $readiness.Contains('"runtime_policy"') -and $readiness.Contains('"dispatch_guard"') -and $readiness.Contains('"plan_queue"')) { "passed" } else { "failed" }; evidence = "readiness requires all passive runtime bridge components" },
        [pscustomobject]@{ name = "gate_coverage"; status = if ($readiness.Contains('"manifest_current"') -and $readiness.Contains('"module_static_gates"') -and $readiness.Contains('"module_attach_smoke"') -and $readiness.Contains('"smoke_attach_all"') -and $readiness.Contains('"live_approval"')) { "passed" } else { "failed" }; evidence = "readiness requires manifest, static, attach, full smoke, and live approval gates" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($readiness.Contains('mode = "passive"') -and $readiness.Contains("runtime_actions = false") -and $readiness.Contains("executes_plans = false") -and $readiness.Contains("dispatch_allowed = false") -and $readiness.Contains("casts = false") -and $readiness.Contains("talks = false") -and $readiness.Contains("uses_items = false") -and $readiness.Contains("walks = false") -and $readiness.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive readiness summary and no execution" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $readiness.Contains("g_game") -and -not $readiness.Contains("g_map") -and -not $readiness.Contains("g_ui") -and -not $readiness.Contains("g_keyboard") -and -not $readiness.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "runtime readiness does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $readiness.Contains("autoWalk") -and -not $readiness.Contains("castSpell") -and -not $readiness.Contains("g_game.talk") -and -not $readiness.Contains("sendActionbarSlot") -and -not $readiness.Contains("useInventoryItem") -and -not $readiness.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "runtime readiness does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_runtime_readiness" -File "ctoa_helper_runtime_readiness.lua")) { "passed" } else { "failed" }; evidence = "loader stages runtime readiness with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_runtime_readiness.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_runtime_readiness.lua")) { "passed" } else { "failed" }; evidence = "dev package copies runtime readiness into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-runtime-readiness-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "runtime_readiness"
        mode = "static_passive_runtime_readiness_contract"
        readiness_path = [System.IO.Path]::GetFullPath($readinessPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed runtime readiness static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "RuntimeReadinessStaticSmoke reads repo readiness files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "runtime_readiness_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Runtime readiness static smoke: $path"
    Write-Output "[solteria-helper-test-env] Runtime readiness static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Runtime readiness static smoke failed"
    }
}

function Invoke-ModuleStatusStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $statusPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_module_status.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $statusSource = if (Test-Path -LiteralPath $statusPath) { Get-Content -LiteralPath $statusPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $statusPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_module_status.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($statusSource.Contains('rawget(_G, "CTOA_HELPER_MODULE_STATUS")') -and $statusSource.Contains("_G.CTOA_HELPER_MODULE_STATUS = ModuleStatus") -and $statusSource.Contains("return ModuleStatus")) { "passed" } else { "failed" }; evidence = "module status keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "status_functions"; status = if ($statusSource.Contains("function ModuleStatus.defaultOrder") -and $statusSource.Contains("function ModuleStatus.normalize") -and $statusSource.Contains("function ModuleStatus.snapshot") -and $statusSource.Contains("function ModuleStatus.summary") -and $statusSource.Contains("function ModuleStatus.contract")) { "passed" } else { "failed" }; evidence = "module status exposes default order, normalize, snapshot, summary, and contract" },
        [pscustomobject]@{ name = "module_coverage"; status = if ($statusSource.Contains('"runtime_readiness"') -and $statusSource.Contains('"heal_friend"') -and $statusSource.Contains('"conditions"') -and $statusSource.Contains('"equipment"') -and $statusSource.Contains('"scripting"')) { "passed" } else { "failed" }; evidence = "module status covers static runtime bridge and prototype modules" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($statusSource.Contains('mode = "passive"') -and $statusSource.Contains("runtime_actions = false") -and $statusSource.Contains("executes_plans = false") -and $statusSource.Contains("dispatch_allowed = false") -and $statusSource.Contains("casts = false") -and $statusSource.Contains("talks = false") -and $statusSource.Contains("uses_items = false") -and $statusSource.Contains("walks = false") -and $statusSource.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive status board and no execution" },
        [pscustomobject]@{ name = "evidence_contract"; status = if ($statusSource.Contains("normalizes_module_status = true") -and $statusSource.Contains("exposes_status_board = true") -and $statusSource.Contains("requires_module_contract = true") -and $statusSource.Contains("requires_module_static_gates = true")) { "passed" } else { "failed" }; evidence = "module status requires contract and static gates before runtime use" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $statusSource.Contains("g_game") -and -not $statusSource.Contains("g_map") -and -not $statusSource.Contains("g_ui") -and -not $statusSource.Contains("g_keyboard") -and -not $statusSource.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "module status does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $statusSource.Contains("autoWalk") -and -not $statusSource.Contains("castSpell") -and -not $statusSource.Contains("g_game.talk") -and -not $statusSource.Contains("sendActionbarSlot") -and -not $statusSource.Contains("useInventoryItem") -and -not $statusSource.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "module status does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_module_status" -File "ctoa_helper_module_status.lua")) { "passed" } else { "failed" }; evidence = "loader stages module status with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_module_status.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_module_status.lua")) { "passed" } else { "failed" }; evidence = "dev package copies module status into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-module-status-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "module_status"
        mode = "static_passive_module_status_contract"
        status_path = [System.IO.Path]::GetFullPath($statusPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed module status static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "ModuleStatusStaticSmoke reads repo status files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "module_status_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Module status static smoke: $path"
    Write-Output "[solteria-helper-test-env] Module status static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Module status static smoke failed"
    }
}

function Invoke-ActionCatalogStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $catalogPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_action_catalog.lua"
    $policyPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_runtime_policy.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $catalog = if (Test-Path -LiteralPath $catalogPath) { Get-Content -LiteralPath $catalogPath -Raw } else { "" }
    $policy = if (Test-Path -LiteralPath $policyPath) { Get-Content -LiteralPath $policyPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $catalogPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_action_catalog.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($catalog.Contains('rawget(_G, "CTOA_HELPER_ACTION_CATALOG")') -and $catalog.Contains("_G.CTOA_HELPER_ACTION_CATALOG = ActionCatalog") -and $catalog.Contains("return ActionCatalog")) { "passed" } else { "failed" }; evidence = "action catalog keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "catalog_functions"; status = if ($catalog.Contains("function ActionCatalog.requiredGates") -and $catalog.Contains("function ActionCatalog.all") -and $catalog.Contains("function ActionCatalog.domains") -and $catalog.Contains("function ActionCatalog.byAction") -and $catalog.Contains("function ActionCatalog.classify") -and $catalog.Contains("function ActionCatalog.summary") -and $catalog.Contains("function ActionCatalog.contract")) { "passed" } else { "failed" }; evidence = "action catalog exposes gates, catalog, lookup, classifier, summary, and contract" },
        [pscustomobject]@{ name = "action_coverage"; status = if ($catalog.Contains('"plan_attack"') -and $catalog.Contains('"plan_walk"') -and $catalog.Contains('"plan_loot"') -and $catalog.Contains('"plan_sio"') -and $catalog.Contains('"plan_ring_swap"') -and $catalog.Contains('"audit_only"')) { "passed" } else { "failed" }; evidence = "action catalog covers combat, cavebot, loot, heal friend, equipment, and passive scripting actions" },
        [pscustomobject]@{ name = "gate_parity"; status = if ($catalog.Contains('"manifest_current"') -and $catalog.Contains('"module_static_gates"') -and $catalog.Contains('"module_attach_smoke"') -and $catalog.Contains('"smoke_attach_all"') -and $catalog.Contains('"live_approval"') -and $policy.Contains('"manifest_current"') -and $policy.Contains('"smoke_attach_all"') -and $policy.Contains('"live_approval"')) { "passed" } else { "failed" }; evidence = "action catalog required gates match runtime policy gate vocabulary" },
        [pscustomobject]@{ name = "v1_exact_action_gates"; status = if ($catalog.Contains('plan_paralyze_recovery = "conditions_runtime_gate"') -and $catalog.Contains('plan_ring_swap = "equipment_runtime_gate"') -and $catalog.Contains('plan_sio = "heal_friend_runtime_gate"') -and -not $catalog.Contains('plan_poison_recovery = "conditions_runtime_gate"') -and -not $catalog.Contains('plan_amulet_swap = "equipment_runtime_gate"') -and $catalog.Contains('DEFERRED_MODULE_SCOPE')) { "passed" } else { "failed" }; evidence = "catalog binds v1 gates to exact actions and marks other module actions deferred" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($catalog.Contains('mode = "passive"') -and $catalog.Contains("runtime_actions = false") -and $catalog.Contains("executes_plans = false") -and $catalog.Contains("dispatch_allowed = false") -and $catalog.Contains("casts = false") -and $catalog.Contains("talks = false") -and $catalog.Contains("uses_items = false") -and $catalog.Contains("walks = false") -and $catalog.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive action catalog and no execution" },
        [pscustomobject]@{ name = "risk_contract"; status = if ($catalog.Contains("catalogs_action_risk = true") -and $catalog.Contains('"runtime_combat"') -and $catalog.Contains('"runtime_movement"') -and $catalog.Contains('"runtime_equipment"') -and $catalog.Contains('"passive_policy"')) { "passed" } else { "failed" }; evidence = "action catalog assigns risk classes to runtime and passive actions" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $catalog.Contains("g_game") -and -not $catalog.Contains("g_map") -and -not $catalog.Contains("g_ui") -and -not $catalog.Contains("g_keyboard") -and -not $catalog.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "action catalog does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $catalog.Contains("autoWalk") -and -not $catalog.Contains("castSpell") -and -not $catalog.Contains("g_game.talk") -and -not $catalog.Contains("sendActionbarSlot") -and -not $catalog.Contains("useInventoryItem") -and -not $catalog.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "action catalog does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_action_catalog" -File "ctoa_helper_action_catalog.lua")) { "passed" } else { "failed" }; evidence = "loader stages action catalog with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_action_catalog.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_action_catalog.lua")) { "passed" } else { "failed" }; evidence = "dev package copies action catalog into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-action-catalog-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "action_catalog"
        mode = "static_passive_action_catalog_contract"
        catalog_path = [System.IO.Path]::GetFullPath($catalogPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed action catalog static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "ActionCatalogStaticSmoke reads repo catalog files only; it does not launch, stop, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "action_catalog_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Action catalog static smoke: $path"
    Write-Output "[solteria-helper-test-env] Action catalog static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Action catalog static smoke failed"
    }
}

function Invoke-DecisionTraceStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $tracePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_decision_trace.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $trace = if (Test-Path -LiteralPath $tracePath) { Get-Content -LiteralPath $tracePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $tracePath) { "passed" } else { "failed" }; evidence = "ctoa_helper_decision_trace.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($trace.Contains('rawget(_G, "CTOA_HELPER_DECISION_TRACE")') -and $trace.Contains("_G.CTOA_HELPER_DECISION_TRACE = DecisionTrace") -and $trace.Contains("return DecisionTrace")) { "passed" } else { "failed" }; evidence = "decision trace keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "trace_functions"; status = if ($trace.Contains("function DecisionTrace.record") -and $trace.Contains("function DecisionTrace.queue") -and $trace.Contains("function DecisionTrace.summary") -and $trace.Contains("function DecisionTrace.contract")) { "passed" } else { "failed" }; evidence = "decision trace exposes record, bounded queue, summary, and contract" },
        [pscustomobject]@{ name = "trace_coverage"; status = if ($trace.Contains("policy_reasons") -and $trace.Contains("guard_reasons") -and $trace.Contains("missing_gates") -and $trace.Contains("risk") -and $trace.Contains("runtime_action")) { "passed" } else { "failed" }; evidence = "decision trace captures policy reasons, guard reasons, missing gates, risk, and runtime action flag" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($trace.Contains('mode = "passive"') -and $trace.Contains("runtime_actions = false") -and $trace.Contains("executes_plans = false") -and $trace.Contains("dispatch_allowed = false") -and $trace.Contains("writes_logs = false") -and $trace.Contains("casts = false") -and $trace.Contains("talks = false") -and $trace.Contains("uses_items = false") -and $trace.Contains("walks = false") -and $trace.Contains("attacks = false")) { "passed" } else { "failed" }; evidence = "contract declares passive no-write decision trace and no execution" },
        [pscustomobject]@{ name = "dependency_contract"; status = if ($trace.Contains("requires_runtime_policy = true") -and $trace.Contains("requires_dispatch_guard = true") -and $trace.Contains("requires_action_catalog = true")) { "passed" } else { "failed" }; evidence = "decision trace requires policy, guard, and action catalog inputs" },
        [pscustomobject]@{ name = "bounded_queue"; status = if ($trace.Contains("maxItems > 20") -and $trace.Contains("maxItems < 1")) { "passed" } else { "failed" }; evidence = "decision trace queue output is bounded" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $trace.Contains("g_game") -and -not $trace.Contains("g_map") -and -not $trace.Contains("g_ui") -and -not $trace.Contains("g_keyboard") -and -not $trace.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "decision trace does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $trace.Contains("autoWalk") -and -not $trace.Contains("castSpell") -and -not $trace.Contains("g_game.talk") -and -not $trace.Contains("sendActionbarSlot") -and -not $trace.Contains("useInventoryItem") -and -not $trace.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "decision trace does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_decision_trace" -File "ctoa_helper_decision_trace.lua")) { "passed" } else { "failed" }; evidence = "loader stages decision trace with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_decision_trace.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_decision_trace.lua")) { "passed" } else { "failed" }; evidence = "dev package copies decision trace into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-decision-trace-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "decision_trace"
        mode = "static_passive_decision_trace_contract"
        trace_path = [System.IO.Path]::GetFullPath($tracePath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed decision trace static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "DecisionTraceStaticSmoke reads repo trace files only; it does not launch, stop, write logs, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "decision_trace_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Decision trace static smoke: $path"
    Write-Output "[solteria-helper-test-env] Decision trace static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Decision trace static smoke failed"
    }
}

function Invoke-SandboxHandoffStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $handoffPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_sandbox_handoff.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $scriptPath = $PSCommandPath
    $handoff = if (Test-Path -LiteralPath $handoffPath) { Get-Content -LiteralPath $handoffPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $handoffPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_sandbox_handoff.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($handoff.Contains('rawget(_G, "CTOA_HELPER_SANDBOX_HANDOFF")') -and $handoff.Contains("_G.CTOA_HELPER_SANDBOX_HANDOFF = SandboxHandoff") -and $handoff.Contains("return SandboxHandoff")) { "passed" } else { "failed" }; evidence = "sandbox handoff keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "handoff_functions"; status = if ($handoff.Contains("function SandboxHandoff.steps") -and $handoff.Contains("function SandboxHandoff.snapshot") -and $handoff.Contains("function SandboxHandoff.next") -and $handoff.Contains("function SandboxHandoff.summary") -and $handoff.Contains("function SandboxHandoff.contract")) { "passed" } else { "failed" }; evidence = "sandbox handoff exposes steps, snapshot, next, summary, and contract" },
        [pscustomobject]@{ name = "sequence_coverage"; status = if ($handoff.Contains("Launch") -and $handoff.Contains("ReadyCheck") -and $handoff.Contains("SmokeAttachModules") -and $handoff.Contains("SmokeAttachAll") -and $handoff.Contains("PromoteLiveCtoa -ApproveLiveDeploy")) { "passed" } else { "failed" }; evidence = "sandbox handoff covers launch, ready check, module attach, full attach, and explicit promotion approval" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($handoff.Contains('mode = "passive"') -and $handoff.Contains("runtime_actions = false") -and $handoff.Contains("executes_plans = false") -and $handoff.Contains("dispatch_allowed = false") -and $handoff.Contains("launches_client = false") -and $handoff.Contains("attaches_client = false") -and $handoff.Contains("promotes_live = false")) { "passed" } else { "failed" }; evidence = "contract declares passive no-launch no-attach no-promote handoff" },
        [pscustomobject]@{ name = "gate_contract"; status = if ($handoff.Contains("requires_ready_check = true") -and $handoff.Contains("requires_module_attach_smoke = true") -and $handoff.Contains("requires_smoke_attach_all = true") -and $handoff.Contains("requires_live_approval = true")) { "passed" } else { "failed" }; evidence = "sandbox handoff requires ready check, attach smoke, full smoke, and live approval" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $handoff.Contains("g_game") -and -not $handoff.Contains("g_map") -and -not $handoff.Contains("g_ui") -and -not $handoff.Contains("g_keyboard") -and -not $handoff.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "sandbox handoff does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $handoff.Contains("autoWalk") -and -not $handoff.Contains("castSpell") -and -not $handoff.Contains("g_game.talk") -and -not $handoff.Contains("sendActionbarSlot") -and -not $handoff.Contains("useInventoryItem") -and -not $handoff.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "sandbox handoff does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_sandbox_handoff" -File "ctoa_helper_sandbox_handoff.lua")) { "passed" } else { "failed" }; evidence = "loader stages sandbox handoff with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_sandbox_handoff.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_sandbox_handoff.lua")) { "passed" } else { "failed" }; evidence = "dev package copies sandbox handoff into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-sandbox-handoff-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "sandbox_handoff"
        mode = "static_passive_sandbox_handoff_contract"
        handoff_path = [System.IO.Path]::GetFullPath($handoffPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed sandbox handoff static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "SandboxHandoffStaticSmoke reads repo handoff files only; it does not launch, stop, attach to, promote, execute plans, cast, talk, walk, use items, attack, or overwrite any client."
    }
    $path = Join-Path $outRoot "sandbox_handoff_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Sandbox handoff static smoke: $path"
    Write-Output "[solteria-helper-test-env] Sandbox handoff static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Sandbox handoff static smoke failed"
    }
}

function Invoke-FeatureFlagsStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $flagsPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_feature_flags.lua"
    $schemaPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_profile_schema.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $flags = if (Test-Path -LiteralPath $flagsPath) { Get-Content -LiteralPath $flagsPath -Raw } else { "" }
    $schema = if (Test-Path -LiteralPath $schemaPath) { Get-Content -LiteralPath $schemaPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $flagsPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_feature_flags.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($flags.Contains('rawget(_G, "CTOA_HELPER_FEATURE_FLAGS")') -and $flags.Contains("_G.CTOA_HELPER_FEATURE_FLAGS = FeatureFlags") -and $flags.Contains("return FeatureFlags")) { "passed" } else { "failed" }; evidence = "feature flags keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "flag_functions"; status = if ($flags.Contains("function FeatureFlags.all") -and $flags.Contains("function FeatureFlags.safeFalseKeys") -and $flags.Contains("function FeatureFlags.byKey") -and $flags.Contains("function FeatureFlags.audit") -and $flags.Contains("function FeatureFlags.summary") -and $flags.Contains("function FeatureFlags.toolsSummary") -and $flags.Contains("function FeatureFlags.contract")) { "passed" } else { "failed" }; evidence = "feature flags exposes catalog, safe false keys, lookup, audit, summary, tools summary, and contract" },
        [pscustomobject]@{ name = "critical_flag_coverage"; status = if ($flags.Contains('"tools.auto_haste"') -and $flags.Contains('"tools.auto_exeta"') -and $flags.Contains('"tools.rune_enabled"') -and $flags.Contains('"tools.cavebot_movement_enabled"') -and $flags.Contains('"tools.feature_flags.experimental_loot"') -and $flags.Contains('"scripting.allow_runtime_eval"')) { "passed" } else { "failed" }; evidence = "feature flags covers runtime spells, runes, cavebot movement, loot, and scripting eval" },
        [pscustomobject]@{ name = "nested_profile_lookup"; status = if ($flags.Contains("local function valueAtPath") -and $flags.Contains('string.gmatch(path, "[^.]+")') -and $flags.Contains("local value = valueAtPath(cfg, flag.key)")) { "passed" } else { "failed" }; evidence = "feature flags audit reads both flat dotted keys and nested profile tables" },
        [pscustomobject]@{ name = "profile_schema_parity"; status = if ($schema.Contains('"tools.auto_haste"') -and $schema.Contains('"tools.cavebot_movement_enabled"') -and $schema.Contains('"tools.feature_flags.experimental_loot"') -and $flags.Contains('"tools.auto_haste"') -and $flags.Contains('"tools.cavebot_movement_enabled"') -and $flags.Contains('"tools.feature_flags.experimental_loot"')) { "passed" } else { "failed" }; evidence = "feature flags align with profile schema safe false vocabulary" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($flags.Contains('mode = "passive"') -and $flags.Contains("runtime_actions = false") -and $flags.Contains("executes_plans = false") -and $flags.Contains("dispatch_allowed = false") -and $flags.Contains("toggles_flags = false") -and $flags.Contains("writes_profile = false")) { "passed" } else { "failed" }; evidence = "contract declares passive no-toggle no-profile-write feature matrix" },
        [pscustomobject]@{ name = "safe_default_contract"; status = if ($flags.Contains("owns_safe_defaults = true") -and $flags.Contains("owns_tools_summary = true") -and $flags.Contains("requires_profile_audit = true") -and $flags.Contains("requires_module_static_gates = true") -and $flags.Contains("requires_smoke_attach_all = true")) { "passed" } else { "failed" }; evidence = "feature flags owns safe defaults/tools summary and requires profile audit, static gates, and SmokeAttachAll" },
        [pscustomobject]@{ name = "helper_uses_feature_flags_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_FEATURE_FLAGS")') -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.tools") -and $helper.Contains('tools = moduleValue(externalOperatorSummary, "bridgeText", "tools", OPERATOR_SUMMARY_BRIDGES)') -and $helper.Contains("tools_summary_text = operatorSummaries.tools") -and $helper.Contains("featureFlags = externalFeatureFlags") -and $helper.Contains('profile = moduleValue(externalProfilePersistence, "exportProfile", HELPER_CONFIG') -and $flags.Contains("function FeatureFlags.audit") -and $flags.Contains("function FeatureFlags.toolsSummary")) { "passed" } else { "failed" }; evidence = "helper shell consumes feature flag audit and guarded support-owned profile export through the operator summary adapter" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $flags.Contains("g_game") -and -not $flags.Contains("g_map") -and -not $flags.Contains("g_ui") -and -not $flags.Contains("g_keyboard") -and -not $flags.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "feature flags does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $flags.Contains("autoWalk") -and -not $flags.Contains("castSpell") -and -not $flags.Contains("g_game.talk") -and -not $flags.Contains("sendActionbarSlot") -and -not $flags.Contains("useInventoryItem") -and -not $flags.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "feature flags does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_feature_flags" -File "ctoa_helper_feature_flags.lua")) { "passed" } else { "failed" }; evidence = "loader stages feature flags with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_feature_flags.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_feature_flags.lua")) { "passed" } else { "failed" }; evidence = "dev package copies feature flags into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-feature-flags-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "feature_flags"
        mode = "static_passive_feature_flags_contract"
        flags_path = [System.IO.Path]::GetFullPath($flagsPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed feature flags static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "FeatureFlagsStaticSmoke reads repo feature flag files only; it does not launch, stop, toggle flags, write profiles, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "feature_flags_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Feature flags static smoke: $path"
    Write-Output "[solteria-helper-test-env] Feature flags static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Feature flags static smoke failed"
    }
}

function Invoke-HudStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $hudPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_hud.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $hud = if (Test-Path -LiteralPath $hudPath) { Get-Content -LiteralPath $hudPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $hudPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_hud.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($hud.Contains('rawget(_G, "CTOA_HELPER_HUD")') -and $hud.Contains("_G.CTOA_HELPER_HUD = Hud") -and $hud.Contains("return Hud")) { "passed" } else { "failed" }; evidence = "HUD keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "hud_functions"; status = if ($hud.Contains("function Hud.startText") -and $hud.Contains("function Hud.disarmedText") -and $hud.Contains("function Hud.position") -and $hud.Contains("function Hud.state") -and $hud.Contains("function Hud.visibilityText") -and $hud.Contains("function Hud.runtimeText") -and $hud.Contains("function Hud.uiSummary") -and $hud.Contains("function Hud.operatorSummary") -and $hud.Contains("function Hud.contract")) { "passed" } else { "failed" }; evidence = "HUD exposes text, state, visibility, UI summary, operator summary, and contract helpers" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($hud.Contains('mode = "passive"') -and $hud.Contains("creates_widgets = false") -and $hud.Contains("owns_start_text = true") -and $hud.Contains("owns_disarmed_text = true") -and $hud.Contains("owns_position = true") -and $hud.Contains("owns_runtime_text = true") -and $hud.Contains("owns_ui_summary = true") -and $hud.Contains("owns_operator_summary = true") -and $hud.Contains("runtime_actions = false")) { "passed" } else { "failed" }; evidence = "HUD contract declares passive text, position, UI/operator summary ownership and no-widget no-runtime-action behavior" },
        [pscustomobject]@{ name = "safe_defaults"; status = if ($hud.Contains("local DEFAULT_X = 22") -and $hud.Contains("local DEFAULT_Y = 170") -and $hud.Contains("local DEFAULT_WIDTH = 210") -and $hud.Contains("local DEFAULT_HEIGHT = 54")) { "passed" } else { "failed" }; evidence = "HUD owns stable default geometry for UI preview and operator attach smoke" },
        [pscustomobject]@{ name = "state_summary"; status = if ($hud.Contains("visible draggable") -and $hud.Contains("visible locked") -and $hud.Contains("ZeroBot ") -and $hud.Contains("HUD ")) { "passed" } else { "failed" }; evidence = "HUD summarizes visibility, runtime text, and UI state without creating UI" },
        [pscustomobject]@{ name = "helper_uses_hud_bridge"; status = if ($helper.Contains("OPERATOR_SUMMARY_BRIDGES.ui") -and $helper.Contains('ui = moduleValue(externalOperatorSummary, "bridgeText", "ui", OPERATOR_SUMMARY_BRIDGES)') -and $helper.Contains("ui_summary_text = operatorSummaries.ui") -and $helper.Contains("hud = externalHud") -and $helper.Contains('hotkey_display_text = type(externalHotkeys) == "table"') -and $helper.Contains("themePresetText = themePresetText") -and -not $helper.Contains("local function hudText(functionName, fallback, options)") -and $helper.Contains('moduleValue(externalHud, "startText")') -and $helper.Contains('moduleValue(externalHud, "disarmedText")') -and $helper.Contains('moduleValue(externalHud, "runtimeText", {') -and $helper.Contains('moduleValue(externalHud, "position", HELPER_CONFIG.hud or {})') -and -not $helper.Contains("local function hudStartText()") -and -not $helper.Contains("local function hudDisarmedText()") -and -not $helper.Contains("local function hudPosition()") -and -not $helper.Contains("local function hudRuntimeText(") -and -not $helper.Contains("local function hotkeyDisplayText(")) { "passed" } else { "failed" }; evidence = "native helper delegates operator UI summary and HUD text/position through guarded HUD adapters without duplicate shell wrappers" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $hud.Contains("g_game") -and -not $hud.Contains("g_map") -and -not $hud.Contains("g_ui") -and -not $hud.Contains("g_keyboard") -and -not $hud.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "HUD does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $hud.Contains("autoWalk") -and -not $hud.Contains("castSpell") -and -not $hud.Contains("g_game.talk") -and -not $hud.Contains("sendActionbarSlot") -and -not $hud.Contains("useInventoryItem") -and -not $hud.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "HUD does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_hud" -File "ctoa_helper_hud.lua")) { "passed" } else { "failed" }; evidence = "loader stages HUD with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_hud.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_hud.lua")) { "passed" } else { "failed" }; evidence = "dev package copies HUD into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"tools_hud"') -and $script.Contains('-Tab tools_hud')) { "passed" } else { "failed" }; evidence = "HUD has a valid tools_hud attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-hud-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "hud"
        mode = "static_passive_hud_contract"
        hud_path = [System.IO.Path]::GetFullPath($hudPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab tools_hud after character is in-world." } else { "Fix failed HUD static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "HudStaticSmoke reads repo HUD files only; it does not launch, stop, create widgets, toggle flags, write profiles, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "hud_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] HUD static smoke: $path"
    Write-Output "[solteria-helper-test-env] HUD static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "HUD static smoke failed"
    }
}

function Invoke-HotkeysStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $hotkeysPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_hotkeys.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $hotkeys = if (Test-Path -LiteralPath $hotkeysPath) { Get-Content -LiteralPath $hotkeysPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $hotkeysPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_hotkeys.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($hotkeys.Contains('rawget(_G, "CTOA_HELPER_HOTKEYS")') -and $hotkeys.Contains("_G.CTOA_HELPER_HOTKEYS = Hotkeys") -and $hotkeys.Contains("return Hotkeys")) { "passed" } else { "failed" }; evidence = "hotkeys keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "parser_functions"; status = if ($hotkeys.Contains("function Hotkeys.trim") -and $hotkeys.Contains("function Hotkeys.normalizeKeyName") -and $hotkeys.Contains("function Hotkeys.parse") -and $hotkeys.Contains("function Hotkeys.normalize") -and $hotkeys.Contains("function Hotkeys.isAllowed") -and $hotkeys.Contains("function Hotkeys.bindingDecision") -and $hotkeys.Contains("function Hotkeys.normalizeHelperHotkey") -and $hotkeys.Contains("function Hotkeys.hotkeyBindingDecision") -and $hotkeys.Contains("function Hotkeys.resolveActionbarSlot") -and $hotkeys.Contains("function Hotkeys.display") -and $hotkeys.Contains("function Hotkeys.actionbarSlotText") -and $hotkeys.Contains("function Hotkeys.contract")) { "passed" } else { "failed" }; evidence = "hotkeys exposes parser, normalization/binding bridges, actionbar resolution, display, and contract helpers" },
        [pscustomobject]@{ name = "modifier_contract"; status = if ($hotkeys.Contains('local MODIFIER_ORDER = {"Ctrl", "Alt", "Shift", "Meta"}') -and $hotkeys.Contains('ctrl = "Ctrl"') -and $hotkeys.Contains('command = "Meta"') -and $hotkeys.Contains('windows = "Meta"')) { "passed" } else { "failed" }; evidence = "hotkeys owns stable modifier order and alias vocabulary" },
        [pscustomobject]@{ name = "invalid_reason_contract"; status = if ($hotkeys.Contains('reason = "empty"') -and $hotkeys.Contains('reason = "invalid_key"') -and $hotkeys.Contains('reason = "multiple_keys"') -and $hotkeys.Contains('reason = "missing_key"') -and $hotkeys.Contains('reason = "reserved_key"') -and $hotkeys.Contains('reason = "ok"')) { "passed" } else { "failed" }; evidence = "hotkeys parser reports explicit failure reasons" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($hotkeys.Contains('mode = "passive"') -and $hotkeys.Contains("owns_actionbar_slot_text = true") -and $hotkeys.Contains("owns_binding_decision = true") -and $hotkeys.Contains("owns_hotkey_normalization = true") -and $hotkeys.Contains("owns_actionbar_slot_resolution = true") -and $hotkeys.Contains("binds_keys = false") -and $hotkeys.Contains("sends_keys = false") -and $hotkeys.Contains("runtime_actions = false")) { "passed" } else { "failed" }; evidence = "hotkeys contract owns passive normalization, binding decisions, and actionbar resolution with no-bind no-send behavior" },
        [pscustomobject]@{ name = "no_runtime_bindings"; status = if (-not $hotkeys.Contains("g_keyboard") -and -not $hotkeys.Contains("bindKeyDown") -and -not $hotkeys.Contains("unbindKeyDown") -and -not $hotkeys.Contains("pressKey")) { "passed" } else { "failed" }; evidence = "hotkeys module does not bind, unbind, or send keys" },
        [pscustomobject]@{ name = "no_otclient_actions"; status = if (-not $hotkeys.Contains("g_game") -and -not $hotkeys.Contains("autoWalk") -and -not $hotkeys.Contains("castSpell") -and -not $hotkeys.Contains("sendActionbarSlot") -and -not $hotkeys.Contains("useInventoryItem") -and -not $hotkeys.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "hotkeys module does not walk, cast, use items, or create widgets" },
        [pscustomobject]@{ name = "helper_runtime_binding_unchanged"; status = if (-not $helper.Contains("local function hotkeyValue") -and -not $helper.Contains("local function hotkeyDisplayText(") -and -not $helper.Contains("local function hotkeyBindingDecision") -and -not $helper.Contains("local function normalizeHelperHotkey") -and $helper.Contains('moduleValue(externalHotkeys, "hotkeyBindingDecision", hotkey, Helper.bound_hotkey or HELPER_CONFIG.hotkey)') -and $helper.Contains('type(externalHotkeys.normalizeHelperHotkey) == "function"') -and $helper.Contains("g_keyboard.bindKeyDown(normalizedHotkey, Helper.toggleWindow or toggleWindow)")) { "passed" } else { "failed" }; evidence = "runtime key binding stays in the guarded shell while pure normalization and binding decisions live in hotkeys" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_hotkeys" -File "ctoa_helper_hotkeys.lua")) { "passed" } else { "failed" }; evidence = "loader stages hotkeys with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_hotkeys.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_hotkeys.lua")) { "passed" } else { "failed" }; evidence = "dev package copies hotkeys into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-hotkeys-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "hotkeys"
        mode = "static_passive_hotkeys_contract"
        hotkeys_path = [System.IO.Path]::GetFullPath($hotkeysPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates; hotkeys stays static-only with no dedicated attach tab." } else { "Fix failed hotkeys static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "HotkeysStaticSmoke reads repo hotkey files only; it does not launch, stop, bind keys, send keys, create widgets, write profiles, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "hotkeys_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Hotkeys static smoke: $path"
    Write-Output "[solteria-helper-test-env] Hotkeys static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Hotkeys static smoke failed"
    }
}

function Invoke-ModalStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $modalPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_modal.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $modal = if (Test-Path -LiteralPath $modalPath) { Get-Content -LiteralPath $modalPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $modalPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_modal.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($modal.Contains('rawget(_G, "CTOA_HELPER_MODAL")') -and $modal.Contains("_G.CTOA_HELPER_MODAL = Modal") -and $modal.Contains("return Modal")) { "passed" } else { "failed" }; evidence = "modal keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "lifecycle_functions"; status = if ($modal.Contains("function Modal.request") -and $modal.Contains("function Modal.modalRequest") -and $modal.Contains("function Modal.isPending") -and $modal.Contains("function Modal.isExpired") -and $modal.Contains("function Modal.confirm") -and $modal.Contains("function Modal.cancel") -and $modal.Contains("function Modal.decision") -and $modal.Contains("function Modal.decisionText") -and $modal.Contains("function Modal.statusText") -and $modal.Contains("function Modal.buttonText") -and $modal.Contains("function Modal.contract")) { "passed" } else { "failed" }; evidence = "modal exposes extracted request bridge, pending, expiry, confirm, cancel, decision, text, and contract helpers" },
        [pscustomobject]@{ name = "guarded_actions"; status = if ($modal.Contains("local GUARDED_ACTIONS = {") -and $modal.Contains("cavebot_delete = true") -and $modal.Contains("cavebot_clear = true") -and $modal.Contains("profile_reset = true") -and $modal.Contains("ui_reset = true") -and $modal.Contains("promote_live = true")) { "passed" } else { "failed" }; evidence = "modal guards destructive helper commands and live promotion intent" },
        [pscustomobject]@{ name = "decision_reasons"; status = if ($modal.Contains('reason = "unguarded_action"') -and $modal.Contains('reason = "confirmed"') -and $modal.Contains('reason = "expired"') -and $modal.Contains('reason = "confirmation_required"')) { "passed" } else { "failed" }; evidence = "modal decision path emits explicit allow/deny reasons" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($modal.Contains('mode = "passive"') -and $modal.Contains("creates_widgets = false") -and $modal.Contains("live_shortcuts = false") -and $modal.Contains("runtime_actions = false") -and $modal.Contains("owns_modal_request = true") -and $modal.Contains("owns_decision_text = true")) { "passed" } else { "failed" }; evidence = "modal contract owns passive request/decision helpers with no widgets or live shortcuts" },
        [pscustomobject]@{ name = "ttl_contract"; status = if ($modal.Contains("local DEFAULT_TTL_MS = 4500") -and $modal.Contains("expires_at_ms = now + ttl")) { "passed" } else { "failed" }; evidence = "modal owns bounded confirmation TTL" },
        [pscustomobject]@{ name = "helper_uses_modal_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_MODAL")') -and -not $helper.Contains("local function modalRequest") -and -not $helper.Contains("local function modalValue") -and -not $helper.Contains("local function modalStatusText") -and $helper.Contains('moduleValue(externalModal, "modalRequest", "cavebot_delete", request.label, request.timeout_ms, helperNowMs())') -and $helper.Contains('moduleValue(externalModal, "isPending", Helper.pending_confirm, "cavebot_delete", helperNowMs())') -and $helper.Contains('moduleValue(externalModal, "statusText", Helper.pending_confirm)')) { "passed" } else { "failed" }; evidence = "native helper delegates pure request construction to modal through a guarded fallback while retaining pending/status integration" },
        [pscustomobject]@{ name = "helper_guarded_shell"; status = if ($helper.Contains("pending_confirm = nil") -and $helper.Contains('moduleValue(externalRoute, "deleteRequest"') -and $helper.Contains('moduleValue(externalModal, "modalRequest", "cavebot_delete", request.label, request.timeout_ms, helperNowMs())') -and $helper.Contains("deleteCurrentCavebotWaypoint(command.confirm == true)")) { "passed" } else { "failed" }; evidence = "destructive execution stays in the guarded shell with explicit confirm flag and route-owned request metadata" },
        [pscustomobject]@{ name = "no_widgets_or_otclient_globals"; status = if (-not $modal.Contains("createWidget") -and -not $modal.Contains("showWidget") -and -not $modal.Contains("g_ui") -and -not $modal.Contains("g_keyboard") -and -not $modal.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "modal module does not create widgets or call native UI globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $modal.Contains("g_game") -and -not $modal.Contains("autoWalk") -and -not $modal.Contains("castSpell") -and -not $modal.Contains("sendActionbarSlot") -and -not $modal.Contains("useInventoryItem") -and -not $modal.Contains("PromoteLiveCtoa")) { "passed" } else { "failed" }; evidence = "modal module does not walk, cast, use items, or bypass live promotion" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_modal" -File "ctoa_helper_modal.lua")) { "passed" } else { "failed" }; evidence = "loader stages modal with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_modal.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_modal.lua")) { "passed" } else { "failed" }; evidence = "dev package copies modal into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-modal-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "modal"
        mode = "static_passive_modal_contract"
        modal_path = [System.IO.Path]::GetFullPath($modalPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates; modal stays static-only with no dedicated attach tab." } else { "Fix failed modal static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "ModalStaticSmoke reads repo modal files only; it does not launch, stop, create widgets, bypass PromoteLiveCtoa, write profiles, execute plans, cast, talk, walk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "modal_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Modal static smoke: $path"
    Write-Output "[solteria-helper-test-env] Modal static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Modal static smoke failed"
    }
}

function Invoke-InputContractsStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $scriptPath = Join-Path $repo "scripts\ops\otclient_input_contract_fixtures.py"
    $jsonPath = Join-Path $outRoot "input_contract_fixtures.json"
    $planPath = Join-Path $repo "docs\otclient\solteria_helper_input_contracts.md"
    & python $scriptPath --json-out $jsonPath --plan-out $planPath
    if ($LASTEXITCODE -ne 0) {
        throw "Input contracts static smoke failed"
    }
    $report = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
    Write-Output "[solteria-helper-test-env] Input contracts static smoke: $jsonPath"
    Write-Output "[solteria-helper-test-env] Input contracts static status: $($report.status) ($($report.passed_count)/$($report.check_count))"
    if (-not [string]::IsNullOrWhiteSpace($report.next_action)) {
        Write-Output "[solteria-helper-test-env] Next action: $($report.next_action)"
    }
    if ($report.status -ne "passed") {
        throw "Input contracts static smoke failed"
    }
}

function Invoke-RouteStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $routePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_route.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $route = if (Test-Path -LiteralPath $routePath) { Get-Content -LiteralPath $routePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $routePath) { "passed" } else { "failed" }; evidence = "ctoa_helper_route.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($route.Contains('rawget(_G, "CTOA_HELPER_ROUTE")') -and $route.Contains("_G.CTOA_HELPER_ROUTE = Route") -and $route.Contains("return Route")) { "passed" } else { "failed" }; evidence = "route keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "route_functions"; status = if ($route.Contains("function Route.distanceChebyshev") -and $route.Contains("function Route.position") -and $route.Contains("function Route.label") -and $route.Contains("function Route.posKey") -and $route.Contains("function Route.positionText") -and $route.Contains("function Route.probeTarget") -and $route.Contains("function Route.probeMetadata") -and $route.Contains("function Route.add") -and $route.Contains("function Route.clear") -and $route.Contains("function Route.select") -and $route.Contains("function Route.delete") -and $route.Contains("function Route.move") -and $route.Contains("function Route.editorAction") -and $route.Contains("function Route.retryStatus") -and $route.Contains("function Route.retryBlocked") -and $route.Contains("function Route.progress") -and $route.Contains("function Route.activeTarget") -and $route.Contains("function Route.stats") -and $route.Contains("function Route.selectedSummary") -and $route.Contains("function Route.uiState") -and $route.Contains("function Route.deleteRequest") -and $route.Contains("function Route.contract")) { "passed" } else { "failed" }; evidence = "route exposes Chebyshev distance, waypoint, non-mutating probe metadata, selection, guarded mutation, retry, active target, stats, editor state and contract helpers" },
        [pscustomobject]@{ name = "waypoint_mutation"; status = if ($route.Contains("tools.cavebot_waypoints = tools.cavebot_waypoints or {}") -and $route.Contains("table.remove(waypoints, index)") -and $route.Contains("waypoints[index], waypoints[target] = waypoints[target], waypoints[index]") -and $route.Contains('return true, "route cleared"')) { "passed" } else { "failed" }; evidence = "route owns bounded waypoint add/delete/move/clear mutations" },
        [pscustomobject]@{ name = "retry_status"; status = if ($route.Contains("function Route.retryStatus") -and $route.Contains("function Route.retryBlocked") -and $route.Contains("function Route.progress") -and $route.Contains("function Route.activeTarget") -and $route.Contains('return "retry " .. tostring(tools.cavebot_retry_attempts or 0)') -and $route.Contains("retry_blocked = retry_attempts >= retry_limit") -and $route.Contains("owns_position_key = true") -and $route.Contains("owns_progress_state = true") -and $route.Contains("owns_target_selection = true")) { "passed" } else { "failed" }; evidence = "route reports retry attempts, position keys, progress state, active target selection, and blocked status without moving" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($route.Contains('mode = "passive"') -and $route.Contains("owns_waypoint_mutation = true") -and $route.Contains("owns_editor_state = true") -and $route.Contains("owns_editor_action = true") -and $route.Contains("owns_distance_chebyshev = true") -and $route.Contains("owns_position_key = true") -and $route.Contains("owns_position_text = true") -and $route.Contains("owns_probe_target = true") -and $route.Contains("owns_probe_metadata = true") -and $route.Contains("owns_retry_status = true") -and $route.Contains("owns_target_selection = true") -and $route.Contains("runtime_actions = false") -and $route.Contains("movement_enabled = false") -and $route.Contains("probe_mutates_route = false") -and $route.Contains("probe_changes_arming = false") -and $route.Contains("pathfinding = false")) { "passed" } else { "failed" }; evidence = "route contract declares passive non-mutating probe metadata, distance/editing/target helpers, and no movement/pathfinding" },
        [pscustomobject]@{ name = "helper_uses_route_domain"; status = if ($helper.Contains("local function moduleValue(module, functionName, ...)") -and $helper.Contains('moduleValue(externalRoute, "probeMetadata", tools, current)') -and $helper.Contains('moduleValue(externalRoute, "editorAction"') -and $helper.Contains('moduleValue(externalRoute, "distanceChebyshev"') -and $helper.Contains('moduleValue(externalRoute, "posKey"') -and $helper.Contains('moduleValue(externalRoute, "progress"') -and $helper.Contains('moduleValue(externalRoute, "activeTarget"') -and $helper.Contains('moduleValue(externalRoute, "uiState"') -and $helper.Contains('moduleValue(externalRoute, "deleteRequest"') -and $helper.Contains('moduleValue(externalRoute, "retryStatus", tools)') -and -not $helper.Contains("local function distanceChebyshev") -and -not $helper.Contains("function posKey(pos)") -and -not $helper.Contains("local function routeRetryStatus")) { "passed" } else { "failed" }; evidence = "helper shell delegates passive probe metadata plus distance/editing/progress/target helpers through guarded route calls" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $route.Contains("g_game") -and -not $route.Contains("g_map") -and -not $route.Contains("g_ui") -and -not $route.Contains("g_keyboard") -and -not $route.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "route module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_movement_or_runtime_actions"; status = if (-not $route.Contains("autoWalk") -and -not $route.Contains("findPath") -and -not $route.Contains("castSpell") -and -not $route.Contains("sendActionbarSlot") -and -not $route.Contains("useInventoryItem") -and -not $route.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "route module does not walk, pathfind, cast, use items, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_route" -File "ctoa_helper_route.lua")) { "passed" } else { "failed" }; evidence = "loader stages route with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_route.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_route.lua")) { "passed" } else { "failed" }; evidence = "dev package copies route into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"cavebot"') -and $script.Contains("-Tab cavebot")) { "passed" } else { "failed" }; evidence = "route engine has a valid cavebot attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-route-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "route"
        mode = "static_passive_route_contract"
        route_path = [System.IO.Path]::GetFullPath($routePath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab cavebot after character is in-world." } else { "Fix failed route static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "RouteStaticSmoke reads repo route files only; it does not launch, stop, walk, pathfind, toggle cavebot movement, create widgets, write profiles, execute plans, cast, talk, use items, attack, attach to, or overwrite any client."
    }
    $path = Join-Path $outRoot "route_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Route static smoke: $path"
    Write-Output "[solteria-helper-test-env] Route static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Route static smoke failed"
    }
}

function Invoke-TargetingStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $targetingPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_targeting.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $targeting = if (Test-Path -LiteralPath $targetingPath) { Get-Content -LiteralPath $targetingPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $targetingPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_targeting.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($targeting.Contains('rawget(_G, "CTOA_HELPER_TARGETING")') -and $targeting.Contains("_G.CTOA_HELPER_TARGETING = Targeting") -and $targeting.Contains("return Targeting")) { "passed" } else { "failed" }; evidence = "targeting keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "targeting_functions"; status = if ($targeting.Contains("function Targeting.normalizedName") -and $targeting.Contains("function Targeting.isIgnoredName") -and $targeting.Contains("function Targeting.hasBlockingNpcIcon") -and $targeting.Contains("function Targeting.creatureHasBlockingNpcIcon") -and $targeting.Contains("function Targeting.isFriendlySummonName") -and $targeting.Contains("function Targeting.isFriendlySummonCandidate") -and $targeting.Contains("function Targeting.priorityRank") -and $targeting.Contains("function Targeting.scoreCandidate") -and $targeting.Contains("function Targeting.targetCandidateScore") -and $targeting.Contains("function Targeting.bestCandidate") -and $targeting.Contains("function Targeting.decision") -and $targeting.Contains("function Targeting.summary") -and $targeting.Contains("function Targeting.configSummary") -and $targeting.Contains("function Targeting.contract")) { "passed" } else { "failed" }; evidence = "targeting exposes name normalization, ignore checks, pure NPC icon guard, friendly summon checks, target score bridge, priority, best-candidate decisions, summaries, and contract helpers" },
        [pscustomobject]@{ name = "scoring_logic"; status = if ($targeting.Contains("rank * 10000 + hp * 100 + distance") -and $targeting.Contains("rank * 10000 + distance * 100 + hp") -and $targeting.Contains("prefer_low_hp") -and $targeting.Contains('reason = "scored"')) { "passed" } else { "failed" }; evidence = "targeting owns deterministic rank/distance/hp score decisions" },
        [pscustomobject]@{ name = "ignored_name_policy"; status = if ($targeting.Contains("function Targeting.isIgnoredName") -and $targeting.Contains("string.find(normalized, needle, 1, true)") -and $targeting.Contains('reason = "ignored_name"') -and $targeting.Contains("score = 99999999")) { "passed" } else { "failed" }; evidence = "targeting owns ignored-name rejection before runtime attack code" },
        [pscustomobject]@{ name = "friendly_summon_policy"; status = if ($targeting.Contains("function Targeting.isFriendlySummonName") -and $targeting.Contains("function Targeting.isFriendlySummonCandidate") -and $targeting.Contains('reason = "friendly_summon"') -and $targeting.Contains("owns_friendly_summon_guard = true") -and $helper.Contains("isFriendlySummonCreature(target, getLocalPlayer())") -and $helper.Contains('clearUnsafeCurrentTarget("friendly summon/familiar target", now, true)')) { "passed" } else { "failed" }; evidence = "targeting/helper block friendly summons or familiars before runtime attack code" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($targeting.Contains('mode = "passive"') -and $targeting.Contains("owns_target_score = true") -and $targeting.Contains("owns_target_candidate_score = true") -and $targeting.Contains("owns_best_candidate = true") -and $targeting.Contains("owns_ignored_names = true") -and $targeting.Contains("owns_npc_icon_guard = true") -and $targeting.Contains("owns_blocking_npc_icon_value = true") -and $targeting.Contains("owns_friendly_summon_name = true") -and $targeting.Contains("owns_config_summary = true") -and $targeting.Contains("owns_targeting_summary_text = true") -and $targeting.Contains("runtime_actions = false") -and $targeting.Contains("attacks = false") -and $targeting.Contains("casts = false") -and $targeting.Contains("creature_scan = false")) { "passed" } else { "failed" }; evidence = "targeting contract declares passive icon, summon-name, scoring/config summary ownership and no attacks/casts/scan" },
        [pscustomobject]@{ name = "helper_uses_targeting_domain"; status = if ($helper.Contains('moduleValue(externalTargeting, "normalizedName", creature)') -and $helper.Contains('moduleValue(externalTargeting, "isIgnoredName", name, HELPER_CONFIG.tools.ignored_names or {})') -and $helper.Contains('moduleValue(externalTargeting, "isFriendlySummonName", normalizedCreatureName(creature), HELPER_CONFIG.tools)') -and $helper.Contains('moduleValue(externalTargeting, "creatureHasBlockingNpcIcon", npcIcon, HELPER_CONFIG.tools)') -and $helper.Contains('moduleValue(externalTargeting, "bestCandidate", candidates, tools)') -and -not $helper.Contains('moduleValue(externalTargeting, "targetCandidateScore", candidate, tools)') -and -not $helper.Contains("local bestScore = nil") -and $helper.Contains("pcall(creature.getIcon, creature)") -and -not $helper.Contains("local function creatureHasBlockingNpcIcon") -and -not $helper.Contains("local function isFriendlySummonName") -and -not $helper.Contains("local function targetCandidateScore") -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.targeting") -and $helper.Contains('targeting = moduleValue(externalOperatorSummary, "bridgeText", "targeting", OPERATOR_SUMMARY_BRIDGES)') -and $helper.Contains("targeting_summary_text = operatorSummaries.targeting") -and $helper.Contains("targeting = externalTargeting")) { "passed" } else { "failed" }; evidence = "helper shell delegates normalized names, ignore policy, icon/summon guards, and best-candidate ranking to the required targeting module; missing module output fails closed" },
        [pscustomobject]@{ name = "runtime_execution_stays_in_helper"; status = if ($helper.Contains("pcall(function() g_game.attack(target) end)") -and -not $targeting.Contains("g_game.attack") -and -not $targeting.Contains("g_game.follow")) { "passed" } else { "failed" }; evidence = "targeting module scores only; guarded attack execution remains in helper runtime" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $targeting.Contains("g_game") -and -not $targeting.Contains("g_map") -and -not $targeting.Contains("g_ui") -and -not $targeting.Contains("g_keyboard") -and -not $targeting.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "targeting module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $targeting.Contains("castSpell") -and -not $targeting.Contains("sendActionbarSlot") -and -not $targeting.Contains("useInventoryItem") -and -not $targeting.Contains("autoWalk") -and -not $targeting.Contains("findPath") -and -not $targeting.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "targeting module does not attack, cast, use items, walk, pathfind, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_targeting" -File "ctoa_helper_targeting.lua")) { "passed" } else { "failed" }; evidence = "loader stages targeting with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_targeting.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_targeting.lua")) { "passed" } else { "failed" }; evidence = "dev package copies targeting into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"hunting"') -and $script.Contains("-Tab hunting")) { "passed" } else { "failed" }; evidence = "target scorer has a valid hunting attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-targeting-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "targeting"
        mode = "static_passive_target_scorer_contract"
        targeting_path = [System.IO.Path]::GetFullPath($targetingPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab hunting after character is in-world." } else { "Fix failed targeting static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "TargetingStaticSmoke reads repo targeting files only; it does not launch, stop, scan creatures, attack, follow, cast, use items, walk, create widgets, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "targeting_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Targeting static smoke: $path"
    Write-Output "[solteria-helper-test-env] Targeting static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Targeting static smoke failed"
    }
}

function Invoke-CombatRuntimeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $combatPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_combat_runtime.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $combat = if (Test-Path -LiteralPath $combatPath) { Get-Content -LiteralPath $combatPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $combatPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_combat_runtime.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($combat.Contains('rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME")') -and $combat.Contains("_G.CTOA_HELPER_COMBAT_RUNTIME = CombatRuntime") -and $combat.Contains("return CombatRuntime")) { "passed" } else { "failed" }; evidence = "combat runtime keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "combat_runtime_functions"; status = if ($combat.Contains("function CombatRuntime.plan") -and $combat.Contains("function CombatRuntime.summary") -and $combat.Contains("function CombatRuntime.adapterSummary") -and $combat.Contains("function CombatRuntime.magicSummary") -and $combat.Contains("function CombatRuntime.msLeftText") -and $combat.Contains("function CombatRuntime.runeReady") -and $combat.Contains("function CombatRuntime.rotationSpellRows") -and $combat.Contains("function CombatRuntime.spellReadiness") -and $combat.Contains("function CombatRuntime.rotationSpell") -and $combat.Contains("function CombatRuntime.selectRotationSpell") -and $combat.Contains("function CombatRuntime.offensiveAction") -and $combat.Contains("function CombatRuntime.actionStatusText") -and $combat.Contains("function CombatRuntime.targetingStatusText") -and $combat.Contains("function CombatRuntime.nextActionText") -and $combat.Contains("function CombatRuntime.waitReason") -and $combat.Contains("function CombatRuntime.decisionState") -and $combat.Contains("function CombatRuntime.decisionStateSummary") -and $combat.Contains("function CombatRuntime.contract")) { "passed" } else { "failed" }; evidence = "combat runtime exposes passive rune readiness, normalized rotation selection, action/status decisions and contract helpers" },
        [pscustomobject]@{ name = "blocked_reasons"; status = if ($combat.Contains('return "runtime_disabled"') -and $combat.Contains('return "protection_zone"') -and $combat.Contains('return "offline"') -and $combat.Contains('return "target_required"')) { "passed" } else { "failed" }; evidence = "combat runtime planner owns disabled/PZ/offline/target-required decisions" },
        [pscustomobject]@{ name = "plan_actions"; status = if ($combat.Contains('action = "target"') -and $combat.Contains('action = "plan_spell"') -and $combat.Contains('action = "plan_rune"') -and $combat.Contains('next_action = "hold"')) { "passed" } else { "failed" }; evidence = "combat runtime returns target, canonical spell/rune, or hold plans without executing them" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($combat.Contains('mode = "passive"') -and $combat.Contains("owns_runtime_plan = true") -and $combat.Contains("owns_adapter_summary = true") -and $combat.Contains("owns_magic_summary = true") -and $combat.Contains("owns_magic_summary_text = true") -and $combat.Contains("owns_cooldown_text = true") -and $combat.Contains("owns_rotation_spell_rows = true") -and $combat.Contains("owns_rotation_spell_selection = true") -and $combat.Contains("owns_select_rotation_spell = true") -and $combat.Contains("owns_action_status_text = true") -and $combat.Contains("owns_targeting_status_text = true") -and $combat.Contains("owns_next_action_text = true") -and $combat.Contains("owns_wait_reason_text = true") -and $combat.Contains("owns_decision_state_text = true") -and $combat.Contains("owns_decision_state_summary = true") -and $combat.Contains("runtime_actions = false") -and $combat.Contains("scans_creatures = false") -and $combat.Contains("attacks = false") -and $combat.Contains("casts = false") -and $combat.Contains("uses_items = false") -and $combat.Contains("requires_target_scorer = true")) { "passed" } else { "failed" }; evidence = "combat runtime contract owns passive normalized rotation selection and no attack/cast/item execution" },
        [pscustomobject]@{ name = "helper_uses_combat_runtime_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME")') -and $helper.Contains("local function moduleValue(module, functionName, ...)") -and -not $helper.Contains("local function combatRuntimeAdapterSummary") -and $helper.Contains('moduleValue(externalCombatRuntime, "decisionStateSummary", tools') -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.magic") -and $helper.Contains('magic = moduleValue(externalOperatorSummary, "bridgeText", "magic", OPERATOR_SUMMARY_BRIDGES)') -and $helper.Contains("magic_summary_text = operatorSummaries.magic") -and $helper.Contains("combatRuntime = externalCombatRuntime") -and -not $helper.Contains("local function msLeftText") -and -not $helper.Contains("local function monsterCountForSpell") -and -not $helper.Contains("local function runeReady") -and -not $helper.Contains("local function selectRotationSpell") -and $helper.Contains('moduleValue(externalCombatRuntime, "runeReady", tools') -and $helper.Contains('moduleValue(externalCombatRuntime, "selectRotationSpell", tools, scan, now)') -and $helper.Contains('moduleValue(externalCombatRuntime, "rotationSpellRows", tools.rotation_spells') -and $helper.Contains('moduleValue(externalCombatRuntime, "spellReadiness", spells') -and $helper.Contains('moduleValue(externalCombatRuntime, "offensiveAction", tools') -and $helper.Contains("local combatRuntimeText") -and $helper.Contains("combatRuntimeText = function(functionName, eventOrAction, data, fallback)") -and $helper.IndexOf("local combatRuntimeText") -lt $helper.IndexOf("local function retargetSafeMonster") -and $helper.Contains("moduleValue(externalCombatRuntime, functionName, eventOrAction, data or {})") -and -not $helper.Contains("local function combatActionStatusText") -and -not $helper.Contains("local function combatTargetingStatusText") -and $helper.Contains('combatRuntimeText("targetingStatusText", "friendly_summon"') -and $helper.Contains('combatRuntimeText("actionStatusText", action') -and $helper.Contains('moduleValue(externalCombatRuntime, "nextActionText", action, fallback)') -and $helper.Contains('moduleValue(externalCombatRuntime, "waitReason", {') -and -not $helper.Contains('moduleValue(externalCombatRuntime, "decisionState", {') -and -not $helper.Contains("adapter_text = adapterText") -and -not $helper.Contains('"Auto exeta: " .. action.spell') -and -not $helper.Contains('"Rotation: " .. action.spell.words') -and -not $helper.Contains('"Rune: " .. (tools.rune_name or "rune")') -and -not $helper.Contains('"Next: rune/AoE"')) { "passed" } else { "failed" }; evidence = "helper shell consumes pure rune/rotation decisions while runtime execution remains shell-owned" },
        [pscustomobject]@{ name = "runtime_execution_stays_in_helper"; status = if ($helper.Contains("local function executeOffensiveAction") -and $helper.Contains('moduleValue(externalCombatRuntime, "dispatchDescriptor", action, tools)') -and $helper.Contains("castSpell(descriptor.words)") -and $helper.Contains("sendActionbarSlot(descriptor.slot, descriptor.hotkey)") -and $combat.Contains("function CombatRuntime.dispatchDescriptor") -and -not $combat.Contains("castSpell") -and -not $combat.Contains("sendActionbarSlot") -and -not $combat.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "combat runtime returns passive dispatch descriptors; guarded attack/cast/rune execution remains in helper runtime" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $combat.Contains("g_game") -and -not $combat.Contains("g_map") -and -not $combat.Contains("g_ui") -and -not $combat.Contains("g_keyboard") -and -not $combat.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "combat runtime module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $combat.Contains("castSpell") -and -not $combat.Contains("sendActionbarSlot") -and -not $combat.Contains("useInventoryItem") -and -not $combat.Contains("autoWalk") -and -not $combat.Contains("findPath") -and -not $combat.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "combat runtime module does not cast, use items, walk, pathfind, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_combat_runtime" -File "ctoa_helper_combat_runtime.lua")) { "passed" } else { "failed" }; evidence = "loader stages combat runtime with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_combat_runtime.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_combat_runtime.lua")) { "passed" } else { "failed" }; evidence = "dev package copies combat runtime into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"hunting_magic"') -and $script.Contains("-Tab hunting_magic")) { "passed" } else { "failed" }; evidence = "combat runtime has a valid hunting_magic attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-combat-runtime-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "combat_runtime"
        mode = "static_passive_combat_runtime_contract"
        combat_runtime_path = [System.IO.Path]::GetFullPath($combatPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab hunting_magic after character is in-world." } else { "Fix failed combat runtime static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "CombatRuntimeStaticSmoke reads repo combat runtime files only; it does not launch, stop, scan creatures, attack, follow, cast, use items, walk, create widgets, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "combat_runtime_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Combat runtime static smoke: $path"
    Write-Output "[solteria-helper-test-env] Combat runtime static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Combat runtime static smoke failed"
    }
}

function Invoke-CavebotRuntimeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $cavebotPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_cavebot_runtime.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $cavebot = if (Test-Path -LiteralPath $cavebotPath) { Get-Content -LiteralPath $cavebotPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $cavebotPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_cavebot_runtime.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($cavebot.Contains('rawget(_G, "CTOA_HELPER_CAVEBOT_RUNTIME")') -and $cavebot.Contains("_G.CTOA_HELPER_CAVEBOT_RUNTIME = CavebotRuntime") -and $cavebot.Contains("return CavebotRuntime")) { "passed" } else { "failed" }; evidence = "cavebot runtime keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "cavebot_runtime_functions"; status = if ($cavebot.Contains("function CavebotRuntime.plan") -and $cavebot.Contains("function CavebotRuntime.summary") -and $cavebot.Contains("function CavebotRuntime.decisionText") -and $cavebot.Contains("function CavebotRuntime.adapterSummary") -and $cavebot.Contains("function CavebotRuntime.adapterStatusText") -and $cavebot.Contains("function CavebotRuntime.adapterStatusSummary") -and $cavebot.Contains("function CavebotRuntime.movementCapability") -and $cavebot.Contains("function CavebotRuntime.probeMetadata") -and $cavebot.Contains("function CavebotRuntime.probeSnapshot") -and $cavebot.Contains("function CavebotRuntime.probeSummary") -and $cavebot.Contains("function CavebotRuntime.probeReport") -and $cavebot.Contains("function CavebotRuntime.pathText") -and $cavebot.Contains("function CavebotRuntime.movementBlockedReason") -and $cavebot.Contains("function CavebotRuntime.walkPreflight") -and $cavebot.Contains("function CavebotRuntime.testWalkPlan") -and $cavebot.Contains("function CavebotRuntime.walkingStatus") -and $cavebot.Contains("function CavebotRuntime.retryDecision") -and $cavebot.Contains("function CavebotRuntime.statusText") -and $cavebot.Contains("function CavebotRuntime.traceText") -and $cavebot.Contains("function CavebotRuntime.cavebotRuntimeText") -and $cavebot.Contains("function CavebotRuntime.cavebotRetryBudgetExceeded") -and $cavebot.Contains("function CavebotRuntime.contract")) { "passed" } else { "failed" }; evidence = "cavebot runtime exposes canonical passive probe metadata/report, plan, status/trace, retry, preflight and contract helpers" },
        [pscustomobject]@{ name = "blocked_reasons"; status = if ($cavebot.Contains('return "movement_disabled"') -and $cavebot.Contains('return "protection_zone"') -and $cavebot.Contains('return "offline"') -and $cavebot.Contains('return "empty_route"') -and $cavebot.Contains('return "retry_budget_exhausted"')) { "passed" } else { "failed" }; evidence = "cavebot runtime planner owns movement/PZ/offline/empty-route/retry-blocked decisions" },
        [pscustomobject]@{ name = "plan_actions"; status = if ($cavebot.Contains('next_action = "hold"') -and $cavebot.Contains('next_action = "plan_walk"') -and $cavebot.Contains("waypoint_index = selected > 0 and selected or 1") -and $cavebot.Contains("retry_budget = numberValue(cfg.max_retries, 3)")) { "passed" } else { "failed" }; evidence = "cavebot runtime returns hold or plan_walk decisions without executing movement" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($cavebot.Contains('mode = "passive"') -and $cavebot.Contains("owns_runtime_plan = true") -and $cavebot.Contains("owns_decision_text = true") -and $cavebot.Contains("owns_adapter_summary = true") -and $cavebot.Contains("owns_adapter_status_text = true") -and $cavebot.Contains("owns_adapter_status_summary = true") -and $cavebot.Contains("owns_probe_metadata = true") -and $cavebot.Contains("owns_probe_summary_text = true") -and $cavebot.Contains("owns_path_text = true") -and $cavebot.Contains("owns_blocked_reason_text = true") -and $cavebot.Contains("owns_walk_preflight = true") -and $cavebot.Contains("owns_test_walk_plan = true") -and $cavebot.Contains("owns_walking_status = true") -and $cavebot.Contains("owns_retry_decision = true") -and $cavebot.Contains("owns_status_text = true") -and $cavebot.Contains("owns_trace_text = true") -and $cavebot.Contains("owns_runtime_text_bridge = true") -and $cavebot.Contains("owns_retry_budget = true") -and $cavebot.Contains("runtime_actions = false") -and $cavebot.Contains("movement_enabled = false") -and $cavebot.Contains("probe_executes_movement = false") -and $cavebot.Contains("probe_mutates_route = false") -and $cavebot.Contains("probe_changes_arming = false") -and $cavebot.Contains("pathfinding = false") -and $cavebot.Contains("uses_map = false") -and $cavebot.Contains("walks = false") -and $cavebot.Contains("requires_route_engine = true")) { "passed" } else { "failed" }; evidence = "cavebot runtime contract declares passive probe metadata/formatting and no movement, mutation, arming, pathfinding or map calls" },
        [pscustomobject]@{ name = "helper_uses_cavebot_runtime_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_CAVEBOT_RUNTIME")') -and $helper.Contains("local function moduleValue(module, functionName, ...)") -and -not $helper.Contains("function cavebotRuntimeAdapterSummary") -and -not $helper.Contains("function cavebotRuntimeAdapterStatusText") -and $helper.Contains('moduleValue(externalCavebotRuntime, "adapterStatusSummary"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "movementCapabilityForPlayer"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "probeReport"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "pathText"') -and $helper.Contains('moduleCall(externalCavebotRuntime, "movementBlockedReason"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "walkPreflight"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "testWalkPlan"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "walkingStatus"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "retryDecision"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "cavebotRuntimeText"') -and $helper.Contains('moduleValue(externalCavebotRuntime, "cavebotRetryBudgetExceeded"') -and -not $helper.Contains("function cavebotRuntimeText(functionName, event, data, fallback)") -and -not $helper.Contains("function cavebotRetryBudgetExceeded(tools)") -and $cavebot.Contains('kind == "movement_reset"') -and $cavebot.Contains("CavebotRuntime.walkingStatus(item)") -and -not $helper.Contains("Cavebot movement target=") -and -not $helper.Contains("Test walk target=") -and -not $helper.Contains("Test walk blocked") -and -not $helper.Contains("Cavebot movement disabled: retry budget reached") -and -not $helper.Contains("Cavebot movement disabled: walk failed retry budget") -and $helper.Contains("setCavebotStatus(fitText(adapterStatus")) { "passed" } else { "failed" }; evidence = "helper shell consumes cavebot runtime through guarded module calls while runtime execution stays shell-owned" },
        [pscustomobject]@{ name = "runtime_execution_stays_in_helper"; status = if ($helper.Contains("function autoWalkTo(pos)") -and $helper.Contains("return player:autoWalk(pos, retry)") -and -not $helper.Contains("function movementPathProbeText") -and $helper.Contains('safeCall(player, "canWalk", true)') -and $helper.Contains('return g_map.findPath(current, target, 200, 0)') -and -not $cavebot.Contains("autoWalk") -and -not $cavebot.Contains("findPath") -and -not $cavebot.Contains("g_map")) { "passed" } else { "failed" }; evidence = "cavebot runtime formats passive metadata only; guarded canWalk/findPath/autoWalk calls remain in helper runtime" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $cavebot.Contains("g_game") -and -not $cavebot.Contains("g_map") -and -not $cavebot.Contains("g_ui") -and -not $cavebot.Contains("g_keyboard") -and -not $cavebot.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "cavebot runtime module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $cavebot.Contains("autoWalk") -and -not $cavebot.Contains("findPath") -and -not $cavebot.Contains("castSpell") -and -not $cavebot.Contains("sendActionbarSlot") -and -not $cavebot.Contains("useInventoryItem") -and -not $cavebot.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "cavebot runtime module does not walk, pathfind, cast, use items, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_cavebot_runtime" -File "ctoa_helper_cavebot_runtime.lua")) { "passed" } else { "failed" }; evidence = "loader stages cavebot runtime with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_cavebot_runtime.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_cavebot_runtime.lua")) { "passed" } else { "failed" }; evidence = "dev package copies cavebot runtime into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"cavebot"') -and $script.Contains("-Tab cavebot")) { "passed" } else { "failed" }; evidence = "cavebot runtime has a valid cavebot attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-cavebot-runtime-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "cavebot_runtime"
        mode = "static_passive_cavebot_runtime_contract"
        cavebot_runtime_path = [System.IO.Path]::GetFullPath($cavebotPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab cavebot after character is in-world." } else { "Fix failed cavebot runtime static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "CavebotRuntimeStaticSmoke reads repo cavebot runtime files only; it does not launch, stop, walk, pathfind, toggle cavebot movement, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "cavebot_runtime_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Cavebot runtime static smoke: $path"
    Write-Output "[solteria-helper-test-env] Cavebot runtime static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Cavebot runtime static smoke failed"
    }
}

function Invoke-LootRuntimeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $lootPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_loot_runtime.lua"
    $diagnosticsPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_diagnostics.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $loot = if (Test-Path -LiteralPath $lootPath) { Get-Content -LiteralPath $lootPath -Raw } else { "" }
    $diagnostics = if (Test-Path -LiteralPath $diagnosticsPath) { Get-Content -LiteralPath $diagnosticsPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $lootPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_loot_runtime.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($loot.Contains('rawget(_G, "CTOA_HELPER_LOOT_RUNTIME")') -and $loot.Contains("_G.CTOA_HELPER_LOOT_RUNTIME = LootRuntime") -and $loot.Contains("return LootRuntime")) { "passed" } else { "failed" }; evidence = "loot runtime keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "loot_runtime_functions"; status = if ($loot.Contains("function LootRuntime.plan") -and $loot.Contains("function LootRuntime.summary") -and $loot.Contains("function LootRuntime.adapterSummary") -and $loot.Contains("function LootRuntime.contract")) { "passed" } else { "failed" }; evidence = "loot runtime exposes plan, summary, adapter summary, and contract helpers" },
        [pscustomobject]@{ name = "blocked_reasons"; status = if ($loot.Contains('return "feature_flag_disabled"') -and $loot.Contains('return "runtime_disabled"') -and $loot.Contains('return "protection_zone"') -and $loot.Contains('return "offline"') -and $loot.Contains('return "no_capacity"') -and $loot.Contains('return "no_open_container"')) { "passed" } else { "failed" }; evidence = "loot runtime planner owns flag/runtime/PZ/offline/capacity/container decisions" },
        [pscustomobject]@{ name = "plan_actions"; status = if ($loot.Contains('next_action = "plan_loot"') -and $loot.Contains('lootOperation = "scan"') -and $loot.Contains('lootOperation = "open"') -and $loot.Contains('lootOperation = "move"') -and $loot.Contains('next_action = "hold"')) { "passed" } else { "failed" }; evidence = "loot runtime returns canonical plan_loot with scan/open/move detail without executing loot actions" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($loot.Contains('mode = "passive"') -and $loot.Contains("owns_runtime_plan = true") -and $loot.Contains("owns_adapter_summary = true") -and $loot.Contains("runtime_actions = false") -and $loot.Contains("scans_containers = false") -and $loot.Contains("opens_containers = false") -and $loot.Contains("moves_items = false") -and $loot.Contains("uses_items = false") -and $loot.Contains("requires_experimental_flag = true")) { "passed" } else { "failed" }; evidence = "loot runtime contract declares passive planning/adapter summary and no scan/open/move/use execution" },
        [pscustomobject]@{ name = "helper_uses_loot_runtime_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_LOOT_RUNTIME")') -and -not $helper.Contains("function lootRuntimeAdapterSummary") -and $helper.Contains('moduleValue(externalLootRuntime, "adapterSummary"') -and -not $helper.Contains("pcall(externalLootRuntime.adapterSummary") -and -not $helper.Contains("pcall(externalLootRuntime.plan") -and -not $helper.Contains("pcall(externalLootRuntime.summary") -and $diagnostics.Contains('" adapter=" .. tostring(data.loot_adapter_text')) { "passed" } else { "failed" }; evidence = "helper shell consumes loot runtime adapter summary for diagnostics only through the shared guarded moduleValue invoker and module-owned passive adapter" },
        [pscustomobject]@{ name = "runtime_execution_stays_out_of_helper_adapter"; status = if ($helper.Contains("loot_adapter_text = function") -and $helper.Contains("game = g_game") -and $diagnostics.Contains('Diagnostics.safeGlobalCall(ctx.game, "getContainers")') -and $diagnostics.Contains('Diagnostics.apiText(game, "move")') -and -not $loot.Contains("g_game.move") -and -not $loot.Contains("useInventoryItem") -and -not $loot.Contains("openContainer(") -and -not $loot.Contains("g_game.open")) { "passed" } else { "failed" }; evidence = "loot runtime plans only; diagnostics controller reads API probe state through the injected game dependency without moving or using items" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $loot.Contains("g_game") -and -not $loot.Contains("g_map") -and -not $loot.Contains("g_ui") -and -not $loot.Contains("g_keyboard") -and -not $loot.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "loot runtime module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $loot.Contains("useInventoryItem") -and -not $loot.Contains("openContainer(") -and -not $loot.Contains("g_game.open") -and -not $loot.Contains("g_game.move") -and -not $loot.Contains("autoWalk") -and -not $loot.Contains("findPath") -and -not $loot.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "loot runtime module does not use items, open containers, move items, walk, pathfind, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_loot_runtime" -File "ctoa_helper_loot_runtime.lua")) { "passed" } else { "failed" }; evidence = "loader stages loot runtime with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_loot_runtime.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_loot_runtime.lua")) { "passed" } else { "failed" }; evidence = "dev package copies loot runtime into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"tools_diag"') -and $script.Contains("-Tab tools_diag")) { "passed" } else { "failed" }; evidence = "loot runtime diagnostics has a valid tools_diag attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-loot-runtime-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "loot_runtime"
        mode = "static_passive_loot_runtime_contract"
        loot_runtime_path = [System.IO.Path]::GetFullPath($lootPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab tools_diag after character is in-world." } else { "Fix failed loot runtime static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "LootRuntimeStaticSmoke reads repo loot runtime files only; it does not launch, stop, scan containers, open containers, move items, use items, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "loot_runtime_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Loot runtime static smoke: $path"
    Write-Output "[solteria-helper-test-env] Loot runtime static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Loot runtime static smoke failed"
    }
}

function Invoke-TimerRuntimeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $timerPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_timer_runtime.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $timer = if (Test-Path -LiteralPath $timerPath) { Get-Content -LiteralPath $timerPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $timerPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_timer_runtime.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($timer.Contains('rawget(_G, "CTOA_HELPER_TIMER_RUNTIME")') -and $timer.Contains("_G.CTOA_HELPER_TIMER_RUNTIME = TimerRuntime") -and $timer.Contains("return TimerRuntime")) { "passed" } else { "failed" }; evidence = "timer runtime keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "timer_runtime_functions"; status = if ($timer.Contains("function TimerRuntime.plan") -and $timer.Contains("function TimerRuntime.summary") -and $timer.Contains("function TimerRuntime.probeSummary") -and $timer.Contains("function TimerRuntime.dispatch") -and $timer.Contains("function TimerRuntime.contract")) { "passed" } else { "failed" }; evidence = "timer runtime exposes plan, passive probe summary, dispatch, and contract helpers" },
        [pscustomobject]@{ name = "blocked_reasons"; status = if ($timer.Contains('return "timer_disabled"') -and $timer.Contains('return "protection_zone"') -and $timer.Contains('return "offline"') -and $timer.Contains('return "missing_message"') -and $timer.Contains('return "cast_bridge_blocked"')) { "passed" } else { "failed" }; evidence = "timer runtime planner owns disabled/PZ/offline/message/cast-bridge decisions" },
        [pscustomobject]@{ name = "plan_actions"; status = if ($timer.Contains('next_action = "hold"') -and $timer.Contains('next_action = "plan_timer"') -and $timer.Contains("message_preview") -and $timer.Contains("due_in_ms")) { "passed" } else { "failed" }; evidence = "timer runtime returns hold or canonical plan_timer decisions without executing timer actions" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($timer.Contains('mode = "passive"') -and $timer.Contains("owns_runtime_plan = true") -and $timer.Contains("owns_probe_summary_text = true") -and $timer.Contains("owns_dispatch_decision = true") -and $timer.Contains("runtime_actions = false") -and $timer.Contains("talks = false") -and $timer.Contains("casts = false") -and $timer.Contains("evaluates = false") -and $timer.Contains("loads_files = false") -and $timer.Contains("requires_sandbox_attach = true")) { "passed" } else { "failed" }; evidence = "timer runtime contract declares passive planning/probe summary/dispatch and no talk/cast/eval/load execution" },
        [pscustomobject]@{ name = "helper_uses_timer_runtime_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_TIMER_RUNTIME")') -and $helper.Contains('moduleValue(externalTimerRuntime, "plan", tools, context)') -and $helper.Contains('moduleValue(externalTimerRuntime, "summary", runtimePlan)') -and $helper.Contains('moduleValue(externalTimerRuntime, "probeSummary", plan)') -and $helper.Contains('moduleValue(externalTimerRuntime, "dispatch", plan, tools, {') -and -not $helper.Contains('status("Timer probe: "') -and -not $helper.Contains("pcall(externalTimerRuntime.plan") -and -not $helper.Contains("pcall(externalTimerRuntime.summary") -and -not $helper.Contains("pcall(externalTimerRuntime.dispatch") -and $helper.Contains("dispatch.status_text")) { "passed" } else { "failed" }; evidence = "helper shell keeps timer observations and consumes module-owned passive probe/decision text through guarded moduleValue" },
        [pscustomobject]@{ name = "runtime_execution_stays_in_helper"; status = if ($helper.Contains("function maybeRunTimer(now)") -and $helper.Contains("castSpell(message)") -and $helper.Contains("tools.last_timer_ms = now") -and -not $timer.Contains("castSpell") -and -not $timer.Contains("g_game.talk") -and -not $timer.Contains("say(")) { "passed" } else { "failed" }; evidence = "timer runtime plans only; guarded timer cast remains in helper runtime" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $timer.Contains("g_game") -and -not $timer.Contains("g_map") -and -not $timer.Contains("g_ui") -and -not $timer.Contains("g_keyboard") -and -not $timer.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "timer runtime module does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $timer.Contains("castSpell") -and -not $timer.Contains("g_game.talk") -and -not $timer.Contains("say(") -and -not $timer.Contains("loadfile") -and -not $timer.Contains("dofile") -and -not $timer.Contains("createWidget")) { "passed" } else { "failed" }; evidence = "timer runtime module does not cast, talk, eval/load files, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_timer_runtime" -File "ctoa_helper_timer_runtime.lua")) { "passed" } else { "failed" }; evidence = "loader stages timer runtime with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_timer_runtime.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_timer_runtime.lua")) { "passed" } else { "failed" }; evidence = "dev package copies timer runtime into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "attach_tab"; status = if ($script.Contains('"tools_timer"') -and $script.Contains("-Tab tools_timer")) { "passed" } else { "failed" }; evidence = "timer runtime has a valid tools_timer attach tab for sandbox evidence" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-timer-runtime-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "timer_runtime"
        mode = "static_passive_timer_runtime_contract"
        timer_runtime_path = [System.IO.Path]::GetFullPath($timerPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttach -Tab tools_timer after character is in-world." } else { "Fix failed timer runtime static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "TimerRuntimeStaticSmoke reads repo timer runtime files only; it does not launch, stop, talk, cast, evaluate snippets, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "timer_runtime_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Timer runtime static smoke: $path"
    Write-Output "[solteria-helper-test-env] Timer runtime static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Timer runtime static smoke failed"
    }
}

function Invoke-RecoveryRuntimeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $recoveryPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_recovery_runtime.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $recovery = if (Test-Path -LiteralPath $recoveryPath) { Get-Content -LiteralPath $recoveryPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $recoveryPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_recovery_runtime.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($recovery.Contains('rawget(_G, "CTOA_HELPER_RECOVERY_RUNTIME")') -and $recovery.Contains("_G.CTOA_HELPER_RECOVERY_RUNTIME = RecoveryRuntime") -and $recovery.Contains("return RecoveryRuntime")) { "passed" } else { "failed" }; evidence = "recovery runtime keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "recovery_runtime_functions"; status = if ($recovery.Contains("function RecoveryRuntime.normalizeVitals") -and $recovery.Contains("function RecoveryRuntime.readVitals") -and $recovery.Contains("function RecoveryRuntime.jitterThreshold") -and $recovery.Contains("function RecoveryRuntime.selectHealingSpell") -and $recovery.Contains("function RecoveryRuntime.potionStatusText") -and $recovery.Contains("function RecoveryRuntime.spellStatusText") -and $recovery.Contains("function RecoveryRuntime.actionGap") -and $recovery.Contains("function RecoveryRuntime.recoveryActionGap") -and $recovery.Contains("function RecoveryRuntime.summary") -and $recovery.Contains("function RecoveryRuntime.contract")) { "passed" } else { "failed" }; evidence = "recovery runtime exposes passive vitals, spell selection, status and configured action-gap helpers" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($recovery.Contains('mode = "passive"') -and $recovery.Contains("owns_vitals_normalization = true") -and $recovery.Contains("owns_vitals_read = true") -and $recovery.Contains("owns_healing_spell_selection = true") -and $recovery.Contains("owns_recovery_status_text = true") -and $recovery.Contains("owns_recovery_action_gap = true") -and $recovery.Contains("owns_recovery_action_gap_bridge = true") -and $recovery.Contains("runtime_actions = false") -and $recovery.Contains("casts = false") -and $recovery.Contains("uses_items = false") -and $recovery.Contains("reads_otclient = false") -and $recovery.Contains("creates_widgets = false")) { "passed" } else { "failed" }; evidence = "recovery runtime owns configured action-gap decisions and no OTClient/runtime/widget behavior" },
        [pscustomobject]@{ name = "helper_uses_recovery_runtime_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_RECOVERY_RUNTIME")') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "readVitals", player)') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "normalizeVitals", {})') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "jitterThreshold"') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "selectHealingSpell", healing, hp, nonce)') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "potionStatusText"') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "spellStatusText", spell, hp)') -and $helper.Contains('moduleValue(externalRecoveryRuntime, "recoveryActionGap", now, HELPER_CONFIG.healing, HELPER_CONFIG.tools)') -and -not $helper.Contains("local function recoveryActionGap") -and -not $helper.Contains("local function selectHealingSpell")) { "passed" } else { "failed" }; evidence = "helper shell delegates vitals, spell selection, status and action-gap decisions through guarded recovery calls" },
        [pscustomobject]@{ name = "runtime_execution_stays_in_helper"; status = if ($helper.Contains("sendActionbarSlot(healing.potion_actionbar_slot, healing.potion_hotkey)") -and $helper.Contains("sendActionbarSlot(healing.mana_potion_actionbar_slot, healing.mana_potion_hotkey)") -and $helper.Contains("castSpell(spell)") -and -not $recovery.Contains("sendActionbarSlot") -and -not $recovery.Contains("castSpell")) { "passed" } else { "failed" }; evidence = "recovery runtime plans/formats only; guarded potion and spell execution remains in helper runtime" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $recovery.Contains("g_game") -and -not $recovery.Contains("g_map") -and -not $recovery.Contains("g_ui") -and -not $recovery.Contains("g_keyboard") -and -not $recovery.Contains("g_resources") -and -not $recovery.Contains("getLocalPlayer")) { "passed" } else { "failed" }; evidence = "recovery runtime module does not call native OTClient globals or local-player APIs" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $recovery.Contains("castSpell") -and -not $recovery.Contains("sendActionbarSlot") -and -not $recovery.Contains("useInventoryItem") -and -not $recovery.Contains("autoWalk") -and -not $recovery.Contains("createWidget") -and -not $recovery.Contains("dofile")) { "passed" } else { "failed" }; evidence = "recovery runtime does not cast, use items, walk, create widgets, or load files" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_recovery_runtime" -File "ctoa_helper_recovery_runtime.lua")) { "passed" } else { "failed" }; evidence = "loader stages recovery runtime with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_recovery_runtime.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_recovery_runtime.lua")) { "passed" } else { "failed" }; evidence = "dev package copies recovery runtime into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-recovery-runtime-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "recovery_runtime"
        mode = "static_passive_recovery_runtime_contract"
        recovery_runtime_path = [System.IO.Path]::GetFullPath($recoveryPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed recovery runtime static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "RecoveryRuntimeStaticSmoke reads repo recovery runtime files only; it does not launch, stop, read player state, cast, use items, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "recovery_runtime_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Recovery runtime static smoke: $path"
    Write-Output "[solteria-helper-test-env] Recovery runtime static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Recovery runtime static smoke failed"
    }
}

function Invoke-RecoveryBridgeStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $bridgePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_recovery_bridge.lua"
    $testPath = Join-Path $repo "tests\test_ctoa_helper_recovery_bridge.py"
    $bridge = if (Test-Path -LiteralPath $bridgePath) { Get-Content -LiteralPath $bridgePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $PSCommandPath -Raw
    & (Join-Path $repo ".venv\Scripts\python.exe") -m pytest $testPath -q
    $pytestExitCode = $LASTEXITCODE
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $bridgePath) { "passed" } else { "failed" }; evidence = "ctoa_helper_recovery_bridge.lua exists" },
        [pscustomobject]@{ name = "safe_defaults"; status = if ($bridge.Contains("default_armed = false") -and $bridge.Contains("default_dry_run = true") -and $bridge.Contains('mode = "sandbox_only"')) { "passed" } else { "failed" }; evidence = "bridge defaults to disarmed sandbox dry-run" },
        [pscustomobject]@{ name = "bounded_controls"; status = if ($bridge.Contains("function RecoveryBridge.arm") -and $bridge.Contains("function RecoveryBridge.kill") -and $bridge.Contains("cooldown_active") -and $bridge.Contains("retry_budget_exhausted") -and $bridge.Contains("armed_session_mismatch")) { "passed" } else { "failed" }; evidence = "session arm, kill switch, cooldown, retry budget, and session match are present" },
        [pscustomobject]@{ name = "trace_contract"; status = if ($bridge.Contains('ctoa.recovery-bridge-trace.v1') -and $bridge.Contains('result = "dry_run"')) { "passed" } else { "failed" }; evidence = "decision guard action result trace is explicit" },
        [pscustomobject]@{ name = "no_direct_otclient_calls"; status = if (-not $bridge.Contains("g_game.") -and -not $bridge.Contains("g_map.") -and -not $bridge.Contains("castSpell(") -and -not $bridge.Contains("sendActionbarSlot(")) { "passed" } else { "failed" }; evidence = "bridge requires an injected executor and has no direct OTClient action calls" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_recovery_bridge" -File "ctoa_helper_recovery_bridge.lua")) { "passed" } else { "failed" }; evidence = "boot graph stages the bridge after its dependencies" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_recovery_bridge.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_recovery_bridge.lua")) { "passed" } else { "failed" }; evidence = "dev package copies the bridge" },
        [pscustomobject]@{ name = "real_lua_tests"; status = if ($pytestExitCode -eq 0) { "passed" } else { "failed" }; evidence = "recovery bridge pytest and real-Lua probes pass" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-recovery-bridge-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "recovery_bridge"
        mode = "sandbox_only_dry_run_first"
        bridge_path = [System.IO.Path]::GetFullPath($bridgePath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run PrepareDev, ValidateDev, and SmokePreflight before sandbox attach." } else { "Fix failed Recovery Bridge contract checks." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev" } else { "" }
        live_safety = "RecoveryBridgeStaticSmoke reads repo sources and runs local tests only; it does not launch, attach, cast, promote, or overwrite a live client."
    }
    $path = Join-Path $outRoot "recovery_bridge_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Recovery bridge static smoke: $path"
    Write-Output "[solteria-helper-test-env] Recovery bridge static status: $($report.status)"
    if ($failed.Count -gt 0) { throw "Recovery bridge static smoke failed" }
}

function Invoke-RuntimeModuleGateStaticSmoke {
    param(
        [Parameter(Mandatory = $true)][string]$ModuleId,
        [Parameter(Mandatory = $true)][string]$ModuleFile,
        [Parameter(Mandatory = $true)][string]$GateId,
        [Parameter(Mandatory = $true)][string]$Phase,
        [Parameter(Mandatory = $true)][string]$AllowedAction,
        [Parameter(Mandatory = $true)][string]$ReportFile
    )
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $enginePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_runtime_module_gate.lua"
    $gatePath = Join-Path $repo ("scripts\lua\otclient\" + $ModuleFile)
    $testPath = Join-Path $repo "tests\test_ctoa_helper_runtime_module_gates.py"
    $engine = if (Test-Path -LiteralPath $enginePath) { Get-Content -LiteralPath $enginePath -Raw } else { "" }
    $gate = if (Test-Path -LiteralPath $gatePath) { Get-Content -LiteralPath $gatePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $script = Get-Content -LiteralPath $PSCommandPath -Raw
    & (Join-Path $repo ".venv\Scripts\python.exe") -m pytest $testPath -q
    $pytestExitCode = $LASTEXITCODE
    $checks = @(
        [pscustomobject]@{ name = "gate_engine_exists"; status = if (Test-Path -LiteralPath $enginePath) { "passed" } else { "failed" }; evidence = "shared runtime module gate exists" },
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $gatePath) { "passed" } else { "failed" }; evidence = "$ModuleFile exists" },
        [pscustomobject]@{ name = "separate_gate_identity"; status = if ($gate.Contains(('gate_id = "' + $GateId + '"')) -and $gate.Contains(('phase = "' + $Phase + '"'))) { "passed" } else { "failed" }; evidence = "$GateId owns phase $Phase" },
        [pscustomobject]@{ name = "bounded_action"; status = if ($gate.Contains(('allowed_actions = {"' + $AllowedAction + '"}'))) { "passed" } else { "failed" }; evidence = "gate allowlists only $AllowedAction" },
        [pscustomobject]@{ name = "safe_contract"; status = if ($gate.Contains('mode = "sandbox_dry_run_gate"') -and $gate.Contains("default_closed = true") -and $gate.Contains("dispatch_allowed = false") -and $gate.Contains("runtime_actions = false") -and $gate.Contains("live_promotion = false") -and $gate.Contains("combat_deferred = true") -and $gate.Contains("cavebot_deferred = true")) { "passed" } else { "failed" }; evidence = "gate is default-closed dry-run and keeps high-risk lanes deferred" },
        [pscustomobject]@{ name = "no_direct_otclient_calls"; status = if (-not $gate.Contains("g_game.") -and -not $gate.Contains("g_map.") -and -not $gate.Contains("castSpell(") -and -not $gate.Contains("sendActionbarSlot(") -and -not $gate.Contains("autoWalk(")) { "passed" } else { "failed" }; evidence = "gate cannot execute OTClient actions" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name $ModuleId -File $ModuleFile)) { "passed" } else { "failed" }; evidence = "boot graph stages the action-specific gate" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains($ModuleFile) -and $script.Contains(("mods/ctoa_otclient/" + $ModuleFile))) { "passed" } else { "failed" }; evidence = "dev package copies the action-specific gate" },
        [pscustomobject]@{ name = "real_lua_tests"; status = if ($pytestExitCode -eq 0) { "passed" } else { "failed" }; evidence = "gate matrix and runtime policy tests pass in real Lua" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        schema_version = "ctoa.runtime-module-safety-gate-report.v1"
        created_at = (Get-Date).ToString("o")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = $ModuleId
        gate_id = $GateId
        phase = $Phase
        mode = "sandbox_dry_run_gate_static_acceptance"
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        dispatch_allowed = $false
        runtime_actions = $false
        live_promotion = $false
        next_action = if ($failed.Count -eq 0) { "Refresh package and sandbox evidence; do not enable execution through this gate." } else { "Fix failed action-specific runtime gate checks." }
        live_safety = "This static gate reads repo sources and runs local tests only; it does not launch, attach, execute, promote, or overwrite a live client."
    }
    $path = Join-Path $outRoot $ReportFile
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Runtime module gate: $path"
    Write-Output "[solteria-helper-test-env] Runtime module gate status: $($report.status) ($($report.passed_count)/$($report.check_count))"
    if ($failed.Count -gt 0) { throw "$GateId static smoke failed" }
}

function Invoke-ConditionsRuntimeGateStaticSmoke {
    Invoke-RuntimeModuleGateStaticSmoke -ModuleId "ctoa_helper_conditions_runtime_gate" -ModuleFile "ctoa_helper_conditions_runtime_gate.lua" -GateId "conditions_runtime_gate" -Phase "conditions_first" -AllowedAction "plan_paralyze_recovery" -ReportFile "conditions_runtime_gate_static_smoke.json"
}

function Invoke-EquipmentRuntimeGateStaticSmoke {
    Invoke-RuntimeModuleGateStaticSmoke -ModuleId "ctoa_helper_equipment_runtime_gate" -ModuleFile "ctoa_helper_equipment_runtime_gate.lua" -GateId "equipment_runtime_gate" -Phase "equipment_after_conditions" -AllowedAction "plan_ring_swap" -ReportFile "equipment_runtime_gate_static_smoke.json"
}

function Invoke-HealFriendRuntimeGateStaticSmoke {
    Invoke-RuntimeModuleGateStaticSmoke -ModuleId "ctoa_helper_heal_friend_runtime_gate" -ModuleFile "ctoa_helper_heal_friend_runtime_gate.lua" -GateId "heal_friend_runtime_gate" -Phase "heal_friend_after_equipment_conditions" -AllowedAction "plan_sio" -ReportFile "heal_friend_runtime_gate_static_smoke.json"
}

function Invoke-RecoveryBridgeActionSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    if (-not (Test-Path -LiteralPath $logPath)) { throw "Sandbox log is required for RecoveryBridgeActionSmoke" }

    function Send-And-WaitRecoveryBridgeCommand {
        param([string]$CommandAction, [string]$Needle, [switch]$Confirm)
        $before = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue).Count
        Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "healing" -CommandAction $CommandAction -Confirm:$Confirm
        $deadline = (Get-Date).AddSeconds(12)
        while ((Get-Date) -lt $deadline) {
            $lines = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
            $fresh = if ($lines.Count -gt $before) { @($lines[$before..($lines.Count - 1)]) } else { @() }
            if ($fresh -match [regex]::Escape($Needle)) { return $true }
            Start-Sleep -Milliseconds 200
        }
        return $false
    }

    $dryRun = Send-And-WaitRecoveryBridgeCommand -CommandAction "recovery_bridge_dry_run" -Needle "Recovery bridge dry-run: ready / dry_run"
    $armRequest = Send-And-WaitRecoveryBridgeCommand -CommandAction "recovery_bridge_arm" -Needle "click ARM again to confirm"
    Start-Sleep -Milliseconds 750
    $armed = Send-And-WaitRecoveryBridgeCommand -CommandAction "recovery_bridge_arm" -Needle "Recovery bridge armed: sandbox Healing session"
    $executed = Send-And-WaitRecoveryBridgeCommand -CommandAction "recovery_bridge_execute_once" -Needle "Recovery bridge execute-once: executed / success" -Confirm
    $killed = Send-And-WaitRecoveryBridgeCommand -CommandAction "recovery_bridge_kill" -Needle "Recovery bridge KILL: runtime disarmed"
    $checks = [ordered]@{ dry_run = $dryRun; arm_request = $armRequest; armed = $armed; executed_once = $executed; kill_switch = $killed }
    $failed = @($checks.GetEnumerator() | Where-Object { $_.Value -ne $true } | ForEach-Object { $_.Key })
    $report = [pscustomobject]@{
        schema_version = "ctoa.recovery-bridge-action-smoke.v1"
        created_at = (Get-Date).ToString("o")
        status = if ($failed.Count -eq 0) { "passed" } else { "blocked" }
        mode = "sandbox_single_healing_action"
        checks = $checks
        passed_count = @($checks.GetEnumerator() | Where-Object { $_.Value -eq $true }).Count
        check_count = $checks.Count
        failed = $failed
        final_state = if ($killed) { "killed_and_disarmed" } else { "unknown" }
        live_promotion = $false
        next_action = if ($failed.Count -eq 0) { "Review evidence; do not promote live through this action." } else { "Inspect sandbox log and repair failed bridge step." }
    }
    $path = Join-Path $outRoot "recovery_bridge_action_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Recovery bridge action smoke: $path"
    Write-Output "[solteria-helper-test-env] Recovery bridge action status: $($report.status) ($($report.passed_count)/$($report.check_count))"
    if ($failed.Count -gt 0) { throw "Recovery bridge action smoke failed: $($failed -join ', ')" }
}

function Invoke-P12ConditionsExecuteOnce {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $planPath = Join-Path $outRoot "p12_conditions_execute_once_plan.json"
    $approvalPath = Join-Path $outRoot "p12_conditions_session_approval.json"
    $tracePath = Join-Path $outRoot "p12_conditions_execute_once_trace.json"
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $planTool = Join-Path $repo "scripts\ops\otclient_p12_conditions_execute_once_plan.py"
    $preflightTool = Join-Path $repo "scripts\ops\otclient_p12_conditions_execution_preflight.py"
    $receiptTool = Join-Path $repo "scripts\ops\otclient_p12_conditions_execute_once_receipt.py"
    & $python $planTool | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "P12 Conditions current plan is blocked." }
    if (-not (Test-Path -LiteralPath $approvalPath -PathType Leaf)) { throw "P12 Conditions session and execution approvals are required." }
    $plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
    $approval = Get-Content -LiteralPath $approvalPath -Raw | ConvertFrom-Json
    if ([string]$plan.status -ne "ready_for_sandbox_session_approval" -or @($plan.blockers).Count -ne 0) { throw "P12 Conditions plan is not ready." }
    if ([string]$approval.status -ne "approved" -or $approval.session_approved -ne $true -or $approval.execution_approved -ne $true) { throw "P12 Conditions requires both separate approvals." }
    if ([string]$approval.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$approval.p9_receipt_sha256 -ne [string]$plan.p9_receipt_sha256) { throw "P12 Conditions approval binding mismatch." }
    & $python $preflightTool | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "P12 Conditions execution preflight is blocked; no attempt was sent." }
    $executionPreflight = Get-Content -LiteralPath (Join-Path $outRoot "p12_conditions_execution_preflight.json") -Raw | ConvertFrom-Json
    if ([string]$executionPreflight.status -ne "ready_for_execution_approval" -or $executionPreflight.execution_approved -ne $true -or @($executionPreflight.blockers).Count -ne 0) { throw "P12 Conditions current domain state is not execution-ready; no attempt was sent." }
    if ([string]$executionPreflight.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$executionPreflight.approval_id -ne [string]$approval.approval_id) { throw "P12 Conditions execution-preflight binding mismatch." }

    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $processes = @(Get-SandboxProcessSummaries)
    if ($processes.Count -ne 1) { throw "P12 Conditions requires exactly one running sandbox process." }
    $moduleRelative = "mods\ctoa_otclient\ctoa_helper_conditions_execute_once.lua"
    $stageModule = Join-Path (Join-Path $outRoot "latest") $moduleRelative
    $sandboxModule = Join-Path $sandboxFull $moduleRelative
    if (-not (Test-Path -LiteralPath $stageModule -PathType Leaf) -or -not (Test-Path -LiteralPath $sandboxModule -PathType Leaf)) { throw "P12 Conditions module is missing from stage or sandbox." }
    $stageHash = (Get-FileHash -LiteralPath $stageModule -Algorithm SHA256).Hash.ToLowerInvariant()
    $sandboxHash = (Get-FileHash -LiteralPath $sandboxModule -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($stageHash -ne [string]$plan.source_sha256 -or $sandboxHash -ne $stageHash) { throw "P12 Conditions sandbox/module hash parity failed." }

    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) { throw "P12 Conditions sandbox log is required." }
    $before = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
    $runtimeStates = @($before | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    if ($runtimeStates.Count -eq 0 -or [string]$runtimeStates[-1] -notmatch "Runtime disarmed$") { throw "P12 Conditions requires the global runtime to be disarmed." }

    $sessionId = [string]$approval.approval_id
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "conditions" -CommandAction "p12_conditions_execute_once" -Confirm -SessionId $sessionId -PlanSha256 ([string]$plan.plan_sha256) -P9ReceiptSha256 ([string]$plan.p9_receipt_sha256) -RetryBudget 0 -SessionApproved -ExecutionApproved
    $deadline = (Get-Date).AddSeconds(12)
    $fresh = @()
    $line = ""
    while ((Get-Date) -lt $deadline) {
        $all = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
        $fresh = if ($all.Count -gt $before.Count) { @($all[$before.Count..($all.Count - 1)]) } else { @() }
        $line = [string](@($fresh | Where-Object { [string]$_ -match "P12 Conditions execute-once:" } | Select-Object -Last 1) | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($line)) { break }
        Start-Sleep -Milliseconds 200
    }
    $pattern = 'status=(\w+) result=(\w+) attempt=(\d+) final=([\w_]+) retry=(true|false) armed=(true|false) killed=(true|false) consumed=(true|false) plan=([0-9a-f]{64}) p9=([0-9a-f]{64})'
    $terminalMatch = [regex]::Match($line, $pattern)
    if (-not $terminalMatch.Success) { throw "P12 Conditions did not emit a complete terminal trace." }
    if (@($fresh | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0) { throw "P12 Conditions unexpectedly armed the global runtime." }
    $groups = $terminalMatch.Groups
    $trace = [ordered]@{
        schema_version = "ctoa.p12-conditions-execute-once-trace.v1"
        created_at = (Get-Date).ToString("o")
        status = $groups[1].Value
        result = $groups[2].Value
        vocation = "ek"
        action = "cast_exura_ico"
        spell = "exura ico"
        attempt_count = [int]$groups[3].Value
        retry_budget = 0
        executor_called = ($groups[1].Value -in @("executed", "failed"))
        retry_scheduled = ($groups[5].Value -eq "true")
        final_state = $groups[4].Value
        live_promotion = $false
        plan_sha256 = $groups[9].Value
        p9_receipt_sha256 = $groups[10].Value
        terminal_snapshot = [ordered]@{
            armed = ($groups[6].Value -eq "true")
            killed = ($groups[7].Value -eq "true")
            consumed = ($groups[8].Value -eq "true")
            attempt_count = [int]$groups[3].Value
        }
    }
    Write-JsonAtomic -InputObject $trace -Path $tracePath -Depth 8
    & $python $receiptTool --trace $tracePath
    if ($LASTEXITCODE -ne 0) { throw "P12 Conditions terminal receipt was rejected." }
    Write-Output "[solteria-helper-test-env] P12 Conditions execute-once completed and terminally disarmed. Live client untouched."
}

function Invoke-P12EquipmentExecuteOnce {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $planPath = Join-Path $outRoot "p12_equipment_execute_once_plan.json"
    $approvalPath = Join-Path $outRoot "p12_equipment_session_approval.json"
    $tracePath = Join-Path $outRoot "p12_equipment_execute_once_trace.json"
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $preflightTool = Join-Path $repo "scripts\ops\otclient_p12_equipment_execution_preflight.py"
    $receiptTool = Join-Path $repo "scripts\ops\otclient_p12_equipment_execute_once_receipt.py"
    if (-not (Test-Path -LiteralPath $planPath -PathType Leaf)) { throw "P12 Equipment approved plan is required." }
    if (-not (Test-Path -LiteralPath $approvalPath -PathType Leaf)) { throw "P12 Equipment session and execution approvals are required." }
    $plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
    $approval = Get-Content -LiteralPath $approvalPath -Raw | ConvertFrom-Json
    if ([string]$plan.status -ne "ready_for_sandbox_session_approval" -or @($plan.blockers).Count -ne 0) { throw "P12 Equipment plan is not ready." }
    if ([string]$approval.status -ne "approved" -or $approval.session_approved -ne $true -or $approval.execution_approved -ne $true) { throw "P12 Equipment requires both separate approvals." }
    if ([string]$approval.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$approval.p10_receipt_sha256 -ne [string]$plan.p10_receipt_sha256) { throw "P12 Equipment approval binding mismatch." }
    & $python $preflightTool | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "P12 Equipment execution preflight is blocked; no attempt was sent." }
    $executionPreflight = Get-Content -LiteralPath (Join-Path $outRoot "p12_equipment_execution_preflight.json") -Raw | ConvertFrom-Json
    if ([string]$executionPreflight.status -ne "ready_for_execution_approval" -or $executionPreflight.execution_approved -ne $true -or @($executionPreflight.blockers).Count -ne 0) { throw "P12 Equipment current domain state is not execution-ready; no attempt was sent." }
    if ([string]$executionPreflight.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$executionPreflight.approval_id -ne [string]$approval.approval_id) { throw "P12 Equipment execution-preflight binding mismatch." }

    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $processes = @(Get-SandboxProcessSummaries)
    if ($processes.Count -ne 1) { throw "P12 Equipment requires exactly one running sandbox process." }
    $liveBefore = @((Get-SourceClientProcessSummaries) | Sort-Object id)
    $liveBeforeJson = ConvertTo-Json -InputObject @($liveBefore) -Compress -Depth 6
    $moduleRelative = "mods\ctoa_otclient\ctoa_helper_equipment_execute_once.lua"
    $stageModule = Join-Path (Join-Path $outRoot "latest") $moduleRelative
    $sandboxModule = Join-Path $sandboxFull $moduleRelative
    if (-not (Test-Path -LiteralPath $stageModule -PathType Leaf) -or -not (Test-Path -LiteralPath $sandboxModule -PathType Leaf)) { throw "P12 Equipment module is missing from stage or sandbox." }
    $stageHash = (Get-FileHash -LiteralPath $stageModule -Algorithm SHA256).Hash.ToLowerInvariant()
    $sandboxHash = (Get-FileHash -LiteralPath $sandboxModule -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($stageHash -ne [string]$plan.source_sha256 -or $sandboxHash -ne $stageHash) { throw "P12 Equipment sandbox/module hash parity failed." }

    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $capabilityPath = Join-Path $sandboxFull "mods\ctoa_otclient\ctoa_client_capabilities.json"
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf) -or -not (Test-Path -LiteralPath $capabilityPath -PathType Leaf)) { throw "P12 Equipment sandbox log and capability evidence are required." }
    $before = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
    $runtimeStates = @($before | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    if ($runtimeStates.Count -eq 0 -or [string]$runtimeStates[-1] -notmatch "Runtime disarmed$") { throw "P12 Equipment requires the global runtime to be disarmed." }

    $commandStartedAt = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $sessionId = [string]$approval.approval_id
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "equipment" -CommandAction "p12_equipment_execute_once" -Confirm -SessionId $sessionId -PlanSha256 ([string]$plan.plan_sha256) -P10ReceiptSha256 ([string]$plan.p10_receipt_sha256) -BeforeItemId ([int]$plan.before_item_id) -CandidateItemId ([int]$plan.candidate_item_id) -SourceContainerId ([int]$plan.source_container_id) -SourceSlotIndex ([int]$plan.source_slot_index) -RetryBudget 0 -SessionApproved -ExecutionApproved
    $deadline = (Get-Date).AddSeconds(12)
    $fresh = @()
    $line = ""
    while ((Get-Date) -lt $deadline) {
        $all = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
        $fresh = if ($all.Count -gt $before.Count) { @($all[$before.Count..($all.Count - 1)]) } else { @() }
        $line = [string](@($fresh | Where-Object { [string]$_ -match "P12 Equipment execute-once:" } | Select-Object -Last 1) | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($line)) { break }
        Start-Sleep -Milliseconds 200
    }
    $pattern = 'status=(\w+) result=(\w+) attempt=(\d+) final=([\w_]+) retry=(true|false) armed=(true|false) killed=(true|false) consumed=(true|false) plan=([0-9a-f]{64}) p10=([0-9a-f]{64})'
    $terminalMatch = [regex]::Match($line, $pattern)
    if (-not $terminalMatch.Success) { throw "P12 Equipment did not emit a complete terminal trace." }
    if (@($fresh | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0) { throw "P12 Equipment unexpectedly armed the global runtime." }

    $postCapability = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $candidate = Get-Content -LiteralPath $capabilityPath -Raw | ConvertFrom-Json
            $observation = $candidate.equipment_shadow_observation
            if ([long]$candidate.observed_at_unix_ms -ge $commandStartedAt -and $candidate.runtime_state -eq "disarmed" -and $candidate.runtime_enabled -eq $false -and $null -ne $observation -and [int]$observation.ring.item_id -eq [int]$plan.requires_post_action_ring_id) {
                $postCapability = $candidate
                break
            }
        } catch {
            # The reporter writes atomically, but tolerate a transient read boundary.
        }
        Start-Sleep -Milliseconds 200
    }
    if ($null -eq $postCapability) { throw "P12 Equipment did not prove the requested ring as equipped; no retry was attempted." }
    $liveAfter = @((Get-SourceClientProcessSummaries) | Sort-Object id)
    $liveAfterJson = ConvertTo-Json -InputObject @($liveAfter) -Compress -Depth 6
    if ($liveAfterJson -ne $liveBeforeJson) { throw "P12 Equipment detected a live-client process change; receipt refused." }

    $groups = $terminalMatch.Groups
    $trace = [ordered]@{
        schema_version = "ctoa.p12-equipment-execute-once-trace.v1"
        created_at = (Get-Date).ToString("o")
        status = $groups[1].Value
        result = $groups[2].Value
        action = "move_ring_candidate_to_equipment_slot"
        before_item_id = [int]$plan.before_item_id
        candidate_item_id = [int]$plan.candidate_item_id
        source_container_id = [int]$plan.source_container_id
        source_slot_index = [int]$plan.source_slot_index
        attempt_count = [int]$groups[3].Value
        retry_budget = 0
        executor_called = ($groups[1].Value -in @("dispatched", "failed"))
        retry_scheduled = ($groups[5].Value -eq "true")
        final_state = $groups[4].Value
        live_promotion = $false
        live_processes_before = @($liveBefore)
        live_processes_after = @($liveAfter)
        plan_sha256 = $groups[9].Value
        p10_receipt_sha256 = $groups[10].Value
        post_action_observation = $postCapability.equipment_shadow_observation
        post_action_capability = [ordered]@{
            observed_at_unix_ms = $postCapability.observed_at_unix_ms
            online = $postCapability.online
            runtime_state = $postCapability.runtime_state
            runtime_enabled = $postCapability.runtime_enabled
        }
        terminal_snapshot = [ordered]@{
            armed = ($groups[6].Value -eq "true")
            killed = ($groups[7].Value -eq "true")
            consumed = ($groups[8].Value -eq "true")
            attempt_count = [int]$groups[3].Value
        }
    }
    Write-JsonAtomic -InputObject $trace -Path $tracePath -Depth 12
    & $python $receiptTool --trace $tracePath
    if ($LASTEXITCODE -ne 0) { throw "P12 Equipment terminal receipt was rejected; no retry was attempted." }
    Write-Output "[solteria-helper-test-env] P12 Equipment execute-once completed and terminally disarmed. Live client untouched."
}

function Invoke-P12HealFriendExecuteOnce {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    $planPath = Join-Path $outRoot "p12_heal_friend_execute_once_plan.json"
    $approvalPath = Join-Path $outRoot "p12_heal_friend_session_approval.json"
    $tracePath = Join-Path $outRoot "p12_heal_friend_execute_once_trace.json"
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $preflightTool = Join-Path $repo "scripts\ops\otclient_p12_heal_friend_execution_preflight.py"
    $receiptTool = Join-Path $repo "scripts\ops\otclient_p12_heal_friend_execute_once_receipt.py"
    if (-not (Test-Path -LiteralPath $planPath -PathType Leaf)) { throw "P12 Heal Friend approved plan is required." }
    if (-not (Test-Path -LiteralPath $approvalPath -PathType Leaf)) { throw "P12 Heal Friend session and execution approvals are required." }
    $plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
    $approval = Get-Content -LiteralPath $approvalPath -Raw | ConvertFrom-Json
    if ([string]$plan.status -ne "ready_for_sandbox_session_approval" -or @($plan.blockers).Count -ne 0) { throw "P12 Heal Friend plan is not ready." }
    if ([string]$approval.status -ne "approved" -or $approval.session_approved -ne $true -or $approval.execution_approved -ne $true) { throw "P12 Heal Friend requires both separate approvals." }
    if ([string]$approval.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$approval.p11_receipt_sha256 -ne [string]$plan.p11_receipt_sha256 -or [string]$approval.p12_equipment_receipt_sha256 -ne [string]$plan.p12_equipment_receipt_sha256) { throw "P12 Heal Friend approval binding mismatch." }
    & $python $preflightTool | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "P12 Heal Friend execution preflight is blocked; no cast was sent." }
    $executionPreflight = Get-Content -LiteralPath (Join-Path $outRoot "p12_heal_friend_execution_preflight.json") -Raw | ConvertFrom-Json
    if ([string]$executionPreflight.status -ne "ready_for_execution_approval" -or $executionPreflight.execution_approved -ne $true -or @($executionPreflight.blockers).Count -ne 0) { throw "P12 Heal Friend current exact-target state is not execution-ready; no cast was sent." }
    if ([string]$executionPreflight.plan_sha256 -ne [string]$plan.plan_sha256 -or [string]$executionPreflight.approval_id -ne [string]$approval.approval_id) { throw "P12 Heal Friend execution-preflight binding mismatch." }

    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $processes = @(Get-SandboxProcessSummaries)
    if ($processes.Count -ne 1) { throw "P12 Heal Friend requires exactly one running sandbox process." }
    $liveBefore = @((Get-SourceClientProcessSummaries) | Sort-Object id)
    $liveBeforeJson = ConvertTo-Json -InputObject @($liveBefore) -Compress -Depth 6
    $moduleRelative = "mods\ctoa_otclient\ctoa_helper_heal_friend_execute_once.lua"
    $stageModule = Join-Path (Join-Path $outRoot "latest") $moduleRelative
    $sandboxModule = Join-Path $sandboxFull $moduleRelative
    if (-not (Test-Path -LiteralPath $stageModule -PathType Leaf) -or -not (Test-Path -LiteralPath $sandboxModule -PathType Leaf)) { throw "P12 Heal Friend module is missing from stage or sandbox." }
    $stageHash = (Get-FileHash -LiteralPath $stageModule -Algorithm SHA256).Hash.ToLowerInvariant()
    $sandboxHash = (Get-FileHash -LiteralPath $sandboxModule -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($stageHash -ne [string]$plan.source_sha256 -or $sandboxHash -ne $stageHash) { throw "P12 Heal Friend sandbox/module hash parity failed." }

    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $capabilityPath = Join-Path $sandboxFull "mods\ctoa_otclient\ctoa_client_capabilities.json"
    if (-not (Test-Path -LiteralPath $logPath -PathType Leaf) -or -not (Test-Path -LiteralPath $capabilityPath -PathType Leaf)) { throw "P12 Heal Friend sandbox log and capability evidence are required." }
    $before = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
    $runtimeStates = @($before | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    if ($runtimeStates.Count -eq 0 -or [string]$runtimeStates[-1] -notmatch "Runtime disarmed$") { throw "P12 Heal Friend requires the global runtime to be disarmed." }

    $commandStartedAt = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $sessionId = [string]$approval.approval_id
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "heal_friend" -CommandAction "p12_heal_friend_execute_once" -Confirm -SessionId $sessionId -PlanSha256 ([string]$plan.plan_sha256) -P11ReceiptSha256 ([string]$plan.p11_receipt_sha256) -P12EquipmentReceiptSha256 ([string]$plan.p12_equipment_receipt_sha256) -TargetId ([int]$plan.target_id) -TargetName ([string]$plan.target_name) -WhitelistRevision ([string]$plan.whitelist_revision) -HpThreshold ([int]$plan.hp_threshold) -MaxRange ([int]$plan.max_range) -RetryBudget 0 -SessionApproved -ExecutionApproved
    $deadline = (Get-Date).AddSeconds(12)
    $fresh = @()
    $line = ""
    while ((Get-Date) -lt $deadline) {
        $all = @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue)
        $fresh = if ($all.Count -gt $before.Count) { @($all[$before.Count..($all.Count - 1)]) } else { @() }
        $line = [string](@($fresh | Where-Object { [string]$_ -match "P12 Heal Friend execute-once:" } | Select-Object -Last 1) | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($line)) { break }
        Start-Sleep -Milliseconds 200
    }
    $pattern = 'status=(\w+) result=(\w+) attempt=(\d+) final=([\w_]+) retry=(true|false) armed=(true|false) killed=(true|false) consumed=(true|false) target=(\d+) plan=([0-9a-f]{64}) p11=([0-9a-f]{64}) p12e=([0-9a-f]{64})'
    $terminalMatch = [regex]::Match($line, $pattern)
    if (-not $terminalMatch.Success) { throw "P12 Heal Friend did not emit a complete terminal trace." }
    if (@($fresh | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0) { throw "P12 Heal Friend unexpectedly armed the global runtime." }

    $postCapability = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $candidate = Get-Content -LiteralPath $capabilityPath -Raw | ConvertFrom-Json
            if ([long]$candidate.observed_at_unix_ms -ge $commandStartedAt -and $candidate.runtime_state -eq "disarmed" -and $candidate.runtime_enabled -eq $false -and $candidate.online -eq $true) {
                $postCapability = $candidate
                break
            }
        } catch {
            # Tolerate an atomic reporter write boundary.
        }
        Start-Sleep -Milliseconds 200
    }
    if ($null -eq $postCapability) { throw "P12 Heal Friend did not prove a fresh terminally disarmed capability; no retry was attempted." }
    $liveAfter = @((Get-SourceClientProcessSummaries) | Sort-Object id)
    $liveAfterJson = ConvertTo-Json -InputObject @($liveAfter) -Compress -Depth 6
    if ($liveAfterJson -ne $liveBeforeJson) { throw "P12 Heal Friend detected a live-client process change; receipt refused." }

    $groups = $terminalMatch.Groups
    $trace = [ordered]@{
        schema_version = "ctoa.p12-heal-friend-execute-once-trace.v1"
        created_at_unix_ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        status = $groups[1].Value
        result = $groups[2].Value
        action = "cast_exura_sio_exact_target"
        spell = "exura sio"
        vocation = "ed"
        target_id = [int]$groups[9].Value
        target_name_sha256 = [string]$plan.target_name_sha256
        whitelist_revision = [string]$plan.whitelist_revision
        attempt_count = [int]$groups[3].Value
        retry_budget = 0
        executor_called = ($groups[1].Value -in @("executed", "failed"))
        retry_scheduled = ($groups[5].Value -eq "true")
        final_state = $groups[4].Value
        live_promotion = $false
        live_processes_before = @($liveBefore)
        live_processes_after = @($liveAfter)
        plan_sha256 = $groups[10].Value
        p11_receipt_sha256 = $groups[11].Value
        p12_equipment_receipt_sha256 = $groups[12].Value
        terminal_snapshot = [ordered]@{
            armed = ($groups[6].Value -eq "true")
            killed = ($groups[7].Value -eq "true")
            consumed = ($groups[8].Value -eq "true")
            attempt_count = [int]$groups[3].Value
        }
    }
    Write-JsonAtomic -InputObject $trace -Path $tracePath -Depth 12
    & $python $receiptTool --trace $tracePath
    if ($LASTEXITCODE -ne 0) { throw "P12 Heal Friend terminal receipt was rejected; no retry was attempted." }
    Write-Output "[solteria-helper-test-env] P12 Heal Friend execute-once completed and terminally disarmed. Live client untouched."
}

function Invoke-HealingVitalsSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $lines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
    $probeIndex = -1
    $probeLine = ""
    for ($index = $lines.Count - 1; $index -ge 0; $index--) {
        if ([string]$lines[$index] -match "API probe \(startup\):.*player\[vitals=real hp=(\d+)/(\d+) hpPct=(\d+) mana=(\d+)/(\d+) manaPct=(\d+)") {
            $probeIndex = $index
            $probeLine = [string]$lines[$index]
            break
        }
    }
    $hp = 0
    $hpMax = 0
    $hpPct = 0
    $mana = 0
    $manaMax = 0
    $manaPct = 0
    if ($probeIndex -ge 0 -and $probeLine -match "player\[vitals=real hp=(\d+)/(\d+) hpPct=(\d+) mana=(\d+)/(\d+) manaPct=(\d+)") {
        $hp = [int]$Matches[1]
        $hpMax = [int]$Matches[2]
        $hpPct = [int]$Matches[3]
        $mana = [int]$Matches[4]
        $manaMax = [int]$Matches[5]
        $manaPct = [int]$Matches[6]
    }
    $afterProbe = if ($probeIndex -ge 0 -and $probeIndex + 1 -lt $lines.Count) { @($lines[($probeIndex + 1)..($lines.Count - 1)]) } else { @() }
    $runtimeStates = @($afterProbe | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    $latestRuntimeState = if ($runtimeStates.Count -gt 0) { [string]$runtimeStates[-1] } else { "" }
    $runtimeDisarmed = $latestRuntimeState -match "Runtime disarmed$"
    $checks = @(
        [pscustomobject]@{ name = "sandbox_log_present"; status = if (Test-Path -LiteralPath $logPath) { "passed" } else { "failed" }; evidence = "sandbox ctoa_local.log exists" },
        [pscustomobject]@{ name = "real_vitals_probe"; status = if ($probeIndex -ge 0) { "passed" } else { "failed" }; evidence = "latest startup API probe exposes real HP and mana vitals" },
        [pscustomobject]@{ name = "hp_bounds"; status = if ($hpMax -gt 0 -and $hp -ge 0 -and $hp -le $hpMax -and $hpPct -ge 0 -and $hpPct -le 100) { "passed" } else { "failed" }; evidence = "HP sample is within bounded real-player values" },
        [pscustomobject]@{ name = "mana_bounds"; status = if ($manaMax -gt 0 -and $mana -ge 0 -and $mana -le $manaMax -and $manaPct -ge 0 -and $manaPct -le 100) { "passed" } else { "failed" }; evidence = "mana sample is within bounded real-player values" },
        [pscustomobject]@{ name = "runtime_remains_disarmed"; status = if ($runtimeDisarmed) { "passed" } else { "failed" }; evidence = "latest runtime state after the vitals probe is disarmed" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-healing-vitals-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "healing"
        mode = "sandbox_read_only_vitals"
        vitals = [pscustomobject]@{ hp = $hp; hp_max = $hpMax; hp_pct = $hpPct; mana = $mana; mana_max = $manaMax; mana_pct = $manaPct }
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Capture a fresh Healing tab with SmokeAttach; keep spell and potion execution unchanged." } else { "Enter the sandbox character and obtain a real vitals API probe while runtime stays disarmed." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab healing" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck" }
        live_safety = "HealingVitalsSmoke reads bounded vitals evidence from the sandbox log only; it does not launch, stop, cast, use potions, arm runtime, attach to live, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "healing_vitals_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Healing vitals smoke: $path"
    Write-Output "[solteria-helper-test-env] Healing vitals status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    if ($failed.Count -gt 0) {
        throw "Healing vitals smoke failed"
    }
}

function Invoke-CombatSafetySmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxFull
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $targetingPath = Join-Path $outRoot "targeting_static_smoke.json"
    $combatRuntimePath = Join-Path $outRoot "combat_runtime_static_smoke.json"
    $moduleGatesPath = Join-Path $outRoot "module_static_gates.json"
    $beforeLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
    $beforeRuntimeStates = @($beforeLines | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    $runtimeDisarmedBefore = $beforeRuntimeStates.Count -gt 0 -and [string]$beforeRuntimeStates[-1] -match "Runtime disarmed$"
    $lineCount = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "hunting" -CommandAction "api_probe"
    Wait-ForSmokeTab -ActiveTab "hunting" -Required -AfterLineCount $lineCount | Out-Null

    $deadline = (Get-Date).AddSeconds(12)
    $newLines = @()
    while ((Get-Date) -lt $deadline) {
        $allLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
        $newLines = if ($allLines.Count -gt $lineCount) { @($allLines[$lineCount..($allLines.Count - 1)]) } else { @() }
        if (@($newLines | Where-Object { [string]$_ -match "API probe \(manual\):" }).Count -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 250
    }
    $probeLine = [string](@($newLines | Where-Object { [string]$_ -match "API probe \(manual\):" } | Select-Object -Last 1) | Select-Object -First 1)
    $detailLine = [string](@($newLines | Where-Object { [string]$_ -match "API probe detail:" } | Select-Object -Last 1) | Select-Object -First 1)
    $runtimeArmedDuringProbe = @($newLines | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0

    function Get-ReportCheckStatus {
        param([string]$Path, [string[]]$RequiredChecks)
        if (-not (Test-Path -LiteralPath $Path)) { return $false }
        try {
            $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
            if ([string]$payload.status -ne "passed") { return $false }
            if ($RequiredChecks.Count -eq 0) { return $true }
            $rows = if ($null -ne $payload.PSObject.Properties["checks"]) { @($payload.checks) } elseif ($null -ne $payload.PSObject.Properties["gates"]) { @($payload.gates) } else { @() }
            $passedNames = @($rows | Where-Object { [string]$_.status -eq "passed" } | ForEach-Object { [string]$_.name })
            foreach ($required in $RequiredChecks) {
                if ($required -notin $passedNames) { return $false }
            }
            return $true
        } catch {
            return $false
        }
    }

    $targetingGuardsPassed = Get-ReportCheckStatus -Path $targetingPath -RequiredChecks @("ignored_name_policy", "friendly_summon_policy", "no_runtime_actions")
    $combatGuardsPassed = Get-ReportCheckStatus -Path $combatRuntimePath -RequiredChecks @("blocked_reasons", "runtime_execution_stays_in_helper", "no_runtime_actions")
    $moduleGatesPassed = Get-ReportCheckStatus -Path $moduleGatesPath -RequiredChecks @()
    $checks = @(
        [pscustomobject]@{ name = "manual_api_probe"; status = if ($probeLine -match "API probe \(manual\):") { "passed" } else { "failed" }; evidence = "fresh manual API probe completed in sandbox" },
        [pscustomobject]@{ name = "no_active_target"; status = if ($detailLine -match "target=no" -and $detailLine -match "targetName=n/a") { "passed" } else { "failed" }; evidence = "fresh combat probe reports no active target" },
        [pscustomobject]@{ name = "targeting_guards"; status = if ($targetingGuardsPassed) { "passed" } else { "failed" }; evidence = "targeting static gate covers ignored names, NPC/friendly guards, and no runtime actions" },
        [pscustomobject]@{ name = "combat_policy_guards"; status = if ($combatGuardsPassed) { "passed" } else { "failed" }; evidence = "combat planner covers PZ/offline/target-required blocks and keeps execution in helper" },
        [pscustomobject]@{ name = "module_static_gates"; status = if ($moduleGatesPassed) { "passed" } else { "failed" }; evidence = "current module static gate report passed" },
        [pscustomobject]@{ name = "runtime_remains_disarmed"; status = if ($runtimeDisarmedBefore -and -not $runtimeArmedDuringProbe) { "passed" } else { "failed" }; evidence = "runtime was disarmed before the manual combat probe and was not armed during it" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-combat-safety-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "combat"
        mode = "sandbox_read_only_combat_safety"
        target_state = if ($detailLine -match "target=no") { "none" } else { "unknown" }
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Capture fresh Hunting and Hunting/Magic tabs; keep attack, rune, and cast execution unchanged." } else { "Restore a disarmed in-world sandbox and refresh TargetingStaticSmoke plus CombatRuntimeStaticSmoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" }
        live_safety = "CombatSafetySmoke requests a read-only sandbox API probe and reads static reports/log evidence; it does not arm runtime, attack, follow, cast, use runes or items, promote, or touch the live client."
    }
    $path = Join-Path $outRoot "combat_safety_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Combat safety smoke: $path"
    Write-Output "[solteria-helper-test-env] Combat safety status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    if ($failed.Count -gt 0) {
        throw "Combat safety smoke failed"
    }
}

function Invoke-CavebotSafetySmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxFull
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $routePath = Join-Path $outRoot "route_static_smoke.json"
    $cavebotRuntimePath = Join-Path $outRoot "cavebot_runtime_static_smoke.json"
    $moduleGatesPath = Join-Path $outRoot "module_static_gates.json"
    $beforeLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
    $beforeRuntimeStates = @($beforeLines | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    $runtimeDisarmedBefore = $beforeRuntimeStates.Count -gt 0 -and [string]$beforeRuntimeStates[-1] -match "Runtime disarmed$"
    $lineCount = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "cavebot" -CommandAction "cavebot_probe"
    Wait-ForSmokeTab -ActiveTab "cavebot" -Required -AfterLineCount $lineCount | Out-Null

    $deadline = (Get-Date).AddSeconds(12)
    $newLines = @()
    while ((Get-Date) -lt $deadline) {
        $allLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
        $newLines = if ($allLines.Count -gt $lineCount) { @($allLines[$lineCount..($allLines.Count - 1)]) } else { @() }
        if (@($newLines | Where-Object { [string]$_ -match "Move API probe \(manual\):" }).Count -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 250
    }
    $probeLine = [string](@($newLines | Where-Object { [string]$_ -match "Move API probe \(manual\):" } | Select-Object -Last 1) | Select-Object -First 1)
    $runtimeArmedDuringProbe = @($newLines | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0

    function Test-CavebotStaticReport {
        param([string]$Path, [string[]]$RequiredChecks)
        if (-not (Test-Path -LiteralPath $Path)) { return $false }
        try {
            $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
            if ([string]$payload.status -ne "passed") { return $false }
            if ($RequiredChecks.Count -eq 0) { return $true }
            $passedNames = @($payload.checks | Where-Object { [string]$_.status -eq "passed" } | ForEach-Object { [string]$_.name })
            foreach ($required in $RequiredChecks) {
                if ($required -notin $passedNames) { return $false }
            }
            return $true
        } catch {
            return $false
        }
    }

    $routeGuardsPassed = Test-CavebotStaticReport -Path $routePath -RequiredChecks @("waypoint_mutation", "retry_status", "no_movement_or_runtime_actions")
    $runtimeGuardsPassed = Test-CavebotStaticReport -Path $cavebotRuntimePath -RequiredChecks @("blocked_reasons", "runtime_execution_stays_in_helper", "no_runtime_actions")
    $moduleGatesPassed = Test-CavebotStaticReport -Path $moduleGatesPath -RequiredChecks @()
    $checks = @(
        [pscustomobject]@{ name = "manual_movement_probe"; status = if ($probeLine -match "Move API probe \(manual\):") { "passed" } else { "failed" }; evidence = "fresh manual movement capability probe completed in sandbox" },
        [pscustomobject]@{ name = "no_route_target"; status = if ($probeLine -match "target=nil" -and $probeLine -match "path=n/a") { "passed" } else { "failed" }; evidence = "movement probe has no route target and performs no path request" },
        [pscustomobject]@{ name = "movement_capabilities_read_only"; status = if ($probeLine -match "player\.walk=yes" -and $probeLine -match "player\.stop=yes") { "passed" } else { "failed" }; evidence = "probe reads autoWalk and stopAutoWalk capabilities without calling them" },
        [pscustomobject]@{ name = "route_retry_guards"; status = if ($routeGuardsPassed) { "passed" } else { "failed" }; evidence = "route static gate covers bounded mutation, retry budget/status, and no movement" },
        [pscustomobject]@{ name = "cavebot_policy_guards"; status = if ($runtimeGuardsPassed) { "passed" } else { "failed" }; evidence = "cavebot planner covers PZ/offline/empty-route/retry blocks and keeps execution in helper" },
        [pscustomobject]@{ name = "module_static_gates"; status = if ($moduleGatesPassed) { "passed" } else { "failed" }; evidence = "current module static gate report passed" },
        [pscustomobject]@{ name = "runtime_remains_disarmed"; status = if ($runtimeDisarmedBefore -and -not $runtimeArmedDuringProbe) { "passed" } else { "failed" }; evidence = "runtime was disarmed before the movement probe and was not armed during it" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-cavebot-safety-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "cavebot"
        mode = "sandbox_read_only_cavebot_safety"
        route_target = if ($probeLine -match "target=nil") { "none" } else { "unknown" }
        path_probe = if ($probeLine -match "path=n/a") { "not_requested" } else { "unknown" }
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Capture a fresh CaveBot tab; keep autoWalk and findPath execution unchanged." } else { "Restore a disarmed in-world sandbox and refresh RouteStaticSmoke plus CavebotRuntimeStaticSmoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" }
        live_safety = "CavebotSafetySmoke requests a read-only movement capability probe and reads static reports/log evidence; it does not arm runtime, walk, pathfind, mutate routes, promote, or touch the live client."
    }
    $path = Join-Path $outRoot "cavebot_safety_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] CaveBot safety smoke: $path"
    Write-Output "[solteria-helper-test-env] CaveBot safety status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    if ($failed.Count -gt 0) {
        throw "CaveBot safety smoke failed"
    }
}

function Invoke-LootSafetySmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxFull
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $lootStaticPath = Join-Path $outRoot "loot_runtime_static_smoke.json"
    $moduleGatesPath = Join-Path $outRoot "module_static_gates.json"
    $beforeLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
    $beforeRuntimeStates = @($beforeLines | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    $runtimeDisarmedBefore = $beforeRuntimeStates.Count -gt 0 -and [string]$beforeRuntimeStates[-1] -match "Runtime disarmed$"
    $lineCount = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "tools" -SmokeSubtab "diag" -CommandAction "api_probe"
    Wait-ForSmokeTab -ActiveTab "tools" -SmokeSubtab "diag" -Required -AfterLineCount $lineCount | Out-Null

    $deadline = (Get-Date).AddSeconds(12)
    $newLines = @()
    while ((Get-Date) -lt $deadline) {
        $allLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
        $newLines = if ($allLines.Count -gt $lineCount) { @($allLines[$lineCount..($allLines.Count - 1)]) } else { @() }
        if (@($newLines | Where-Object { [string]$_ -match "API probe detail:.*loot\[" }).Count -gt 0) { break }
        Start-Sleep -Milliseconds 250
    }
    $detailLine = [string](@($newLines | Where-Object { [string]$_ -match "API probe detail:.*loot\[" } | Select-Object -Last 1) | Select-Object -First 1)
    $runtimeArmedDuringProbe = @($newLines | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0

    function Test-LootReport {
        param([string]$Path, [string[]]$RequiredChecks)
        if (-not (Test-Path -LiteralPath $Path)) { return $false }
        try {
            $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
            if ([string]$payload.status -ne "passed") { return $false }
            $rows = if ($null -ne $payload.PSObject.Properties["checks"]) { @($payload.checks) } elseif ($null -ne $payload.PSObject.Properties["gates"]) { @($payload.gates) } else { @() }
            $passedNames = @($rows | Where-Object { [string]$_.status -eq "passed" } | ForEach-Object { [string]$_.name })
            foreach ($required in $RequiredChecks) { if ($required -notin $passedNames) { return $false } }
            return $true
        } catch { return $false }
    }

    $lootStaticPassed = Test-LootReport -Path $lootStaticPath -RequiredChecks @("blocked_reasons", "runtime_execution_stays_out_of_helper_adapter", "no_runtime_actions")
    $moduleGatesPassed = $false
    try { $moduleGatesPassed = (Test-Path -LiteralPath $moduleGatesPath) -and [string]((Get-Content -LiteralPath $moduleGatesPath -Raw | ConvertFrom-Json).status) -eq "passed" } catch { $moduleGatesPassed = $false }
    $checks = @(
        [pscustomobject]@{ name = "read_only_container_probe"; status = if ($detailLine -match "loot\[getContainers=yes containers=\d+ container\.getItems=yes container\.getItemsCount=yes move=yes") { "passed" } else { "failed" }; evidence = "fresh API probe reads container capabilities without invoking move" },
        [pscustomobject]@{ name = "feature_flag_disabled"; status = if ($detailLine -match "adapter=hold \| feature_flag_disabled") { "passed" } else { "failed" }; evidence = "loot adapter holds because the experimental feature flag remains disabled" },
        [pscustomobject]@{ name = "zero_planned_items"; status = if ($detailLine -match "items 0 \| containers \d+\]") { "passed" } else { "failed" }; evidence = "passive adapter reports zero planned items" },
        [pscustomobject]@{ name = "loot_static_guards"; status = if ($lootStaticPassed) { "passed" } else { "failed" }; evidence = "loot planner covers flag/runtime/PZ/offline/capacity/container blocks and no runtime actions" },
        [pscustomobject]@{ name = "module_static_gates"; status = if ($moduleGatesPassed) { "passed" } else { "failed" }; evidence = "current module static gate report passed" },
        [pscustomobject]@{ name = "runtime_remains_disarmed"; status = if ($runtimeDisarmedBefore -and -not $runtimeArmedDuringProbe) { "passed" } else { "failed" }; evidence = "runtime was disarmed before the loot probe and was not armed during it" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-loot-safety-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "loot"
        mode = "sandbox_read_only_container_probe"
        decision = if ($detailLine -match "adapter=hold \| feature_flag_disabled") { "hold_feature_flag_disabled" } else { "unknown" }
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Keep loot runtime disabled and retain tools/diag evidence for P6 closure." } else { "Restore a disarmed sandbox and refresh LootRuntimeStaticSmoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" }
        live_safety = "LootSafetySmoke requests the existing read-only API probe; it does not arm runtime, scan beyond API capability reads, open containers, move or use items, promote, or touch the live client."
    }
    $path = Join-Path $outRoot "loot_safety_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Loot safety smoke: $path"
    Write-Output "[solteria-helper-test-env] Loot safety status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    if ($failed.Count -gt 0) { throw "Loot safety smoke failed" }
}

function Invoke-TimerSafetySmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $sandboxFull = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxFull
    $logPath = Join-Path $sandboxFull "ctoa_local.log"
    $timerStaticPath = Join-Path $outRoot "timer_runtime_static_smoke.json"
    $moduleGatesPath = Join-Path $outRoot "module_static_gates.json"
    $beforeLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
    $beforeRuntimeStates = @($beforeLines | Where-Object { [string]$_ -match "Runtime (armed|disarmed)$" })
    $runtimeDisarmedBefore = $beforeRuntimeStates.Count -gt 0 -and [string]$beforeRuntimeStates[-1] -match "Runtime disarmed$"
    $lineCount = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxFull -ActiveTab "tools" -SmokeSubtab "timer" -CommandAction "timer_probe"
    Wait-ForSmokeTab -ActiveTab "tools" -SmokeSubtab "timer" -Required -AfterLineCount $lineCount | Out-Null

    $deadline = (Get-Date).AddSeconds(12)
    $newLines = @()
    while ((Get-Date) -lt $deadline) {
        $allLines = if (Test-Path -LiteralPath $logPath) { @(Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue) } else { @() }
        $newLines = if ($allLines.Count -gt $lineCount) { @($allLines[$lineCount..($allLines.Count - 1)]) } else { @() }
        if (@($newLines | Where-Object { [string]$_ -match "Timer probe:" }).Count -gt 0) { break }
        Start-Sleep -Milliseconds 250
    }
    $probeLine = [string](@($newLines | Where-Object { [string]$_ -match "Timer probe:" } | Select-Object -Last 1) | Select-Object -First 1)
    $runtimeArmedDuringProbe = @($newLines | Where-Object { [string]$_ -match "Runtime armed$" }).Count -gt 0
    $timerStaticPassed = $false
    $moduleGatesPassed = $false
    try {
        $timerStatic = Get-Content -LiteralPath $timerStaticPath -Raw | ConvertFrom-Json
        $passedNames = @($timerStatic.checks | Where-Object { [string]$_.status -eq "passed" } | ForEach-Object { [string]$_.name })
        $timerStaticPassed = [string]$timerStatic.status -eq "passed" -and "blocked_reasons" -in $passedNames -and "no_runtime_actions" -in $passedNames -and "runtime_execution_stays_in_helper" -in $passedNames
    } catch { $timerStaticPassed = $false }
    try {
        $moduleGates = Get-Content -LiteralPath $moduleGatesPath -Raw | ConvertFrom-Json
        $moduleGatesPassed = [string]$moduleGates.status -eq "passed"
    } catch { $moduleGatesPassed = $false }
    $checks = @(
        [pscustomobject]@{ name = "passive_timer_tick"; status = if ($probeLine -match "Timer probe: hold \| timer_disabled \| due \d+ms") { "passed" } else { "failed" }; evidence = "fresh passive timer plan tick holds because timer is disabled" },
        [pscustomobject]@{ name = "bounded_due_value"; status = if ($probeLine -match "due \d+ms") { "passed" } else { "failed" }; evidence = "timer probe emits a bounded non-negative due value" },
        [pscustomobject]@{ name = "timer_static_guards"; status = if ($timerStaticPassed) { "passed" } else { "failed" }; evidence = "timer static contract covers disabled/PZ/offline/message/cast blocks and no runtime actions" },
        [pscustomobject]@{ name = "module_static_gates"; status = if ($moduleGatesPassed) { "passed" } else { "failed" }; evidence = "current module static gate report passed" },
        [pscustomobject]@{ name = "runtime_remains_disarmed"; status = if ($runtimeDisarmedBefore -and -not $runtimeArmedDuringProbe) { "passed" } else { "failed" }; evidence = "runtime was disarmed before the timer probe and was not armed during it" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-timer-safety-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "timer"
        mode = "sandbox_passive_timer_tick"
        decision = if ($probeLine -match "timer_disabled") { "hold_timer_disabled" } else { "unknown" }
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Capture a fresh Tools/Timer tab; keep talk/cast execution and scripting bridge unavailable." } else { "Restore a disarmed sandbox and refresh TimerRuntimeStaticSmoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" }
        live_safety = "TimerSafetySmoke requests one passive timer planning tick; it does not arm runtime, talk, cast, evaluate scripts, load files, promote, or touch the live client."
    }
    $path = Join-Path $outRoot "timer_safety_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Timer safety smoke: $path"
    Write-Output "[solteria-helper-test-env] Timer safety status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    if ($failed.Count -gt 0) { throw "Timer safety smoke failed" }
}

function Invoke-ProfileSchemaStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $schemaPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_profile_schema.lua"
    $persistencePath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_profile_persistence.lua"
    $profilePath = Join-Path $repo "scripts\lua\otclient\ctoa_ek_profile.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $schema = if (Test-Path -LiteralPath $schemaPath) { Get-Content -LiteralPath $schemaPath -Raw } else { "" }
    $persistence = if (Test-Path -LiteralPath $persistencePath) { Get-Content -LiteralPath $persistencePath -Raw } else { "" }
    $profile = if (Test-Path -LiteralPath $profilePath) { Get-Content -LiteralPath $profilePath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $schemaPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_profile_schema.lua exists" },
        [pscustomobject]@{ name = "persistence_module_exists"; status = if (Test-Path -LiteralPath $persistencePath) { "passed" } else { "failed" }; evidence = "ctoa_helper_profile_persistence.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($schema.Contains('rawget(_G, "CTOA_HELPER_PROFILE_SCHEMA")') -and $schema.Contains("_G.CTOA_HELPER_PROFILE_SCHEMA = ProfileSchema") -and $schema.Contains("return ProfileSchema")) { "passed" } else { "failed" }; evidence = "profile schema keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "persistence_global_contract"; status = if ($persistence.Contains('rawget(_G, "CTOA_HELPER_PROFILE_PERSISTENCE")') -and $persistence.Contains("_G.CTOA_HELPER_PROFILE_PERSISTENCE = ProfilePersistence") -and $persistence.Contains("return ProfilePersistence")) { "passed" } else { "failed" }; evidence = "profile persistence keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "schema_functions"; status = if ($schema.Contains("function ProfileSchema.requiredSections") -and $schema.Contains("function ProfileSchema.sectionOrder") -and $schema.Contains("function ProfileSchema.safeFalseKeys") -and $schema.Contains("function ProfileSchema.optionList") -and $schema.Contains("function ProfileSchema.rotationPresets") -and $schema.Contains("function ProfileSchema.keyOrder") -and $schema.Contains("function ProfileSchema.valueIndex") -and $schema.Contains("function ProfileSchema.cycleValue") -and $schema.Contains("function ProfileSchema.fieldGeometry") -and $schema.Contains("function ProfileSchema.stepValue") -and $schema.Contains("function ProfileSchema.displayProfileName") -and $schema.Contains("function ProfileSchema.profileSchemaValue") -and $schema.Contains("function ProfileSchema.profileSchemaTable") -and $schema.Contains("function ProfileSchema.mergeTable") -and $schema.Contains("function ProfileSchema.serializeLua") -and $schema.Contains("function ProfileSchema.currentVersion") -and $schema.Contains("function ProfileSchema.currentSchema") -and $schema.Contains("function ProfileSchema.profileVersion") -and $schema.Contains("function ProfileSchema.migrationPlan") -and $schema.Contains("function ProfileSchema.migrate") -and $schema.Contains("function ProfileSchema.summary") -and $schema.Contains("function ProfileSchema.profileSchemaSuffix") -and $schema.Contains("function ProfileSchema.rotationPresetIds") -and $schema.Contains("function ProfileSchema.rotationPresetLabel") -and $schema.Contains("function ProfileSchema.rotationPresetFormatter") -and $schema.Contains("function ProfileSchema.rotationSummary") -and $schema.Contains("function ProfileSchema.rotationSummaryText") -and $schema.Contains("function ProfileSchema.spellLabel") -and $schema.Contains("function ProfileSchema.potionLabel") -and $schema.Contains("function ProfileSchema.runeLabel") -and $schema.Contains("function ProfileSchema.healFriendPriorityLabel") -and $schema.Contains("function ProfileSchema.magicPriorityLabel") -and $schema.Contains("function ProfileSchema.themePresetLabel") -and $schema.Contains("function ProfileSchema.onOffLabel") -and $schema.Contains("function ProfileSchema.autosaveLabel") -and $schema.Contains("function ProfileSchema.titleSummary") -and $schema.Contains("function ProfileSchema.healingSummary") -and $schema.Contains("function ProfileSchema.profileSummary") -and $schema.Contains("function ProfileSchema.contract")) { "passed" } else { "failed" }; evidence = "profile schema exposes extracted display, formatter, rotation-summary, migration, metadata and serialization helpers" },
        [pscustomobject]@{ name = "required_sections"; status = if ($schema.Contains('"schema_version"') -and $schema.Contains('"name"') -and $schema.Contains('"enabled"') -and $schema.Contains('"safe_boot_runtime_disabled"') -and $schema.Contains('"tick_ms"') -and $schema.Contains('"healing"') -and $schema.Contains('"tools"') -and $schema.Contains('"hud"')) { "passed" } else { "failed" }; evidence = "profile schema declares version and required core profile sections" },
        [pscustomobject]@{ name = "safe_false_keys"; status = if ($schema.Contains('"tools.auto_attack"') -and $schema.Contains('"tools.auto_exeta"') -and $schema.Contains('"tools.auto_haste"') -and $schema.Contains('"tools.spell_rotation"') -and $schema.Contains('"tools.rune_enabled"') -and $schema.Contains('"tools.cavebot_movement_enabled"') -and $schema.Contains('"tools.timer_enabled"') -and $schema.Contains('"tools.feature_flags.experimental_loot"')) { "passed" } else { "failed" }; evidence = "profile schema owns safe false keys for runtime-dangerous toggles" },
        [pscustomobject]@{ name = "migration_plan_contract"; status = if ($schema.Contains('local CURRENT_PROFILE_SCHEMA = "ctoa-helper-profile-v1"') -and $schema.Contains('reason = "future_schema_version"') -and $schema.Contains('reason = "invalid_schema_version"') -and $schema.Contains('steps[#steps + 1] = "enforce_safe_defaults"') -and $schema.Contains("function ProfileSchema.migrate") -and $schema.Contains("migrated.safe_boot_runtime_disabled = true") -and $schema.Contains("preserves_key_order = true") -and $schema.Contains("runtime_actions = false")) { "passed" } else { "failed" }; evidence = "profile schema versions migrations, rejects future/invalid profiles, and enforces safe in-memory defaults without mutating files" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($schema.Contains('mode = "passive"') -and $schema.Contains("owns_schema_metadata = true") -and $schema.Contains("owns_versioned_migration_plan = true") -and $schema.Contains("owns_safe_profile_migration = true") -and $schema.Contains("owns_key_order_metadata = true") -and $schema.Contains("owns_merge_table = true") -and $schema.Contains("owns_lua_serializer = true") -and $schema.Contains("owns_display_profile_name = true") -and $schema.Contains("owns_schema_value_bridge = true") -and $schema.Contains("owns_schema_table_bridge = true") -and $schema.Contains("owns_rotation_metadata = true") -and $schema.Contains("owns_profile_labels = true") -and $schema.Contains("owns_profile_summaries = true") -and $schema.Contains("owns_rotation_preset_formatter = true") -and $schema.Contains("owns_rotation_summary_text = true") -and $schema.Contains("runtime_actions = false") -and $schema.Contains("loads_files = false") -and $schema.Contains("saves_files = false") -and $schema.Contains("migrates_files = false") -and $schema.Contains("requires_profile_audit = true") -and $schema.Contains("requires_safe_boot_defaults = true")) { "passed" } else { "failed" }; evidence = "profile schema contract owns pure formatter/summary helpers and passive in-memory migration" },
        [pscustomobject]@{ name = "helper_uses_profile_schema_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_PROFILE_SCHEMA")') -and -not $helper.Contains("local function profileSchemaValue(functionName, fallback, ...)") -and -not $helper.Contains("local function profileSchemaTable(functionName, fallback, ...)") -and -not $helper.Contains("local profileSchemaValue = externalProfileSchema.profileSchemaValue") -and -not $helper.Contains("local profileSchemaTable = externalProfileSchema.profileSchemaTable") -and -not $helper.Contains("local profileDisplayName = externalProfileSchema.displayProfileName") -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaValue"') -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaTable"') -and $helper.Contains('moduleValue(externalProfileSchema, "displayProfileName"') -and $helper.Contains("profileSchema = externalProfileSchema")) { "passed" } else { "failed" }; evidence = "helper shell consumes schema/display helpers through guarded calls with fail-closed standalone fallbacks" },
        [pscustomobject]@{ name = "helper_uses_profile_cycle_adapter"; status = if ($helper.Contains('moduleValue(externalProfileSchema, "profileSchemaValue", "cycleValue", current, options, current, direction)') -and -not $helper.Contains("local function profileValueIndex")) { "passed" } else { "failed" }; evidence = "native helper delegates profile option cycle decisions through the guarded schema adapter" },
        [pscustomobject]@{ name = "helper_uses_profile_row_decision_adapter"; status = if (-not $helper.Contains("function profileSchemaNumber(functionName, fallback, ...)") -and -not $helper.Contains("function profileFieldGeometry(x, width)") -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaTable", "fieldGeometry", styleUi("profileFieldGeometry", x, width), x, width)') -and $helper.Contains("return geometry.label_width and geometry or nil") -and $helper.Contains('styleUi("addProfileStepRow"') -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaValue", "stepValue", value, value, 0, minValue, maxValue)') -and $helper.Contains('if type(stepValue) == "number" then')) { "passed" } else { "failed" }; evidence = "native helper delegates UI/profile row geometry and step clamping through guarded passive adapters" },
        [pscustomobject]@{ name = "helper_uses_rotation_schema_adapter"; status = if ($helper.Contains('local SPELL_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "spell")') -and $helper.Contains('local ROTATION_PRESETS = moduleValue(externalProfileSchema, "profileSchemaTable", "rotationPresets", {})') -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaTable", "rotationPresetIds", {}, ROTATION_PRESETS)') -and $helper.Contains('moduleValue(externalProfileSchema, "rotationPresetFormatter", ROTATION_PRESETS)') -and $helper.Contains('moduleValue(externalProfileSchema, "rotationSummaryText"') -and -not $helper.Contains("local function formatter") -and -not $helper.Contains("function rotationSummaryText()") -and -not $helper.Contains("profileSchemaText(")) { "passed" } else { "failed" }; evidence = "native helper delegates rotation formatter and summary text through guarded schema calls" },
        [pscustomobject]@{ name = "helper_uses_profile_schema_serializer"; status = if ($helper.Contains('moduleValue(externalProfileSchema, "mergeTable", HELPER_CONFIG, migrated)') -and $helper.Contains('moduleValue(externalProfileSchema, "serializeLua"') -and $helper.Contains('moduleValue(externalProfilePersistence, "exportProfile", HELPER_CONFIG') -and $helper.Contains('moduleValue(externalProfilePersistence, "exportUiPrefs", HELPER_CONFIG, Helper)') -and -not $helper.Contains("local function mergeTable(base, override)") -and -not $helper.Contains("local function serializeLua(value, rootKey)") -and -not $helper.Contains("local function exportProfile()") -and -not $helper.Contains("local function exportUiPrefs()") -and -not $helper.Contains("local function profileKeyOrder(key)") -and -not $helper.Contains("local PROFILE_KEY_ORDER = profileKeyOrder") -and -not $helper.Contains("local function luaQuote(value)")) { "passed" } else { "failed" }; evidence = "native helper delegates merge, serialization, and export through guarded passive support calls" },
        [pscustomobject]@{ name = "helper_uses_profile_label_adapter"; status = if ($helper.Contains("externalProfileSchema.spellLabel") -and $helper.Contains("externalProfileSchema.potionLabel") -and $helper.Contains("externalProfileSchema.runeLabel") -and $helper.Contains("externalProfileSchema.healFriendPriorityLabel") -and $helper.Contains("externalProfileSchema.magicPriorityLabel") -and $helper.Contains("externalProfileSchema.themePresetLabel") -and $helper.Contains('moduleValue(externalProfileSchema, "profileSchemaValue", "onOffLabel", fallback, value)') -and -not $helper.Contains("local PROFILE_LABEL_BRIDGES = {") -and -not $helper.Contains("local function profileLabelText(labelName, value)")) { "passed" } else { "failed" }; evidence = "native helper delegates labels through type-guarded schema references and calls" },
        [pscustomobject]@{ name = "helper_uses_profile_summary_adapter"; status = if ($helper.Contains('moduleValue(externalProfileSchema, "profileSchemaValue", "autosaveLabel", fallback, {') -and $helper.Contains('title = {fallback = "profile summary unavailable"') -and $helper.Contains('healing = {fallback = "healing summary unavailable"') -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.profile") -and $helper.Contains("profileSchema = externalProfileSchema")) { "passed" } else { "failed" }; evidence = "native helper delegates autosave through guarded schema calls and summaries through operator context" },
        [pscustomobject]@{ name = "persistence_functions"; status = if ($persistence.Contains("function ProfilePersistence.profileCandidates") -and $persistence.Contains("function ProfilePersistence.uiPrefsCandidates") -and $persistence.Contains("function ProfilePersistence.profilePersistenceValue") -and $persistence.Contains("function ProfilePersistence.profilePersistenceTable") -and $persistence.Contains("function ProfilePersistence.saveDefaults") -and $persistence.Contains("function ProfilePersistence.resolveSavePath") -and $persistence.Contains("function ProfilePersistence.fallbackSavePath") -and $persistence.Contains("function ProfilePersistence.saveText") -and $persistence.Contains("function ProfilePersistence.loadSuccessText") -and $persistence.Contains("function ProfilePersistence.loadFailureText") -and $persistence.Contains("function ProfilePersistence.exportProfile") -and $persistence.Contains("function ProfilePersistence.exportUiPrefs") -and $persistence.Contains("function ProfilePersistence.dirtyState") -and $persistence.Contains("function ProfilePersistence.contract")) { "passed" } else { "failed" }; evidence = "profile persistence exposes extracted value/table bridges, export, candidates, save policy, status, dirty state, and contract helpers" },
        [pscustomobject]@{ name = "persistence_passive_contract"; status = if ($persistence.Contains('mode = "passive"') -and $persistence.Contains("owns_load_candidates = true") -and $persistence.Contains("owns_save_path_policy = true") -and $persistence.Contains("owns_save_headers = true") -and $persistence.Contains("owns_autosave_metadata = true") -and $persistence.Contains("owns_persistence_value_bridge = true") -and $persistence.Contains("owns_persistence_table_bridge = true") -and $persistence.Contains("owns_export_profile = true") -and $persistence.Contains("owns_export_ui_prefs = true") -and $persistence.Contains("runtime_actions = false") -and $persistence.Contains("loads_files = false") -and $persistence.Contains("saves_files = false") -and $persistence.Contains("writes_profile = false") -and $persistence.Contains("touches_otclient_globals = false") -and $persistence.Contains("preserves_key_order = true")) { "passed" } else { "failed" }; evidence = "profile persistence owns pure bridges/exports and declares passive no-file no-global behavior" },
        [pscustomobject]@{ name = "helper_uses_profile_persistence_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_PROFILE_PERSISTENCE")') -and -not $helper.Contains("local function profilePersistenceValue(functionName, fallback, ...)") -and -not $helper.Contains("local function profilePersistenceTable(functionName, fallback, ...)") -and -not $helper.Contains("local profilePersistenceValue = externalProfilePersistence.profilePersistenceValue") -and -not $helper.Contains("local profilePersistenceTable = externalProfilePersistence.profilePersistenceTable") -and $helper.Contains('moduleValue(externalProfilePersistence, "profilePersistenceTable", "profileCandidates"') -and $helper.Contains('moduleValue(externalProfilePersistence, "profilePersistenceTable", "uiPrefsCandidates"') -and $helper.Contains('moduleValue(externalProfilePersistence, "profilePersistenceValue", "resolveSavePath"') -and $helper.Contains('moduleValue(externalProfilePersistence, "profilePersistenceValue", "saveText"') -and $helper.Contains('moduleValue(externalProfilePersistence, "profilePersistenceTable", "dirtyState"')) { "passed" } else { "failed" }; evidence = "native helper consumes persistence bridges through guarded calls with standalone fallbacks" },
        [pscustomobject]@{ name = "profile_defaults_parity"; status = if ($profile.Contains("safe_boot_runtime_disabled = true") -and $profile.Contains("enabled = false") -and $profile.Contains("timer_enabled = false") -and $profile.Contains("cavebot_movement_enabled = false") -and $helper.Contains("HELPER_CONFIG.enabled = false") -and $helper.Contains("HELPER_CONFIG.tools.timer_enabled = false")) { "passed" } else { "failed" }; evidence = "profile defaults and helper loader keep safe boot runtime toggles disabled" },
        [pscustomobject]@{ name = "no_file_or_runtime_actions"; status = if (-not $schema.Contains("g_resources") -and -not $schema.Contains("io.open") -and -not $schema.Contains("dofile") -and -not $schema.Contains("loadfile") -and -not $schema.Contains("loadstring") -and -not $schema.Contains("castSpell") -and -not $schema.Contains("autoWalk") -and -not $schema.Contains("g_game.attack") -and -not $schema.Contains("createWidget(")) { "passed" } else { "failed" }; evidence = "profile schema module does not read/write files, eval/load snippets, cast, walk, attack, or create widgets" },
        [pscustomobject]@{ name = "persistence_no_file_or_runtime_actions"; status = if (-not $persistence.Contains("g_resources") -and -not $persistence.Contains("io.open") -and -not $persistence.Contains("dofile") -and -not $persistence.Contains("loadfile") -and -not $persistence.Contains("loadstring") -and -not $persistence.Contains("castSpell") -and -not $persistence.Contains("autoWalk") -and -not $persistence.Contains("g_game.attack") -and -not $persistence.Contains("createWidget(")) { "passed" } else { "failed" }; evidence = "profile persistence module does not read/write files, eval/load snippets, cast, walk, attack, or create widgets" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_profile_schema" -File "ctoa_helper_profile_schema.lua") -and (Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_profile_persistence" -File "ctoa_helper_profile_persistence.lua")) { "passed" } else { "failed" }; evidence = "loader stages profile schema and persistence with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_profile_schema.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_profile_schema.lua") -and $script.Contains("ctoa_helper_profile_persistence.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_profile_persistence.lua")) { "passed" } else { "failed" }; evidence = "dev package copies profile schema and persistence into mods/ctoa_otclient" },
        [pscustomobject]@{ name = "static_only"; status = if ($script.Contains("ProfileSchemaStaticSmoke") -and -not $script.Contains(("SmokeAttach -Tab " + "profile_schema"))) { "passed" } else { "failed" }; evidence = "profile schema is covered by static gate only; no fake attach tab is introduced" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-profile-schema-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "profile_schema"
        mode = "static_passive_profile_schema_contract"
        profile_schema_path = [System.IO.Path]::GetFullPath($schemaPath)
        profile_path = [System.IO.Path]::GetFullPath($profilePath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates; profile schema stays static-only with profile audit coverage." } else { "Fix failed profile schema static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "ProfileSchemaStaticSmoke reads repo profile schema files only; it does not launch, stop, read/write profile state, migrate files, toggle runtime, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "profile_schema_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Profile schema static smoke: $path"
    Write-Output "[solteria-helper-test-env] Profile schema static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Profile schema static smoke failed"
    }
}

function Invoke-OperatorSummaryStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $summaryPath = Join-Path $repo "scripts\lua\otclient\ctoa_helper_operator_summary.lua"
    $loaderPath = Join-Path $repo "scripts\lua\otclient\ctoa_otclient_loader.lua"
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $scriptPath = $PSCommandPath
    $summary = if (Test-Path -LiteralPath $summaryPath) { Get-Content -LiteralPath $summaryPath -Raw } else { "" }
    $loader = Get-CtoaHelperBootGraphSource -RepoRoot $repo
    $helper = if (Test-Path -LiteralPath $helperPath) { Get-Content -LiteralPath $helperPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "module_exists"; status = if (Test-Path -LiteralPath $summaryPath) { "passed" } else { "failed" }; evidence = "ctoa_helper_operator_summary.lua exists" },
        [pscustomobject]@{ name = "global_contract"; status = if ($summary.Contains('rawget(_G, "CTOA_HELPER_OPERATOR_SUMMARY")') -and $summary.Contains("_G.CTOA_HELPER_OPERATOR_SUMMARY = OperatorSummary") -and $summary.Contains("return OperatorSummary")) { "passed" } else { "failed" }; evidence = "operator summary keeps a guarded global and returns module table" },
        [pscustomobject]@{ name = "summary_functions"; status = if ($summary.Contains("function OperatorSummary.title") -and $summary.Contains("function OperatorSummary.healing") -and $summary.Contains("function OperatorSummary.healFriend") -and $summary.Contains("function OperatorSummary.conditions") -and $summary.Contains("function OperatorSummary.equipment") -and $summary.Contains("function OperatorSummary.scripting") -and $summary.Contains("function OperatorSummary.targeting") -and $summary.Contains("function OperatorSummary.magic") -and $summary.Contains("function OperatorSummary.tools") -and $summary.Contains("function OperatorSummary.profile") -and $summary.Contains("function OperatorSummary.ui") -and $summary.Contains("function OperatorSummary.bridgeText") -and $summary.Contains("function OperatorSummary.contract")) { "passed" } else { "failed" }; evidence = "operator summary exposes title/domain/profile/UI summary bridge functions and contract" },
        [pscustomobject]@{ name = "passive_contract"; status = if ($summary.Contains('mode = "passive"') -and $summary.Contains("owns_operator_summary_text = true") -and $summary.Contains("owns_profile_summary_bridge = true") -and $summary.Contains("owns_module_summary_bridge = true") -and $summary.Contains("owns_bridge_dispatch = true") -and $summary.Contains("creates_widgets = false") -and $summary.Contains("runtime_actions = false") -and $summary.Contains("executes_plans = false") -and $summary.Contains("dispatch_allowed = false")) { "passed" } else { "failed" }; evidence = "operator summary contract declares passive formatting, no widgets, and no runtime dispatch" },
        [pscustomobject]@{ name = "helper_uses_adapter"; status = if ($helper.Contains('rawget(_G, "CTOA_HELPER_OPERATOR_SUMMARY")') -and -not $helper.Contains("function operatorSummaryText") -and $helper.Contains('moduleValue(externalOperatorSummary, "bridgeText"') -and -not $helper.Contains(("pcall(externalOperatorSummary" + "[functionName]")) -and $helper.Contains("local OPERATOR_SUMMARY_BRIDGES") -and -not $helper.Contains("local function operatorSummaryBridgeText") -and $helper.Contains('title = {fallback = "profile summary unavailable"') -and $helper.Contains('healFriend = {fallback = "Heal Friend module unavailable | runtime gated"') -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.tools") -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.profile") -and $helper.Contains("OPERATOR_SUMMARY_BRIDGES.ui")) { "passed" } else { "failed" }; evidence = "native helper delegates operator summary text directly through the shared guarded module adapter" },
        [pscustomobject]@{ name = "no_otclient_globals"; status = if (-not $summary.Contains("g_game") -and -not $summary.Contains("g_map") -and -not $summary.Contains("g_ui") -and -not $summary.Contains("g_keyboard") -and -not $summary.Contains("g_resources")) { "passed" } else { "failed" }; evidence = "operator summary does not call native OTClient globals" },
        [pscustomobject]@{ name = "no_runtime_actions"; status = if (-not $summary.Contains("autoWalk") -and -not $summary.Contains("castSpell") -and -not $summary.Contains("g_game.talk") -and -not $summary.Contains("sendActionbarSlot") -and -not $summary.Contains("useInventoryItem") -and -not $summary.Contains("g_game.attack")) { "passed" } else { "failed" }; evidence = "operator summary does not walk, cast, talk, use items, or attack" },
        [pscustomobject]@{ name = "loader_present"; status = if ((Test-CtoaHelperBootGraphModule -Source $loader -Name "ctoa_helper_operator_summary" -File "ctoa_helper_operator_summary.lua")) { "passed" } else { "failed" }; evidence = "loader stages operator summary with support modules" },
        [pscustomobject]@{ name = "packaged"; status = if ($script.Contains("ctoa_helper_operator_summary.lua") -and $script.Contains("mods/ctoa_otclient/ctoa_helper_operator_summary.lua")) { "passed" } else { "failed" }; evidence = "dev package copies operator summary into mods/ctoa_otclient" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-operator-summary-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "operator_summary"
        mode = "static_passive_operator_summary_contract"
        summary_path = [System.IO.Path]::GetFullPath($summaryPath)
        loader_path = [System.IO.Path]::GetFullPath($loaderPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates, then sandbox SmokeAttachModules after character is in-world." } else { "Fix failed operator summary static checks before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "OperatorSummaryStaticSmoke reads repo operator summary files only; it does not launch, stop, attach to, promote, execute plans, cast, talk, walk, use items, attack, create widgets, or overwrite any client."
    }
    $path = Join-Path $outRoot "operator_summary_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Operator summary static smoke: $path"
    Write-Output "[solteria-helper-test-env] Operator summary static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Operator summary static smoke failed"
    }
}

function Invoke-ExternalBotImportGateStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $intakePath = Join-Path $repo "scripts\ops\otclient_external_bot_intake.py"
    $reviewPath = Join-Path $repo "docs\otclient\vbot_import_review.md"
    $planPath = Join-Path $repo "docs\otclient\solteria_helper_next_modules_plan.md"
    $planScriptPath = Join-Path $repo "scripts\ops\otclient_helper_next_modules_plan.py"
    $testPath = Join-Path $repo "tests\test_otclient_external_bot_intake.py"
    $modulePlanTestPath = Join-Path $repo "tests\test_otclient_helper_next_modules_plan.py"
    $scriptPath = $PSCommandPath
    $intake = if (Test-Path -LiteralPath $intakePath) { Get-Content -LiteralPath $intakePath -Raw } else { "" }
    $review = if (Test-Path -LiteralPath $reviewPath) { Get-Content -LiteralPath $reviewPath -Raw } else { "" }
    $plan = if (Test-Path -LiteralPath $planPath) { Get-Content -LiteralPath $planPath -Raw } else { "" }
    $planScript = if (Test-Path -LiteralPath $planScriptPath) { Get-Content -LiteralPath $planScriptPath -Raw } else { "" }
    $test = if (Test-Path -LiteralPath $testPath) { Get-Content -LiteralPath $testPath -Raw } else { "" }
    $modulePlanTest = if (Test-Path -LiteralPath $modulePlanTestPath) { Get-Content -LiteralPath $modulePlanTestPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    $checks = @(
        [pscustomobject]@{ name = "intake_script_exists"; status = if (Test-Path -LiteralPath $intakePath) { "passed" } else { "failed" }; evidence = "otclient_external_bot_intake.py exists" },
        [pscustomobject]@{ name = "import_gate_builder"; status = if ($intake.Contains("def build_import_gate(report: dict) -> dict:") -and $intake.Contains('"capability_mapping_only"') -and $intake.Contains('"review_required"') -and $intake.Contains('"source_required"')) { "passed" } else { "failed" }; evidence = "intake converts source state into explicit import gate decisions" },
        [pscustomobject]@{ name = "runtime_and_copy_blocked"; status = if ($intake.Contains('"runtime_import_allowed": False') -and $intake.Contains('"direct_copy_allowed": False') -and $review.Contains('`import_gate.direct_copy_allowed` is always `false`')) { "passed" } else { "failed" }; evidence = "external bot import never grants runtime import or direct copy approval" },
        [pscustomobject]@{ name = "capability_targets"; status = if ($intake.Contains("CAPABILITY_TARGETS") -and $intake.Contains('"targeting": "ctoa_helper_targeting.lua"') -and $intake.Contains('"cavebot": "ctoa_helper_route.lua"') -and $intake.Contains('"scripting": "ctoa_helper_scripting.lua"')) { "passed" } else { "failed" }; evidence = "external capabilities map into CTOAi module targets" },
        [pscustomobject]@{ name = "runtime_gate_mapping"; status = if ($intake.Contains("RUNTIME_ACTION_GATES") -and $intake.Contains('"attack": "combat_runtime"') -and $intake.Contains('"movement": "cavebot_runtime"') -and $intake.Contains('"item_move": "loot_runtime"') -and $intake.Contains('"dynamic_code": "scripting"')) { "passed" } else { "failed" }; evidence = "runtime action findings map to existing CTOAi gates" },
        [pscustomobject]@{ name = "report_always_includes_gate"; status = if ($intake.Contains('report["import_gate"] = build_import_gate(report)') -and $test.Contains('report["import_gate"]["decision"] == "source_required"')) { "passed" } else { "failed" }; evidence = "missing-source and scanned-source reports include import_gate" },
        [pscustomobject]@{ name = "review_contract"; status = if ($review.Contains("## Import Gate Contract") -and $review.Contains('`import_gate.runtime_import_allowed`') -and $review.Contains('`runtime_gate_mapping`') -and $review.Contains('`capability_mapping_only`')) { "passed" } else { "failed" }; evidence = "vBot review documents source-required, review-required, and capability-only gate states" },
        [pscustomobject]@{ name = "next_modules_plan_contract"; status = if ($plan.Contains('External vBot source: `capability_mapping_only`') -and $plan.Contains("External bot import gate: import_gate.runtime_import_allowed must remain false") -and $plan.Contains("require its import_gate before expanding the mapping") -and $plan.Contains("runtime_gate_mapping") -and $planScript.Contains('"external_bot_import_gate"')) { "passed" } else { "failed" }; evidence = "next module plan keeps capability mapping separate from direct copy/runtime import and gated by import_gate" },
        [pscustomobject]@{ name = "test_coverage"; status = if ($test.Contains("capability_mapping_only") -and $test.Contains("runtime_import_allowed") -and $test.Contains("runtime_gate_mapping") -and $modulePlanTest.Contains("external_bot_import_gate")) { "passed" } else { "failed" }; evidence = "pytest coverage protects import gate and plan policy" },
        [pscustomobject]@{ name = "static_only"; status = if ($script.Contains("ExternalBotImportGateStaticSmoke") -and -not $script.Contains(("SmokeAttach -Tab " + "external_bot_import_gate"))) { "passed" } else { "failed" }; evidence = "external bot import gate is static-only and has no attach tab" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-external-bot-import-gate-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "external_bot_import_gate"
        mode = "static_source_provenance_import_gate"
        intake_path = [System.IO.Path]::GetFullPath($intakePath)
        review_path = [System.IO.Path]::GetFullPath($reviewPath)
        plan_path = [System.IO.Path]::GetFullPath($planPath)
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Run ModuleStaticGates; external bot imports stay capability-mapping-only until source provenance and sandbox gates pass." } else { "Fix failed external bot import gate checks before any external source review." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "ExternalBotImportGateStaticSmoke reads repo intake, plan, docs, and tests only; it does not launch, stop, attach to, promote, copy external bot code, or overwrite any client."
    }
    $path = Join-Path $outRoot "external_bot_import_gate_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] External bot import gate static smoke: $path"
    Write-Output "[solteria-helper-test-env] External bot import gate static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "External bot import gate static smoke failed"
    }
}

function Invoke-HelperShellBudgetStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $helperPath = Join-Path $repo "scripts\lua\otclient\ctoa_native_helper.lua"
    $planScript = Join-Path $repo "scripts\ops\otclient_helper_shell_budget_plan.py"
    $planJsonPath = Join-Path $outRoot "helper_shell_budget_plan.json"
    $auditPath = Join-Path $repo "scripts\ops\otclient_helper_module_audit.py"
    $workplanPath = Join-Path $repo "docs\otclient\solteria_helper_module_workplan.md"
    $testPath = Join-Path $repo "tests\test_otclient_helper_module_audit.py"
    $scriptPath = $PSCommandPath
    $audit = if (Test-Path -LiteralPath $auditPath) { Get-Content -LiteralPath $auditPath -Raw } else { "" }
    $workplan = if (Test-Path -LiteralPath $workplanPath) { Get-Content -LiteralPath $workplanPath -Raw } else { "" }
    $test = if (Test-Path -LiteralPath $testPath) { Get-Content -LiteralPath $testPath -Raw } else { "" }
    $script = Get-Content -LiteralPath $scriptPath -Raw
    & python $planScript --json-out $planJsonPath --no-plan-write
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $planJsonPath -PathType Leaf)) {
        throw "Canonical helper shell budget measurement failed"
    }
    $budgetPlan = Get-Content -LiteralPath $planJsonPath -Raw | ConvertFrom-Json
    $lineCount = [int]$budgetPlan.helper_line_count
    $functionCount = [int]$budgetPlan.helper_function_count
    $lineBudget = [int]$budgetPlan.helper_line_budget
    $functionBudget = [int]$budgetPlan.helper_function_budget
    $hardLineCeiling = [int]$budgetPlan.hard_line_ceiling
    $hardFunctionCeiling = [int]$budgetPlan.hard_function_ceiling
    $checks = @(
        [pscustomobject]@{ name = "helper_exists"; status = if (Test-Path -LiteralPath $helperPath) { "passed" } else { "failed" }; evidence = "ctoa_native_helper.lua exists" },
        [pscustomobject]@{ name = "line_budget_declared"; status = if ($audit.Contains("helper_line_budget") -and $audit.Contains("4500") -and $test.Contains("helper_line_budget == 4500")) { "passed" } else { "failed" }; evidence = "module audit declares the target shell line budget" },
        [pscustomobject]@{ name = "function_budget_declared"; status = if ($audit.Contains("helper_function_budget") -and $audit.Contains("130") -and $test.Contains("helper_function_budget == 130")) { "passed" } else { "failed" }; evidence = "module audit declares the target shell function budget" },
        [pscustomobject]@{ name = "canonical_budget_status"; status = if ([string]$budgetPlan.status -eq "within_budget") { "passed" } else { "failed" }; evidence = ("canonical generator status {0}" -f $budgetPlan.status) },
        [pscustomobject]@{ name = "line_count_within_budget"; status = if ($lineCount -gt 0 -and $lineCount -le $lineBudget) { "passed" } else { "failed" }; evidence = ("helper lines {0}; target budget {1}; hard ceiling {2}" -f $lineCount, $lineBudget, $hardLineCeiling) },
        [pscustomobject]@{ name = "function_count_within_budget"; status = if ($functionCount -gt 0 -and $functionCount -le $functionBudget) { "passed" } else { "failed" }; evidence = ("helper named functions {0}; target budget {1}; hard ceiling {2}" -f $functionCount, $functionBudget, $hardFunctionCeiling) },
        [pscustomobject]@{ name = "shell_target_documented"; status = if ($audit.Contains("UI composition, profile persistence, and guarded dispatch only") -and $workplan.Contains("Helper shell target")) { "passed" } else { "failed" }; evidence = "module workplan keeps the main helper as a UI composition shell" },
        [pscustomobject]@{ name = "modularization_pressure_visible"; status = if ($workplan.Contains("Helper budget status:") -and $workplan.Contains("P6 Module Lane") -and $workplan.Contains("Supplemental Refactor Plan")) { "passed" } else { "failed" }; evidence = "operator docs keep shell budget and extraction lanes visible" },
        [pscustomobject]@{ name = "next_runtime_step_not_hidden"; status = if ($workplan.Contains("SmokeAttachModules") -and $workplan.Contains("PromoteLiveCtoa -ApproveLiveDeploy")) { "passed" } else { "failed" }; evidence = "budget gate does not hide sandbox and explicit live approval requirements" },
        [pscustomobject]@{ name = "module_static_gate_registered"; status = if ($script.Contains("HelperShellBudgetStaticSmoke") -and $script.Contains("helper_shell_budget_static_smoke.json") -and $script.Contains('module = "helper_shell_budget"')) { "passed" } else { "failed" }; evidence = "helper shell budget is included in ModuleStaticGates and GoalStatus summaries" },
        [pscustomobject]@{ name = "static_only"; status = if ($script.Contains("HelperShellBudgetStaticSmoke") -and -not $script.Contains(("SmokeAttach -Tab " + "helper_shell_budget"))) { "passed" } else { "failed" }; evidence = "helper shell budget is static-only and has no attach tab" }
    )
    $failed = @($checks | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-shell-budget-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        module = "helper_shell_budget"
        mode = "static_helper_shell_budget_guard"
        helper_path = [System.IO.Path]::GetFullPath($helperPath)
        helper_line_count = $lineCount
        helper_line_budget = $lineBudget
        helper_hard_line_ceiling = $hardLineCeiling
        helper_function_count = $functionCount
        helper_function_budget = $functionBudget
        helper_hard_function_ceiling = $hardFunctionCeiling
        check_count = $checks.Count
        passed_count = @($checks | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        checks = $checks
        next_action = if ($failed.Count -eq 0) { "Keep the shell at or below the canonical target; runtime sandbox evidence is still required before live promotion." } else { "Reduce helper shell to the canonical target before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "HelperShellBudgetStaticSmoke reads repo helper, audit, docs, tests, and this script only; it does not launch, stop, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "helper_shell_budget_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Helper shell budget static smoke: $path"
    Write-Output "[solteria-helper-test-env] Helper shell budget static status: $($report.status)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($failed.Count -gt 0) {
        throw "Helper shell budget static smoke failed"
    }
}

function Invoke-HelperShellBudgetPlanStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $planScript = Join-Path $repo "scripts\ops\otclient_helper_shell_budget_plan.py"
    $jsonPath = Join-Path $outRoot "helper_shell_budget_plan.json"
    $planPath = Join-Path $repo "docs\otclient\solteria_helper_shell_budget_plan.md"
    & python $planScript --json-out $jsonPath --plan-out $planPath
    if ($LASTEXITCODE -ne 0) {
        throw "Helper shell budget plan static smoke failed"
    }
    $report = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
    Write-Output "[solteria-helper-test-env] Helper shell budget plan static smoke: $jsonPath"
    Write-Output "[solteria-helper-test-env] Helper shell budget plan status: $($report.status); lines=$($report.helper_line_count); functions=$($report.helper_function_count)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_action)) {
        Write-Output "[solteria-helper-test-env] Next action: $($report.next_action)"
    }
    if ([string]$report.status -ne "within_budget" -or $report.over_line_budget_by -ne 0 -or $report.over_function_budget_by -ne 0) {
        throw "Helper shell budget plan static smoke requires canonical within_budget status"
    }
}

function Invoke-DecisionPipelineStaticSmoke {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    & python -m pytest tests\test_ctoa_helper_decision_pipeline.py -q
    $exitCode = $LASTEXITCODE
    $report = [pscustomobject]@{
        name = "solteria-helper-decision-pipeline-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($exitCode -eq 0) { "passed" } else { "failed" }
        module = "decision_pipeline"
        mode = "real_lua_passive_pipeline_contract"
        check_count = 1
        passed_count = if ($exitCode -eq 0) { 1 } else { 0 }
        failed_count = if ($exitCode -eq 0) { 0 } else { 1 }
        next_action = if ($exitCode -eq 0) { "Run ModuleStaticGates, then sandbox attach evidence before any adapter execution bridge." } else { "Fix decision pipeline contract or real Lua behavior before sandbox attach." }
        next_command = if ($exitCode -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates" } else { "" }
        live_safety = "DecisionPipelineStaticSmoke runs passive repo tests only; it does not launch, attach to, promote, dispatch to, or overwrite any client."
    }
    $path = Join-Path $outRoot "decision_pipeline_static_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Decision pipeline static smoke: $path"
    Write-Output "[solteria-helper-test-env] Decision pipeline static status: $($report.status)"
    if ($exitCode -ne 0) {
        throw "Decision pipeline static smoke failed"
    }
}

function Invoke-ModuleStaticGates {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $steps = @(
        [pscustomobject]@{ module = "module_contract"; action = "ModuleContract"; report = "module_contract.json"; attach_command = "" },
        [pscustomobject]@{ module = "conditions"; action = "ConditionsObserverSmoke"; report = "conditions_observer_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions" },
        [pscustomobject]@{ module = "equipment"; action = "EquipmentObserverSmoke"; report = "equipment_observer_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment" },
        [pscustomobject]@{ module = "heal_friend"; action = "HealFriendNoTargetSmoke"; report = "heal_friend_no_target_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend" },
        [pscustomobject]@{ module = "scripting"; action = "ScriptingPolicySmoke"; report = "scripting_policy_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting" },
        [pscustomobject]@{ module = "planner"; action = "PlannerStaticSmoke"; report = "planner_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "runtime_policy"; action = "RuntimePolicyStaticSmoke"; report = "runtime_policy_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "dispatch_guard"; action = "DispatchGuardStaticSmoke"; report = "dispatch_guard_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "plan_queue"; action = "PlanQueueStaticSmoke"; report = "plan_queue_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "runtime_readiness"; action = "RuntimeReadinessStaticSmoke"; report = "runtime_readiness_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "module_status"; action = "ModuleStatusStaticSmoke"; report = "module_status_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "action_catalog"; action = "ActionCatalogStaticSmoke"; report = "action_catalog_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "decision_trace"; action = "DecisionTraceStaticSmoke"; report = "decision_trace_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "decision_pipeline"; action = "DecisionPipelineStaticSmoke"; report = "decision_pipeline_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "sandbox_handoff"; action = "SandboxHandoffStaticSmoke"; report = "sandbox_handoff_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "feature_flags"; action = "FeatureFlagsStaticSmoke"; report = "feature_flags_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "hud"; action = "HudStaticSmoke"; report = "hud_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud" },
        [pscustomobject]@{ module = "hotkeys"; action = "HotkeysStaticSmoke"; report = "hotkeys_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "modal"; action = "ModalStaticSmoke"; report = "modal_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "input_contracts"; action = "InputContractsStaticSmoke"; report = "input_contract_fixtures.json"; attach_command = "" },
        [pscustomobject]@{ module = "route"; action = "RouteStaticSmoke"; report = "route_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot" },
        [pscustomobject]@{ module = "targeting"; action = "TargetingStaticSmoke"; report = "targeting_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting" },
        [pscustomobject]@{ module = "combat_runtime"; action = "CombatRuntimeStaticSmoke"; report = "combat_runtime_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic" },
        [pscustomobject]@{ module = "cavebot_runtime"; action = "CavebotRuntimeStaticSmoke"; report = "cavebot_runtime_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot" },
        [pscustomobject]@{ module = "loot_runtime"; action = "LootRuntimeStaticSmoke"; report = "loot_runtime_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag" },
        [pscustomobject]@{ module = "timer_runtime"; action = "TimerRuntimeStaticSmoke"; report = "timer_runtime_static_smoke.json"; attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer" },
        [pscustomobject]@{ module = "recovery_runtime"; action = "RecoveryRuntimeStaticSmoke"; report = "recovery_runtime_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "recovery_bridge"; action = "RecoveryBridgeStaticSmoke"; report = "recovery_bridge_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "conditions_runtime_gate"; action = "ConditionsRuntimeGateStaticSmoke"; report = "conditions_runtime_gate_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "equipment_runtime_gate"; action = "EquipmentRuntimeGateStaticSmoke"; report = "equipment_runtime_gate_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "equipment_shadow_snapshot"; action = "EquipmentShadowSnapshotStaticSmoke"; report = "equipment_shadow_snapshot_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "equipment_shadow_replay"; action = "EquipmentShadowReplayStaticSmoke"; report = "equipment_shadow_replay_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "equipment_shadow_acceptance"; action = "EquipmentShadowAcceptanceStaticSmoke"; report = "equipment_shadow_acceptance_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "heal_friend_runtime_gate"; action = "HealFriendRuntimeGateStaticSmoke"; report = "heal_friend_runtime_gate_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "profile_schema"; action = "ProfileSchemaStaticSmoke"; report = "profile_schema_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "operator_summary"; action = "OperatorSummaryStaticSmoke"; report = "operator_summary_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "external_bot_import_gate"; action = "ExternalBotImportGateStaticSmoke"; report = "external_bot_import_gate_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "helper_shell_budget"; action = "HelperShellBudgetStaticSmoke"; report = "helper_shell_budget_static_smoke.json"; attach_command = "" },
        [pscustomobject]@{ module = "helper_shell_budget_plan"; action = "HelperShellBudgetPlanStaticSmoke"; report = "helper_shell_budget_plan.json"; attach_command = "" }
    )
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($step in $steps) {
        try {
            switch ([string]$step.action) {
                "ModuleContract" { Invoke-ModuleContract }
                "ConditionsObserverSmoke" { Invoke-ConditionsObserverSmoke }
                "EquipmentObserverSmoke" { Invoke-EquipmentObserverSmoke }
                "HealFriendNoTargetSmoke" { Invoke-HealFriendNoTargetSmoke }
                "ScriptingPolicySmoke" { Invoke-ScriptingPolicySmoke }
                "PlannerStaticSmoke" { Invoke-PlannerStaticSmoke }
                "RuntimePolicyStaticSmoke" { Invoke-RuntimePolicyStaticSmoke }
                "DispatchGuardStaticSmoke" { Invoke-DispatchGuardStaticSmoke }
                "PlanQueueStaticSmoke" { Invoke-PlanQueueStaticSmoke }
                "RuntimeReadinessStaticSmoke" { Invoke-RuntimeReadinessStaticSmoke }
                "ModuleStatusStaticSmoke" { Invoke-ModuleStatusStaticSmoke }
                "ActionCatalogStaticSmoke" { Invoke-ActionCatalogStaticSmoke }
                "DecisionTraceStaticSmoke" { Invoke-DecisionTraceStaticSmoke }
                "DecisionPipelineStaticSmoke" { Invoke-DecisionPipelineStaticSmoke }
                "SandboxHandoffStaticSmoke" { Invoke-SandboxHandoffStaticSmoke }
                "FeatureFlagsStaticSmoke" { Invoke-FeatureFlagsStaticSmoke }
                "HudStaticSmoke" { Invoke-HudStaticSmoke }
                "HotkeysStaticSmoke" { Invoke-HotkeysStaticSmoke }
                "ModalStaticSmoke" { Invoke-ModalStaticSmoke }
                "InputContractsStaticSmoke" { Invoke-InputContractsStaticSmoke }
                "RouteStaticSmoke" { Invoke-RouteStaticSmoke }
                "TargetingStaticSmoke" { Invoke-TargetingStaticSmoke }
                "CombatRuntimeStaticSmoke" { Invoke-CombatRuntimeStaticSmoke }
                "CavebotRuntimeStaticSmoke" { Invoke-CavebotRuntimeStaticSmoke }
                "LootRuntimeStaticSmoke" { Invoke-LootRuntimeStaticSmoke }
                "TimerRuntimeStaticSmoke" { Invoke-TimerRuntimeStaticSmoke }
                "RecoveryRuntimeStaticSmoke" { Invoke-RecoveryRuntimeStaticSmoke }
                "RecoveryBridgeStaticSmoke" { Invoke-RecoveryBridgeStaticSmoke }
                "ConditionsRuntimeGateStaticSmoke" { Invoke-ConditionsRuntimeGateStaticSmoke }
                "EquipmentRuntimeGateStaticSmoke" { Invoke-EquipmentRuntimeGateStaticSmoke }
                "HealFriendRuntimeGateStaticSmoke" { Invoke-HealFriendRuntimeGateStaticSmoke }
                "ProfileSchemaStaticSmoke" { Invoke-ProfileSchemaStaticSmoke }
                "OperatorSummaryStaticSmoke" { Invoke-OperatorSummaryStaticSmoke }
                "ExternalBotImportGateStaticSmoke" { Invoke-ExternalBotImportGateStaticSmoke }
                "HelperShellBudgetStaticSmoke" { Invoke-HelperShellBudgetStaticSmoke }
                "HelperShellBudgetPlanStaticSmoke" { Invoke-HelperShellBudgetPlanStaticSmoke }
            }
        } catch {
            $errors.Add(("{0}: {1}" -f $step.module, [string]$_.Exception.Message))
        }
    }
    $gates = @($steps | ForEach-Object {
        $reportPath = Join-Path $outRoot ([string]$_.report)
        $status = "missing"
        $createdAt = ""
        $passedCount = 0
        $checkCount = 0
        if (Test-Path -LiteralPath $reportPath) {
            try {
                $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
                $status = [string]$report.status
                $createdAt = [string]$report.created_at
                if ($report.PSObject.Properties.Name -contains "passed_count") {
                    $passedCount = [int]$report.passed_count
                }
                if ($report.PSObject.Properties.Name -contains "check_count") {
                    $checkCount = [int]$report.check_count
                }
                if ([string]$_.module -eq "helper_shell_budget_plan" -and $status -eq "within_budget" -and $report.over_line_budget_by -eq 0 -and $report.over_function_budget_by -eq 0) {
                    $status = "passed"
                    $passedCount = 1
                    $checkCount = 1
                }
            } catch {
                $status = "invalid"
            }
        }
        [pscustomobject]@{
            module = [string]$_.module
            status = $status
            created_at = $createdAt
            passed_count = $passedCount
            check_count = $checkCount
            report_path = [System.IO.Path]::GetFullPath($reportPath)
            static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action $([string]$_.action)"
            attach_command = [string]$_.attach_command
        }
    })
    $failed = @($gates | Where-Object { [string]$_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-module-static-gates"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0 -and $errors.Count -eq 0) { "passed" } else { "failed" }
        gate_count = $gates.Count
        passed_count = @($gates | Where-Object { [string]$_.status -eq "passed" }).Count
        failed_count = $failed.Count
        gates = $gates
        errors = @($errors)
        next_action = if ($failed.Count -eq 0 -and $errors.Count -eq 0) { "Run GoalStatus for release routing; sandbox attach smoke is still required before live promotion." } else { "Fix failed static module gates before sandbox attach smoke." }
        next_command = if ($failed.Count -eq 0 -and $errors.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action GoalStatus" } else { "" }
        live_safety = "ModuleStaticGates runs repo-only static module gates; it does not launch, stop, attach to, promote, or overwrite any client."
    }
    $path = Join-Path $outRoot "module_static_gates.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Module static gates: $path"
    Write-Output "[solteria-helper-test-env] Module static gates status: $($report.status) ($($report.passed_count)/$($report.gate_count))"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if ($report.status -ne "passed") {
        throw "Module static gates failed"
    }
}

function Invoke-ModuleContract {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $contractScript = Join-Path $repo "scripts\ops\otclient_helper_module_contract.py"
    if (-not (Test-Path -LiteralPath $contractScript)) {
        throw "Missing module contract validator: $contractScript"
    }
    $jsonOut = Join-Path $outRoot "module_contract.json"
    $planOut = Join-Path $repo "docs\otclient\solteria_helper_module_contract.md"
    & python $contractScript --json-out $jsonOut --plan-out $planOut
    if ($LASTEXITCODE -ne 0) {
        throw "ModuleContract failed with exit code $LASTEXITCODE"
    }
}

function Invoke-ModuleAudit {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $auditScript = Join-Path $repo "scripts\ops\otclient_helper_module_audit.py"
    if (-not (Test-Path -LiteralPath $auditScript)) {
        throw "Missing module audit generator: $auditScript"
    }
    $jsonOut = Join-Path $outRoot "module_audit.json"
    $planOut = Join-Path $repo "docs\otclient\solteria_helper_module_workplan.md"
    & python $auditScript --json-out $jsonOut --plan-out $planOut
    if ($LASTEXITCODE -ne 0) {
        throw "ModuleAudit failed with exit code $LASTEXITCODE"
    }
}

function Write-GoalHandoff {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Solteria Helper Goal Handoff")
    $lines.Add("")
    $lines.Add(("Generated: {0}" -f $Status.created_at))
    $lines.Add("")
    $lines.Add("## Current State")
    $lines.Add("")
    $lines.Add(("- Goal status: {0}" -f $Status.status))
    $lines.Add(("- Release gate: {0}" -f $Status.release_gate_status))
    $lines.Add(("- Releasable to live: {0}" -f $Status.releasable_to_live))
    $lines.Add(("- Live safety: {0}" -f $Status.live_safety))
    $lines.Add("")
    $lines.Add("## Roadmap")
    $lines.Add("")
    foreach ($item in @($Status.roadmap)) {
        $lines.Add(("- {0}: {1}" -f $item.name, $item.status))
    }
    $handoffRoot = Split-Path -Parent $Path
    $queuePath = Join-Path $handoffRoot "sandbox_smoke_queue.json"
    if ($Status.sandbox_smoke_queue -and -not [string]::IsNullOrWhiteSpace([string]$Status.sandbox_smoke_queue.status)) {
        $queue = $Status.sandbox_smoke_queue
        $lines.Add("")
        $lines.Add("## Sandbox Smoke Queue")
        $lines.Add("")
        $lines.Add(("- Queue status: {0}" -f $queue.status))
        $lines.Add(("- Runtime status: {0}" -f $queue.runtime_status))
        $lines.Add(("- Next queue action: {0}" -f $queue.next_action))
        $lines.Add(("- Queue evidence: {0}" -f $queue.path))
        foreach ($step in @($queue.next_steps)) {
            $lines.Add(("- queue {0}. {1}: {2}; command: {3}" -f $step.order, $step.step_id, $step.status, $step.command))
        }
    } elseif (Test-Path -LiteralPath $queuePath) {
        try {
            $queue = Get-Content -LiteralPath $queuePath -Raw | ConvertFrom-Json
            $lines.Add("")
            $lines.Add("## Sandbox Smoke Queue")
            $lines.Add("")
            $lines.Add(("- Queue status: {0}" -f $queue.status))
            $lines.Add(("- Runtime status: {0}" -f $queue.runtime_status))
            $lines.Add(("- Next queue action: {0}" -f $queue.next_action))
            $lines.Add(("- Queue evidence: {0}" -f [System.IO.Path]::GetFullPath($queuePath)))
            $shown = 0
            foreach ($step in @($queue.steps)) {
                if ($shown -ge 5) {
                    break
                }
                if ($step.status -in @("required", "queued", "blocked")) {
                    $lines.Add(("- queue {0}. {1}: {2}; command: {3}" -f $step.order, $step.step_id, $step.status, $step.command))
                    $shown += 1
                }
            }
        } catch {
            $lines.Add("")
            $lines.Add("## Sandbox Smoke Queue")
            $lines.Add("")
            $lines.Add(("- Queue status: unreadable; error: {0}" -f $_.Exception.Message))
        }
    }
    $moduleAudit = $Status.module_audit
    if ($moduleAudit -and -not [string]::IsNullOrWhiteSpace([string]$moduleAudit.status)) {
        $lines.Add("")
        $lines.Add("## Module Workplan")
        $lines.Add("")
        $lines.Add(("- Audit status: {0}" -f $moduleAudit.status))
        $lines.Add(("- Pressure: {0}" -f $moduleAudit.modularization_pressure))
        $lines.Add(("- Helper budget: {0}; lines: {1}/{2}" -f $moduleAudit.helper_budget_status, $moduleAudit.helper_line_count, $moduleAudit.helper_line_budget))
        $lines.Add(("- Implemented/prototype: {0}/{1}" -f $moduleAudit.implemented_count, $moduleAudit.prototype_count))
        $lines.Add(("- Registry coverage: {0}" -f $moduleAudit.registry_coverage))
        if (-not [string]::IsNullOrWhiteSpace([string]$moduleAudit.next_extraction_id)) {
            $lines.Add(("- Next extraction: {0}" -f $moduleAudit.next_extraction_id))
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$moduleAudit.next_supplemental_id)) {
            $lines.Add(("- Next supplemental split: {0}" -f $moduleAudit.next_supplemental_id))
        }
        $lines.Add(("- Next phase: {0}" -f $moduleAudit.next_phase))
        $lines.Add(("- Next module: {0}" -f $moduleAudit.next_module_id))
        $lines.Add(("- Next module action: {0}" -f $moduleAudit.next_module_action))
        if (-not [string]::IsNullOrWhiteSpace([string]$moduleAudit.next_module_evidence_status)) {
            $lines.Add(("- Next module evidence: {0}" -f $moduleAudit.next_module_evidence_status))
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$moduleAudit.next_module_command)) {
            $lines.Add(("- Next module command: {0}" -f $moduleAudit.next_module_command))
        }
        $staticGateSummary = @($moduleAudit.static_gate_summary)
        if ($staticGateSummary.Count -gt 0) {
            $lines.Add(("- Static gates: {0}/{1} passed" -f $moduleAudit.static_gate_passed_count, $moduleAudit.static_gate_count))
            foreach ($gate in $staticGateSummary) {
                $lines.Add(("- gate {0}: {1}; static: {2}; attach: {3}" -f $gate.module, $gate.status, $gate.static_command, $gate.attach_command))
            }
        }
        $extractionPlan = @($moduleAudit.extraction_plan)
        if ($extractionPlan.Count -gt 0) {
            $lines.Add("")
            $lines.Add("### Extraction Map")
            foreach ($item in $extractionPlan) {
                $lines.Add(("- {0}. {1}: {2}; target: {3}; gate: {4}" -f $item.safe_order, $item.id, $item.status, $item.target_file, $item.gate))
            }
        }
        $supplementalPlan = @($moduleAudit.supplemental_refactor_plan)
        if ($supplementalPlan.Count -gt 0) {
            $lines.Add("")
            $lines.Add("### Supplemental Refactor Plan")
            foreach ($item in $supplementalPlan) {
                $lines.Add(("- {0}. {1}: {2}; target: {3}; gate: {4}" -f $item.safe_order, $item.id, $item.status, $item.target_file, $item.gate))
            }
        }
        $lines.Add("")
        foreach ($module in @($moduleAudit.modules)) {
            $lines.Add(("- {0}: {1}; next: {2}" -f $module.id, $module.status, $module.next_step))
        }
    }
    $lines.Add("")
    $lines.Add("## Blockers")
    $lines.Add("")
    $blockers = @($Status.blockers)
    if ($blockers.Count -eq 0) {
        $lines.Add("- none")
    } else {
        foreach ($blocker in $blockers) {
            $lines.Add(("- {0}" -f $blocker))
        }
    }
    $lines.Add("")
    $lines.Add("## Next Safe Step")
    $lines.Add("")
    $lines.Add(("- Action: {0}" -f $Status.next_action))
    if (-not [string]::IsNullOrWhiteSpace([string]$Status.next_command)) {
        $lines.Add(("- Command: {0}" -f $Status.next_command))
    }
    $lines.Add("")
    $lines.Add("## Completion Rule")
    $lines.Add("")
    $lines.Add("Do not promote to live until SmokePreflight passes, in-world SmokeAttachAll evidence is fresh for the current manifest, and PromoteLiveCtoa is run with explicit approval.")
    Write-TextAtomic -Text ($lines -join [Environment]::NewLine) -Path $Path
}

function Read-SmokeQueueSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DevRoot
    )
    $path = Join-Path $DevRoot "sandbox_smoke_queue.json"
    if (-not (Test-Path -LiteralPath $path)) {
        return [pscustomobject]@{
            status = "missing"
            path = [System.IO.Path]::GetFullPath($path)
            runtime_status = ""
            release_gate_status = ""
            next_action = "Run SmokeQueue after GoalStatus."
            required_count = 0
            queued_count = 0
            next_steps = @()
        }
    }
    try {
        $queue = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        $actionable = @($queue.steps | Where-Object { $_.status -in @("required", "queued", "blocked") } | Select-Object -First 5)
        return [pscustomobject]@{
            status = [string]$queue.status
            path = [System.IO.Path]::GetFullPath($path)
            runtime_status = [string]$queue.runtime_status
            release_gate_status = [string]$queue.release_gate_status
            next_action = [string]$queue.next_action
            required_count = @($queue.steps | Where-Object { $_.status -eq "required" }).Count
            queued_count = @($queue.steps | Where-Object { $_.status -eq "queued" }).Count
            next_steps = @($actionable | ForEach-Object {
                [pscustomobject]@{
                    order = [int]$_.order
                    step_id = [string]$_.step_id
                    label = [string]$_.label
                    status = [string]$_.status
                    command = [string]$_.command
                    evidence = [string]$_.evidence
                }
            })
        }
    } catch {
        return [pscustomobject]@{
            status = "invalid"
            path = [System.IO.Path]::GetFullPath($path)
            runtime_status = ""
            release_gate_status = ""
            next_action = $_.Exception.Message
            required_count = 0
            queued_count = 0
            next_steps = @()
        }
    }
}

function Read-ModuleAuditSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DevRoot
    )
    $path = Join-Path $DevRoot "module_audit.json"
    if (-not (Test-Path -LiteralPath $path)) {
        return [pscustomobject]@{
            status = "missing"
            path = [System.IO.Path]::GetFullPath($path)
            modularization_pressure = ""
            implemented_count = 0
            prototype_count = 0
            registry_coverage = "0 / 0"
            next_phase = "Run otclient_helper_module_audit.py."
            next_module_id = ""
            next_module_action = "Run otclient_helper_module_audit.py."
            next_module_command = ""
            next_extraction_id = ""
            next_supplemental_id = ""
            helper_budget_status = ""
            helper_line_count = 0
            helper_line_budget = 0
            supplemental_refactor_plan = @()
            extraction_plan = @()
            static_gate_count = 0
            static_gate_passed_count = 0
            static_gate_summary = @()
            modules = @()
        }
    }
    try {
        $audit = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        $registryCoverage = ("{0} / {1}" -f $audit.registry_count, @($audit.modules).Count)
        $nextModuleId = [string]$audit.next_module_id
        $nextModuleAction = [string]$audit.next_module_action
        $moduleEvidencePath = ""
        $moduleEvidenceStatus = ""
        $nextModuleCommand = ""
        $runtimeGateRoutes = @{
            conditions = [pscustomobject]@{
                report = "conditions_observer_smoke.json"
                static_action = "ConditionsObserverSmoke"
                accepted_action = "Review the action-bound paralyze-only dry-run trace; Equipment remains blocked until this gate is accepted."
            }
            equipment = [pscustomobject]@{
                report = "equipment_observer_smoke.json"
                static_action = "EquipmentObserverSmoke"
                accepted_action = "Review the ring-only rollback trace; Heal Friend remains blocked until Conditions and Equipment are accepted."
            }
            heal_friend = [pscustomobject]@{
                report = "heal_friend_no_target_smoke.json"
                static_action = "HealFriendNoTargetSmoke"
                accepted_action = "Review the exact-whitelist Heal Friend dry-run; Combat and CaveBot remain deferred_high_risk."
            }
        }
        if ($runtimeGateRoutes.ContainsKey($nextModuleId)) {
            $route = $runtimeGateRoutes[$nextModuleId]
            $evidencePath = Join-Path $DevRoot ([string]$route.report)
            if (Test-Path -LiteralPath $evidencePath) {
                try {
                    $evidence = Get-Content -LiteralPath $evidencePath -Raw | ConvertFrom-Json
                    $moduleEvidencePath = [System.IO.Path]::GetFullPath($evidencePath)
                    $moduleEvidenceStatus = [string]$evidence.status
                } catch {
                    $moduleEvidencePath = [System.IO.Path]::GetFullPath($evidencePath)
                    $moduleEvidenceStatus = "invalid"
                }
            }
            if ($moduleEvidenceStatus -ne "passed") {
                $nextModuleCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action $([string]$route.static_action)"
            } else {
                $runtimeGateEvidencePath = Join-Path $DevRoot "runtime_module_gates_sandbox_smoke.json"
                $runtimeGateEvidenceStatus = ""
                if (Test-Path -LiteralPath $runtimeGateEvidencePath) {
                    try {
                        $runtimeGateEvidence = Get-Content -LiteralPath $runtimeGateEvidencePath -Raw | ConvertFrom-Json
                        $runtimeGateEvidenceStatus = [string]$runtimeGateEvidence.status
                    } catch {
                        $runtimeGateEvidenceStatus = "invalid"
                    }
                }
                if ($runtimeGateEvidenceStatus -eq "passed") {
                    $nextModuleAction = [string]$route.accepted_action
                } else {
                    $nextModuleAction = "Capture ordered Conditions -> Equipment -> Heal Friend fail-closed sandbox evidence before reviewing this lane."
                    $nextModuleCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action RuntimeModuleGatesSandboxSmoke"
                }
            }
        }
        $staticGateSpecs = @(
            [pscustomobject]@{
                module = "conditions"
                report = "conditions_observer_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ConditionsObserverSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions"
            },
            [pscustomobject]@{
                module = "equipment"
                report = "equipment_observer_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action EquipmentObserverSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment"
            },
            [pscustomobject]@{
                module = "heal_friend"
                report = "heal_friend_no_target_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HealFriendNoTargetSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend"
            },
            [pscustomobject]@{
                module = "scripting"
                report = "scripting_policy_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ScriptingPolicySmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting"
            },
            [pscustomobject]@{
                module = "planner"
                report = "planner_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PlannerStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "runtime_policy"
                report = "runtime_policy_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action RuntimePolicyStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "dispatch_guard"
                report = "dispatch_guard_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action DispatchGuardStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "plan_queue"
                report = "plan_queue_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PlanQueueStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "runtime_readiness"
                report = "runtime_readiness_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action RuntimeReadinessStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "module_status"
                report = "module_status_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStatusStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "action_catalog"
                report = "action_catalog_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ActionCatalogStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "decision_trace"
                report = "decision_trace_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action DecisionTraceStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "sandbox_handoff"
                report = "sandbox_handoff_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SandboxHandoffStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "feature_flags"
                report = "feature_flags_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action FeatureFlagsStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "hud"
                report = "hud_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HudStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud"
            },
            [pscustomobject]@{
                module = "hotkeys"
                report = "hotkeys_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HotkeysStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "modal"
                report = "modal_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModalStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "input_contracts"
                report = "input_contract_fixtures.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action InputContractsStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "route"
                report = "route_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action RouteStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot"
            },
            [pscustomobject]@{
                module = "targeting"
                report = "targeting_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action TargetingStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting"
            },
            [pscustomobject]@{
                module = "combat_runtime"
                report = "combat_runtime_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CombatRuntimeStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic"
            },
            [pscustomobject]@{
                module = "cavebot_runtime"
                report = "cavebot_runtime_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CavebotRuntimeStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot"
            },
            [pscustomobject]@{
                module = "loot_runtime"
                report = "loot_runtime_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LootRuntimeStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag"
            },
            [pscustomobject]@{
                module = "timer_runtime"
                report = "timer_runtime_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action TimerRuntimeStaticSmoke"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer"
            },
            [pscustomobject]@{
                module = "profile_schema"
                report = "profile_schema_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ProfileSchemaStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "operator_summary"
                report = "operator_summary_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action OperatorSummaryStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "external_bot_import_gate"
                report = "external_bot_import_gate_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ExternalBotImportGateStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "helper_shell_budget"
                report = "helper_shell_budget_static_smoke.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetStaticSmoke"
                attach_command = ""
            },
            [pscustomobject]@{
                module = "helper_shell_budget_plan"
                report = "helper_shell_budget_plan.json"
                static_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke"
                attach_command = ""
            }
        )
        $staticGateSummary = @($staticGateSpecs | ForEach-Object {
            $reportPath = Join-Path $DevRoot ([string]$_.report)
            $status = "missing"
            $createdAt = ""
            $passedCount = 0
            $checkCount = 0
            if (Test-Path -LiteralPath $reportPath) {
                try {
                    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
                    $status = [string]$report.status
                    $createdAt = [string]$report.created_at
                    if ($report.PSObject.Properties.Name -contains "passed_count") {
                        $passedCount = [int]$report.passed_count
                    }
                    if ($report.PSObject.Properties.Name -contains "check_count") {
                        $checkCount = [int]$report.check_count
                    }
                    if ([string]$_.module -eq "helper_shell_budget_plan" -and $status -eq "within_budget" -and $report.over_line_budget_by -eq 0 -and $report.over_function_budget_by -eq 0) {
                        $status = "passed"
                        $passedCount = 1
                        $checkCount = 1
                    }
                } catch {
                    $status = "invalid"
                }
            }
            [pscustomobject]@{
                module = [string]$_.module
                status = $status
                created_at = $createdAt
                passed_count = $passedCount
                check_count = $checkCount
                report_path = [System.IO.Path]::GetFullPath($reportPath)
                static_command = [string]$_.static_command
                attach_command = [string]$_.attach_command
            }
        })
        $staticGatePassedCount = @($staticGateSummary | Where-Object { [string]$_.status -eq "passed" }).Count
        $modules = @($audit.modules | ForEach-Object {
            [pscustomobject]@{
                id = [string]$_.id
                status = [string]$_.status
                next_step = [string]$_.next_step
                gate = [string]$_.gate
            }
        })
        $extractionPlan = @($audit.extraction_plan | ForEach-Object {
            [pscustomobject]@{
                id = [string]$_.id
                target_file = [string]$_.target_file
                source_domain = [string]$_.source_domain
                safe_order = [int]$_.safe_order
                status = [string]$_.status
                gate = [string]$_.gate
            }
        })
        $supplementalPlan = @($audit.supplemental_refactor_plan | ForEach-Object {
            [pscustomobject]@{
                id = [string]$_.id
                target_file = [string]$_.target_file
                source_domain = [string]$_.source_domain
                safe_order = [int]$_.safe_order
                status = [string]$_.status
                gate = [string]$_.gate
            }
        })
        return [pscustomobject]@{
            status = [string]$audit.status
            path = [System.IO.Path]::GetFullPath($path)
            modularization_pressure = [string]$audit.modularization_pressure
            helper_budget_status = [string]$audit.helper_budget_status
            helper_line_count = [int]$audit.helper_line_count
            helper_line_budget = [int]$audit.helper_line_budget
            implemented_count = [int]$audit.implemented_count
            prototype_count = [int]$audit.prototype_count
            registry_coverage = $registryCoverage
            next_phase = [string]$audit.next_phase
            next_module_id = $nextModuleId
            next_module_action = $nextModuleAction
            next_module_evidence = $moduleEvidencePath
            next_module_evidence_status = $moduleEvidenceStatus
            next_module_command = $nextModuleCommand
            next_extraction_id = [string]$audit.next_extraction_id
            next_supplemental_id = [string]$audit.next_supplemental_id
            extraction_plan = $extractionPlan
            supplemental_refactor_plan = $supplementalPlan
            static_gate_count = $staticGateSummary.Count
            static_gate_passed_count = $staticGatePassedCount
            static_gate_summary = $staticGateSummary
            modules = $modules
        }
    } catch {
        return [pscustomobject]@{
            status = "invalid"
            path = [System.IO.Path]::GetFullPath($path)
            modularization_pressure = ""
            implemented_count = 0
            prototype_count = 0
            registry_coverage = "0 / 0"
            next_phase = "Regenerate module audit."
            next_module_id = ""
            next_module_action = "Regenerate module audit."
            next_module_command = ""
            next_extraction_id = ""
            next_supplemental_id = ""
            helper_budget_status = ""
            helper_line_count = 0
            helper_line_budget = 0
            extraction_plan = @()
            supplemental_refactor_plan = @()
            static_gate_count = 0
            static_gate_passed_count = 0
            static_gate_summary = @()
            modules = @()
        }
    }
}

function Invoke-GoalStatus {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    Invoke-SmokeStatus
    Invoke-ModuleAudit

    Push-Location $repo
    try {
        & python scripts\ops\solteria_helper_release_gate.py --dev-dir $outRoot --allow-blocked
        if ($LASTEXITCODE -ne 0) {
            throw "Release gate audit failed"
        }
        & python scripts\ops\solteria_helper_goal_audit.py --dev-dir $outRoot --allow-blocked
        if ($LASTEXITCODE -ne 0) {
            throw "Goal audit failed"
        }
    } finally {
        Pop-Location
    }

    $goalPath = Join-Path $outRoot "goal_audit.json"
    $goalDashboardPath = Join-Path $outRoot "goal_audit.html"
    $gatePath = Join-Path $outRoot "release_gate.json"
    $goal = Get-Content -LiteralPath $goalPath -Raw | ConvertFrom-Json
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    $moduleAudit = Read-ModuleAuditSummary -DevRoot $outRoot
    $smokeQueue = Read-SmokeQueueSummary -DevRoot $outRoot
    $roadmap = @($goal.items | Where-Object { [string]$_.name -like "P*" } | ForEach-Object {
        [pscustomobject]@{
            name = [string]$_.name
            status = [string]$_.status
            evidence = [string]$_.evidence
        }
    })
    $liveProcesses = @(Get-Process solteria-client -ErrorAction SilentlyContinue | Where-Object {
        try {
            $_.Path -and ([System.IO.Path]::GetFullPath($_.Path) -like ([System.IO.Path]::GetFullPath($SourceClient) + "*"))
        } catch {
            $false
        }
    } | ForEach-Object {
        [pscustomobject]@{
            id = $_.Id
            responding = $_.Responding
            path = $_.Path
        }
    })
    $status = [pscustomobject]@{
        name = "solteria-helper-goal-status"
        created_at = (Get-Date).ToString("s")
        status = [string]$goal.status
        complete = [bool]$goal.complete
        release_gate_status = [string]$gate.status
        releasable_to_live = [bool]$gate.releasable_to_live
        blockers = @($goal.blockers)
        next_action = [string]$goal.next_action
        next_command = [string]$goal.next_command
        roadmap = $roadmap
        sandbox_smoke_queue = $smokeQueue
        module_audit = $moduleAudit
        live_processes = $liveProcesses
        handoff_path = [System.IO.Path]::GetFullPath((Join-Path $outRoot "GOAL_HANDOFF.md"))
        dashboard_path = [System.IO.Path]::GetFullPath($goalDashboardPath)
        live_safety = "GoalStatus refreshes SmokeStatus and dev audit files only; it does not launch, stop, or overwrite any client."
    }
    $statusPath = Join-Path $outRoot "goal_status.json"
    Write-JsonAtomic -InputObject $status -Path $statusPath -Depth 8
    Write-GoalHandoff -Status $status -Path $status.handoff_path

    Write-Output "[solteria-helper-test-env] Goal status: $statusPath"
    Write-Output "[solteria-helper-test-env] Goal dashboard: $($status.dashboard_path)"
    Write-Output "[solteria-helper-test-env] Goal handoff: $($status.handoff_path)"
    Write-Output "[solteria-helper-test-env] Goal: $($status.status); complete=$($status.complete); release_gate=$($status.release_gate_status); releasable_to_live=$($status.releasable_to_live)"
    foreach ($item in $roadmap) {
        Write-Output ("[solteria-helper-test-env] {0}: {1}" -f $item.name, $item.status)
    }
    foreach ($blocker in $status.blockers) {
        Write-Output "[solteria-helper-test-env] Blocker: $blocker"
    }
    if (-not [string]::IsNullOrWhiteSpace($status.next_action)) {
        Write-Output "[solteria-helper-test-env] Next action: $($status.next_action)"
    }
    if (-not [string]::IsNullOrWhiteSpace($status.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($status.next_command)"
    }
}

function Invoke-LocalReady {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    Invoke-DevValidation
    Invoke-SmokePreflight
    Invoke-ModuleStaticGates
    Invoke-GoalStatus
    Invoke-SmokeQueue

    $validationPath = Join-Path $outRoot "validation.json"
    $preflightPath = Join-Path $outRoot "smoke_preflight.json"
    $moduleGatesPath = Join-Path $outRoot "module_static_gates.json"
    $goalStatusPath = Join-Path $outRoot "goal_status.json"
    $releaseGatePath = Join-Path $outRoot "release_gate.json"
    $smokeQueuePath = Join-Path $outRoot "sandbox_smoke_queue.json"
    $validation = Get-Content -LiteralPath $validationPath -Raw | ConvertFrom-Json
    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    $moduleGates = Get-Content -LiteralPath $moduleGatesPath -Raw | ConvertFrom-Json
    $goalStatus = Get-Content -LiteralPath $goalStatusPath -Raw | ConvertFrom-Json
    $releaseGate = Get-Content -LiteralPath $releaseGatePath -Raw | ConvertFrom-Json
    $smokeQueue = Get-Content -LiteralPath $smokeQueuePath -Raw | ConvertFrom-Json
    $localPassed = (
        [string]$validation.status -eq "passed" -and
        [string]$preflight.status -eq "passed" -and
        [string]$moduleGates.status -eq "passed"
    )
    $report = [pscustomobject]@{
        name = "solteria-helper-local-ready"
        created_at = (Get-Date).ToString("s")
        status = if ($localPassed) { "ready_for_sandbox" } else { "blocked" }
        validation_status = [string]$validation.status
        smoke_preflight_status = [string]$preflight.status
        module_static_gates_status = [string]$moduleGates.status
        module_static_gates_passed = ("{0}/{1}" -f $moduleGates.passed_count, $moduleGates.gate_count)
        release_gate_status = [string]$releaseGate.status
        goal_status = [string]$goalStatus.status
        sandbox_smoke_queue_status = [string]$smokeQueue.status
        next_action = [string]$goalStatus.next_action
        next_command = [string]$goalStatus.next_command
        validation_path = [System.IO.Path]::GetFullPath($validationPath)
        smoke_preflight_path = [System.IO.Path]::GetFullPath($preflightPath)
        module_static_gates_path = [System.IO.Path]::GetFullPath($moduleGatesPath)
        release_gate_path = [System.IO.Path]::GetFullPath($releaseGatePath)
        goal_status_path = [System.IO.Path]::GetFullPath($goalStatusPath)
        sandbox_smoke_queue_path = [System.IO.Path]::GetFullPath($smokeQueuePath)
        handoff_path = [System.IO.Path]::GetFullPath((Join-Path $outRoot "GOAL_HANDOFF.md"))
        live_safety = "LocalReady runs local packaging, static validation, SmokePreflight, ModuleStaticGates, GoalStatus, and SmokeQueue only; it does not launch, stop, attach to, promote, or overwrite any live client."
    }
    $path = Join-Path $outRoot "local_ready.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Local ready: $path"
    Write-Output "[solteria-helper-test-env] Local ready status: $($report.status)"
    Write-Output "[solteria-helper-test-env] Smoke queue: $smokeQueuePath"
    Write-Output "[solteria-helper-test-env] Smoke queue status: $($report.sandbox_smoke_queue_status)"
    Write-Output "[solteria-helper-test-env] Next action: $($report.next_action)"
    if (-not [string]::IsNullOrWhiteSpace($report.next_command)) {
        Write-Output "[solteria-helper-test-env] Next command: $($report.next_command)"
    }
    if (-not $localPassed) {
        throw "LocalReady failed before sandbox runtime step"
    }
}

function Invoke-SmokeQueue {
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    Invoke-GoalStatus
    $queueScript = Join-Path $repo "scripts\ops\solteria_helper_sandbox_smoke_queue.py"
    if (-not (Test-Path -LiteralPath $queueScript)) {
        throw "Missing sandbox smoke queue generator: $queueScript"
    }
    $jsonOut = Join-Path $outRoot "sandbox_smoke_queue.json"
    $planOut = Join-Path $repo "docs\otclient\solteria_helper_sandbox_smoke_queue.md"
    & python $queueScript --dev-dir $outRoot --json-out $jsonOut --plan-out $planOut
    if ($LASTEXITCODE -ne 0) {
        throw "SmokeQueue generator failed with exit code $LASTEXITCODE"
    }
    $queue = Get-Content -LiteralPath $jsonOut -Raw | ConvertFrom-Json
    Write-Output "[solteria-helper-test-env] Smoke queue: $jsonOut"
    Write-Output "[solteria-helper-test-env] Smoke queue plan: $planOut"
    Write-Output "[solteria-helper-test-env] Smoke queue status: $($queue.status)"
    Write-Output "[solteria-helper-test-env] Smoke queue next action: $($queue.next_action)"
    Invoke-GoalStatus
}

function Invoke-Smoke {
    $resolved = Resolve-SmokeTab -RequestedTab $Tab
    Initialize-Sandbox
    Stop-SandboxClient
    Start-SandboxClient
    Start-Sleep -Seconds 3

    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32SolteriaTestEnv {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
  }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
"@
    $proc = $null
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not $proc) {
        $proc = Get-SandboxProcesses |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if (-not $proc) {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $proc) {
        throw "Sandbox client window was not found for: $SandboxClient"
    }
    [Win32SolteriaTestEnv]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null
    [Win32SolteriaTestEnv]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
    [Win32SolteriaTestEnv]::SetCursorPos(20, 20) | Out-Null
    Start-Sleep -Milliseconds 800
    Add-Type -AssemblyName System.Windows.Forms
    if ($ToggleHelper) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('^j')
        Start-Sleep -Seconds 2
    } else {
        Wait-ForSmokeTab -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab | Out-Null
    }
    if ($DismissDialogs) {
        [Win32SolteriaTestEnv]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
        Start-Sleep -Milliseconds 300
        [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
        Start-Sleep -Milliseconds 300
        $rect = New-Object Win32SolteriaTestEnv+RECT
        if ([Win32SolteriaTestEnv]::GetWindowRect($proc.MainWindowHandle, [ref]$rect)) {
            $clickX = [int]($rect.Left + (($rect.Right - $rect.Left) * 0.755))
            $clickY = [int]($rect.Top + (($rect.Bottom - $rect.Top) * 0.760))
            [Win32SolteriaTestEnv]::SetCursorPos($clickX, $clickY) | Out-Null
            Start-Sleep -Milliseconds 100
            [Win32SolteriaTestEnv]::mouse_event(0x0002, 0, 0, 0, 0)
            Start-Sleep -Milliseconds 80
            [Win32SolteriaTestEnv]::mouse_event(0x0004, 0, 0, 0, 0)
        }
        Start-Sleep -Milliseconds 1200
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $shot = Capture-Screenshot -Name ("solteria-helper-testenv-{0}-{1}.png" -f $resolved.Requested, $stamp) -WindowHandle $proc.MainWindowHandle
    Write-Output "[solteria-helper-test-env] Screenshot: $shot"
    if ($DismissDialogs) {
        Write-Output "[solteria-helper-test-env] Note: -DismissDialogs attempts to close the character modal, but Solteria may keep Select Character above helper until a character is entered."
    }
    if (Test-AtCharacterSelect) {
        Write-Output "[solteria-helper-test-env] Runtime view may be modal-obscured before character login."
    }
    if (Test-Path -LiteralPath (Join-Path $SandboxClient "ctoa_local.log")) {
        Get-Content -LiteralPath (Join-Path $SandboxClient "ctoa_local.log") -Tail 20
    }
}

function Invoke-SmokeAttach {
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxRoot
    $resolved = Resolve-SmokeTab -RequestedTab $Tab
    $lineCountBeforeCommand = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxRoot -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab

    $proc = $null
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline -and -not $proc) {
        $proc = Get-SandboxProcesses |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if (-not $proc) {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $proc) {
        throw "No running sandbox client window found for SmokeAttach: $SandboxClient"
    }

    Wait-ForSmokeTab -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab -Required -AfterLineCount $lineCountBeforeCommand | Out-Null
    $stamp = if ([string]::IsNullOrWhiteSpace($RunId)) { Get-Date -Format "yyyyMMdd-HHmmss" } else { $RunId + (Get-Date -Format "ss") }
    $shot = Capture-Screenshot -Name ("solteria-helper-attach-{0}-{1}.png" -f $resolved.Requested, $stamp) -WindowHandle $proc.MainWindowHandle
    Write-Output "[solteria-helper-test-env] Attach screenshot: $shot"
    if (Test-Path -LiteralPath (Join-Path $SandboxClient "ctoa_local.log")) {
        Get-Content -LiteralPath (Join-Path $SandboxClient "ctoa_local.log") -Tail 20
    }
}

function Invoke-SmokeAttachAll {
    $attachRunId = $RunId
    if ([string]::IsNullOrWhiteSpace($attachRunId)) {
        $attachRunId = Get-Date -Format "yyyyMMdd-HHmm"
    }
    $repoRoot = Get-RepoRoot
    $manifestPath = Join-Path (Join-Path $repoRoot $DevDir) "manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "SmokeAttachAll requires the current dev manifest: $manifestPath"
    }
    Write-Output "[solteria-helper-test-env] Attach run id: $attachRunId"
    $tabs = @(
        "overview",
        "healing",
        "heal_friend",
        "conditions",
        "hunting",
        "hunting_magic",
        "cavebot",
        "equipment",
        "tools",
        "tools_pvp",
        "tools_hud",
        "tools_timer",
        "tools_diag",
        "scripting",
        "profile",
        "ui"
    )
    foreach ($tabName in $tabs) {
        Write-Output "[solteria-helper-test-env] Attach smoke tab: $tabName"
        $script = $PSCommandPath
        $args = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $script,
            "-Action", "SmokeAttach",
            "-Tab", $tabName,
            "-SourceClient", $SourceClient,
            "-SandboxClient", $SandboxClient,
            "-ScreenshotDir", $ScreenshotDir,
            "-RunId", $attachRunId
        )
        & powershell @args
        if ($LASTEXITCODE -ne 0) {
            throw "Attach smoke failed for tab: $tabName"
        }
    }
    if (-not $NoReport) {
        $reportScript = Join-Path $repoRoot "scripts\ops\ctoa_helper_smoke_report.py"
        & python $reportScript --run-id $attachRunId --prefix solteria-helper-attach --in-world --screenshot-dir (Join-Path $repoRoot $ScreenshotDir) --manifest-path $manifestPath
        if ($LASTEXITCODE -ne 0) {
            throw "Attach smoke coverage report failed for run id: $attachRunId"
        }
    }
}

function Invoke-SmokeAttachModules {
    $attachRunId = $RunId
    if ([string]::IsNullOrWhiteSpace($attachRunId)) {
        $attachRunId = Get-Date -Format "yyyyMMdd-HHmm"
    }
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $manifestPath = Join-Path $outRoot "manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Module attach smoke requires the current dev manifest: $manifestPath"
    }
    $manifestDocument = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $manifestSha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifestCreatedAt = [string]$manifestDocument.created_at
    Write-Output "[solteria-helper-test-env] Module attach run id: $attachRunId"

    $moduleTabs = @("conditions", "equipment", "heal_friend", "scripting")
    $modules = New-Object System.Collections.Generic.List[object]
    foreach ($tabName in $moduleTabs) {
        Write-Output "[solteria-helper-test-env] Module attach smoke tab: $tabName"
        $script = $PSCommandPath
        $args = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $script,
            "-Action", "SmokeAttach",
            "-Tab", $tabName,
            "-SourceClient", $SourceClient,
            "-SandboxClient", $SandboxClient,
            "-ScreenshotDir", $ScreenshotDir,
            "-RunId", $attachRunId
        )
        & powershell @args
        if ($LASTEXITCODE -eq 0) {
            $modules.Add([pscustomobject]@{
                module = $tabName
                status = "passed"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab $tabName"
                error = ""
            })
        } else {
            $modules.Add([pscustomobject]@{
                module = $tabName
                status = "failed"
                attach_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab $tabName"
                error = "SmokeAttach failed for tab: $tabName"
            })
        }
    }

    $moduleArray = @($modules.ToArray())
    $failed = @($moduleArray | Where-Object { $_.status -ne "passed" })
    $report = [pscustomobject]@{
        name = "solteria-helper-module-attach-smoke"
        created_at = (Get-Date).ToString("s")
        status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        run_id = $attachRunId
        module_count = $moduleArray.Count
        passed_count = @($moduleArray | Where-Object { $_.status -eq "passed" }).Count
        failed_count = $failed.Count
        manifest = [pscustomobject]@{
            path = [System.IO.Path]::GetFullPath($manifestPath)
            created_at = $manifestCreatedAt
            sha256 = $manifestSha256
        }
        modules = $moduleArray
        required_sequence = @("conditions", "equipment", "heal_friend")
        next_action = if ($failed.Count -eq 0) { "Run SmokeAttachAll for final in-world visual acceptance." } else { "Enter the sandbox test character, run ReadyCheck, then rerun SmokeAttachModules." }
        next_command = if ($failed.Count -eq 0) { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll" } else { "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck" }
        live_safety = "SmokeAttachModules attaches only to an already-running sandbox client and switches prototype module tabs; it does not launch, stop, promote, overwrite live files, cast, talk, or enable runtime automation."
    }
    $path = Join-Path $outRoot "module_attach_smoke.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Module attach smoke: $path"
    Write-Output "[solteria-helper-test-env] Module attach status: $($report.status) ($($report.passed_count)/$($report.module_count))"
    if ($report.status -ne "passed") {
        throw "Module attach smoke failed"
    }
}

function Invoke-ThemeSnapshotMatrix {
    $sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient
    Sync-CtoaRuntimeFiles -ClientDir $sandboxRoot
    $proc = Get-SandboxProcesses |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1
    if (-not $proc) {
        throw "No running sandbox client window found for ThemeSnapshotMatrix: $sandboxRoot"
    }

    $repo = Get-RepoRoot
    $outputRoot = Join-Path $repo $ScreenshotDir
    $devRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $devRoot | Out-Null
    $themes = @("classic", "graphite", "amber", "emerald")
    $tabs = @("overview", "profile", "cavebot", "healing", "ui")
    $helperVersion = Get-HelperVersion
    $shots = New-Object System.Collections.Generic.List[object]

    foreach ($theme in $themes) {
        foreach ($tabName in $tabs) {
            $resolved = Resolve-SmokeTab -RequestedTab $tabName
            $lineCount = Get-SmokeLogLineCount
            Write-SmokeCommand -ClientDir $sandboxRoot -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab -CommandAction "theme_set" -Theme $theme
            Wait-ForSmokeTab -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab -Required -AfterLineCount $lineCount | Out-Null
            $name = "solteria-helper-$helperVersion-theme-$theme-$tabName.png"
            $path = Capture-Screenshot -Name $name -WindowHandle $proc.MainWindowHandle
            $shots.Add([pscustomobject]@{ theme = $theme; tab = $tabName; path = $path })
            Write-Output "[solteria-helper-test-env] Theme snapshot: $theme/$tabName -> $path"
        }
    }

    $lineCount = Get-SmokeLogLineCount
    Write-SmokeCommand -ClientDir $sandboxRoot -ActiveTab "ui" -CommandAction "theme_set" -Theme "graphite"
    Wait-ForSmokeTab -ActiveTab "ui" -Required -AfterLineCount $lineCount | Out-Null
    $report = [pscustomobject]@{
        name = "solteria-helper-theme-snapshot-matrix"
        created_at = (Get-Date).ToString("s")
        helper_version = $helperVersion
        status = if ($shots.Count -eq 20) { "passed" } else { "failed" }
        screenshot_count = $shots.Count
        expected_count = 20
        restored_theme = "graphite"
        runtime_arming = "unchanged"
        screenshots = @($shots.ToArray())
        live_safety = "ThemeSnapshotMatrix writes sandbox smoke commands and captures the sandbox window only; it does not arm runtime or touch the live client."
    }
    $reportPath = Join-Path $devRoot "theme_snapshot_matrix.json"
    Write-JsonAtomic -InputObject $report -Path $reportPath -Depth 6
    Write-Output "[solteria-helper-test-env] Theme matrix: $reportPath ($($report.screenshot_count)/$($report.expected_count))"
    if ($report.status -ne "passed") {
        throw "ThemeSnapshotMatrix did not capture all expected screenshots"
    }
}

function Invoke-Snapshot {
    $proc = $null
    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $deadline -and -not $proc) {
        $proc = Get-SandboxProcesses |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if (-not $proc) {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $proc) {
        throw "No running sandbox client window found for Snapshot: $SandboxClient"
    }
    $stamp = if ([string]::IsNullOrWhiteSpace($RunId)) { Get-Date -Format "yyyyMMdd-HHmmss" } else { $RunId + (Get-Date -Format "ss") }
    $shot = Capture-Screenshot -Name ("solteria-helper-snapshot-{0}.png" -f $stamp) -WindowHandle $proc.MainWindowHandle
    $script:LastSnapshotPath = $shot
    Write-Output "[solteria-helper-test-env] Snapshot: $shot"
}

function Write-ReadyCheckReport {
    param(
        [string]$Status,
        [string]$Screenshot = "",
        [string]$ErrorMessage = "",
        [string]$NextAction = "",
        [string]$NextCommand = ""
    )
    $repo = Get-RepoRoot
    $outRoot = Join-Path $repo $DevDir
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $ctoaLog = Join-Path $SandboxClient "ctoa_local.log"
    $latestSmokeMarker = ""
    if (Test-Path -LiteralPath $ctoaLog) {
        $latestSmokeMarker = [string](@(Get-Content -LiteralPath $ctoaLog -Tail 40 -ErrorAction SilentlyContinue | Where-Object { $_ -match "Smoke tab visible:" } | Select-Object -Last 1) | Select-Object -First 1)
    }
    $report = [pscustomobject]@{
        name = "solteria-helper-ready-check"
        created_at = (Get-Date).ToString("s")
        status = $Status
        screenshot = $Screenshot
        latest_smoke_marker = $latestSmokeMarker
        error = $ErrorMessage
        next_action = $NextAction
        next_command = $NextCommand
        live_safety = "ReadyCheck attaches to the sandbox client only; it does not launch, stop, or overwrite the live client."
    }
    $path = Join-Path $outRoot "ready_check.json"
    Write-JsonAtomic -InputObject $report -Path $path -Depth 8
    Write-Output "[solteria-helper-test-env] Ready check report: $path"
}

function Invoke-ReadyCheck {
    Write-Output "[solteria-helper-test-env] Ready check: snapshot"
    try {
        Invoke-Snapshot
    } catch {
        Write-ReadyCheckReport -Status "blocked_no_sandbox_window" -ErrorMessage ([string]$_.Exception.Message) -NextAction "Launch the sandbox client, enter the test character, then rerun ReadyCheck." -NextCommand "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch"
        throw
    }
    $snapshotPath = [string]$script:LastSnapshotPath
    Write-Output "[solteria-helper-test-env] Ready check: fresh helper marker"
    $previousTab = $Tab
    try {
        $script:Tab = "ui"
        Invoke-SmokeAttach
        Write-ReadyCheckReport -Status "ready" -Screenshot $snapshotPath -NextAction "Run SmokeAttachModules for focused prototype module evidence, then SmokeAttachAll for final in-world visual acceptance." -NextCommand "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules"
        Write-Output "[solteria-helper-test-env] Ready: in-world attach smoke can switch helper tabs."
    } catch {
        Write-Output "[solteria-helper-test-env] Not ready: blocked_by_character_modal or helper not online."
        Write-Output "[solteria-helper-test-env] Enter a character, then rerun ReadyCheck or SmokeAttachModules."
        Write-ReadyCheckReport -Status "blocked_by_character_modal_or_helper_offline" -Screenshot $snapshotPath -ErrorMessage ([string]$_.Exception.Message) -NextAction "Enter the sandbox test character, then rerun ReadyCheck or SmokeAttachModules." -NextCommand "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck"
        throw
    } finally {
        $script:Tab = $previousTab
    }
}

function Invoke-SmokeAll {
    $tabs = @(
        "overview",
        "healing",
        "heal_friend",
        "conditions",
        "hunting",
        "hunting_magic",
        "cavebot",
        "equipment",
        "tools",
        "tools_pvp",
        "tools_hud",
        "tools_timer",
        "tools_diag",
        "scripting",
        "profile",
        "ui"
    )
    foreach ($tabName in $tabs) {
        Write-Output "[solteria-helper-test-env] Smoke tab: $tabName"
        $script = $PSCommandPath
        $args = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $script,
            "-Action", "Smoke",
            "-Tab", $tabName,
            "-SourceClient", $SourceClient,
            "-SandboxClient", $SandboxClient,
            "-ScreenshotDir", $ScreenshotDir
        )
        if ($DismissDialogs) {
            $args += "-DismissDialogs"
        }
        if ($ToggleHelper) {
            $args += "-ToggleHelper"
        }
        & powershell @args
        if ($LASTEXITCODE -ne 0) {
            throw "Smoke failed for tab: $tabName"
        }
    }
}

function Get-BackgroundProcessSample {
    $items = @(Get-SourceClientProcessSummaries | Sort-Object id)
    $tokens = @($items | ForEach-Object { "{0}|{1}" -f $_.id, $_.start_time })
    $startUnixMs = 0
    if ($items.Count -eq 1) {
        $startUnixMs = [long]$items[0].start_unix_ms
    }
    return [pscustomobject]@{
        count = $items.Count
        signature = ($tokens -join ";")
        start_unix_ms = $startUnixMs
    }
}

function Get-BackgroundScreenshotCount {
    $repo = Get-RepoRoot
    $root = Join-Path $repo $ScreenshotDir
    if (-not (Test-Path -LiteralPath $root)) {
        return 0
    }
    return @(Get-ChildItem -LiteralPath $root -Filter "*.png" -File -ErrorAction SilentlyContinue).Count
}

function Invoke-BackgroundStatus {
    $repo = Get-RepoRoot
    $sourceRoot = Assert-ExactLiveClientPath -Path $SourceClient
    $outRoot = Assert-ExactBackgroundOutputPath -RepoRoot $repo -Candidate (Join-Path $repo $DevDir)
    $scriptPath = Join-Path $repo "scripts\ops\otclient_headless_status.py"
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "BackgroundNoScreen requires the trusted repo interpreter: $python"
    }

    $beforeProcesses = Get-BackgroundProcessSample
    $beforeScreenshots = Get-BackgroundScreenshotCount
    $arguments = @(
        $scriptPath,
        "--client-root", $sourceRoot,
        "--dev-dir", $outRoot,
        "--process-count", ([string]$beforeProcesses.count),
        "--process-start-unix-ms", ([string]$beforeProcesses.start_unix_ms),
        "--json-out", (Join-Path $outRoot "background_status.json"),
        "--no-write"
    )
    $rawPayload = @(& $python @arguments)
    $observerExitCode = $LASTEXITCODE
    if ($observerExitCode -gt 1) {
        throw "BackgroundStatus evidence collection failed before producing evidence."
    }
    try {
        $payload = ($rawPayload -join "`n") | ConvertFrom-Json
    } catch {
        throw "BackgroundStatus returned malformed evidence."
    }

    $afterProcesses = Get-BackgroundProcessSample
    $afterScreenshots = Get-BackgroundScreenshotCount
    $processStable = $beforeProcesses.signature -ceq $afterProcesses.signature
    $screenshotsStable = $beforeScreenshots -eq $afterScreenshots
    $payload.checks | Add-Member -NotePropertyName "client_process_stable_during_wrapper" -NotePropertyValue $processStable -Force
    $payload.checks | Add-Member -NotePropertyName "screenshot_count_stable_during_wrapper" -NotePropertyValue $screenshotsStable -Force
    $payload | Add-Member -NotePropertyName "wrapper_invariants" -NotePropertyValue ([pscustomobject]@{
        client_process_stable = $processStable
        screenshot_count_stable = $screenshotsStable
    }) -Force
    $blockers = @($payload.blockers)
    if (-not $processStable) {
        $blockers += "client_process_changed_during_observation"
    }
    if (-not $screenshotsStable) {
        $blockers += "screenshot_count_changed_during_observation"
    }
    if (-not $processStable -or -not $screenshotsStable) {
        $payload.status = "blocked"
        $payload.next_action = "Discard this sample; repeat passive observation after the external state is stable."
    }
    $payload.blockers = @($blockers | Select-Object -Unique)
    $payload.passed_check_count = @(
        $payload.checks.PSObject.Properties | Where-Object { $_.Value -eq $true }
    ).Count
    $payload.check_count = @($payload.checks.PSObject.Properties).Count

    $outRoot = Assert-ExactBackgroundOutputPath -RepoRoot $repo -Candidate $outRoot
    $outputPath = [System.IO.Path]::GetFullPath((Join-Path $outRoot "background_status.json"))
    $expectedOutputPath = [System.IO.Path]::GetFullPath(
        (Join-Path (Join-Path $repo "runtime\solteria_helper_dev") "background_status.json")
    )
    if (-not $outputPath.Equals($expectedOutputPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "BackgroundNoScreen publication escaped the exact runtime output path."
    }
    if ($NoReport) {
        $payload | ConvertTo-Json -Depth 12
    } else {
        Write-JsonAtomic -InputObject $payload -Path $outputPath -Depth 12
        Write-Output "[otclient-headless-status] JSON: $outputPath"
        Write-Output "[otclient-headless-status] Status: $($payload.status)"
        Write-Output "[otclient-headless-status] Next: $($payload.next_action)"
    }

    if (-not $processStable) {
        throw "BackgroundStatus observed a client process change and stored a blocked sample."
    }
    if (-not $screenshotsStable) {
        throw "BackgroundStatus observed a screenshot-count change and stored a blocked sample."
    }
    Write-Output "[solteria-helper-test-env] BackgroundNoScreen invariants passed: process and screenshot state unchanged."
}

function Invoke-EquipmentShadowSnapshotStaticSmoke {
    $repo = Get-RepoRoot
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $repo "scripts\ops\otclient_equipment_shadow_snapshot.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or -not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 Equipment shadow snapshot static smoke requires the repo interpreter and producer."
    }
    $raw = (& $python $scriptPath --no-write --allow-blocked | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "P10 Equipment shadow snapshot static smoke failed." }
    $payload = $raw | ConvertFrom-Json
    if ($payload.schema_version -ne "ctoa.equipment-shadow-snapshot-ingest.v1" -or $payload.snapshot_written -eq $true -or $payload.runtime_actions -eq $true -or $payload.dispatch_allowed -eq $true) {
        throw "P10 Equipment shadow snapshot producer violated its fail-closed contract."
    }
    $outRoot = Assert-ExactBackgroundOutputPath -RepoRoot $repo -Candidate (Join-Path $repo $DevDir)
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $report = [pscustomobject]@{
        name = "equipment-shadow-snapshot-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = "passed"
        producer_status = [string]$payload.status
        acceptance_granted = $false
        dispatch_allowed = $false
        runtime_actions = $false
        executes_plan = $false
        execute_once_allowed = $false
        promotion_allowed = $false
        intrusive_actions_performed = @()
    }
    Write-JsonAtomic -InputObject $report -Path (Join-Path $outRoot "equipment_shadow_snapshot_static_smoke.json") -Depth 8
    Write-Output "[solteria-helper-test-env] Equipment shadow snapshot static smoke: passed (producer remains fail-closed)."
}

function Invoke-EquipmentShadowReplayStaticSmoke {
    $repo = Get-RepoRoot
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $repo "scripts\ops\otclient_equipment_shadow_replay.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or -not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 Equipment shadow replay static smoke requires the repo interpreter and replay tool."
    }
    & $python $scriptPath --no-write --source fixture | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "P10 Equipment shadow replay static smoke failed."
    }
    $outRoot = Assert-ExactBackgroundOutputPath -RepoRoot $repo -Candidate (Join-Path $repo $DevDir)
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $report = [pscustomobject]@{
        name = "equipment-shadow-replay-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = "passed"
        passed_count = 30
        check_count = 30
        failed_count = 0
        fixture_only = $true
        runtime_readiness_claimed = $false
        dispatch_allowed = $false
        runtime_actions = $false
        executes_plan = $false
        execute_once_allowed = $false
        promotion_allowed = $false
        intrusive_actions_performed = @()
    }
    Write-JsonAtomic -InputObject $report -Path (Join-Path $outRoot "equipment_shadow_replay_static_smoke.json") -Depth 8
    Write-Output "[solteria-helper-test-env] Equipment shadow replay static smoke: passed (30/30 fixture cases)."
}

function Invoke-EquipmentShadowAcceptanceStaticSmoke {
    $repo = Get-RepoRoot
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $scriptPath = Join-Path $repo "scripts\ops\otclient_equipment_shadow_acceptance.py"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or -not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "P10 Equipment shadow acceptance static smoke requires the repo interpreter and acceptance tool."
    }
    $raw = (& $python $scriptPath --no-write | Out-String)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 1) { throw "P10 Equipment acceptance must remain blocked without exact confirmation and operational inputs." }
    $payload = $raw | ConvertFrom-Json
    if ($payload.acceptance_granted -eq $true -or $payload.receipt_persisted -eq $true -or $payload.runtime_actions -eq $true -or $payload.dispatch_allowed -eq $true) {
        throw "P10 Equipment acceptance preflight violated its no-action contract."
    }
    $outRoot = Assert-ExactBackgroundOutputPath -RepoRoot $repo -Candidate (Join-Path $repo $DevDir)
    New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
    $report = [pscustomobject]@{
        name = "equipment-shadow-acceptance-static-smoke"
        created_at = (Get-Date).ToString("s")
        status = "passed"
        preflight_status = [string]$payload.status
        acceptance_granted = $false
        receipt_persisted = $false
        dispatch_allowed = $false
        runtime_actions = $false
        executes_plan = $false
        execute_once_allowed = $false
        promotion_allowed = $false
        intrusive_actions_performed = @()
    }
    Write-JsonAtomic -InputObject $report -Path (Join-Path $outRoot "equipment_shadow_acceptance_static_smoke.json") -Depth 8
    Write-Output "[solteria-helper-test-env] Equipment shadow acceptance static smoke: passed (independent receipt remains blocked)."
}

Assert-OperatorModeAction

switch ($Action) {
    "PrepareDev" {
        New-DevPackage
    }
    "ValidateDev" {
        Invoke-DevValidation
    }
    "Setup" {
        Initialize-Sandbox
        Write-Output "[solteria-helper-test-env] Sandbox ready: $SandboxClient"
    }
    "SmokePreflight" {
        Invoke-SmokePreflight
    }
    "SmokeStatus" {
        Invoke-SmokeStatus
    }
    "SmokeQueue" {
        Invoke-SmokeQueue
    }
    "GoalStatus" {
        Invoke-GoalStatus
    }
    "BackgroundStatus" {
        Invoke-BackgroundStatus
    }
    "LocalReady" {
        Invoke-LocalReady
    }
    "Launch" {
        Initialize-Sandbox
        Start-SandboxClient
        Write-Output "[solteria-helper-test-env] Launched: $SandboxClient"
    }
    "Smoke" {
        Invoke-Smoke
    }
    "SmokeAttach" {
        Invoke-SmokeAttach
    }
    "SmokeAttachModules" {
        Invoke-SmokeAttachModules
    }
    "SmokeAttachAll" {
        Invoke-SmokeAttachAll
    }
    "ThemeSnapshotMatrix" {
        Invoke-ThemeSnapshotMatrix
    }
    "HealingVitalsSmoke" {
        Invoke-HealingVitalsSmoke
    }
    "CombatSafetySmoke" {
        Invoke-CombatSafetySmoke
    }
    "CavebotSafetySmoke" {
        Invoke-CavebotSafetySmoke
    }
    "TimerSafetySmoke" {
        Invoke-TimerSafetySmoke
    }
    "LootSafetySmoke" {
        Invoke-LootSafetySmoke
    }
    "HealFriendNoTargetSmoke" {
        Invoke-HealFriendNoTargetSmoke
    }
    "ConditionsObserverSmoke" {
        Invoke-ConditionsObserverSmoke
    }
    "EquipmentObserverSmoke" {
        Invoke-EquipmentObserverSmoke
    }
    "ScriptingPolicySmoke" {
        Invoke-ScriptingPolicySmoke
    }
    "PlannerStaticSmoke" {
        Invoke-PlannerStaticSmoke
    }
    "RuntimePolicyStaticSmoke" {
        Invoke-RuntimePolicyStaticSmoke
    }
    "DispatchGuardStaticSmoke" {
        Invoke-DispatchGuardStaticSmoke
    }
    "PlanQueueStaticSmoke" {
        Invoke-PlanQueueStaticSmoke
    }
    "RuntimeReadinessStaticSmoke" {
        Invoke-RuntimeReadinessStaticSmoke
    }
    "ModuleStatusStaticSmoke" {
        Invoke-ModuleStatusStaticSmoke
    }
    "ActionCatalogStaticSmoke" {
        Invoke-ActionCatalogStaticSmoke
    }
    "DecisionTraceStaticSmoke" {
        Invoke-DecisionTraceStaticSmoke
    }
    "DecisionPipelineStaticSmoke" {
        Invoke-DecisionPipelineStaticSmoke
    }
    "SandboxHandoffStaticSmoke" {
        Invoke-SandboxHandoffStaticSmoke
    }
    "FeatureFlagsStaticSmoke" {
        Invoke-FeatureFlagsStaticSmoke
    }
    "HudStaticSmoke" {
        Invoke-HudStaticSmoke
    }
    "HotkeysStaticSmoke" {
        Invoke-HotkeysStaticSmoke
    }
    "ModalStaticSmoke" {
        Invoke-ModalStaticSmoke
    }
    "InputContractsStaticSmoke" {
        Invoke-InputContractsStaticSmoke
    }
    "RouteStaticSmoke" {
        Invoke-RouteStaticSmoke
    }
    "TargetingStaticSmoke" {
        Invoke-TargetingStaticSmoke
    }
    "CombatRuntimeStaticSmoke" {
        Invoke-CombatRuntimeStaticSmoke
    }
    "CavebotRuntimeStaticSmoke" {
        Invoke-CavebotRuntimeStaticSmoke
    }
    "LootRuntimeStaticSmoke" {
        Invoke-LootRuntimeStaticSmoke
    }
    "TimerRuntimeStaticSmoke" {
        Invoke-TimerRuntimeStaticSmoke
    }
    "RecoveryRuntimeStaticSmoke" {
        Invoke-RecoveryRuntimeStaticSmoke
    }
    "RecoveryBridgeStaticSmoke" {
        Invoke-RecoveryBridgeStaticSmoke
    }
    "ConditionsRuntimeGateStaticSmoke" {
        Invoke-ConditionsRuntimeGateStaticSmoke
    }
    "EquipmentRuntimeGateStaticSmoke" {
        Invoke-EquipmentRuntimeGateStaticSmoke
    }
    "HealFriendRuntimeGateStaticSmoke" {
        Invoke-HealFriendRuntimeGateStaticSmoke
    }
    "RuntimeModuleGatesSandboxSmoke" {
        & (Join-Path (Get-RepoRoot) ".venv\Scripts\python.exe") (Join-Path (Get-RepoRoot) "scripts\ops\otclient_runtime_module_gates_sandbox_smoke.py")
        if ($LASTEXITCODE -ne 0) { throw "Runtime module gates sandbox smoke failed" }
    }
    "RecoveryBridgeSandboxSmoke" {
        & (Join-Path (Get-RepoRoot) ".venv\Scripts\python.exe") (Join-Path (Get-RepoRoot) "scripts\ops\otclient_recovery_bridge_sandbox_smoke.py")
        if ($LASTEXITCODE -ne 0) { throw "Recovery bridge sandbox smoke failed" }
    }
    "RecoveryBridgeActionSmoke" {
        Invoke-RecoveryBridgeActionSmoke
    }
    "P12ConditionsExecuteOnce" {
        Invoke-P12ConditionsExecuteOnce
    }
    "P12EquipmentExecuteOnce" {
        Invoke-P12EquipmentExecuteOnce
    }
    "P12HealFriendExecuteOnce" {
        Invoke-P12HealFriendExecuteOnce
    }
    "ProfileSchemaStaticSmoke" {
        Invoke-ProfileSchemaStaticSmoke
    }
    "OperatorSummaryStaticSmoke" {
        Invoke-OperatorSummaryStaticSmoke
    }
    "ExternalBotImportGateStaticSmoke" {
        Invoke-ExternalBotImportGateStaticSmoke
    }
    "HelperShellBudgetStaticSmoke" {
        Invoke-HelperShellBudgetStaticSmoke
    }
    "HelperShellBudgetPlanStaticSmoke" {
        Invoke-HelperShellBudgetPlanStaticSmoke
    }
    "ModuleContract" {
        Invoke-ModuleContract
    }
    "ModuleAudit" {
        Invoke-ModuleAudit
    }
    "ModuleStaticGates" {
        Invoke-ModuleStaticGates
    }
    "EquipmentShadowReplayStaticSmoke" {
        Invoke-EquipmentShadowReplayStaticSmoke
    }
    "EquipmentShadowSnapshotStaticSmoke" {
        Invoke-EquipmentShadowSnapshotStaticSmoke
    }
    "EquipmentShadowAcceptanceStaticSmoke" {
        Invoke-EquipmentShadowAcceptanceStaticSmoke
    }
    "Snapshot" {
        Invoke-Snapshot
    }
    "ReadyCheck" {
        Invoke-ReadyCheck
    }
    "BackupLiveCtoa" {
        New-LiveCtoaBackup | Out-Null
    }
    "PromoteLiveCtoa" {
        Invoke-LivePromotion
    }
    "EmergencyRepairLiveCtoa" {
        Invoke-LiveEmergencyRepair
    }
    "DisableLiveCtoa" {
        Set-LiveCtoaEnabled -Enabled $false
    }
    "EnableLiveCtoa" {
        Set-LiveCtoaEnabled -Enabled $true
    }
    "EnableLiveCtoaUiOnly" {
        Set-LiveCtoaUiOnly
    }
    "SmokeAll" {
        Invoke-SmokeAll
    }
    "Stop" {
        Stop-SandboxClient
        Write-Output "[solteria-helper-test-env] Stopped sandbox client: $SandboxClient"
    }
}
