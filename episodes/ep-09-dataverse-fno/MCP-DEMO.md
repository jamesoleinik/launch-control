# Episode 9 demo: read, write, and a recurring batch job across the unified model

This is the runnable spine of the Episode 9 demo. The launch plan lives in
Dataverse (`lc_*`) and the vendor / purchase-order money lives in Dynamics 365
Finance & Operations. Because they now sit on one platform, an agent can **read**
both from a single MCP endpoint, **write** to each side, and a scheduled job can
keep the picture current. Three scripts prove each pillar, all idempotent and all
exiting non-zero on failure.

| Pillar | Script | What it proves |
| --- | --- | --- |
| a. Read the unified model via MCP | `verify_mcp.py` | The Dataverse MCP server returns the launch-to-procurement join and rollups |
| b. Write to F&O and to Dataverse | `write_fno.py`, `erp_mcp_write.py` | A new PO lands in F&O and a new engagement lands in Dataverse via MCP, then both read back through the unified endpoint |
| c. Recurring batch job (unified CLI + GitHub) | `batch_launch_sync.py`, `.github/workflows/nightly-launch-procurement.yml` | A scheduled job uses the unified Dataverse CLI to digest outstanding vendor commitments nightly |

All identifiers are demo values. Resolve the environment from the episode `.env`
(`LC_ENV=ep-09-dataverse-fno`); nothing here hardcodes an env URL, tenant, or user.

## Prerequisite: enable the Dataverse MCP server

The MCP endpoint (`<env>/api/mcp`) is 403 until a Power Platform admin enables it
and allowlists the calling client app: Power Platform admin center > the
environment > Settings > Product > Features > **Dataverse Model Context
Protocol** > turn on **Allow MCP clients to interact with Dataverse MCP server**,
then in **Advanced Settings** set the client records you use (for example
Microsoft GitHub Copilot) to **Is Enabled = Yes**. Non-Microsoft clients require a
Managed Environment. The unified CLI can allowlist an app id directly:

```
dataverse mcp allow <appId>            # Dataverse MCP client allow-list
dataverse mcp allow <appId> --erp      # F&O (ERP) MCP client allow-list
```

Reference: https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable

## a. Read the unified model through the Dataverse MCP server

```
python episodes/ep-09-dataverse-fno/verify_mcp.py
```

Initializes an MCP session, lists tools, and calls `read_query` for the launch
procurement join and a GROUP BY vendor rollup. See `VENDORWORK-BUILD.md` for the
full read design (this doc focuses on write and batch).

## b. Write to F&O and to Dataverse

### Two write paths, and one that does not work

There are two servers in play, and only some writes go through each:

- **Dataverse MCP server** (`<env>/api/mcp`, remote HTTP). Its `create_record` /
  `update_record` tools write **real Dataverse tables** such as `lc_vendorwork`.
  They **cannot** write the F&O `mserp_*` virtual entities: the platform rejects
  it with *"Custom plugin execution is not allowed in nested pipeline for Virtual
  Entity."* So the launch side is writable over MCP; the F&O side is not, through
  this server.
- **F&O (ERP) MCP server** (`dataverse mcp <fno-operations-url>`, a **local stdio**
  server the unified CLI hosts). It routes to Finance & Operations and its tools
  write F&O through the F&O business APIs. F&O has **no standalone HTTP MCP
  endpoint** (`<fno>/api/mcp` is 404), so the only way to reach it from code is
  over the CLI process's stdin/stdout. This is the same "Dynamics 365 ERP MCP"
  tool an agent uses in Copilot Studio.

### `write_fno.py` (the tested end-to-end write)

```
python episodes/ep-09-dataverse-fno/write_fno.py           # create
python episodes/ep-09-dataverse-fno/write_fno.py --cleanup # undo, replayable
```

It (1) creates a new purchase order in F&O through the F&O OData API (the exact
operation the ERP MCP tool wraps), (2) creates the matching `lc_vendorwork`
engagement through the **Dataverse MCP `create_record` tool** (a genuine agent
write over MCP), linked to a real WIDGET-Q3 task, then (3) reads both back through
the unified Dataverse MCP `read_query` (the PO via the `mserp_` virtual entity,
the engagement via `lc_vendorwork`). All four checks pass and the run is
idempotent.

### `erp_mcp_write.py` (the literal ERP MCP transport)

```
python episodes/ep-09-dataverse-fno/erp_mcp_write.py           # list ERP MCP tools
python episodes/ep-09-dataverse-fno/erp_mcp_write.py --write   # create a PO via ERP MCP
```

Spawns `dataverse mcp <fno-url>` and drives it over stdio. The ERP MCP server
authenticates through the unified CLI's own auth profile (an MSAL token cache),
not a bearer token, so it needs a profile whose environment is this one:

```
dataverse auth create --environment <dataverse-url>        # interactive
dataverse auth create --environment <dataverse-url> -dc    # device code
```

Without a matching profile the server blocks on interactive sign-in; the script
detects this within a bounded wait, prints the CLI stderr and the exact
`auth create` command to run, and exits non-zero. Run it once interactively (or
point the CLI at a service-principal profile) for the live ERP-MCP write; the
underlying write is already proven by `write_fno.py`.

## c. Recurring batch job: unified Dataverse CLI + GitHub

```
python episodes/ep-09-dataverse-fno/batch_launch_sync.py            # via MCP (local)
python episodes/ep-09-dataverse-fno/batch_launch_sync.py --via cli  # via unified CLI (CI)
python episodes/ep-09-dataverse-fno/batch_launch_sync.py --out digest.json
```

`batch_launch_sync.py` reads the unified launch-plus-procurement model and emits a
per-launch digest: engagements, vendors, committed, invoiced, outstanding, open
POs, and an AT-RISK flag when outstanding commitment is at least half of the
committed total. The same logic runs two ways: `--via mcp` (the Dataverse MCP
server, no CLI profile needed) for a laptop run, and `--via cli` (the unified
`dataverse data query --sql ... --json`) for CI.

`.github/workflows/nightly-launch-procurement.yml` schedules it (`cron: 0 6 * * *`).
The workflow installs the unified Dataverse CLI, authenticates it with **GitHub
OIDC federated credentials** (`dataverse auth create --githubFederated`, no repo
secrets), monitors F&O batch jobs with `dataverse erp batch list`, runs the digest
with `--via cli`, and uploads the JSON as an artifact. One-time setup (Entra app +
application user + federated credential + repo variables `DATAVERSE_URL`,
`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`) is described in the workflow header.

To run it on a Windows box instead of GitHub, register the same script with Task
Scheduler:

```
schtasks /Create /SC DAILY /ST 06:00 /TN "LaunchProcurementDigest" ^
  /TR "powershell -NoProfile -Command \"$env:PYTHONIOENCODING='utf-8'; python <repo>\episodes\ep-09-dataverse-fno\batch_launch_sync.py --out <repo>\digest.json\""
```

## The unified Dataverse CLI, in one place

The `@microsoft/dataverse` CLI is the single tool behind all three pillars:

| Command | Used for |
| --- | --- |
| `dataverse mcp <dataverse-url>` | Host the Dataverse MCP server (read pillar) |
| `dataverse mcp <fno-url>` | Host the F&O (ERP) MCP server (write pillar) |
| `dataverse mcp allow <appId> [--erp]` | Allowlist an MCP client app |
| `dataverse data query --sql ... --json` | Read the unified model in the batch job |
| `dataverse data create/update` | Write records from scripts or CI |
| `dataverse erp batch list` | Monitor Finance & Operations batch jobs |
| `dataverse auth create --githubFederated` | CI auth with no stored secret |
