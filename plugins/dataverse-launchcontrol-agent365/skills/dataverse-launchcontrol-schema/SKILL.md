---
name: dataverse-launchcontrol-schema
description: |
  Authoritative schema reference for the lc_* tables in the LaunchControl
  Dataverse environment. Resolves table + column logical names and lists
  the case-sensitive $expand navigation properties needed to traverse
  lookups via the OData layer or the preview MCP's describe tool.

  Two entry points:
  (1) By lc_* table — return the entity set, schema name, lookup columns,
      and case-sensitive $expand nav properties.
  (2) By solution — list every table in a solution and forward to entry
      point (1) per table.

  Trigger phrases: "what's the logical name for [table]", "schema for
  [table]", "describe lc_task", "columns on lc_milestone", "what tables
  are in the LaunchControl solution", "how do I $expand the owner on
  lc_task", "what nav property points lc_task at lc_launch".

  Do NOT use for: querying row data (use dataverse-launchcontrol-mcp),
  schema modifications (admin task), or other environments (install a
  separate env-scoped plugin).
license: MIT
metadata:
  author: Launch Control
  version: "1.4"
---

# Dataverse Schema Explorer — LaunchControl

Schema-only helper for the **LaunchControl** environment. Resolves
display ↔ logical names and — critically — surfaces the **case-sensitive**
navigation property names used in `$expand` clauses. Dataverse will reject
a mis-cased nav (e.g. `lc_githubissueid` vs `lc_GitHubIssueId`) with a
400, so the per-table catalog below is the source of truth.

This skill never returns row data and never writes. For data queries use
`dataverse-launchcontrol-mcp`.

## When NOT to use

- Querying actual row data → `dataverse-launchcontrol-mcp`
- Creating, updating, or deleting tables / columns → admin task in the
  maker portal
- Other environments → install a separate env-scoped plugin

## lc_* table catalog (case-sensitive `$expand` nav properties)

Each entry lists: entity set (use this in OData URLs), schema name, key
lookup columns, and the **exact** nav property names accepted in
`$expand`. Standard system lookups (`createdby`, `modifiedby`,
`owninguser`, `owningteam`, `owningbusinessunit`, `createdonbehalfby`,
`modifiedonbehalfby`) are present on every custom table; they are listed
once below and omitted from the per-table sections to keep them scannable.

**Standard system lookups (all `lc_*` tables)** — case-sensitive:
`createdby`, `createdonbehalfby`, `modifiedby`, `modifiedonbehalfby`,
`owninguser`, `owningteam`, `owningbusinessunit`.

### `lc_launch` (entity set `lc_launchs`, schema `lc_Launch`)

A product or feature launch. Root of the LaunchControl model.

| Lookup attribute | Target table | `$expand` nav property |
|---|---|---|
| `lc_ownerid` | `lc_teammember` | `lc_ownerid` |

Notable AI prompt column: **`lc_risksummary`** — authoritative readiness
narrative (see the `dataverse-launchcontrol-mcp` skill's hard rule).

Example `$expand`:

```
GET /api/data/v9.2/lc_launchs(<guid>)?$expand=lc_ownerid($select=lc_name,lc_email)
```

### `lc_milestone` (entity set `lc_milestones`, schema `lc_Milestone`)

A milestone on a launch (e.g. "Code complete", "Marketing ready").

| Lookup attribute | Target table | `$expand` nav property |
|---|---|---|
| `lc_launchid` | `lc_launch` | `lc_launchid` |
| `lc_ownerid` | `lc_teammember` | `lc_ownerid` |
| `lc_sourcestagingcid` | `lc_stg_tracker_c` | `lc_sourcestagingcid` |
| `lc_sourcestagingeid` | `lc_stg_tracker_e` | `lc_sourcestagingeid` |

Example `$expand`:

```
GET /api/data/v9.2/lc_milestones?$select=lc_name,lc_milestonestatus&$expand=lc_launchid($select=lc_name),lc_ownerid($select=lc_name)
```

### `lc_task` (entity set `lc_tasks`, schema `lc_Task`)

A task under a milestone (or directly under a launch). The `lc_isblocked`
boolean is the authoritative blocker flag (see the MCP skill's hard rule).

| Lookup attribute | Target table | `$expand` nav property (case matters) |
|---|---|---|
| `lc_milestoneid` | `lc_milestone` | `lc_milestoneid` |
| `lc_launchid` | `lc_launch` | `lc_launchid` |
| `lc_assignedtoid` | `lc_teammember` | `lc_assignedtoid` |
| `lc_githubissueid` | `lc_githubissue` | **`lc_GitHubIssueId`** *(Pascal-cased — verbatim)* |
| `lc_sourcestagingaid` | `lc_stg_tracker_a` | `lc_sourcestagingaid` |
| `lc_sourcestagingbid` | `lc_stg_tracker_b` | `lc_sourcestagingbid` |
| `lc_sourcestagingdid` | `lc_stg_tracker_d` | `lc_sourcestagingdid` |

> **Watch the casing on `lc_GitHubIssueId`.** It's the only lc_* nav that
> is not all-lowercase; the attribute logical name is `lc_githubissueid`
> but the relationship's referencing-entity navigation property is
> `lc_GitHubIssueId`. `$expand=lc_githubissueid(...)` returns 400.

Example `$expand`:

```
GET /api/data/v9.2/lc_tasks?$select=lc_name,lc_taskstatus,lc_isblocked
  &$filter=_lc_launchid_value eq <guid> and lc_isblocked eq true
  &$expand=lc_milestoneid($select=lc_name),lc_assignedtoid($select=lc_name),lc_GitHubIssueId($select=lc_number,lc_title,lc_url)
```

### `lc_statusupdate` (entity set `lc_statusupdates`, schema `lc_StatusUpdate`)

A narrative status update authored by a team member, scoped to a launch /
milestone / task.

| Lookup attribute | Target table | `$expand` nav property |
|---|---|---|
| `lc_launchid` | `lc_launch` | `lc_launchid` |
| `lc_milestoneid` | `lc_milestone` | `lc_milestoneid` |
| `lc_taskid` | `lc_task` | `lc_taskid` |
| `lc_authorid` | `lc_teammember` | `lc_authorid` |

### `lc_teammember` (entity set `lc_teammembers`, schema `lc_TeamMember`)

A person (typically backed by a `systemuser`) who can own launches /
milestones / tasks. No business lookups beyond the standard system set.

### `lc_githubissue` (entity set `lc_githubissues`, schema `lc_GitHubIssue`)

GitHub issue mirror (number, title, state, URL). Read-only from the
plugin's perspective; written by the GitHub ingest flow.

No business lookups beyond the standard system set. **Note**:
`lc_task` points at this table through the Pascal-cased
`lc_GitHubIssueId` nav property (see `lc_task` above).

### `lc_githubdatasource` (entity set `lc_githubdatasources`, schema `lc_GitHubDataSource`)

Virtual-entity data source registration backing the GitHub mirror.
Operationally read-only. No business lookups beyond the standard
system set.

### `lc_scoutskill` (entity set `lc_scoutskills`, schema `lc_ScoutSkill`)

Holding table for Launch Risk Scout's heuristic rules. No business
lookups beyond the standard system set.

## Entry point A — by lc_* table

User input: "what columns are on lc_task" / "schema for lc_milestone" /
"how do I expand the owner on lc_launch".

Workflow:

1. Match the user's input against the catalog above. If they gave a
   display name, map it to the lc_* logical name first.
2. Surface the entity set, schema name, and lookup table.
3. If they asked about a specific nav property, return the **exact**
   case-sensitive name from the catalog. Never paraphrase casing.
4. For column-level detail beyond what's in the catalog, fall through to
   `describe("tables/<lc_logical_name>")` via the MCP skill and merge the
   results.

## Entry point B — by solution

User input: "what tables are in the LaunchControl solution" / "list
everything in solution lc_core".

Workflow:

1. `execute(operation='read', query="SELECT solutionid, friendlyname,
   uniquename, version, ismanaged FROM solution WHERE friendlyname =
   '<input>'")` — fall back to `uniquename` if no match.
2. `execute(operation='read', query="SELECT objectid, componenttype
   FROM solutioncomponent WHERE _solutionid_value = '<solutionid>'
   AND componenttype = 1")` — `componenttype = 1` filters to entities.
3. For each `objectid` (MetadataId), resolve to a logical name and
   forward to entry point A.

## Resolution rules

- **Always prefer logical names** in returned data; show display names
  alongside.
- **Lookup columns on the OData layer** are exposed as
  `_<attr>_value` (e.g. `_lc_launchid_value`). The metadata logical
  name is unprefixed (`lc_launchid`). The `$expand` nav property is
  also unprefixed *but case-sensitive* — refer to the catalog above.
- **Choice columns**: return `LogicalValue (Label)` rows on request.
  For `lc_taskstatus`, `lc_milestonestatus`, `lc_launchstatus` see the
  status-transition skill in the business-skills catalog.
- **Custom prefixes** (`lc_`, `cr88d_`, `new_`) — surface them clearly.

## Caching

Within a single session:

- The lc_* catalog above is static for the duration of the session;
  reuse it without re-fetching.
- Cache `describe("tables/<name>")` results per table.
- Do **not** cache across sessions — schema can change.

## Confirmation gates

- Read-only skill. No confirmations required.
- If a user asks for a schema change (add column, rename, etc.),
  decline and refer them to the maker portal.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| Table not found | Typo or display-name mismatch | Offer the closest catalog match |
| 400 on `$expand` | Wrong casing on a nav property | Look up the case-sensitive nav in the catalog above (esp. `lc_GitHubIssueId`) |
| Solution not found | Friendly vs unique name confusion | Try the other name field |
| Permission denied on `solution` table | User lacks System Customizer | Surface the role requirement |

## Tone

Concise and technical. Lead with the table or nav property listing;
explanations come after the data.
