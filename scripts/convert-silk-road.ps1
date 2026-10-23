[CmdletBinding()]
param(
    [switch]$Draft,
    [switch]$Overwrite,
    [string]$AudiverisExe = 'C:\Program Files\Audiveris\Audiveris.exe'
)
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Project Python environment is missing.' }
if (-not (Test-Path -LiteralPath $AudiverisExe)) { throw 'Audiveris is missing; install only after user approval.' }
Push-Location -LiteralPath $taskRoot
try {
    if (-not (Test-Path -LiteralPath 'dist\render.js')) { & '.\scripts\build.ps1' }
    $taskArgs = @('-m','jianpu','convert','--config','configs\silk-road.json','--audiveris',$AudiverisExe)
    if ($Draft) { $taskArgs += '--draft' }
    if ($Overwrite) { $taskArgs += '--overwrite' }
    & $taskPython @taskArgs
    if ($LASTEXITCODE -ne 0) { throw 'Conversion failed; inspect the printed run directory and logs.' }
} finally { Pop-Location }
