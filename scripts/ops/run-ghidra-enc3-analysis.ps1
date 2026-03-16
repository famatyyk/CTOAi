$ErrorActionPreference = 'Stop'

$javaHome = 'C:\Users\zycie\Tools\jdk-21.0.10+7'
$ghidraRoot = 'C:\Users\zycie\Tools\ghidra_12.0.4_PUBLIC'
$projectRoot = 'C:\Users\zycie\CTOAi\artifacts\enc3\ghidra-project'
$projectName = 'mythibia_enc3'
$scriptPath = 'C:\Users\zycie\CTOAi\scripts\ops\ghidra'
$outputDir = 'C:\Users\zycie\CTOAi\artifacts\enc3'
$binaryPath = 'C:\Users\zycie\AppData\Roaming\Mythibia\MythibiaV2\mythibia_dx-1773218163.exe'

if (-not (Test-Path $javaHome)) {
    throw "JAVA_HOME not found: $javaHome"
}
if (-not (Test-Path $ghidraRoot)) {
    throw "Ghidra root not found: $ghidraRoot"
}
if (-not (Test-Path $binaryPath)) {
    throw "Binary not found: $binaryPath"
}

$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;" + $env:Path

New-Item -ItemType Directory -Force -Path $projectRoot | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

& "$ghidraRoot\support\analyzeHeadless.bat" `
    $projectRoot `
    $projectName `
    -import $binaryPath `
    -overwrite `
    -scriptPath $scriptPath `
    -postScript Enc3StringXrefs.java $outputDir `
    -analysisTimeoutPerFile 1200 `
    -max-cpu 4