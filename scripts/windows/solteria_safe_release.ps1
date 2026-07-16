param(
    [ValidateSet("Validate", "Package", "Status", "Promote")]
    [string]$Action = "Status",
    [string]$SourceClient = "$env:LOCALAPPDATA\Solteria\client",
    [string]$OutDir = "runtime\solteria_safe_release",
    [switch]$ApproveLiveDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-OutRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    if ([System.IO.Path]::IsPathRooted($OutDir)) {
        return [System.IO.Path]::GetFullPath($OutDir)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $OutDir))
}

function Write-JsonAtomic {
    param([Parameter(Mandatory = $true)]$Value, [Parameter(Mandatory = $true)][string]$Path)
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = "$Path.tmp"
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $temporary -Encoding utf8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    $stream = [System.IO.File]::OpenRead([System.IO.Path]::GetFullPath($Path))
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
        } finally {
            $sha.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Get-SafeFiles {
    return @(
        "mods/ctoa_safe/ctoa_safe.otmod",
        "mods/ctoa_safe/ctoa_safe_loader.lua",
        "mods/ctoa_safe/ctoa_safe_helper.lua",
        "mods/ctoa_safe/styles/helper.otui",
        "mods/ctoa_safe/styles/spell.otui",
        "mods/ctoa_safe/styles/siolist.otui",
        "mods/ctoa_safe/styles/shooterPreset.otui"
    )
}

function Get-SafeVersion {
    param([Parameter(Mandatory = $true)][string]$Root)
    $metadata = Get-Content -LiteralPath (Join-Path $Root "mods\ctoa_safe\ctoa_safe.otmod") -Raw
    $match = [regex]::Match($metadata, '(?m)^\s*version:\s*([^\s]+)\s*$')
    if (-not $match.Success) { throw "Safe version is missing from ctoa_safe.otmod." }
    return $match.Groups[1].Value
}

function Get-FileEntries {
    param([Parameter(Mandatory = $true)][string]$Root)
    $entries = @()
    foreach ($relative in Get-SafeFiles) {
        $path = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Missing Safe release file: $path"
        }
        $item = Get-Item -LiteralPath $path -Force
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Safe release rejects reparse files: $path"
        }
        if ([long]$item.Length -gt 2MB) { throw "Safe release file exceeds 2 MiB: $path" }
        $entries += [ordered]@{
            path = $relative
            bytes = [long]$item.Length
            sha256 = Get-Sha256 -Path $path
        }
    }
    return @($entries)
}

function Get-LiveProcessIds {
    param([Parameter(Mandatory = $true)][string]$ClientRoot)
    $exe = [System.IO.Path]::GetFullPath((Join-Path $ClientRoot "solteria-client.exe"))
    $ids = @(Get-CimInstance Win32_Process -Filter "Name = 'solteria-client.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and [System.IO.Path]::GetFullPath($_.ExecutablePath) -eq $exe } |
        ForEach-Object { [int]$_.ProcessId })
    return @($ids | Sort-Object)
}

function Assert-LiveRoot {
    param([Parameter(Mandatory = $true)][string]$Candidate)
    $full = [System.IO.Path]::GetFullPath($Candidate)
    $allowed = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\') + '\'
    if (-not $full.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Live Safe target must stay under LOCALAPPDATA: $full"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $full "solteria-client.exe") -PathType Leaf)) {
        throw "Solteria executable is missing from live target: $full"
    }
    return $full
}

function Invoke-ValidateSafe {
    $repo = Get-RepoRoot
    $outRoot = Get-OutRoot -RepoRoot $repo
    $stage = Join-Path $outRoot "latest"
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
    foreach ($relative in Get-SafeFiles) {
        $source = Join-Path $repo $relative
        $destination = Join-Path $stage $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    $sourceText = Get-Content -LiteralPath (Join-Path $repo "mods\ctoa_safe\ctoa_safe_helper.lua") -Raw
    $loaderText = Get-Content -LiteralPath (Join-Path $repo "mods\ctoa_safe\ctoa_safe_loader.lua") -Raw
    $metadata = Get-Content -LiteralPath (Join-Path $repo "mods\ctoa_safe\ctoa_safe.otmod") -Raw
    $safeVersion = Get-SafeVersion -Root $repo
    $checks = @(
        [ordered]@{ name = "seven_file_runtime_scope"; passed = (@(Get-SafeFiles).Count -eq 7) },
        [ordered]@{ name = "safe_autoload_disabled"; passed = ($metadata -match '(?m)^\s*autoload:\s*false\s*$') },
        [ordered]@{ name = "safe_boot_default_off"; passed = ($sourceText.Contains('safe_boot_runtime_disabled = true') -and $sourceText.Contains('if not CFG.enabled or not RT.armed then return end')) },
        [ordered]@{ name = "runtime_version_parity"; passed = ($sourceText.Contains('"v' + $safeVersion + '"') -and $loaderText.Contains('"' + $safeVersion + '"')) },
        [ordered]@{ name = "npc_target_guard"; passed = ($sourceText.Contains('isNpcCreature(creature)') -and $sourceText.Contains('CreatureTypeNpc') -and $sourceText.Contains('0x80000000') -and $sourceText.Contains('icon>0') -and $sourceText.Contains('g_game.cancelAttack()')) },
        [ordered]@{ name = "central_pz_spell_guard"; passed = ($sourceText.Contains('options.spell == true') -and $sourceText.Contains('protectionZoneEvidence()') -and $sourceText.Contains('numericCall(tile,"getFlags")') -and $sourceText.Contains('numericCall(player,"getStates")')) },
        [ordered]@{ name = "npc_dialogue_guard"; passed = $sourceText.Contains('BLOCKED_NPC_DIALOGUE') },
        [ordered]@{ name = "exercise_dummy_targeting"; passed = ($sourceText.Contains('findExerciseDummy()') -and $sourceText.Contains('EXERCISE_DUMMY_IDS') -and $sourceText.Contains('[28558]=true') -and $sourceText.Contains('g_map.getTiles(position.z)') -and $sourceText.Contains('tile:getItems()') -and $sourceText.Contains('useInventoryItemOn(itemId, target)')) },
        [ordered]@{ name = "environment_family_snapshot"; passed = ($sourceText.Contains('environmentFamilySnapshot(radius)') -and $sourceText.Contains('protection_zone_evidence') -and $sourceText.Contains('EXERCISE_WEAPON_FAMILIES')) },
        [ordered]@{ name = "exercise_weapon_family_autodetect"; passed = ($sourceText.Contains('findExerciseWeaponIdForVocation') -and $sourceText.Contains('EXERCISE_VOCATION_FAMILIES') -and $sourceText.Contains('exercise weapon auto-detected')) },
        [ordered]@{ name = "kingsvale_page_parity"; passed = ($sourceText.Contains('label="Healing"') -and $sourceText.Contains('label="Tools"') -and $sourceText.Contains('label="KVShooter"')) },
        [ordered]@{ name = "kingsvale_json_adapter"; passed = ($sourceText.Contains('kingsvale-helper-json-v1') -and $sourceText.Contains('importKingsValeSettings')) },
        [ordered]@{ name = "vocation_ui_contract"; passed = ($sourceText.Contains('VOCATION_UI_CONTRACT') -and $sourceText.Contains('monk = {label="Monk"') -and $sourceText.Contains('spell_slots=2, potion_slots=2') -and $sourceText.Contains('vocationUiContract(RT.vocation).auto_exeta')) },
        [ordered]@{ name = "reference_data_not_embedded"; passed = (-not $sourceText.Contains('KingsValeLauncher') -and -not $sourceText.Contains('characterdata\\gto_gto_gto_gto')) },
        [ordered]@{ name = "no_cavebot_or_settings"; passed = (-not $sourceText.Contains('id = "cavebot"') -and -not $sourceText.Contains('id = "settings"')) },
        [ordered]@{ name = "item_slots"; passed = $sourceText.Contains('mkWidget("UIItem"') },
        [ordered]@{ name = "actionbar_item_drop_contract"; passed = ($sourceText.Contains('currentDragThing') -and $sourceText.Contains('draggedWidget.cache.itemId') -and $sourceText.Contains('slot.selectable=true') -and $sourceText.Contains('slot.editable=true')) },
        [ordered]@{ name = "healing_checkbox_runtime_contract"; passed = ($sourceText.Contains('for _,slot in ipairs(H.spell_slots or {})') -and $sourceText.Contains('if slot.enabled and type(slot.words)=="string"')) },
        [ordered]@{ name = "rune_target_dispatch"; passed = $sourceText.Contains('useInventoryItemOn(action.item_id,target)') },
        [ordered]@{ name = "plain_equipment_dispatch"; passed = ($sourceText.Contains('useInventoryItemPlain(rule.id)') -and $sourceText.Contains('useInventoryItemPlain(ammo.id)')) },
        [ordered]@{ name = "native_solteria_skin"; passed = ($sourceText.Contains('mkWidget("CTOASafeWindow"') -and $sourceText.Contains('mkWidget("CTOASafeItem"') -and $sourceText.Contains('mkWidget("CTOASafeTab"')) },
        [ordered]@{ name = "mana_and_randomization"; passed = ($sourceText.Contains('"Mana potion %"') -and $sourceText.Contains('mana_randomization')) },
        [ordered]@{ name = "support_spell_item"; passed = ($sourceText.Contains('SUPPORT RULES: SPELL / ITEM') -and $sourceText.Contains('useInventoryItem(rule.item_id)')) },
        [ordered]@{ name = "visible_shooter_profile_only"; passed = ($sourceText.Contains('runSelectedShooterProfile(now)') -and -not $sourceText.Contains('local minNearby = spell.min_nearby')) },
        [ordered]@{ name = "hidden_compatibility_runtime_blocked"; passed = ($sourceText.Contains('RT.compatibility_runtime_disabled = true') -and $sourceText.Contains('if not RT.compatibility_runtime_disabled then')) },
        [ordered]@{ name = "editor_viewport_clamp"; passed = ($sourceText.Contains('root:getWidth()') -and $sourceText.Contains('panelW - 30')) }
    )
    $failed = @($checks | Where-Object { -not $_.passed })
    if ($failed.Count -gt 0) { throw "Safe static validation failed: $($failed.name -join ', ')" }

    $python = Join-Path $repo ".venv\Scripts\python.exe"
    & $python -m pytest (Join-Path $repo "tests\test_ctoa_exclusive_project_loader.py") -q
    if ($LASTEXITCODE -ne 0) { throw "Safe executable tests failed." }

    $entries = @(Get-FileEntries -Root $stage)
    $manifest = [ordered]@{
        schema_version = "ctoa.safe-release-manifest.v1"
        generated_at = (Get-Date).ToString("o")
        safe_version = Get-SafeVersion -Root $stage
        source = [System.IO.Path]::GetFullPath((Join-Path $repo "mods\ctoa_safe"))
        stage = [System.IO.Path]::GetFullPath($stage)
        files = $entries
    }
    $manifestPath = Join-Path $outRoot "manifest.json"
    Write-JsonAtomic -Value $manifest -Path $manifestPath
    $validation = [ordered]@{
        schema_version = "ctoa.safe-release-validation.v1"
        generated_at = (Get-Date).ToString("o")
        status = "passed"
        safe_version = $manifest.safe_version
        manifest_sha256 = Get-Sha256 -Path $manifestPath
        checks = $checks
        executable_tests = "pytest_passed"
        live_client_touched = $false
    }
    Write-JsonAtomic -Value $validation -Path (Join-Path $outRoot "validation.json")
    Write-Output "[solteria-safe-release] Validation passed for Safe $($manifest.safe_version): $manifestPath"
}

function Invoke-PackageSafe {
    Invoke-ValidateSafe
    $repo = Get-RepoRoot
    $outRoot = Get-OutRoot -RepoRoot $repo
    $stage = Join-Path $outRoot "latest"
    $version = Get-SafeVersion -Root $stage
    $zipPath = Join-Path $outRoot ("ctoa-safe-{0}-minimal.zip" -f $version)
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal
    $entries = @(Get-FileEntries -Root $stage)
    if ($entries.Count -ne 7) { throw "Minimal Safe package must contain exactly 7 runtime files." }
    $package = [ordered]@{
        schema_version = "ctoa.safe-friend-package.v1"
        generated_at = (Get-Date).ToString("o")
        safe_version = $version
        status = "passed"
        source_code_local_only = $true
        character_data_included = $false
        reference_module_included = $false
        runtime_file_count = $entries.Count
        archive = [System.IO.Path]::GetFullPath($zipPath)
        archive_sha256 = Get-Sha256 -Path $zipPath
        files = $entries
    }
    Write-JsonAtomic -Value $package -Path (Join-Path $outRoot "package.json")
    Write-Output "[solteria-safe-release] Minimal friend package ready: $zipPath"
}

function Invoke-SafeStatus {
    $repo = Get-RepoRoot
    $live = Assert-LiveRoot -Candidate $SourceClient
    $sourceEntries = @(Get-FileEntries -Root $repo)
    $liveEntries = @(Get-FileEntries -Root $live)
    $matching = @()
    foreach ($source in $sourceEntries) {
        $candidate = $liveEntries | Where-Object { $_.path -eq $source.path } | Select-Object -First 1
        $matching += [ordered]@{ path = $source.path; match = ($null -ne $candidate -and $candidate.sha256 -eq $source.sha256) }
    }
    $result = [ordered]@{
        schema_version = "ctoa.safe-release-status.v1"
        generated_at = (Get-Date).ToString("o")
        repo_version = Get-SafeVersion -Root $repo
        live_version = Get-SafeVersion -Root $live
        parity = (@($matching | Where-Object { -not $_.match }).Count -eq 0)
        files = $matching
        live_process_ids = @(Get-LiveProcessIds -ClientRoot $live)
    }
    $result | ConvertTo-Json -Depth 8
}

function Invoke-PromoteSafe {
    if (-not $ApproveLiveDeploy) { throw "Promote requires explicit -ApproveLiveDeploy." }
    $repo = Get-RepoRoot
    $live = Assert-LiveRoot -Candidate $SourceClient
    $outRoot = Get-OutRoot -RepoRoot $repo
    $manifestPath = Join-Path $outRoot "manifest.json"
    $validationPath = Join-Path $outRoot "validation.json"
    if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $validationPath)) {
        throw "Run -Action Validate before Safe promotion."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $validation = Get-Content -LiteralPath $validationPath -Raw | ConvertFrom-Json
    if ($validation.status -ne "passed") { throw "Safe validation is not passed." }
    $currentEntries = @(Get-FileEntries -Root $repo)
    foreach ($entry in $currentEntries) {
        $expected = $manifest.files | Where-Object { $_.path -eq $entry.path } | Select-Object -First 1
        if ($null -eq $expected -or $expected.sha256 -ne $entry.sha256) {
            throw "Safe source changed after validation: $($entry.path)"
        }
    }

    $before = @(Get-LiveProcessIds -ClientRoot $live)
    $backup = Join-Path $outRoot ("live_backup_{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    foreach ($entry in $currentEntries) {
        $livePath = Join-Path $live $entry.path
        if (Test-Path -LiteralPath $livePath) {
            $backupPath = Join-Path $backup $entry.path
            New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
            Copy-Item -LiteralPath $livePath -Destination $backupPath -Force
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $livePath) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $repo $entry.path) -Destination $livePath -Force
    }
    $verified = @(Get-FileEntries -Root $live)
    foreach ($entry in $currentEntries) {
        $actual = $verified | Where-Object { $_.path -eq $entry.path } | Select-Object -First 1
        if ($null -eq $actual -or $actual.sha256 -ne $entry.sha256) {
            throw "Safe live SHA256 verification failed: $($entry.path)"
        }
    }
    $after = @(Get-LiveProcessIds -ClientRoot $live)
    if (($before -join ',') -ne ($after -join ',')) {
        throw "Live process set changed during Safe promotion."
    }
    $report = [ordered]@{
        schema_version = "ctoa.safe-live-promotion.v1"
        generated_at = (Get-Date).ToString("o")
        status = "passed"
        safe_version = Get-SafeVersion -Root $live
        approval_switch = "ApproveLiveDeploy"
        backup = [System.IO.Path]::GetFullPath($backup)
        live_client = $live
        verified_file_count = $verified.Count
        verification = "source_live_sha256_match"
        process_ids_before = $before
        process_ids_after = $after
        client_stopped_or_restarted = $false
        activation_note = "The running Lua instance remains in memory; the promoted Safe version activates after a normal client/session reload."
        files = $verified
    }
    $reportPath = Join-Path $outRoot "live_promotion.json"
    Write-JsonAtomic -Value $report -Path $reportPath
    Write-Output "[solteria-safe-release] Safe $($report.safe_version) promoted with $($currentEntries.Count)/$($currentEntries.Count) SHA256 parity; client process unchanged."
    Write-Output "[solteria-safe-release] Report: $reportPath"
}

switch ($Action) {
    "Validate" { Invoke-ValidateSafe }
    "Package" { Invoke-PackageSafe }
    "Status" { Invoke-SafeStatus }
    "Promote" { Invoke-PromoteSafe }
}
