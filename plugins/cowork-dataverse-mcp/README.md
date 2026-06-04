# Cowork \u2194 Dataverse MCP \u2014 plugin package

Custom Microsoft 365 Cowork plugin that talks to the **Dataverse MCP server**
of the Launch Control environment. This is the artifact deployed in
**Episode 6 \u2014 Cowork Plugin for Dataverse**.

## What this package is

A Teams app package + a Copilot plugin descriptor:

| File | Role |
|---|---|
| `manifest.json` | Teams app manifest (Microsoft Teams v1.19). References `plugin-action.json` under `copilotAgents.plugins[]`. |
| `plugin-action.json` | Copilot plugin descriptor (v2.4 schema). Declares an `McpServer` runtime pointing at `{DATAVERSE_ORG_URL}/api/mcp` with `OAuthPluginVault` auth bound to `{TEAMS_OAUTH_REGISTRATION_ID}`. |

The package is intentionally tiny because the **server side** (Dataverse
MCP server) already exposes every table, lookup, and Custom API. The
package's job is just to (1) make the endpoint reachable from Cowork and
(2) bind the right OAuth registration.

## Three values you must substitute

Before zipping and uploading, replace the placeholders:

| Placeholder | Where it comes from |
|---|---|
| `{DATAVERSE_ORG_URL}` | The exact org URL of the Launch Control Dataverse environment, e.g. `https://org40ae6a46.crm.dynamics.com`. The MCP endpoint is this URL + `/api/mcp`. |
| `{TEAMS_OAUTH_REGISTRATION_ID}` | The **OAuth Registration ID** copied from **Teams Developer Portal \u2192 OAuth registrations** (NOT the Entra Client ID). |
| `manifest.json#id` | A fresh GUID per package version \u2014 generate with `python -c "import uuid; print(uuid.uuid4())"`. Re-using a GUID across versions makes Cowork serve stale packages. |

> The two IDs **most commonly mixed up** are the Entra Application (Client)
> ID and the Teams Developer Portal OAuth Registration ID. Power Platform's
> *Allowed MCP Client* row takes the **Entra Client ID**. This package's
> `referenceId` takes the **Teams OAuth Registration ID**. They are
> different IDs from different portals \u2014 see Episode 6 README \u00a7Pitfalls.

## Build + upload (manual)

```powershell
# from repo root
cd plugins/cowork-dataverse-mcp

# 1. Substitute placeholders (one-liner; or do it by hand)
$dvUrl = "<your Dataverse org URL>"
$oauthId = "<Teams Developer Portal OAuth Registration ID>"
$id = [guid]::NewGuid().ToString()
(Get-Content manifest.json) | ForEach-Object { $_ -replace '00000000-0000-0000-0000-000000000000', $id } | Set-Content manifest.json
(Get-Content plugin-action.json) | ForEach-Object { $_ -replace '\{DATAVERSE_ORG_URL\}', $dvUrl -replace '\{TEAMS_OAUTH_REGISTRATION_ID\}', $oauthId } | Set-Content plugin-action.json

# 2. Pack \u2014 Cowork expects a zip with manifest.json at the root
Compress-Archive -Path manifest.json, plugin-action.json, color.png, outline.png -DestinationPath launch-control-cowork-plugin.zip -Force
```

Then in **Microsoft 365 Admin Center \u2192 Integrated apps \u2192 Upload custom apps**,
upload `launch-control-cowork-plugin.zip`. Publish to a small test audience
first. Open Cowork, **Add plugin \u2192 Launch Control**, click **Connect**,
complete the OAuth flow. The plugin should now appear in the connected
list.

## Verify

Run the episode's preflight from the repo root:

```powershell
python episodes/ep-06-cowork-plugin/preflight.py --run
```

Checks P3 + P4 inspect this directory for `manifest.json`, an action JSON,
and the three required markers (`/api/mcp`, `OAuthPluginVault`,
`referenceId`).

## Hardening (post-validation)

In **Teams Developer Portal \u2192 OAuth registrations \u2192 \u003cyour registration\u003e \u2192
App restrictions**, change *Any Teams app* to **the specific Teams App ID**
from `manifest.json#id`. That restricts which custom plugin packages can
use this OAuth registration; it's the difference between "anyone in tenant
can build a plugin reusing this OAuth" and "only the published Launch
Control package can".

## Iconography

`color.png` (192x192) and `outline.png` (32x32 transparent) are required by
the Teams manifest but are **not** in source control \u2014 drop your own
brand icons here before packaging. The Teams validator will reject the
package if either is missing.
