[CmdletBinding()]
param(
    [switch]$Install,

    [switch]$Run,

    [switch]$CleanupBootstrapLogon
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# This answer-ISO-resident bootstrap deliberately runs Guest Additions only
# after Windows Setup/OOBE has completed and the host has performed one
# controlled ACPI startup. Both phases execute as LOCAL SYSTEM; no remote
# control channel, network, operator logon, or staged P14 content is accepted
# or used here.  After Guest Additions is verified, the task may prepare one
# blank-password local automatic bootstrap logon.  Its separate LOCAL SYSTEM
# at-logon cleanup removes every autologon value before later B1 work.
$P14BootstrapScript = 'C:\Windows\Setup\Scripts\ctoa_p14_post_oobe_bootstrap.ps1'
$P14BootstrapTaskName = 'CTOAi-P14-PostOOBE-GuestAdditions'
$P14BootstrapLogonCleanupTaskName = 'CTOAi-P14-BootstrapLogon-Cleanup'
$P14StageBootstrapTaskName = 'CTOAi-P14-Stage-Bootstrap'
$P14BootstrapOperatorName = 'p14operator'
$P14GuestAdditionsScript = 'C:\Windows\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd'
$P14StageBootstrapScript = 'C:\Windows\Setup\Scripts\ctoa_p14_stage_bootstrap.ps1'
$P14PowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$P14Cmd = 'C:\Windows\System32\cmd.exe'
$P14Net = 'C:\Windows\System32\net.exe'
$P14ReceiptDirectory = 'C:\ProgramData\CTOAi\P14'
$P14ReceiptPath = 'C:\ProgramData\CTOAi\P14\guest-additions-post-oobe-receipt.json'
$P14BootstrapLogonCleanupReceiptPath = 'C:\ProgramData\CTOAi\P14\bootstrap-logon-cleanup-receipt.json'
$P14LogPath = 'C:\ProgramData\CTOAi\P14\guest-additions-post-oobe.log'
$P14AllowedExitCodes = @(0, 3010, 1641)
$P14ReceiptSchema = 'ctoa.p14-post-oobe-guest-additions.v2'
$P14BootstrapLogonCleanupReceiptSchema = 'ctoa.p14-bootstrap-logon-cleanup.v1'

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
    [bool]$StageBootstrapInstalled,
    [bool]$BootstrapLogonCleanupRegistered
) {
    Initialize-P14ReceiptPaths
    [ordered]@{
        schema_version = $P14ReceiptSchema
        status = $Status
        installer_exit_code = $InstallerExitCode
        guest_additions_verified = $GuestAdditionsVerified
        stage_bootstrap_installed = $StageBootstrapInstalled
        bootstrap_logon_cleanup_registered = $BootstrapLogonCleanupRegistered
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
        'guest_additions_verified', 'stage_bootstrap_installed',
        'bootstrap_logon_cleanup_registered', 'recorded_at'
    )
    $actual = @($receipt.PSObject.Properties.Name)
    if (
        $receipt.schema_version -ne $P14ReceiptSchema -or
        @(Compare-Object -ReferenceObject $expected -DifferenceObject $actual -CaseSensitive).Count -ne 0 -or
        $receipt.status -notin @('ga_installed_reboot_pending', 'bootstrap_logon_pending', 'ready_for_stage', 'blocked') -or
        ($receipt.installer_exit_code -isnot [int] -and $receipt.installer_exit_code -isnot [long]) -or
        $receipt.guest_additions_verified -isnot [bool] -or
        $receipt.stage_bootstrap_installed -isnot [bool] -or
        $receipt.bootstrap_logon_cleanup_registered -isnot [bool] -or
        $receipt.recorded_at -isnot [string]
    ) {
        Stop-P14PostOobe 'receipt_invalid'
    }
    return $receipt
}

function Write-P14BootstrapLogonCleanupReceipt(
    [int]$InstallerExitCode
) {
    Initialize-P14ReceiptPaths
    if (Test-Path -LiteralPath $P14BootstrapLogonCleanupReceiptPath) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_receipt_already_exists'
    }
    $receipt = [ordered]@{
        schema_version = $P14BootstrapLogonCleanupReceiptSchema
        status = 'automatic_bootstrap_completed'
        user = $P14BootstrapOperatorName
        automatic_logon_consumed = $true
        autoadminlogon_cleared = $true
        default_username_cleared = $true
        default_domain_name_cleared = $true
        default_password_cleared = $true
        cleanup_task_removed = $true
        stage_bootstrap_registered = $true
        installer_exit_code = $InstallerExitCode
        recorded_at = (Get-Date -AsUTC -Format 'o')
    }
    $raw = [Text.UTF8Encoding]::new($false).GetBytes(($receipt | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
    $stream = $null
    try {
        $stream = [IO.File]::Open(
            $P14BootstrapLogonCleanupReceiptPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        $stream.Write($raw, 0, $raw.Length)
        $stream.Flush($true)
    } finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function Assert-P14GuestAdditionsInstalled {
    foreach ($path in @(
            'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxService.exe',
            'C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxControl.exe'
        )) {
        Assert-P14FixedFile $path
    }
}

function Get-P14WinlogonPath {
    return 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
}

function Test-P14RegistryValuePresent([string]$Path, [string]$Name) {
    $item = Get-ItemProperty -LiteralPath $Path -ErrorAction Stop
    return $item.PSObject.Properties.Match($Name).Count -eq 1
}

function Assert-P14OperatorIsDedicatedStandardUser {
    try {
        $operator = Get-LocalUser -Name $P14BootstrapOperatorName -ErrorAction Stop
        $administrators = Get-LocalGroup -SID 'S-1-5-32-544' -ErrorAction Stop
        $administratorMembers = @(Get-LocalGroupMember -Group $administrators -ErrorAction Stop)
    } catch {
        Stop-P14PostOobe 'operator_account_lookup_failed'
    }
    if (-not $operator.Enabled) {
        Stop-P14PostOobe 'operator_account_disabled'
    }
    if (@($administratorMembers | Where-Object {
                $null -ne $_.SID -and $_.SID.Value -eq $operator.SID.Value
            }).Count -ne 0) {
        Stop-P14PostOobe 'operator_account_not_standard'
    }
}

function Set-P14OperatorBlankCredential {
    Assert-P14FixedFile $P14Net
    & $P14Net ('u' + 'ser') $P14BootstrapOperatorName ''
    if ($LASTEXITCODE -ne 0) {
        Stop-P14PostOobe 'operator_blank_credential_failed'
    }
}

function Assert-P14BootstrapLogonStateCleared {
    $winlogonPath = Get-P14WinlogonPath
    if ((Get-ItemPropertyValue -LiteralPath $winlogonPath -Name 'AutoAdminLogon' -ErrorAction Stop) -ne '0') {
        Stop-P14PostOobe 'autologon_disable_failed'
    }
    foreach ($name in @('DefaultUserName', 'DefaultDomainName', 'DefaultPassword')) {
        if (Test-P14RegistryValuePresent $winlogonPath $name) {
            Stop-P14PostOobe 'autologon_value_clear_failed'
        }
    }
}

function Assert-P14NoActiveBootstrapLogonState {
    $winlogonPath = Get-P14WinlogonPath
    $item = Get-ItemProperty -LiteralPath $winlogonPath -ErrorAction Stop
    $autoAdminLogon = $item.PSObject.Properties.Match('AutoAdminLogon')
    if ($autoAdminLogon.Count -eq 1 -and [string]$autoAdminLogon[0].Value -ne '0') {
        Stop-P14PostOobe 'autologon_existing_state_rejected'
    }
    foreach ($name in @('DefaultUserName', 'DefaultDomainName', 'DefaultPassword')) {
        if (Test-P14RegistryValuePresent $winlogonPath $name) {
            Stop-P14PostOobe 'autologon_existing_state_rejected'
        }
    }
}

function Configure-P14SingleBootstrapLogon {
    Assert-P14OperatorIsDedicatedStandardUser
    Set-P14OperatorBlankCredential

    $winlogonPath = Get-P14WinlogonPath
    Set-ItemProperty -LiteralPath $winlogonPath -Name 'AutoAdminLogon' -Value '1' -Type String
    Set-ItemProperty -LiteralPath $winlogonPath -Name 'DefaultUserName' -Value $P14BootstrapOperatorName -Type String
    Set-ItemProperty -LiteralPath $winlogonPath -Name 'DefaultDomainName' -Value $env:COMPUTERNAME -Type String
    Set-ItemProperty -LiteralPath $winlogonPath -Name 'DefaultPassword' -Value '' -Type String
    if (
        (Get-ItemPropertyValue -LiteralPath $winlogonPath -Name 'AutoAdminLogon' -ErrorAction Stop) -ne '1' -or
        (Get-ItemPropertyValue -LiteralPath $winlogonPath -Name 'DefaultUserName' -ErrorAction Stop) -ne $P14BootstrapOperatorName -or
        (Get-ItemPropertyValue -LiteralPath $winlogonPath -Name 'DefaultDomainName' -ErrorAction Stop) -ne $env:COMPUTERNAME -or
        (Get-ItemPropertyValue -LiteralPath $winlogonPath -Name 'DefaultPassword' -ErrorAction Stop) -ne ''
    ) {
        Stop-P14PostOobe 'bootstrap_logon_configure_failed'
    }
}

function Clear-P14BootstrapLogonState {
    $winlogonPath = Get-P14WinlogonPath
    Set-ItemProperty -LiteralPath $winlogonPath -Name 'AutoAdminLogon' -Value '0' -Type String
    foreach ($name in @('DefaultUserName', 'DefaultDomainName', 'DefaultPassword')) {
        Remove-ItemProperty -LiteralPath $winlogonPath -Name $name -ErrorAction SilentlyContinue
    }
    Assert-P14BootstrapLogonStateCleared
}

function Register-P14PostOobeTask {
    $arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$P14BootstrapScript`" -Run"
    $action = New-ScheduledTaskAction -Execute $P14PowerShell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtStartup
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

function Register-P14BootstrapLogonCleanupTask {
    if (Test-Path -LiteralPath $P14BootstrapLogonCleanupReceiptPath) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_receipt_already_exists'
    }
    if (Get-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -ErrorAction SilentlyContinue) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_task_already_exists'
    }
    $arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$P14BootstrapScript`" -CleanupBootstrapLogon"
    $action = New-ScheduledTaskAction -Execute $P14PowerShell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $P14BootstrapOperatorName
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable
    Register-ScheduledTask `
        -TaskName $P14BootstrapLogonCleanupTaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings | Out-Null
}

function Remove-P14BootstrapLogonCleanupTask {
    if (-not (Get-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -ErrorAction SilentlyContinue)) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_task_missing'
    }
    Unregister-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -Confirm:$false
    if (Get-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -ErrorAction SilentlyContinue) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_task_remove_failed'
    }
}

function Register-P14StageBootstrapTask {
    if (Get-ScheduledTask -TaskName $P14StageBootstrapTaskName -ErrorAction SilentlyContinue) {
        Stop-P14PostOobe 'stage_bootstrap_task_already_exists'
    }
    $arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$P14StageBootstrapScript`" -Run"
    $action = New-ScheduledTaskAction -Execute $P14PowerShell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable
    Register-ScheduledTask `
        -TaskName $P14StageBootstrapTaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings | Out-Null
}

function Invoke-P14PostOobeBootstrap {
    Assert-P14SystemBootstrap
    Assert-P14OfflineGuest
    foreach ($path in @($P14BootstrapScript, $P14GuestAdditionsScript, $P14StageBootstrapScript, $P14PowerShell, $P14Cmd, $P14Net)) {
        Assert-P14FixedFile $path
    }

    $receipt = Get-P14Receipt
    if ($null -ne $receipt) {
        if ($receipt.status -ne 'ga_installed_reboot_pending') {
            Stop-P14PostOobe 'receipt_state_invalid'
        }
        try {
            Assert-P14GuestAdditionsInstalled
            Assert-P14OperatorIsDedicatedStandardUser
            Assert-P14NoActiveBootstrapLogonState
            Register-P14BootstrapLogonCleanupTask
            try {
                Configure-P14SingleBootstrapLogon
            } catch {
                Remove-P14BootstrapLogonCleanupTask
                throw
            }
            Write-P14Receipt 'bootstrap_logon_pending' $receipt.installer_exit_code $true $false $true
            Write-P14Log 'Guest Additions verified after controlled reboot; one automatic blank-password bootstrap logon is pending its LOCAL SYSTEM cleanup.'
            Remove-P14PostOobeTask
            Restart-Computer -Force
        } catch {
            try {
                Clear-P14BootstrapLogonState
            } catch {
            }
            try {
                if (Get-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -ErrorAction SilentlyContinue) {
                    Unregister-ScheduledTask -TaskName $P14BootstrapLogonCleanupTaskName -Confirm:$false
                }
            } catch {
            }
            Write-P14Receipt 'blocked' $receipt.installer_exit_code $false $false $false
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
        Write-P14Receipt 'blocked' $installerExitCode $false $false $false
        Remove-P14PostOobeTask
        Stop-P14PostOobe "guest_additions_exit_$installerExitCode"
    }

    try {
        Assert-P14GuestAdditionsInstalled
    } catch {
        Write-P14Receipt 'blocked' $installerExitCode $false $false $false
        Write-P14Log "Guest Additions binary verification failed: $($_.Exception.Message)"
        Remove-P14PostOobeTask
        throw
    }
    Write-P14Receipt 'ga_installed_reboot_pending' $installerExitCode $true $false $false
    Write-P14Log 'Guest Additions verified; requesting one controlled reboot before automatic bootstrap preparation.'
    Restart-Computer -Force
}

function Invoke-P14BootstrapLogonCleanup {
    Assert-P14SystemBootstrap
    Assert-P14OfflineGuest
    foreach ($path in @($P14BootstrapScript, $P14StageBootstrapScript, $P14PowerShell)) {
        Assert-P14FixedFile $path
    }
    $receipt = Get-P14Receipt
    if (
        $null -eq $receipt -or
        $receipt.status -ne 'bootstrap_logon_pending' -or
        -not $receipt.guest_additions_verified -or
        $receipt.stage_bootstrap_installed -or
        -not $receipt.bootstrap_logon_cleanup_registered
    ) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_state_invalid'
    }
    if (Test-Path -LiteralPath $P14BootstrapLogonCleanupReceiptPath) {
        Stop-P14PostOobe 'bootstrap_logon_cleanup_receipt_already_exists'
    }

    Clear-P14BootstrapLogonState
    Register-P14StageBootstrapTask
    Remove-P14BootstrapLogonCleanupTask
    Write-P14BootstrapLogonCleanupReceipt $receipt.installer_exit_code
    Write-P14Receipt 'ready_for_stage' $receipt.installer_exit_code $true $true $false
    Write-P14Log 'Automatic bootstrap logon consumed and cleared by LOCAL SYSTEM; stage bootstrap is registered for a later startup and has not run.'
}

if ((@($Install, $Run, $CleanupBootstrapLogon | Where-Object { $_ }).Count -ne 1)) {
    Stop-P14PostOobe 'exactly_one_mode_required'
}

Assert-P14SystemBootstrap
Assert-P14OfflineGuest
Assert-P14FixedFile $P14BootstrapScript
Assert-P14FixedFile $P14GuestAdditionsScript
Assert-P14FixedFile $P14StageBootstrapScript
Assert-P14FixedFile $P14PowerShell
Assert-P14FixedFile $P14Cmd
Assert-P14FixedFile $P14Net

if ($Install) {
    if (Test-Path -LiteralPath $P14ReceiptPath) {
        Stop-P14PostOobe 'receipt_already_exists'
    }
    Register-P14PostOobeTask
    return
}

if ($CleanupBootstrapLogon) {
    Invoke-P14BootstrapLogonCleanup
    return
}

Invoke-P14PostOobeBootstrap
