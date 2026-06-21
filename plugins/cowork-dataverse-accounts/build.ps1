# build.ps1 - stage + zip the Cowork "Dataverse Accounts" plugin package.
#
# The source manifest.json carries the placeholder __OAUTH_REFERENCE_ID__.
# Pass the base64 referenceId emitted by deploy/deploy.py (Phase E, atk
# oauth/register) to bake it into the packaged manifest.
#
# Usage (from this folder or repo root):
#   .\build.ps1 -OAuthReferenceId "<base64 tenantId##oAuthConfigId>"
#   .\build.ps1 -OAuthReferenceId "<...>" -Version "1.0.1"
#
# Output:
#   .\out\dataverse-accounts-cowork.zip   <- upload this to M365 Admin Center
#   .\out\manifest.json                   <- the substituted copy (for inspection)

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

# manifest.json - substitute the OAuth referenceId (and version if provided)
$mf = Get-Content (Join-Path $here "manifest.json") -Raw
$mf = $mf -replace '__OAUTH_REFERENCE_ID__', $OAuthReferenceId
if ($Version) {
    $mf = $mf -replace '"version":\s*"[^"]+"', "`"version`": `"$Version`""
}
if ($mf -match '__OAUTH_REFERENCE_ID__') {
    throw "OAuth referenceId placeholder still present after substitution."
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
$zip = Join-Path $out "dataverse-accounts-cowork.zip"
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
Write-Host "=== Cowork 'Dataverse Accounts' package built ===" -ForegroundColor Green
Write-Host "  MCP endpoint  : https://org77c9659c.crm.dynamics.com/api/mcp"
Write-Host "  OAuth ref id  : $OAuthReferenceId"
Write-Host "  Package zip   : $zip"
Write-Host ""
Write-Host "Next: upload the zip via M365 Admin Center -> Copilot -> Agents & connectors,"
Write-Host "publish to a small audience, then Add + Connect the plugin in Cowork."
