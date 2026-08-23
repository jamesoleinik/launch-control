---
name: dataverse-launchcontrol-schema
description: |
  Discover Dataverse logical names for tables and columns in the
  LaunchControl environment. Two entry points:
  (1) By table: user gives a display name or partial; returns the
  table logical name plus column logical names, types, and flags for
  lookup / choice / primary key.
  (2) By solution: user gives a solution friendly or unique name;
  returns every table in that solution and their column logical names.

  Trigger phrases: "what's the logical name for [table]", "schema for
  [table]", "describe [table]", "columns on [table]", "what tables are
  in the [solution] solution", "logical name for [field]", "give me
  the schema for solution [name]".

  Do NOT use for: querying row data (use the dataverse-launchcontrol-mcp skill),
  schema modifications (admin task), or other environments (use a
  separate env-scoped plugin).
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# Dataverse Schema Explorer: LaunchControl

Discovery helper for the **LaunchControl** Dataverse environment.
Resolves display names to logical names so the user (or another skill)
can build accurate queries without guessing.

This skill is intentionally schema-only: it never returns row data
and never writes. For data queries, use the `dataverse-launchcontrol-mcp`
skill in the same plugin.

## When NOT to Use

- Querying actual row data → `dataverse-launchcontrol-mcp` skill
- Creating, updating, or deleting tables / columns → admin task
- Discovering data in other environments → install a separate
  env-scoped plugin

## Two Entry Points

### A) By table (display or partial name)

User input: "what columns are on the Account table" / "schema for
inspections" / "show me the contact table fields".

Workflow:
1. Call `describe("tables/")` once per session and cache the result.
   Match the user's input against `DisplayName`,
   `DisplayCollectionName`, and `LogicalName`: prefer exact
   display-name match, fall back to case-insensitive contains. Use
   `search("<input>")` for fuzzy disambiguation.
2. If multiple candidates match, surface them and ask which one.
3. Call `describe("tables/<logical_name>")` on the resolved logical name.
4. Return the table summary plus a compact column table.

### B) By solution (friendly or unique name)

User input: "list everything in the Sales Hub solution" / "what tables
are in solution kavora_core".

Workflow:
1. Use `execute(operation='read', query='SELECT solutionid, friendlyname,
   uniquename, version, ismanaged FROM solution WHERE friendlyname =
   ''<input>''')` to resolve the solution. If no match, retry with
   `WHERE uniquename = '<input>'`.
2. Use `execute(operation='read', query='SELECT objectid, componenttype
   FROM solutioncomponent WHERE _solutionid_value = ''<solutionid>'' AND
   componenttype = 1')` to list its entity components.
3. For each `objectid` (the table's MetadataId), resolve the table
   logical name via `describe("tables/<name>")` or by matching against
   the cached `describe("tables/")` result.
4. For each resolved table, call `describe("tables/<logical_name>")`
   to enumerate columns.
5. Return a structured listing: solution → tables → columns.

## Output Format

### For a single table

> **Account** (`account`)
> *Display collection:* Accounts · *Ownership:* User-owned · *Custom:* No
>
> | Display name      | Logical name        | Type        | Required | Notes        |
> |-------------------|---------------------|-------------|----------|--------------|
> | Account Name      | `name`              | String      | Yes      | Primary name |
> | Account ID        | `accountid`         | Uniqueidentifier | Yes | Primary key  |
> | Primary Contact   | `primarycontactid`  | Lookup → contact | No  | Lookup       |
> | Account Status    | `statuscode`        | Choice      | No       | 7 options    |

For lookup columns, surface the **target table** logical name.
For choice columns, surface the **option count** (and the full option
list on request).

### For a solution

> **Sales Hub** (`sales_hub`, v1.0.0.5, managed)
>
> Tables (5):
> - **Account** (`account`): 47 columns
> - **Contact** (`contact`): 32 columns
> - **Opportunity** (`opportunity`): 41 columns
> - **Lead** (`lead`): 38 columns
> - **Case** (`incident`): 29 columns
>
> Reply with a table name to see its columns, or "all columns" to get
> the full schema dump.

Default to the table-list view first: full column dumps for every
table in a solution can be hundreds of rows.

## Resolution Rules

- **Always prefer logical names in returned data**, but show display
  names alongside so the user can pick the right column.
- **Lookup columns** in Dataverse have a logical name prefixed with
  underscore in OData (`_primarycontactid_value`) but the metadata
  logical name is unprefixed (`primarycontactid`). Return the metadata
  form and note the OData form when relevant.
- **Choice columns**: by default return the option count. If the user
  asks for values, list them as `LogicalValue (Label)` rows.
- **Custom prefixes** (e.g. `cr88d_`, `new_`): surface them
  clearly so the user knows they're custom.
- **System vs custom**: flag `IsCustomEntity` /
  `IsCustomAttribute` in the output.

## Caching

Within a single session:
- Cache `describe("tables/")` after the first call.
- Cache `describe("tables/<name>")` results per table after the first call.
- Do NOT cache across sessions: schema can change.

## Confirmation Gates

- This skill is read-only. No confirmations required.
- If a user asks for a schema change (add column, rename, etc.),
  decline and explain that schema is administered through the
  Power Platform maker portal, not through Cowork.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| Table not found | Typo or display-name mismatch | Run `describe("tables/")` and offer the 3 closest matches |
| Solution not found | Friendly name vs unique name confusion | Try the other name field; list candidate solutions |
| Permission denied on `solution` table | User lacks System Customizer / similar role | Surface the role requirement; do not retry |
| Many tables in solution (>50) | Large solution dump | Page output; return the table list first, expand columns on request |

## Tone

Concise and technical. Audience is usually a maker or developer
building a query: they want logical names fast, not prose. Lead
with the table or column listing; explanations come after the data.
