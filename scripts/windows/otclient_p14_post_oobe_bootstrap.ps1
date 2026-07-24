[CmdletBinding()]
param(
    [switch]$Install,

    [switch]$Run
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This answer-ISO-resident bootstrap deliberately runs Guest Additions only
# after OOBE has completed and the dedicated standard account has logged on.
# Both phases execute as LOCAL SYSTEM; no remote control channel, network, or
# staged P14 content is accepted or used here.
$P14BootstrapScript = 'C:\Windows\Setup\Scripts\ctoa_p14_post_oobe_bootstrap.ps1'
$P14BootstrapTaskName = 'CTOAi-P14-PostOOBE-GuestAdditions'
$P14GuestAdditionsScript = 'C:\Windows\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd'
$P14StageBootstrapScript = 'C:\Windows\Setup\Scripts\ctoa_p14_stage_bootstrap.ps1'
$P14PowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$P14Cmd = 'C:\Windows\System32\cmd.exe'
$P14ReceiptDirectory = 'C:\ProgramData\CTOAi\P14'
$P14ReceiptPath = 'C:\ProgramData\CTOAi\P14\guest-additions-post-oobe-receipt.json'
$P14LogPath = 'C:\ProgramData\CTOAi\P14\guest-additions-post-oobe.log'
$P14AllowedExitCodes = @(0, 3010, 1641)
$P14ReceiptSchema = 'ctoa.p14-post-oobe-guest-additions.v1'

function Stop-P14PostOobe([string]$Code) {
    throw "p14_post_oobe:$Code"
}

function Test-P14ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Assert-P14FixedFile([string]$Path) {
    if (
        -not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14PostOobe 'fixed_file_missing_or_reparse'
    }
}

function Assert-P14Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    if (
        -not (Test-Path -LiteralPath $Path -PathType Container) -or
        (Test-P14ReparsePoint $Path)
    ) {
        Stop-P14PostOobe 'receipt_directory_invalid'
    }
}

function Assert-P14SystemBootstrap {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if ($null -eq $identity.User -or $identity.User.Value -ne 'S-1-5-18') {
        Stop-P14PostOobe 'system_identity_required'
    }
}

function Assert-P14OfflineGuest {
    $activeAdapters = @(Get-NetAdapter -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' })
    if ($activeAdapters.Count -ne 0) {
        Stop-P14PostOobe 'network_adapter_not_isolated'
    }
}

function Initialize-P14ReceiptPaths {
    Assert-P14Directory 'C:\ProgramData\CTOAi'
    Assert-P14Directory $P14ReceiptDirectory
}

function Write-P14Log([string]$Message) {
    Initialize-P14ReceiptPaths
    "$(Get-Date -AsUTC -Format 'o') $Message" | Add-Content -LiteralPath $P14LogPath -Encoding UTF8
}

function Write-P14Receipt(
    [string]$Status,
    [int]$InstallerExitCode,
    [bool]$GuestAdditionsVerified,
    [bool]$StageBootstrapInstalled
) {
    Initialize-P14ReceiptPaths
    [ordered]@{
        schema_version = $P14ReceiptSchema
        status = $Status
        installer_exit_code = $InstallerExitCode
        guest_additions_verified = $GuestAdditionsVerified
        stage_bootstrap_installed = $StageBootstrapInstalled
        recorded_at = (Get-Date -AsUTC -Format 'o')
    } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $P14ReceiptPath -Encoding UTF8 -NoNewline
}

function Get-P14Receipt {
    if (-not (Test-Path -LiteralPath $P14ReceiptPath)) {
        return $null
    }
    if ((Test-P14ReparsePoint $P14ReceiptPath)) {
        Stop-P14PostOobe 'receipt_reparse_rejected'
    }
    try {
        $receipt = Get-Content -LiteralPath $P14ReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Stop-P14PostOobe 'receipt_invalid'
    }
    $expected = @(
        'schema_version', 'status', 'installer_exit_code',
        'guest_additions_verified', 'stage_bootstrap_installed', 'recorded_at'
    )
    $actual = @($receipt.PSObject.Properties.Name)
    if (
        $receipt.schema_version -ne $P14ReceiptSchema -or
        @(Compare-Object -ReferenceObject $expected -DifferenceObject $actual -CaseSensitive).Count -ne 0 -or
        $receipt.status -notin @('ga_installed_reboot_pending', 'ready_for_stage', 'blocked') -or
        ($receipt.installer_exit_code -isnot [int] -and $receipt.installer_exit_code -isnot [long]) -or
        $receipt.guest_additions_verified -isnot [bool] -or
        $receipt.stage_bootstrap_installed -isnot [bool] -or
        $receipt.recorded_at -isnot [string]
    ) {
        Stop-P14PostOobe 'receipt_invalid'
    }
    return $receipt
}

function Assert-P14GuestAdditionsInstalled {
    foreach ($path in @(
            'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxService.exe',
            'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxControl.exe'
        )) {
        Assert-P14FixedFile $path
    }
}

function Register-P14PostOobeTask {
    $arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$P14BootstrapScript`" -Run"
    $action = New-ScheduledTaskAction -Execute $P14PowerShell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User 'p14operator'
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable
    Register-ScheduledTask `
        -TaskName $P14BootstrapTaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force | Out-Null
}

function Remove-P14PostOobeTask {
    if (Get-ScheduledTask -TaskName $P14BootstrapTaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $P14BootstrapTaskName -Confirm:$false
    }
}

function Install-P14StageBootstrap {
    & $P14PowerShell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $P14StageBootstrapScript -Install
    if ($LASTEXITCODE -ne 0) {
        Stop-P14PostOobe 'stage_bootstrap_install_failed'
    }
}

function Invoke-P14PostOobeBootstrap {
    Assert-P14SystemBootstrap
    Assert-P14OfflineGuest
    foreach ($path in @($P14BootstrapScript, $P14GuestAdditionsScript, $P14StageBootstrapScript, $P14PowerShell, $P14Cmd)) {
        Assert-P14FixedFile $path
    }

    $receipt = Get-P14Receipt
    if ($null -ne $receipt) {
        if ($receipt.status -ne 'ga_installed_reboot_pending') {
            Stop-P14PostOobe 'receipt_state_invalid'
        }
        try {
            Assert-P14GuestAdditionsInstalled
            Install-P14StageBootstrap
            Write-P14Receipt 'ready_for_stage' $receipt.installer_exit_code $true $true
            Write-P14Log 'Guest Additions verified after controlled reboot; stage bootstrap installed for the next startup.'
            Remove-P14PostOobeTask
            return
        } catch {
            Write-P14Receipt 'blocked' $receipt.installer_exit_code $false $false
            Write-P14Log "Guest Additions post-reboot verification failed: $($_.Exception.Message)"
            Remove-P14PostOobeTask
            throw
        }
    }

    Write-P14Log 'Invoking fixed Guest Additions helper after OOBE.'
    & $P14Cmd /d /c $P14GuestAdditionsScript *>> $P14LogPath
    $installerExitCode = [int]$LASTEXITCODE
    Write-P14Log "Guest Additions helper exited with code $installerExitCode."
    if ($P14AllowedExitCodes -notcontains $installerExitCode) {
        Write-P14Receipt 'blocked' $installerExitCode $false $false
        Remove-P14PostOobeTask
        Stop-P14PostOobe "guest_additions_exit_$installerExitCode"
    }

    try {
        Assert-P14GuestAdditionsInstalled
    } catch {
        Write-P14Receipt 'blocked' $installerExitCode $false $false
        Write-P14Log "Guest Additions binary verification failed: $($_.Exception.Message)"
        Remove-P14PostOobeTask
        throw
    }
    Write-P14Receipt 'ga_installed_reboot_pending' $installerExitCode $true $false
    Write-P14Log 'Guest Additions verified; requesting one controlled reboot before stage task registration.'
    Restart-Computer -Force
}

if (($Install -and $Run) -or (-not $Install -and -not $Run)) {
    Stop-P14PostOobe 'exactly_one_mode_required'
}

Assert-P14SystemBootstrap
Assert-P14OfflineGuest
Assert-P14FixedFile $P14BootstrapScript
Assert-P14FixedFile $P14GuestAdditionsScript
Assert-P14FixedFile $P14StageBootstrapScript
Assert-P14FixedFile $P14PowerShell
Assert-P14FixedFile $P14Cmd

if ($Install) {
    if (Test-Path -LiteralPath $P14ReceiptPath) {
        Stop-P14PostOobe 'receipt_already_exists'
    }
    Register-P14PostOobeTask
    return
}

Invoke-P14PostOobeBootstrap
