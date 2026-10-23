[CmdletBinding()]
param([string]$NodeExe, [string]$PythonExe)
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = if ($PythonExe) { $PythonExe } else { Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not $NodeExe) {
    $NodeExe = if ($env:JIANPU_NODE) { $env:JIANPU_NODE } else { (Get-Command node -ErrorAction Stop).Source }
}
$taskTsc = Join-Path $taskRoot 'node_modules\typescript\bin\tsc'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Project venv missing. Install dependencies only after user approval.' }
if (-not (Test-Path -LiteralPath $taskTsc)) { throw 'TypeScript missing. Install dependencies only after user approval.' }
Push-Location -LiteralPath $taskRoot
try {
    & $NodeExe $taskTsc -p tsconfig.json
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript compilation failed.' }
    & $NodeExe --test tests/layout.test.mjs tests/style.test.mjs tests/rests.test.mjs tests/spans.test.mjs tests/voices.test.mjs tests/render.test.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Notation layout tests failed.' }
    New-Item -ItemType Directory -Path (Join-Path $taskRoot 'tmp') -Force | Out-Null
    & $taskPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Music semantics tests failed.' }
    & $taskPython -m jianpu doctor
    if ($LASTEXITCODE -ne 0) { throw 'Environment probe failed.' }
} finally { Pop-Location }
