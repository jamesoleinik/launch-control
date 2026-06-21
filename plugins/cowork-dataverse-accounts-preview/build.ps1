# build.ps1 - stage + zip the Cowork "Dataverse Accounts (Preview)" plugin.
#
# The source manifest.json already carries the OAuth referenceId (shared with
# the GA package - both resolve to the same Teams Dev Portal OAuth
# registration, whose base URL is the org root and therefore covers both
# /api/mcp and /api/mcp_preview). Pass -OAuthReferenceId to override it.
#
# Usage (from this folder or repo root):
#   .\build.ps1
#   .\build.ps1 -OAuthReferenceId "<base64 tenantId##oAuthConfigId>" -Version "1.0.1"
#
# Output:
#   .\out\dataverse-accounts-preview-cowork.zip   <- upload to M365 Admin Center
#   .\out\manifest.json                           <- the packaged copy

[CmdletBinding()]
param(
    [string]$OAuthReferenceId,
    [string]$Version
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out  = Join-Path $here "out"
$stage = Join-Path $out "pkg"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

# manifest.json - optional referenceId / version substitution
$mf = Get-Content (Join-Path $here "manifest.json") -Raw
if ($OAuthReferenceId) {
    $mf = $mf -replace '"referenceId":\s*"[^"]+"', "`"referenceId`": `"$OAuthReferenceId`""
}
if ($Version) {
    $mf = $mf -replace '"version":\s*"[^"]+"', "`"version`": `"$Version`""
}
if ($mf -match '__OAUTH_REFERENCE_ID__') {
    throw "OAuth referenceId placeholder still present; pass -OAuthReferenceId."
}
$mf | Set-Content (Join-Path $stage "manifest.json") -NoNewline

# icons (required by the manifest validator)
Copy-Item (Join-Path $here "color.png")   (Join-Path $stage "color.png")   -Force
Copy-Item (Join-Path $here "outline.png") (Join-Path $stage "outline.png") -Force

# bundled agentSkills - preserve the ./skills/list-my-accounts layout
Copy-Item (Join-Path $here "skills") (Join-Path $stage "skills") -Recurse -Force

# Teams app packages require forward-slash entry names. Compress-Archive emits
# backslashes on Windows, which breaks the manifest validator, so build the
# archive explicitly with normalized entry paths.
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = Join-Path $out "dataverse-accounts-preview-cowork.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem -Path $stage -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($stage.Length + 1) -replace '\\', '/'
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $rel) | Out-Null
    }
} finally {
    $archive.Dispose()
}
Copy-Item (Join-Path $stage "manifest.json") (Join-Path $out "manifest.json") -Force

Write-Host ""
Write-Host "=== Cowork 'Dataverse Accounts (Preview)' package built ===" -ForegroundColor Green
Write-Host "  MCP endpoint  : https://org77c9659c.crm.dynamics.com/api/mcp_preview"
Write-Host "  Package zip   : $zip"
Write-Host ""
Write-Host "Next: upload the zip via M365 Admin Center -> Copilot -> Agents & connectors,"
Write-Host "publish to a small audience, then Add + Connect the plugin in Cowork."
