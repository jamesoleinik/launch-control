# build.ps1 - stage + zip the Cowork "Dataverse EPPCDemo1FnO" plugin (preview MCP).
#
# The source manifest.json carries the placeholder __OAUTH_REFERENCE_ID__ until
# deploy/provision.py emits the real base64 referenceId. Pass it here to bake
# it into the packaged manifest.
#
# Usage (from this folder or repo root):
#   .\build.ps1 -OAuthReferenceId "<base64 tenantId##oAuthConfigId>"
#   .\build.ps1 -OAuthReferenceId "<...>" -Version "1.0.1"
#
# Output:
#   .\out\dataverse-eppcdemo1fno-cowork.zip   <- upload this to M365 Admin Center
#   .\out\manifest.json                    <- the substituted copy

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OAuthReferenceId,
    [string]$Version
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out  = Join-Path $here "out"
$stage = Join-Path $out "pkg"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

$mf = Get-Content (Join-Path $here "manifest.json") -Raw
$mf = $mf -replace '__OAUTH_REFERENCE_ID__', $OAuthReferenceId
if ($Version) { $mf = $mf -replace '"version":\s*"[^"]+"', "`"version`": `"$Version`"" }
if ($mf -match '__OAUTH_REFERENCE_ID__') { throw "OAuth referenceId placeholder still present." }
$mf | Set-Content (Join-Path $stage "manifest.json") -NoNewline

Copy-Item (Join-Path $here "color.png")   (Join-Path $stage "color.png")   -Force
Copy-Item (Join-Path $here "outline.png") (Join-Path $stage "outline.png") -Force
Copy-Item (Join-Path $here "skills") (Join-Path $stage "skills") -Recurse -Force

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = Join-Path $out "dataverse-eppcdemo1fno-cowork.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem -Path $stage -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($stage.Length + 1) -replace '\\', '/'
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $rel) | Out-Null
    }
} finally { $archive.Dispose() }
Copy-Item (Join-Path $stage "manifest.json") (Join-Path $out "manifest.json") -Force

Write-Host ""
Write-Host "=== Cowork 'Dataverse EPPCDemo1FnO' package built ===" -ForegroundColor Green
Write-Host "  MCP endpoint  : https://eppcdemo1fno.crm.dynamics.com/api/mcp_preview"
Write-Host "  Package zip   : $zip"
