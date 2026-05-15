#!/usr/bin/env pwsh
# Re-zip the app package after manual tweaks (icons, instruction.txt, etc.)
# without re-running the toolkit's full provision.

[CmdletBinding()]
param(
    [string]$Env = 'dev'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$appPackage = Join-Path $root 'appPackage'
$build = Join-Path $appPackage 'build'
$zip = Join-Path $build "appPackage.$Env.zip"

if (-not (Test-Path $build)) {
    New-Item -ItemType Directory -Path $build | Out-Null
}

$required = @(
    (Join-Path $appPackage 'manifest.json'),
    (Join-Path $appPackage 'declarativeAgent.json'),
    (Join-Path $appPackage 'instruction.txt'),
    (Join-Path $appPackage 'actions\dataverse-mcp.action.json'),
    (Join-Path $appPackage 'color.png'),
    (Join-Path $appPackage 'outline.png')
)
foreach ($f in $required) {
    if (-not (Test-Path $f)) {
        throw "Missing required file: $f"
    }
}

if (Test-Path $zip) { Remove-Item $zip }

Push-Location $appPackage
try {
    $items = @('manifest.json', 'declarativeAgent.json', 'instruction.txt',
        'color.png', 'outline.png', 'actions')
    Compress-Archive -Path $items -DestinationPath $zip
}
finally {
    Pop-Location
}

Write-Host "Wrote $zip"
