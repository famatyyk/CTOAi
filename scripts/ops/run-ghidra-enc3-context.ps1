param(
    [string]$JavaHome = 'C:\Users\zycie\Tools\jdk-21.0.10+7',
    [string]$GhidraRoot = 'C:\Users\zycie\Tools\ghidra_12.0.4_PUBLIC',
    [string]$ProjectRoot = 'C:\Users\zycie\CTOAi\artifacts\enc3\ghidra-project',
    [string]$ProjectName = 'mythibia_enc3',
    [string]$ScriptPath = 'C:\Users\zycie\CTOAi\scripts\ops\ghidra',
    [string]$OutputDir = 'C:\Users\zycie\CTOAi\artifacts\enc3',
    [string]$BinaryName = 'mythibia_dx-1773218163.exe'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $JavaHome)) {
    throw "JAVA_HOME not found: $JavaHome"
}
if (-not (Test-Path $GhidraRoot)) {
    throw "Ghidra root not found: $GhidraRoot"
}
if (-not (Test-Path $ProjectRoot)) {
    throw "Ghidra project root not found: $ProjectRoot"
}
if (-not (Test-Path $ScriptPath)) {
    throw "Ghidra script path not found: $ScriptPath"
}

$env:JAVA_HOME = $JavaHome
$env:Path = "$JavaHome\bin;" + $env:Path

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

& "$GhidraRoot\support\analyzeHeadless.bat" `
    $projectRoot `
    $projectName `
    -process $BinaryName `
    -scriptPath $ScriptPath `
    -postScript Enc3FunctionContext.java $OutputDir `
    -max-cpu 4