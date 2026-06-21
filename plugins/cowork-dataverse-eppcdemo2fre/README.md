# Cowork plugin: Dataverse EppcDemo2FRE (preview MCP)

A Microsoft 365 Cowork custom plugin that connects to the **EppcDemo2FRE**
Dataverse environment through the preview Dataverse MCP endpoint and bundles
three skills, mirroring the Launch Control v2 plugin.

## Target environment

| Field | Value |
|---|---|
| Instance URL | `https://eppcdemo2fre.crm.dynamics.com/` |
| MCP endpoint (preview) | `https://eppcdemo2fre.crm.dynamics.com/api/mcp_preview` |
| Environment ID | `083aad67-1129-e1df-b8e5-756fbf3a6e00` |
| Organization ID | `1401fdb8-d968-f111-9bb3-000d3a5cc31c` |
| Tenant ID | `01eed126-9f96-4d2d-a127-dc2e786a898b` |

## Bundled skills

| Skill | Purpose |
|---|---|
| `dataverse-eppcdemo2fre-schema` | Resolve display names to logical names for tables, columns, and solutions (read-only discovery). |
| `dataverse-eppcdemo2fre-mcp` | Read, search, create, and update rows via the preview `search / describe / execute` surface. |
| `dataverse-eppcdemo2fre-business-skills` | Discover and follow policy rows stored in the Dataverse `skill` table. |

## Unique app identities

This plugin has its own Teams app id (`manifest.id`) and its own Entra app
registration (created by `deploy/provision.py`). The OAuth `referenceId` in the
manifest binds to that env-specific Teams Developer Portal OAuth registration.

## Build

```powershell
cd plugins/cowork-dataverse-eppcdemo2fre
.\build.ps1 -OAuthReferenceId "<base64 referenceId from provision.py>"
# -> out/dataverse-eppcdemo2fre-cowork.zip
```

## Provision + connect

`deploy/provision.py` creates the unique Entra app, Dataverse application user,
MCP allowlist row, and the Teams OAuth registration for this environment, then
prints the `referenceId` to bake into the manifest. See `deploy/RUNBOOK.md` for
the portal-only steps (enable env-level Dataverse MCP, upload, connect, test,
harden).
