param(
    [string]$JavaHome,
    [string]$AndroidSdk,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
$taskBuildArgs = @((Join-Path $PSScriptRoot 'tools\build.py'))
if ($JavaHome) { $taskBuildArgs += @('--java-home', $JavaHome) }
if ($AndroidSdk) { $taskBuildArgs += @('--sdk', $AndroidSdk) }
if ($Offline) { $taskBuildArgs += '--offline' }
& python @taskBuildArgs
if ($LASTEXITCODE -ne 0) { throw "Build failed: $LASTEXITCODE" }
