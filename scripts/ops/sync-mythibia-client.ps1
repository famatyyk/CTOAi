param(
    [string]$VpsHost = '46.225.110.52',
    [string]$VpsUser = 'root',
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\ctoa_vps_ed25519",
    [string]$RemoteDir = '/opt/ctoa/generated/mythibia_online',
    [string]$ClientAiDir = "$env:APPDATA\Mythibia\MythibiaV2\user_dir\ai_generated",
    [switch]$UnsafeRuntimeBootstrap
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$localTemplateDir = Join-Path $repoRoot 'scripts\lua'
$clientRoot = Split-Path -Parent (Split-Path -Parent $ClientAiDir)
$trainerConfigPath = Join-Path $clientRoot 'settings\profile_1\trainer.json'
$opsLogPath = Join-Path $clientRoot 'ctoa_local.log'
$runtimeProbeName = 'ctoa_runtime_probe.lua'
$autoloadFileName = 'ctoa_mythibia_autoload.lua'
$runtimeAutoloadDirs = @(
    (Join-Path $clientRoot 'user_dir'),
    $ClientAiDir,
    (Join-Path $clientRoot 'user_dir\scripts'),
    (Join-Path $clientRoot 'user_dir\trainer')
)
$runtimeMirrorDirs = @(
    (Join-Path $clientRoot 'user_dir'),
    (Join-Path $clientRoot 'user_dir\scripts'),
    (Join-Path $clientRoot 'user_dir\trainer')
)
$expectedScripts = @(
    'alarmy.lua',
    'anti_stuck.lua',
    'area_spell_ctrl.lua',
    'auto_heal.lua',
    'auto_reconnect.lua',
    'auto_resupply.lua',
    'bank_automation.lua',
    'break_scheduler.lua',
    'cavebot_pathing.lua',
    'combo_spells.lua',
    'ctoa_hotkey_status.lua',
    'ctoa_path_probe.lua',
    'depot_manager.lua',
    'exp_tracker.lua',
    'flee_logic.lua',
    'gold_tracker.lua',
    'healer_profiles.lua',
    'human_delay.lua',
    'hunt_orchestrator.lua',
    'login_randomizer.lua',
    'module_reporter.lua',
    'proximity_watch.lua',
    'emergency_heal.lua',
    'status_beacon.lua',
    'rune_maker.lua',
    'session_log.lua',
    'target_selector.lua'
)

$criticalScripts = @(
    'module_reporter.lua',
    'ctoa_hotkey_status.lua',
    'ctoa_path_probe.lua'
)

function Write-OpsLogLine {
    param([string]$Message)

    $line = '{0} [CTOA-OPS] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $opsLogPath -Value $line -Encoding UTF8
}

function Ensure-CriticalScripts {
    param(
        [string]$TargetDir,
        [string]$TemplateDir,
        [string[]]$CriticalFiles
    )

    $updated = @()
    $skipped = @()

    foreach ($name in $CriticalFiles) {
        $templatePath = Join-Path $TemplateDir $name
        if (-not (Test-Path $templatePath)) {
            $skipped += $name
            continue
        }

        $targetPath = Join-Path $TargetDir $name
        Copy-Item -Path $templatePath -Destination $targetPath -Force
        $updated += $name
    }

    return [ordered]@{
        updated = $updated
        skipped = $skipped
    }
}

function Ensure-TrainerEnabled {
    param([string]$TrainerPath)

    if (-not (Test-Path $TrainerPath)) {
        $dir = Split-Path -Parent $TrainerPath
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }

        $obj = [ordered]@{
            enabled = $true
            checkDummy = $false
            checkIdle = $true
            checkFood = $false
            checkMT = $false
            checkRM = $false
            spellMT = 'utana vid'
            spellRM = 'adura vita'
            manaMT = 46
            manaRM = 80
        }

        $obj | ConvertTo-Json -Depth 5 | Set-Content -Path $TrainerPath -Encoding UTF8
        return 'created_enabled_true'
    }

    $raw = Get-Content -Path $TrainerPath -Raw
    try {
        $obj = $raw | ConvertFrom-Json
        $wasEnabled = $false
        if ($null -ne $obj.PSObject.Properties['enabled']) {
            $wasEnabled = [bool]$obj.enabled
        }

        if (-not $wasEnabled) {
            $obj | Add-Member -NotePropertyName enabled -NotePropertyValue $true -Force
            $obj | ConvertTo-Json -Depth 6 | Set-Content -Path $TrainerPath -Encoding UTF8
            return 'patched_enabled_true'
        }

        return 'already_enabled_true'
    }
    catch {
        $patched = $raw -replace '"enabled"\s*:\s*false', '"enabled": true'
        if ($patched -ne $raw) {
            Set-Content -Path $TrainerPath -Value $patched -Encoding UTF8
            return 'patched_regex_enabled_true'
        }

        throw "Unable to enforce trainer enabled=true for $TrainerPath"
    }
}

function Write-Utf8NoBomFile {
    param(
        [string]$Path,
        [string]$Content
    )

    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Get-RuntimeProbeContent {
    return @"
-- ctoa_runtime_probe.lua  [CTOA Diagnostic]
-- Safe probe: writes runtime markers without touching UI APIs.

local function append(path, line)
    local f = io.open(path, "a")
    if not f then return false end
    f:write(line .. "\n")
    f:close()
    return true
end

local function logRuntime(msg)
    local line = os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-RUNTIME] " .. msg
    append("ctoa_local.log", line)
    append("user_dir/ctoa_local.log", line)
    append("ctoa_probe.log", line)
    append("user_dir/ctoa_probe.log", line)
end

logRuntime("runtime probe loaded")

if register and type(register) == "function" then
    local lastTick = 0
    local function onThink()
        local now = os.time()
        if (now - lastTick) < 10 then return end
        lastTick = now
        logRuntime("runtime probe tick")
    end

    pcall(function()
        register("onThink", onThink)
    end)
end
"@
}

function Get-RuntimeAutoloadContent {
    param([string[]]$ScriptNames)

    $quoted = $ScriptNames | ForEach-Object { "    '$_'" }
    $namesBlock = ($quoted -join ",`n")

    return @"
-- ctoa_mythibia_autoload.lua  [CTOA Diagnostic]
-- Attempts to load CTOA runtime scripts from user_dir/ai_generated.

local scripts = {
$namesBlock
}

local function append(path, line)
    local f = io.open(path, "a")
    if not f then return end
    f:write(line .. "\n")
    f:close()
end

local function log(msg)
    local line = os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-LOAD] " .. msg
    append("ctoa_local.log", line)
    append("user_dir/ctoa_local.log", line)
end

for _, name in ipairs(scripts) do
    local candidates = {
        "user_dir/ai_generated/" .. name,
        "ai_generated/" .. name,
        "user_dir/scripts/" .. name,
        "user_dir/trainer/" .. name,
        "user_dir/" .. name,
        name
    }

    local loaded = false
    local lastErr = nil

    for _, path in ipairs(candidates) do
        local ok, err = pcall(function()
            dofile(path)
        end)

        if ok then
            log("loaded " .. path)
            loaded = true
            break
        else
            lastErr = err
        end
    end

    if not loaded then
        log("failed " .. name .. " err=" .. tostring(lastErr))
    end
end
"@
}

function Ensure-RuntimeAutoloadDiagnostics {
    param(
        [string]$ClientRoot,
        [string[]]$TargetDirs,
        [string]$AutoloadName,
        [string]$ProbeName,
        [string[]]$ScriptNames
    )

    $deployed = @()
    $errors = @()

    $autoloadContent = Get-RuntimeAutoloadContent -ScriptNames $ScriptNames
    $probeContent = Get-RuntimeProbeContent
    $reportPath = Join-Path $ClientRoot 'runtime_loader_diagnosis.txt'

    foreach ($dir in $TargetDirs) {
        try {
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }

            $autoloadPath = Join-Path $dir $AutoloadName
            $probePath = Join-Path $dir $ProbeName

            Write-Utf8NoBomFile -Path $autoloadPath -Content $autoloadContent
            Write-Utf8NoBomFile -Path $probePath -Content $probeContent

            $deployed += $autoloadPath
            $deployed += $probePath
        }
        catch {
            $errors += ("{0} :: {1}" -f $dir, $_.Exception.Message)
        }
    }

    $report = New-Object System.Collections.Generic.List[string]
    $report.Add('Runtime Loader Diagnosis')
    $report.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $report.Add('ClientRoot: ' + $ClientRoot)
    $report.Add('AutoloadName: ' + $AutoloadName)
    $report.Add('ProbeName: ' + $ProbeName)
    $report.Add('TargetDirCount: ' + $TargetDirs.Count)
    $report.Add('DeployedFileCount: ' + $deployed.Count)
    $report.Add('')
    $report.Add('=== Target Dirs ===')
    $TargetDirs | ForEach-Object { $report.Add($_) }
    $report.Add('')
    $report.Add('=== Deployed Files ===')
    if ($deployed.Count -eq 0) { $report.Add('(none)') } else { $deployed | ForEach-Object { $report.Add($_) } }
    $report.Add('')
    $report.Add('=== Script Names ===')
    $ScriptNames | ForEach-Object { $report.Add($_) }
    $report.Add('')
    $report.Add('=== Errors ===')
    if ($errors.Count -eq 0) { $report.Add('(none)') } else { $errors | ForEach-Object { $report.Add($_) } }

    [System.IO.File]::WriteAllLines($reportPath, $report)

    return [ordered]@{
        reportPath = $reportPath
        deployedCount = $deployed.Count
        errorCount = $errors.Count
    }
}

function Ensure-RuntimeScriptMirrors {
    param(
        [string]$SourceDir,
        [string[]]$TargetDirs,
        [string[]]$ScriptNames,
        [string]$ClientRoot
    )

    $copied = @()
    $missing = @()
    $errors = @()

    foreach ($name in $ScriptNames) {
        $sourcePath = Join-Path $SourceDir $name
        if (-not (Test-Path $sourcePath)) {
            $missing += $name
            continue
        }

        foreach ($dir in $TargetDirs) {
            try {
                if (-not (Test-Path $dir)) {
                    New-Item -ItemType Directory -Path $dir -Force | Out-Null
                }

                $targetPath = Join-Path $dir $name
                Copy-Item -Path $sourcePath -Destination $targetPath -Force
                $copied += $targetPath
            }
            catch {
                $errors += ("{0} :: {1}" -f (Join-Path $dir $name), $_.Exception.Message)
            }
        }
    }

    $reportPath = Join-Path $ClientRoot 'runtime_script_mirror_report.txt'
    $report = New-Object System.Collections.Generic.List[string]
    $report.Add('Runtime Script Mirror Report')
    $report.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $report.Add('SourceDir: ' + $SourceDir)
    $report.Add('TargetDirCount: ' + $TargetDirs.Count)
    $report.Add('ScriptCount: ' + $ScriptNames.Count)
    $report.Add('CopiedCount: ' + $copied.Count)
    $report.Add('MissingCount: ' + $missing.Count)
    $report.Add('ErrorCount: ' + $errors.Count)
    $report.Add('')
    $report.Add('=== Scripts ===')
    $ScriptNames | ForEach-Object { $report.Add($_) }
    $report.Add('')
    $report.Add('=== Copied Paths ===')
    if ($copied.Count -eq 0) { $report.Add('(none)') } else { $copied | ForEach-Object { $report.Add($_) } }
    $report.Add('')
    $report.Add('=== Missing Sources ===')
    if ($missing.Count -eq 0) { $report.Add('(none)') } else { $missing | ForEach-Object { $report.Add($_) } }
    $report.Add('')
    $report.Add('=== Errors ===')
    if ($errors.Count -eq 0) { $report.Add('(none)') } else { $errors | ForEach-Object { $report.Add($_) } }

    [System.IO.File]::WriteAllLines($reportPath, $report)

    return [ordered]@{
        copiedCount = $copied.Count
        missingCount = $missing.Count
        errorCount = $errors.Count
        reportPath = $reportPath
    }
}

function Ensure-UnsafeRuntimeBootstrap {
    param(
        [string]$ClientRoot,
        [string]$AutoloadName,
        [string]$ProbeName
    )

    $targets = @(
        (Join-Path $ClientRoot 'modules\ctoa_bootstrap'),
        (Join-Path $ClientRoot '_tmp_unpack\modules\ctoa_bootstrap')
    )

    $otmodContent = @"
Module
  name: ctoa_bootstrap
  description: CTOA unsafe runtime bootstrap
  author: CTOA
  website: ctoa.local
  sandboxed: true
  scripts: [ ctoa_bootstrap ]
  @onLoad: init()
"@

    $luaContent = @"
-- ctoa_bootstrap.lua  [CTOA Unsafe]
-- WARNING: experimental plaintext module for ENC3 clients.

local function append(path, line)
    local f = io.open(path, "a")
    if not f then return end
    f:write(line .. "\n")
    f:close()
end

local function log(msg)
    local line = os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-UNSAFE] " .. msg
    append("ctoa_local.log", line)
    append("user_dir/ctoa_local.log", line)
end

function init()
    log("unsafe bootstrap init")
    pcall(function() dofile("user_dir/" .. "$AutoloadName") end)
    pcall(function() dofile("user_dir/ai_generated/" .. "$AutoloadName") end)
    pcall(function() dofile("user_dir/" .. "$ProbeName") end)
    pcall(function() dofile("user_dir/ai_generated/" .. "$ProbeName") end)
end
"@

    $written = @()
    $errors = @()

    foreach ($dir in $targets) {
        try {
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }

            $otmodPath = Join-Path $dir 'ctoa_bootstrap.otmod'
            $luaPath = Join-Path $dir 'ctoa_bootstrap.lua'

            Write-Utf8NoBomFile -Path $otmodPath -Content $otmodContent
            Write-Utf8NoBomFile -Path $luaPath -Content $luaContent

            $written += $otmodPath
            $written += $luaPath
        }
        catch {
            $errors += ("{0} :: {1}" -f $dir, $_.Exception.Message)
        }
    }

    $reportPath = Join-Path $ClientRoot 'unsafe_runtime_bootstrap_report.txt'
    $report = New-Object System.Collections.Generic.List[string]
    $report.Add('Unsafe Runtime Bootstrap Report')
    $report.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $report.Add('ClientRoot: ' + $ClientRoot)
    $report.Add('UnsafeRuntimeBootstrap: true')
    $report.Add('')
    $report.Add('=== Written Files ===')
    if ($written.Count -eq 0) { $report.Add('(none)') } else { $written | ForEach-Object { $report.Add($_) } }
    $report.Add('')
    $report.Add('=== Errors ===')
    if ($errors.Count -eq 0) { $report.Add('(none)') } else { $errors | ForEach-Object { $report.Add($_) } }

    [System.IO.File]::WriteAllLines($reportPath, $report)

    return [ordered]@{
        enabled = $true
        reportPath = $reportPath
        writtenCount = $written.Count
        errorCount = $errors.Count
    }
}

function Remove-UnsafeRuntimeBootstrapArtifacts {
    param([string]$ClientRoot)

    $targets = @(
        (Join-Path $ClientRoot 'modules\ctoa_bootstrap'),
        (Join-Path $ClientRoot '_tmp_unpack\modules\ctoa_bootstrap')
    )

    $removed = @()
    foreach ($target in $targets) {
        if (Test-Path $target) {
            try {
                Remove-Item -Path $target -Recurse -Force
                $removed += $target
            }
            catch {
                Write-Warning "failed to remove unsafe bootstrap path: $target ; $($_.Exception.Message)"
            }
        }
    }

    return $removed
}


function New-LuaStubContent {
    param([string]$FileName)

    return @"
-- $FileName  [CTOA Local Fallback]
-- Auto-generated stub to keep local runtime consistent when VPS sync is incomplete.

local function onThink()
    -- Intentionally left as a no-op fallback.
end

register("onThink", onThink)
"@
}

function Ensure-LocalLuaFiles {
    param(
        [string]$TargetDir,
        [string]$TemplateDir,
        [string[]]$ExpectedFiles
    )

    $created = @()
    $copied = @()
    $missing = @()

    foreach ($name in $ExpectedFiles) {
        $targetPath = Join-Path $TargetDir $name
        if (Test-Path $targetPath) {
            continue
        }

        $templatePath = Join-Path $TemplateDir $name
        if (Test-Path $templatePath) {
            Copy-Item -Path $templatePath -Destination $targetPath -Force
            $copied += $name
            continue
        }

        New-LuaStubContent -FileName $name | Set-Content -Path $targetPath -Encoding UTF8
        $created += $name
        $missing += $name
    }

    return [ordered]@{
        copied = $copied
        created = $created
        missingTemplates = $missing
    }
}

function Write-ManifestVsDiskReports {
    param(
        [string]$ClientAiDir,
        [string]$ManifestPath,
        [string]$SourceLabel,
        [string[]]$RemoteFiles = @()
    )

    $clientRoot = Split-Path -Parent (Split-Path -Parent $ClientAiDir)
    $reportPath = Join-Path $clientRoot 'manifest_vs_disk_report.txt'
    $missingForVpsPath = Join-Path $clientRoot 'missing_for_vps.txt'

    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $manifestFiles = @($manifest.files | ForEach-Object { [string]$_ })
    $sourceFiles = if ($RemoteFiles.Count -gt 0) {
        @($RemoteFiles | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    } else {
        @($manifestFiles | Sort-Object -Unique)
    }
    $diskFiles = @(Get-ChildItem -Path $ClientAiDir -Filter '*.lua' -File | Select-Object -ExpandProperty Name)

    $missing = @($sourceFiles | Where-Object { $_ -notin $diskFiles } | Sort-Object)
    $extra = @($diskFiles | Where-Object { $_ -notin $sourceFiles } | Sort-Object)
    $common = @($sourceFiles | Where-Object { $_ -in $diskFiles } | Sort-Object)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('Manifest vs Disk Report')
    $lines.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $lines.Add('ClientRoot: ' + $clientRoot)
    $lines.Add('ManifestPath: ' + $ManifestPath)
    $lines.Add('Source: ' + $SourceLabel)
    $lines.Add('ManifestCount: ' + $manifestFiles.Count)
    $lines.Add('SourceFilesCount: ' + $sourceFiles.Count)
    $lines.Add('DiskLuaCount: ' + $diskFiles.Count)
    $lines.Add('CommonCount: ' + $common.Count)
    $lines.Add('MissingOnDiskCount: ' + $missing.Count)
    $lines.Add('ExtraOnDiskCount: ' + $extra.Count)
    $lines.Add('')
    $lines.Add('=== Missing On Disk ===')
    if ($missing.Count -eq 0) { $lines.Add('(none)') } else { $missing | ForEach-Object { $lines.Add($_) } }
    $lines.Add('')
    $lines.Add('=== Extra On Disk ===')
    if ($extra.Count -eq 0) { $lines.Add('(none)') } else { $extra | ForEach-Object { $lines.Add($_) } }
    $lines.Add('')
    $lines.Add('=== Common ===')
    if ($common.Count -eq 0) { $lines.Add('(none)') } else { $common | ForEach-Object { $lines.Add($_) } }

    [IO.File]::WriteAllLines($reportPath, $lines)

    $missingVpsLines = New-Object System.Collections.Generic.List[string]
    $missingVpsLines.Add('Missing scripts for VPS sync')
    $missingVpsLines.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $missingVpsLines.Add('Source: ' + $SourceLabel)
    $missingVpsLines.Add('Count: ' + $missing.Count)
    $missingVpsLines.Add('')
    if ($missing.Count -eq 0) {
        $missingVpsLines.Add('(none)')
    } else {
        $missing | ForEach-Object { $missingVpsLines.Add($_) }
    }
    [IO.File]::WriteAllLines($missingForVpsPath, $missingVpsLines)

    return [ordered]@{
        reportPath = $reportPath
        missingForVpsPath = $missingForVpsPath
        missingCount = $missing.Count
    }
}

if (-not (Test-Path $SshKeyPath)) {
    throw "SSH key not found: $SshKeyPath"
}

if (-not (Test-Path $ClientAiDir)) {
    New-Item -ItemType Directory -Path $ClientAiDir -Force | Out-Null
}

if (-not (Test-Path $opsLogPath)) {
    New-Item -ItemType File -Path $opsLogPath -Force | Out-Null
}

# Pull latest Lua files from VPS in a robust way (no remote wildcard tar expansion)
$escapedRemoteDir = $RemoteDir.Replace("'", "'\''")
$listCmd = "find '$escapedRemoteDir' -maxdepth 1 -type f -name '*.lua' -exec basename {} \;"
$remoteFiles = & ssh -i $SshKeyPath "$VpsUser@$VpsHost" $listCmd
if ($LASTEXITCODE -ne 0) {
    Write-Warning "ssh list failed with exit code $LASTEXITCODE - keeping local scripts and using local repair only"
    $remoteFiles = @()
}

$remoteFiles = @($remoteFiles | Where-Object { $_ -and $_.Trim().Length -gt 0 } | ForEach-Object { $_.Trim() })
if ($remoteFiles.Count -eq 0) {
    Write-Warning "No remote .lua files resolved from $RemoteDir - skipping remote overwrite"
}

foreach ($fileName in $remoteFiles) {
    $remotePath = "$VpsUser@$VpsHost`:$RemoteDir/$fileName"
    & scp -i $SshKeyPath $remotePath $ClientAiDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "scp failed for $fileName (exit $LASTEXITCODE) - keeping existing local file state"
    }
}

$repair = Ensure-LocalLuaFiles -TargetDir $ClientAiDir -TemplateDir $localTemplateDir -ExpectedFiles $expectedScripts
$critical = Ensure-CriticalScripts -TargetDir $ClientAiDir -TemplateDir $localTemplateDir -CriticalFiles $criticalScripts
$runtimeDiag = Ensure-RuntimeAutoloadDiagnostics -ClientRoot $clientRoot -TargetDirs $runtimeAutoloadDirs -AutoloadName $autoloadFileName -ProbeName $runtimeProbeName -ScriptNames @($criticalScripts + $runtimeProbeName)
$mirrorResult = Ensure-RuntimeScriptMirrors -SourceDir $ClientAiDir -TargetDirs $runtimeMirrorDirs -ScriptNames @($criticalScripts + $runtimeProbeName + $autoloadFileName) -ClientRoot $clientRoot
$unsafeResult = $null
 $unsafeRemoved = @()
if ($UnsafeRuntimeBootstrap.IsPresent) {
    $unsafeResult = Ensure-UnsafeRuntimeBootstrap -ClientRoot $clientRoot -AutoloadName $autoloadFileName -ProbeName $runtimeProbeName
}
else {
    $unsafeRemoved = Remove-UnsafeRuntimeBootstrapArtifacts -ClientRoot $clientRoot
}
$trainerState = Ensure-TrainerEnabled -TrainerPath $trainerConfigPath
Write-OpsLogLine -Message ("sync cycle complete; trainer={0}; critical_updated={1}; remote_files={2}" -f $trainerState, $critical.updated.Count, $remoteFiles.Count)

# Build manifest for local visibility/debug
$luaFiles = Get-ChildItem -Path $ClientAiDir -Filter '*.lua' -File | Sort-Object Name
$manifest = [ordered]@{
    syncedAt = (Get-Date).ToUniversalTime().ToString('o')
    source = "${VpsUser}@${VpsHost}:${RemoteDir}"
    count = $luaFiles.Count
    files = @($luaFiles.Name)
}
$manifestPath = Join-Path $ClientAiDir 'manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8

$reports = Write-ManifestVsDiskReports -ClientAiDir $ClientAiDir -ManifestPath $manifestPath -SourceLabel "${VpsUser}@${VpsHost}:${RemoteDir}" -RemoteFiles $remoteFiles

Write-Output "[sync] done"
Write-Output "[sync] target=$ClientAiDir"
Write-Output "[sync] files=$($luaFiles.Count)"
Write-Output "[sync] copied_from_templates=$($repair.copied.Count)"
Write-Output "[sync] created_fallback_stubs=$($repair.created.Count)"
Write-Output "[sync] critical_updated=$($critical.updated.Count)"
Write-Output "[sync] runtime_diag_deployed=$($runtimeDiag.deployedCount)"
Write-Output "[sync] runtime_diag_errors=$($runtimeDiag.errorCount)"
Write-Output "[sync] runtime_mirror_copied=$($mirrorResult.copiedCount)"
Write-Output "[sync] runtime_mirror_missing=$($mirrorResult.missingCount)"
Write-Output "[sync] runtime_mirror_errors=$($mirrorResult.errorCount)"
Write-Output "[sync] runtime_mirror_report=$($mirrorResult.reportPath)"
if ($unsafeResult) {
    Write-Output "[sync] unsafe_runtime_bootstrap=true"
    Write-Output "[sync] unsafe_runtime_written=$($unsafeResult.writtenCount)"
    Write-Output "[sync] unsafe_runtime_errors=$($unsafeResult.errorCount)"
    Write-Output "[sync] unsafe_runtime_report=$($unsafeResult.reportPath)"
}
if ($unsafeRemoved.Count -gt 0) {
    Write-Output "[sync] unsafe_runtime_removed=$($unsafeRemoved.Count)"
}
Write-Output "[sync] trainer_state=$trainerState"
Write-Output "[sync] report=$($reports.reportPath)"
Write-Output "[sync] missing_for_vps=$($reports.missingForVpsPath)"
Write-Output "[sync] runtime_loader_diag=$($runtimeDiag.reportPath)"
if ($reports.missingCount -gt 0) {
    Write-Output "[alert] missing_on_disk=$($reports.missingCount)"
}
