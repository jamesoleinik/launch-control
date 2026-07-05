# Vendor-outsourcing model: build log and verification

This is the end-to-end record of how the WIDGET-Q3 vendor-outsourcing model was
built and made queryable through **both** Dataverse data APIs (OData Web API and
the SQL / TDS endpoint). It doubles as a runbook: the two scripts named here are
idempotent and safe to re-run.

- Build / seed: `python episodes/ep-09-dataverse-fno/seed_vendor_work.py`
- Verify both APIs: `python episodes/ep-09-dataverse-fno/verify_vendorwork.py`
- Verify the MCP path: `python episodes/ep-09-dataverse-fno/verify_mcp.py`

All identifiers below (env, vendors, POs) are demo values for the Launch Control
series. Resolve the environment from the episode `.env` (`LC_ENV=ep-09-dataverse-fno`);
nothing here is hardcoded in committed scripts.

## What was built

The launch model gains a first-class launch-to-procurement join:

```
lc_launch --< lc_task --< lc_vendorwork >-- F&O Vendor (V0001 / V0002 / V0003)
                                         >-- F&O PurchaseOrderHeader (PO-105xx)
```

- `lc_vendorwork` (real Dataverse table) has a real `lc_taskid` lookup to
  `lc_task`, plus the F&O business keys (`lc_vendoraccount`, `lc_ponumber`) and
  the money the launch team tracks (`lc_committedamount`, `lc_invoicedamount`,
  `lc_status`, `lc_duedate`).
- **6 outsourced engagements** for WIDGET-Q3, each linked to a real `lc_task` and
  a real F&O vendor + open PO, across **3 vendors**:

  | Task (lc_task) | Vendor | PO | Committed | Invoiced | Status |
  |---|---|---|--:|--:|---|
  | Translation vendor contract | Contoso Supply Co (V0001) | PO-10501 | 45,000 | 0 | PO open |
  | Launch video (90s) | Contoso Supply Co (V0001) | PO-10502 | 37,000 | 12,000 | Invoice pending |
  | Load test API at 5x peak | Contoso Supply Co (V0001) | PO-10503 | 28,000 | 28,000 | Invoiced (paid) |
  | Hero copy + visuals | Fabrikam Media (V0002) | PO-10504 | 22,000 | 8,000 | Invoice pending |
  | Quickstart tutorial | Fabrikam Media (V0002) | PO-10505 | 15,000 | 0 | PO open |
  | DPA addendum review | Northwind Legal Advisors (V0003) | PO-10506 | 18,000 | 18,000 | Invoiced (paid) |

  Totals: **165,000 committed, 66,000 invoiced, 99,000 open.**

## The two-API design decision

`lc_vendorwork` stores the F&O keys as its own string columns instead of a hard
Dataverse lookup to a virtual entity. That is deliberate and is what makes the
model queryable both ways:

- **OData Web API** can `$expand` / filter the generated `mserp_*` virtual
  entities, so the keys light up a **live** read of the real F&O vendor and PO.
- **SQL / TDS** does **not** expose virtual entities at all. Because the keys and
  amounts live on the real `lc_vendorwork` table, the same rows are fully
  queryable (and joinable to `lc_task` / `lc_launch`) over TDS.

One model, two endpoints, no reseed required when virtual entities are toggled on
or off.

## Build steps, in order (and the gotchas each one cost)

### 1. Generate the F&O virtual entities (Dataverse side, API-drivable)

Enabling F&O virtual tables is a **Dataverse** operation, not an ERP one. It is
driven off the `mserp_financeandoperationsentity` catalog table (the same catalog
exposed by Advanced Find > "Available finance and operations entities", where the
UI "Visible" checkbox maps to the `mserp_hasbeengenerated` flag). See
[Enable Dataverse virtual entities](https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/power-platform/enable-virtual-entities).

To generate an entity by API, PATCH its catalog row:

```
PATCH {DATAVERSE}/api/data/v9.2/mserp_financeandoperationsentities(<id>)
{ "mserp_hasbeengenerated": true }
```

Find `<id>` by filtering on `mserp_physicalname` (e.g. `VendVendorV2Entity`).

Gotchas:

- **Generation is async and serialized.** Firing PATCHes for several entities at
  once returns `PluginSqlLockManager failed to acquire lock` for all but one, and
  the winning PATCH's HTTP call often times out even though generation completes
  server-side a minute or two later. Do them **one at a time** and poll.
- **The entity-set name is not what you'd guess.** It is
  `mserp_<physicalname lowercased>` + `s`, for example:
  - `VendVendorV2Entity` -> `mserp_vendvendorv2entities` (NOT `mserp_vendorsv2`)
  - `PurchPurchaseOrderHeaderV2Entity` -> `mserp_purchpurchaseorderheaderv2entities`
  - `CurrencyEntity` -> `mserp_currencyentities`
  - `VendVendorGroupEntity` -> `mserp_vendvendorgroupentities`
  Probing the wrong set (e.g. `mserp_vendorsv2`) returns 404 and looks like a
  failed generation when it actually succeeded.
- **`startswith()` on EntityDefinitions returns 501** on this env
  (`The "startswith" function isn't supported for Metadata Entities`). A naive
  `.get("value", [])` reads that as empty. **Probe the entity set directly**
  (`GET /<entityset>?$top=1` -> 200 / 404) instead of filtering metadata.

Entities generated for this build: `VendVendorV2Entity`,
`PurchPurchaseOrderHeaderV2Entity`, `CurrencyEntity`, `VendVendorGroupEntity`.

### 2. Seed the F&O masters and open POs (direct OData writes)

`seed_vendor_work.py` writes directly to the F&O OData endpoint
(`{FNO}/data/...`), which is the reliable loader on a bare env (the DMF package
path can produce FK phantoms; see the README).

Gotchas:

- **Vendor create: use `VendorName`, not `VendorOrganizationName`.** Posting
  `VendorOrganizationName` to the `Vendors` entity (VendVendorV2Entity) fails with
  a deserialization `TargetInvocationException`; omitting the name fails
  `validateWrite` (`Field 'Name' must be filled in` on DirPartyTable). The working
  writable field for the org name is `VendorName`. Required body:
  `dataAreaId`, `VendorAccountNumber`, `VendorGroupId`, `VendorPartyType=Organization`,
  `CurrencyCode`, `VendorName`.
- **PO create needs `LanguageId`** (e.g. `en-us`) and a manually supplied
  `PurchaseOrderNumber` (no number sequence on a bare env). POs are open headers
  only: no released products / procurement categories exist, so there are no PO
  lines. The committed / invoiced amounts are carried on `lc_vendorwork`.
- **The F&O endpoint drops SSL intermittently.** All F&O calls go through a
  session with a small retry loop (5 tries, sleep 3).

### 3. Fix "System language is not specified" (one-time F&O env fix)

Opening a PO in the F&O client first failed with a system-language error. The
trigger was **`SystemParameters.SystemLanguage` empty**, not the user or legal
entity language. Fix (all three were set, the last is the one that mattered):

```
PATCH {FNO}/data/SystemParameters(0)            { "SystemLanguage": "en-us" }
PATCH {FNO}/data/LegalEntities('dat')           { "LanguageId": "en-us" }
PATCH {FNO}/data/SystemUsers('Admin')           { "Language": "en-us" }
```

Note the key is `SystemParameters(0)` (integer key), not `SystemParameters(ID='0')`.

### 4. Build `lc_vendorwork` and seed the join (Dataverse side)

`seed_vendor_work.py` creates the `lc_vendorwork` table (simple columns) via the
Python SDK, then adds the `lc_taskid` lookup to `lc_task`.

Gotcha: **lookup propagation lag.** Immediately after `create_lookup_field`, a POST
that binds `lc_taskid@odata.bind` can 400. The script retries the lookup create
(8 attempts, exponential backoff) and the seed upsert tolerates the race.

## Verification (both APIs)

`verify_vendorwork.py` runs both proofs and exits non-zero on any failure.

### OData Web API (live F&O join)

For each `lc_vendorwork` row it resolves the vendor via
`mserp_vendvendorv2entities?$filter=mserp_vendoraccountnumber eq '<acct>'` and the
PO via `mserp_purchpurchaseorderheaderv2entities?$filter=mserp_purchaseordernumber eq '<po>'`.
Result: **6/6 engagements resolve** to the real F&O vendor and PO (vendor account
on the PO matches the engagement).

### SQL / TDS endpoint

Connect to `{host},5558` with an Azure AD access token (the same Dataverse token,
passed via ODBC attribute `SQL_COPT_SS_ACCESS_TOKEN = 1256`), then run standard
T-SQL joins and `GROUP BY`.

**Critical gotcha: set `TrustServerCertificate=yes`.** With ODBC Driver 17,
`connect()` succeeds but the first `execute` fails with
`08S01 Communication link failure` unless `TrustServerCertificate=yes` is in the
connection string (the endpoint redirects to a backend node whose certificate
Driver 17 otherwise rejects). Driver 18 behaves the same way here; the flag fixes
both. The environment's TDS listener must be enabled
(`<TDSListenerInitialized>1</TDSListenerInitialized>` in the org settings on this
env).

Working connection string:

```
Driver={ODBC Driver 17 for SQL Server};Server=<host>,5558;Database=<host>;
Encrypt=yes;TrustServerCertificate=yes;
```

Proven query (returns 6 rows joined across three tables):

```sql
SELECT l.lc_code, t.lc_title, vw.lc_vendorname, vw.lc_ponumber,
       vw.lc_committedamount, vw.lc_invoicedamount, vw.lc_status
FROM lc_vendorwork vw
JOIN lc_task   t ON vw.lc_taskid  = t.lc_taskid
JOIN lc_launch l ON t.lc_launchid = l.lc_launchid
WHERE l.lc_code = 'WIDGET-Q3'
ORDER BY vw.lc_ponumber;
```

Both checks pass:

```
OData live join : PASS   (6/6 engagements resolve to live F&O vendor + PO)
SQL / TDS join  : PASS   (6 rows; vendor and launch rollups correct)
```

## Verification (Dataverse MCP server)

`verify_mcp.py` proves the same `lc_vendorwork` model is reachable through the
Dataverse **Model Context Protocol** endpoint, which is how a Copilot Studio or
VS Code agent reads the environment. It speaks the streamable-HTTP JSON-RPC
transport directly (no proxy needed for the test):

1. `initialize` and capture the `Mcp-Session-Id` response header, then send the
   `notifications/initialized` notification.
2. `tools/list` and assert the core tools are present (`read_query`, `describe`,
   `search`, `create_record`, `update_record`).
3. `tools/call read_query` for the launch procurement join and a GROUP BY vendor
   rollup.

```
MCP tools present    : PASS
MCP read_query join  : PASS   (6/6 engagements)
MCP GROUP BY rollup  : PASS   (3 vendors)
```

### Enabling the MCP server (one-time, Power Platform admin)

The endpoint (`<env>/api/mcp`) returns **403 Forbidden** until an admin enables it
and allowlists the calling client app. In the Power Platform admin center: select
the environment, then **Settings > Product > Features > Dataverse Model Context
Protocol**, turn on **Allow MCP clients to interact with Dataverse MCP server**,
open **Advanced Settings**, and set the relevant client records (for example
Microsoft GitHub Copilot) to **Is Enabled = Yes**. Enabling non-Microsoft clients
requires a Managed Environment. Reference:
https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable

Notes captured while wiring this up:

- The GA endpoint is `/api/mcp` (used by the `@microsoft/dataverse mcp` proxy at
  runtime); `/api/mcp_preview` is opt-in per environment. Both returned 200 once
  the clients were enabled here.
- GROUP BY results table-qualify the grouped column
  (`lc_vendorwork_lc_vendorname`, not `lc_vendorname`); the test script resolves any
  key ending in `lc_vendorname`.
- To use the MCP tools in-session, register a server against this env (for example
  `npx @microsoft/dataverse@latest mcp https://<env>.crm.dynamics.com` in the
  MCP config) and restart the CLI. The direct-HTTP test above needs no restart.

