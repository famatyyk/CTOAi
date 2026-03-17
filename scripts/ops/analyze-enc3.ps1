param(
    [string[]]$Files = @(
        "$env:APPDATA\Mythibia\MythibiaV2\_tmp_unpack\init.lua",
        "$env:APPDATA\Mythibia\MythibiaV2\_tmp_unpack\modules\client\client.lua",
        "$env:APPDATA\Mythibia\MythibiaV2\_tmp_unpack\modules\client\client.otmod",
        "$env:APPDATA\Mythibia\MythibiaV2\_tmp_unpack\modules\game_trainer\trainer.lua",
        "$env:APPDATA\Mythibia\MythibiaV2\_tmp_unpack\modules\game_trainer\trainer.otmod"
    )
)

$ErrorActionPreference = 'Stop'

function Get-ShannonEntropy {
    param([byte[]]$Bytes)

    if (-not $Bytes -or $Bytes.Length -eq 0) {
        return 0.0
    }

    $freq = @{}
    foreach ($value in $Bytes) {
        if ($freq.ContainsKey($value)) {
            $freq[$value]++
        }
        else {
            $freq[$value] = 1
        }
    }

    $entropy = 0.0
    foreach ($count in $freq.Values) {
        $p = $count / $Bytes.Length
        $entropy += -1.0 * $p * ([Math]::Log($p, 2))
    }

    return $entropy
}

function Find-ZlibOffsets {
    param([byte[]]$Bytes)

    $hits = New-Object System.Collections.Generic.List[int]
    for ($i = 0; $i -lt ($Bytes.Length - 1); $i++) {
        if ($Bytes[$i] -eq 0x78 -and @(0x01, 0x5E, 0x9C, 0xDA) -contains $Bytes[$i + 1]) {
            $hits.Add($i)
        }
    }

    return @($hits)
}

function Test-SimpleXorZlib {
    param([byte[]]$Bytes)

    if ($Bytes.Length -lt 26) {
        return @()
    }

    $payload0 = $Bytes[24]
    $payload1 = $Bytes[25]
    $hits = New-Object System.Collections.Generic.List[string]

    foreach ($candidateSecond in @(0x01, 0x5E, 0x9C, 0xDA)) {
        $key = $payload0 -bxor 0x78
        if (($payload1 -bxor $key) -eq $candidateSecond) {
            $hits.Add(('0x{0:X2}->78 {1:X2}' -f $key, $candidateSecond))
        }
    }

    return @($hits)
}

$rows = New-Object System.Collections.Generic.List[string]
$rows.Add('ENC3 analysis report')
$rows.Add('GeneratedAt: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$rows.Add('')

foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        $rows.Add('FILE=' + $file)
        $rows.Add('STATUS=missing')
        $rows.Add('')
        continue
    }

    $bytes = [System.IO.File]::ReadAllBytes($file)
    $headLen = [Math]::Min(64, $bytes.Length)
    $headHex = ($bytes[0..($headLen - 1)] | ForEach-Object { $_.ToString('X2') }) -join ' '
    $entropy = Get-ShannonEntropy -Bytes $bytes
    $zlibOffsets = Find-ZlibOffsets -Bytes $bytes
    $xorKeys = Test-SimpleXorZlib -Bytes $bytes
    $field4 = if ($bytes.Length -ge 8) { [BitConverter]::ToUInt32($bytes, 4) } else { $null }
    $field8 = if ($bytes.Length -ge 12) { [BitConverter]::ToUInt32($bytes, 8) } else { $null }
    $field12 = if ($bytes.Length -ge 16) { [BitConverter]::ToUInt32($bytes, 12) } else { $null }
    $field16 = if ($bytes.Length -ge 20) { [BitConverter]::ToUInt32($bytes, 16) } else { $null }

    $rows.Add('FILE=' + $file)
    $rows.Add('STATUS=ok')
    $rows.Add('LEN=' + $bytes.Length)
    $rows.Add('HEAD_ASCII=' + [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(4, $bytes.Length)))
    $rows.Add('HEAD64=' + $headHex)
    $rows.Add('ENTROPY=' + ('{0:N4}' -f $entropy))
    $rows.Add('FIELD_U32_4=' + $field4)
    $rows.Add('FIELD_U32_8=' + $field8)
    $rows.Add('FIELD_U32_12=' + $field12)
    $rows.Add('FIELD_U32_16=' + $field16)
    $rows.Add('LEN_MINUS_24=' + ($bytes.Length - 24))
    $rows.Add('ZLIB_OFFSETS=' + ($(if ($zlibOffsets.Count -gt 0) { $zlibOffsets -join ',' } else { 'none' })))
    $rows.Add('SIMPLE_XOR_ZLIB_KEYS=' + ($(if ($xorKeys.Count -gt 0) { $xorKeys -join ',' } else { 'none' })))
    $rows.Add('')
}

$reportPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'ops\enc3-analysis-report.txt'
[System.IO.File]::WriteAllLines($reportPath, $rows)
Write-Output $reportPath