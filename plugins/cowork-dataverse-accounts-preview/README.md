# Cowork plugin: Dataverse Accounts (Preview)

The preview-endpoint twin of `plugins/cowork-dataverse-accounts`. Identical
behavior (one read-only `list my accounts` skill over the standard `account`
table) but the MCP connector points at the **preview** endpoint
`/api/mcp_preview` instead of GA `/api/mcp`.

## Why a separate package

A Cowork plugin's connector URL is fixed in the manifest, so GA vs preview is
a per-package choice. This package is a sibling so you can install either (or
both, side by side) without editing the GA package.

## What it reuses from the GA package

No new tenant setup is required. This package reuses everything
`plugins/cowork-dataverse-accounts/deploy/deploy.py` already provisioned:

| Shared item | Value |
|---|---|
| Entra app (client) ID | `d037e0d1-c923-4bcb-9b66-547423399d76` |
| Dataverse app user + allowlist row | `new_coworkaccountsmcp` |
| Teams OAuth registration | config id `8d95fc56-8524-4f41-9dde-cece82045517` |
| OAuth referenceId (in this manifest) | `MDFlZWQx...NTE3=` (base64) |

The OAuth registration's base URL is the org root
(`https://org77c9659c.crm.dynamics.com`), which is a prefix of both
`/api/mcp` and `/api/mcp_preview`, so the **same** `referenceId` authorizes
this package too.

## Differences from the GA package

| | GA package | This (preview) package |
|---|---|---|
| Folder | `cowork-dataverse-accounts` | `cowork-dataverse-accounts-preview` |
| MCP endpoint | `/api/mcp` | `/api/mcp_preview` |
| Teams App ID (`manifest.id`) | `d8fb9683-...` | `5ed1525b-48f5-49a4-9431-6333dcd4983d` |
| Skill | endpoint-agnostic | preview 3-tool surface (search / describe / execute read) |

## Build + deploy

```powershell
cd plugins/cowork-dataverse-accounts-preview
.\build.ps1
# -> out/dataverse-accounts-preview-cowork.zip
```

Then follow the same portal steps in
`plugins/cowork-dataverse-accounts/deploy/RUNBOOK.md` (enable env-level
Dataverse MCP, upload the zip, Connect in Cowork, test). The preview endpoint
requires the env-level Dataverse MCP feature to be enabled, same as GA.

## Hardening note

The shared OAuth registration is currently `applicableToApps: AnyApp`, so both
the GA and preview Teams App IDs can use it. If you harden it to a single
`SpecificApp`, point it at the package you actually ship, or register a second
OAuth client for the other package.

## Re-uploads

Cowork caches packages. Bump `version` in `manifest.json` (and the `id` GUID if
behavior still does not change), rebuild, re-upload, and re-add the plugin.
