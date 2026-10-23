[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$PythonExe,
    [string]$NpmCmd,
    [switch]$SkipAudiverisDownload
)

$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskVenv = Join-Path $taskRoot '.venv'
$taskDownloads = Join-Path $taskRoot 'tools\downloads'
$taskFonts = Join-Path $taskRoot 'tools\fonts'
$taskInstallerName = 'Audiveris-5.11.0-windowsConsole-x86_64.msi'
$taskInstallerUrl = 'https://github.com/Audiveris/audiveris/releases/download/5.11.0/' + $taskInstallerName
$taskInstallerHash = '5f1b4e96a12c53c7da426814b76e599363c4181e291855996e0a6878dda95f71'
$taskFontBase = 'https://raw.githubusercontent.com/steinbergmedia/bravura/37b194378b710cc40e406ab6c4b07608bb9548ae/'

Write-Output "Project: $taskRoot"
Write-Output '1. Create project .venv and install requirements-lock.txt from PyPI.'
Write-Output '2. Install package-lock.json dependencies with npm ci and lifecycle scripts disabled.'
if ($SkipAudiverisDownload) {
    Write-Output '3. Skip the Audiveris installer download.'
} else {
    Write-Output "3. Download $taskInstallerName and verify its published SHA256."
}
Write-Output '4. Download pinned Bravura.otf and its license into tools/fonts.'
Write-Output 'The script does not run MSI installers or change system PATH / JAVA_HOME.'

if (-not $Execute) {
    Write-Output 'PREVIEW ONLY. Nothing was created, downloaded, or installed.'
    Write-Output 'Run with -Execute only after the user approves this exact scope.'
    return
}

if (-not $PythonExe) { $PythonExe = (Get-Command python -ErrorAction Stop).Source }
if (-not $NpmCmd) { $NpmCmd = (Get-Command npm.cmd -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw "Python not found: $PythonExe" }
if (-not (Test-Path -LiteralPath $NpmCmd -PathType Leaf)) { throw "npm not found: $NpmCmd" }
& $PythonExe -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 is required"'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'requirements.txt'))) { throw 'requirements.txt missing.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'package.json'))) { throw 'package.json missing.' }

# Keep temporary wheel extraction inside the approved workspace. Process-only
# environment changes are restored below; no system environment is changed.
$taskTemp = Join-Path $taskRoot 'tmp\environment'
New-Item -ItemType Directory -Path $taskTemp -Force | Out-Null
$taskPreviousTemp = $env:TEMP
$taskPreviousTmp = $env:TMP
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
try {

# Reuse only an existing virtual environment; never overwrite an unrelated directory.
if (Test-Path -LiteralPath $taskVenv) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskVenv 'pyvenv.cfg'))) {
        throw '.venv exists but is not a virtual environment.'
    }
} else {
    & $PythonExe -m venv $taskVenv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}

$taskVenvPython = Join-Path $taskVenv 'Scripts\python.exe'
& $taskVenvPython -m ensurepip --upgrade --default-pip
if ($LASTEXITCODE -ne 0) { throw 'pip bootstrap failed.' }
& $taskVenvPython -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple --cache-dir (Join-Path $taskRoot 'tmp\pip-cache') --requirement (Join-Path $taskRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
& $taskVenvPython -m pip --isolated check
if ($LASTEXITCODE -ne 0) { throw 'Python dependency consistency check failed.' }

Push-Location -LiteralPath $taskRoot
try {
    # A local cache keeps npm's downloaded package data in the workspace as well.
    & $NpmCmd ci --registry=https://registry.npmjs.org --cache (Join-Path $taskRoot 'tmp\npm-cache') --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed.' }
} finally {
    Pop-Location
}

if (-not $SkipAudiverisDownload) {
New-Item -ItemType Directory -Path $taskDownloads -Force | Out-Null
$taskInstallerPath = Join-Path $taskDownloads $taskInstallerName
if (-not (Test-Path -LiteralPath $taskInstallerPath)) {
    Invoke-WebRequest -Uri $taskInstallerUrl -OutFile $taskInstallerPath
}
$taskActualHash = (Get-FileHash -LiteralPath $taskInstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($taskActualHash -ne $taskInstallerHash) {
    throw 'Audiveris installer SHA256 mismatch. File retained for inspection; not executed.'
}
}

New-Item -ItemType Directory -Path $taskFonts -Force | Out-Null
foreach ($taskFontSpec in @(
    @{ Url = $taskFontBase + 'redist/otf/Bravura.otf'; Name = 'Bravura.otf' },
    @{ Url = $taskFontBase + 'LICENSE.txt'; Name = 'Bravura-LICENSE.txt' }
)) {
    $taskFontPath = Join-Path $taskFonts $taskFontSpec.Name
    if (-not (Test-Path -LiteralPath $taskFontPath)) {
        Invoke-WebRequest -Uri $taskFontSpec.Url -OutFile $taskFontPath
    }
}

Write-Output 'Project dependencies installed; installer and font assets downloaded.'
Write-Output 'Audiveris is NOT installed by this script. Downloads, if requested, are in tools/downloads.'
Write-Output 'Next: verify library imports/font embedding, then obtain separate approval for Audiveris system installation.'
} finally {
    $env:TEMP = $taskPreviousTemp
    $env:TMP = $taskPreviousTmp
}
