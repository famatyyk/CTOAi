$ErrorActionPreference = 'Stop'

$javaHome = 'C:\Users\zycie\Tools\jdk-21.0.10+7'
$ghidraRoot = 'C:\Users\zycie\Tools\ghidra_12.0.4_PUBLIC'
$projectRoot = 'C:\Users\zycie\CTOAi\artifacts\enc3\ghidra-project'
$projectName = 'mythibia_enc3'
$scriptPath = 'C:\Users\zycie\CTOAi\scripts\ops\ghidra'
$outputDir = 'C:\Users\zycie\CTOAi\artifacts\enc3'
$binaryName = 'mythibia_dx-1773218163.exe'

$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;" + $env:Path

& "$ghidraRoot\support\analyzeHeadless.bat" `
    $projectRoot `
    $projectName `
    -process $binaryName `
    -scriptPath $scriptPath `
    -postScript Enc3FunctionContext.java $outputDir `
    -max-cpu 4