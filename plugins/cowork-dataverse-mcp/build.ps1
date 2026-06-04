# build.ps1 - substitute placeholders + pack the Cowork plugin zip.
#
# Usage (from repo root or this dir):
#   .\build.ps1 -DataverseUrl "https://org40ae6a46.crm.dynamics.com" `
#               -OAuthRegistrationId "<Teams Dev Portal OAuth Registration ID>"
#
# Outputs:
#   .\out\launch-control-cowork-plugin.zip   <- upload this to M365 Admin Center
#   .\out\manifest.json, .\out\plugin-action.json (the substituted copies)

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$DataverseUrl,
    [Parameter(Mandatory = $true)][string]$OAuthRegistrationId,
    [string]$AppId,
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out  = Join-Path $here "out"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $out | Out-Null

if (-not $AppId) { $AppId = [guid]::NewGuid().ToString() }
$DataverseUrl = $DataverseUrl.TrimEnd('/')

# manifest.json
$mf = Get-Content (Join-Path $here "manifest.json") -Raw
$mf = $mf -replace '00000000-0000-0000-0000-000000000000', $AppId
$mf = $mf -replace '"version":\s*"[^"]+"', "`"version`": `"$Version`""
$mf | Set-Content (Join-Path $out "manifest.json") -NoNewline

# plugin-action.json
$pa = Get-Content (Join-Path $here "plugin-action.json") -Raw
$pa = $pa -replace '\{DATAVERSE_ORG_URL\}',         [regex]::Escape($DataverseUrl).Replace('\','')
$pa = $pa -replace '\{TEAMS_OAUTH_REGISTRATION_ID\}', $OAuthRegistrationId
$pa | Set-Content (Join-Path $out "plugin-action.json") -NoNewline

# icons (required by Teams manifest validator)
Copy-Item (Join-Path $here "color.png")   (Join-Path $out "color.png")   -Force
Copy-Item (Join-Path $here "outline.png") (Join-Path $out "outline.png") -Force

$zip = Join-Path $out "launch-control-cowork-plugin.zip"
Compress-Archive -Path (Join-Path $out "manifest.json"), `
                       (Join-Path $out "plugin-action.json"), `
                       (Join-Path $out "color.png"), `
                       (Join-Path $out "outline.png") `
                 -DestinationPath $zip -Force

Write-Host ""
Write-Host "=== Cowork plugin package built ===" -ForegroundColor Green
Write-Host "  Teams App ID  : $AppId"
Write-Host "  Version       : $Version"
Write-Host "  MCP endpoint  : $DataverseUrl/api/mcp"
Write-Host "  OAuth ref id  : $OAuthRegistrationId"
Write-Host "  Package zip   : $zip"
Write-Host ""
Write-Host "Next:"
Write-Host "  1) M365 Admin Center -> Integrated apps -> Upload custom apps -> $zip"
Write-Host "  2) Publish to a small test audience"
Write-Host "  3) In Cowork: Add plugin -> Launch Control -> Connect (complete OAuth)"
Write-Host "  4) After validation, harden the Teams OAuth registration to App ID $AppId"
