[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputPath,
    [Parameter(Mandatory)][string]$OutputPath,
    [string]$MusicXml,
    [string]$Profile,
    [string]$InstrumentName,
    [ValidateSet('wind','bowed','plucked','struck-string','unknown')][string]$InstrumentFamily,
    [string]$PartId,
    [string]$XmlPart,
    [string]$PrimaryVoice,
    [string]$Title,
    [string]$Composer,
    [string]$Audiveris,
    [string]$NodeExe,
    [string]$PythonExe,
    [ValidateRange(1,86400)][int]$TimeoutSeconds,
    [switch]$BuildRenderer,
    [switch]$Draft,
    [switch]$Overwrite
)
$ErrorActionPreference='Stop'
$taskParameters=@{} + $PSBoundParameters
$taskParameters['VoiceMode']='dual'
& (Join-Path $PSScriptRoot 'convert-single.ps1') @taskParameters
