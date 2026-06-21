# Cowork plugin: Dataverse EPPCDemo1FnO (preview MCP)

A Microsoft 365 Cowork custom plugin that connects to the **EPPCDemo1FnO**
Dataverse environment through the preview Dataverse MCP endpoint and bundles
three skills, mirroring the Launch Control v2 plugin.

## Target environment

| Field | Value |
|---|---|
| Instance URL | `https://eppcdemo1fno.crm.dynamics.com/` |
| MCP endpoint (preview) | `https://eppcdemo1fno.crm.dynamics.com/api/mcp_preview` |
| Environment ID | `6551ba8c-5cc3-efc7-88a9-28b77011a319` |
| Organization ID | `8c3f2a44-3b68-f111-9bb3-6045bd003924` |
| Tenant ID | `01eed126-9f96-4d2d-a127-dc2e786a898b` |

## Bundled skills

| Skill | Purpose |
|---|---|
| `dataverse-eppcdemo1fno-schema` | Resolve display names to logical names for tables, columns, and solutions (read-only discovery). |
| `dataverse-eppcdemo1fno-mcp` | Read, search, create, and update rows via the preview `search / describe / execute` surface. |
| `dataverse-eppcdemo1fno-business-skills` | Discover and follow policy rows stored in the Dataverse `skill` table. |

## Unique app identities

This plugin has its own Teams app id (`manifest.id`) and its own Entra app
registration (created by `deploy/provision.py`). The OAuth `referenceId` in the
manifest binds to that env-specific Teams Developer Portal OAuth registration.

## Build

```powershell
cd plugins/cowork-dataverse-eppcdemo1fno
.\build.ps1 -OAuthReferenceId "<base64 referenceId from provision.py>"
# -> out/dataverse-eppcdemo1fno-cowork.zip
```

## Provision + connect

`deploy/provision.py` creates the unique Entra app, Dataverse application user,
MCP allowlist row, and the Teams OAuth registration for this environment, then
prints the `referenceId` to bake into the manifest. See `deploy/RUNBOOK.md` for
the portal-only steps (enable env-level Dataverse MCP, upload, connect, test,
harden).
