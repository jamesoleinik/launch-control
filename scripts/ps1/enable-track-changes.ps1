<#
Enable-Track-Changes.ps1

Enable Track Changes on a set of lc_* Dataverse tables via the Web API.
Run locally where you have enough privileges (Global Admin / System Administrator) and the az CLI authenticated.

Usage examples:
  # Dry-run to preview
  .\enable-track-changes.ps1 -DataverseUrl 'https://<environment>.crm.dynamics.com' -DryRun

  # Apply changes
  .\enable-track-changes.ps1 -DataverseUrl 'https://<environment>.crm.dynamics.com'
#>

param(
    [string]$DataverseUrl = $env:DATAVERSE_URL,
    [string[]]$Tables = @(
        'lc_launch','lc_milestone','lc_task','lc_statusupdate','lc_teammember',
        'lc_erpsignal',
        'lc_stg_tracker_a','lc_stg_tracker_b','lc_stg_tracker_c','lc_stg_tracker_d','lc_stg_tracker_e'
    ),
    [switch]$DryRun
)

if (-not $DataverseUrl) {
    Write-Error "DATAVERSE_URL must be provided via -DataverseUrl or the DATAVERSE_URL environment variable"
    exit 1
}

# Ensure az is available
$azCmd = Get-Command az -ErrorAction SilentlyContinue
if (-not $azCmd) {
    Write-Error "Azure CLI (az) not found on PATH. Install and run 'az login' before running this script."
    exit 1
}

Write-Host "🔗 Connecting to: $DataverseUrl`n"

# Acquire access token using az
try {
    $tokenJson = az account get-access-token --resource $DataverseUrl | ConvertFrom-Json
    $accessToken = $tokenJson.accessToken
} catch {
    Write-Error "Failed to acquire access token via az: $_"
    exit 1
}

$headers = @{
    Authorization = "Bearer $accessToken"
    Accept = 'application/json'
    'OData-Version' = '4.0'
    'OData-MaxVersion' = '4.0'
}

$disabled = @()
Write-Host "📋 Checking tables...`n"
foreach ($t in $Tables) {
    $metaUrl = "$DataverseUrl/api/data/v9.2/EntityDefinitions(LogicalName='$t')"
    try {
        $resp = Invoke-RestMethod -Uri $metaUrl -Headers $headers -Method Get -ErrorAction Stop
        $enabled = $resp.ChangeTrackingEnabled
        if ($enabled) { Write-Host "$t`t: ENABLED" -ForegroundColor Green } else { Write-Host "$t`t: DISABLED" -ForegroundColor Yellow; $disabled += $t }
    } catch {
        Write-Warning "$t : query failed - $_"
    }
}

if ($disabled.Count -eq 0) {
    Write-Host "`n✓ All tables already have Track Changes enabled." -ForegroundColor Green
    exit 0
}

Write-Host "`n⚠ The following tables are disabled:`n" -ForegroundColor Yellow
$disabled | ForEach-Object { Write-Host "  - $_" }

if ($DryRun) {
    Write-Host "`n🔍 Dry-run mode: no changes will be made. To apply, re-run without -DryRun." -ForegroundColor Cyan
    exit 0
}

Write-Host "`n⚙️ Enabling Track Changes for these tables...`n" -ForegroundColor Cyan

foreach ($t in $disabled) {
    try {
        $metaUrl = "$DataverseUrl/api/data/v9.2/EntityDefinitions(LogicalName='$t')"
        $meta = Invoke-RestMethod -Uri $metaUrl -Headers $headers -Method Get -ErrorAction Stop
        $id = $meta.MetadataId
        if (-not $id) { Write-Warning "${t}: could not retrieve MetadataId"; continue }

        $updateUrl = "$DataverseUrl/api/data/v9.2/EntityDefinitions($id)"

        # build update headers (If-Match required when updating metadata)
        $updateHeaders = @{}
        foreach ($k in $headers.Keys) { $updateHeaders[$k] = $headers[$k] }
        $updateHeaders['If-Match'] = '*'

        $body = @{ ChangeTrackingEnabled = $true } | ConvertTo-Json

        # PATCH via Invoke-RestMethod; some tenants disallow metadata updates via Web API and will return 405
        Invoke-RestMethod -Uri $updateUrl -Headers $updateHeaders -Method Patch -Body $body -ContentType 'application/json' -ErrorAction Stop
        Write-Host "✓ ${t}: Track Changes enabled" -ForegroundColor Green
    } catch {
        Write-Warning "${t}: update failed - $_"
    }
}

Write-Host "`nDone. Run: python scripts/python/check_track_changes.py to verify." -ForegroundColor Cyan
