[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputPath,
    [Parameter(Mandatory)][string]$OutputPath,
    [string]$MusicXml,
    [string]$Profile,
    [string]$InstrumentName = '单乐器',
    [ValidateSet('wind','bowed','plucked','struck-string','unknown')][string]$InstrumentFamily = 'unknown',
    [string]$PartId = 'solo',
    [ValidateSet('single','dual')][string]$VoiceMode = 'single',
    [string]$PrimaryVoice,
    [string]$XmlPart,
    [string]$Title,
    [string]$Composer,
    [string]$Audiveris,
    [string]$NodeExe,
    [string]$PythonExe,
    [ValidateRange(1,86400)][int]$TimeoutSeconds = 1200,
    [switch]$BuildRenderer,
    [switch]$Draft,
    [switch]$Overwrite
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskInput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($InputPath)
$taskOutput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
if (-not $Profile) {
    $taskProfileName = if ($VoiceMode -eq 'dual') { 'configs\dual-voice.json' } else { 'configs\single-voice.json' }
    $Profile = Join-Path $taskRoot $taskProfileName
}
if ($PrimaryVoice -and $VoiceMode -ne 'dual') { throw 'PrimaryVoice is only used in dual mode.' }
$taskProfile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Profile)
$taskXml = if ($MusicXml) { $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($MusicXml) } else { $null }
if (-not $PythonExe) { $PythonExe = Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Project Python missing. Use an approved environment or pass -PythonExe; this command does not install dependencies.' }
if (-not $NodeExe) {
    if ($env:JIANPU_NODE) { $NodeExe = $env:JIANPU_NODE }
    elseif (Get-Command node -ErrorAction SilentlyContinue) { $NodeExe = (Get-Command node).Source }
    elseif (Test-Path -LiteralPath 'E:\ProSoftware\Node\node.exe') { $NodeExe = 'E:\ProSoftware\Node\node.exe' }
    else { throw 'Node missing. Pass -NodeExe to an approved Node installation.' }
}
$taskArgs = @('-m','jianpu',$VoiceMode,$taskInput,'--output',$taskOutput,'--profile',$taskProfile,
    '--instrument-name',$InstrumentName,'--instrument-family',$InstrumentFamily,'--part-id',$PartId,
    '--node',$NodeExe,'--timeout',([string]$TimeoutSeconds))
foreach ($item in @(@('--musicxml',$taskXml),@('--xml-part',$XmlPart),@('--title',$Title),@('--composer',$Composer),@('--audiveris',$Audiveris))) {
    if ($item[1]) { $taskArgs += $item }
}
if ($PrimaryVoice) { $taskArgs += @('--primary-voice',$PrimaryVoice) }
if ($Draft) { $taskArgs += '--draft' }
if ($Overwrite) { $taskArgs += '--overwrite' }
Push-Location -LiteralPath $taskRoot
try {
    $taskCompiled = Join-Path $taskRoot 'dist\render.js'
    # Archive extraction can change source timestamps; compilation is explicit.
    if ($BuildRenderer -or -not (Test-Path -LiteralPath $taskCompiled)) {
        $taskCompiler = Join-Path $taskRoot 'node_modules\typescript\bin\tsc'
        if (-not (Test-Path -LiteralPath $taskCompiler)) { throw 'Local TypeScript dependency missing. Install dependencies only after approval.' }
        & $NodeExe $taskCompiler -p tsconfig.json
        if ($LASTEXITCODE -ne 0) { throw 'Renderer compilation failed.' }
    }
    & $PythonExe @taskArgs
    if ($LASTEXITCODE -ne 0) { throw 'Single-voice conversion failed; inspect the error and retained run logs.' }
} finally { Pop-Location }
