# Cowork plugin: Dataverse Accounts (sample)

A minimal Microsoft 365 Cowork custom plugin that connects to the **Dataverse
MCP server** for a single environment and answers questions about the standard
`account` table. It is the "simple" counterpart to the Launch Control episode 6
plugin: one environment, one read-only Business Skill (`list my accounts`), no
custom schema.

## Target environment

| Field | Value |
|---|---|
| Instance URL | `https://org77c9659c.crm.dynamics.com/` |
| MCP endpoint | `https://org77c9659c.crm.dynamics.com/api/mcp` |
| Tenant ID | `01eed126-9f96-4d2d-a127-dc2e786a898b` |
| Environment ID | `5af9d25e-9d3c-ea33-83a7-e8001dfa6508` |
| Organization ID | `e616ec95-4b6b-f111-9bb1-000d3a31ff0e` |

## What is in the package

| File | Purpose |
|---|---|
| `manifest.json` | devPreview Teams manifest: `agentConnectors[]` points at the MCP endpoint with `OAuthPluginVault`; `agentSkills[]` bundles the skill. The `referenceId` is the placeholder `__OAUTH_REFERENCE_ID__` until `build.ps1` substitutes the real value. |
| `skills/list-my-accounts/SKILL.md` | The read-only `account`-table Business Skill. |
| `color.png`, `outline.png` | Required plugin icons. |
| `build.ps1` | Substitutes the OAuth `referenceId` and zips the package. |
| `deploy/` | The scriptable tenant setup (Entra app, Dataverse app user, MCP allowlist, Teams OAuth registration) plus a read-only preflight and the portal runbook. |

## End-to-end flow

1. `deploy/deploy.py` runs the scriptable tenant setup and prints the OAuth
   `referenceId`.
2. `build.ps1 -OAuthReferenceId <value>` produces `out/dataverse-accounts-cowork.zip`.
3. `deploy/preflight.py --run` confirms the package wiring and Dataverse
   reachability are green.
4. `deploy/RUNBOOK.md` covers the portal-only steps: upload, publish, connect in
   Cowork, test "list my accounts", and harden the OAuth registration.

## Re-uploads

Cowork caches packages. Bump `version` in `manifest.json` (and the `id` GUID if
behavior still does not change) on every re-upload, then remove and re-add the
plugin in Cowork.
