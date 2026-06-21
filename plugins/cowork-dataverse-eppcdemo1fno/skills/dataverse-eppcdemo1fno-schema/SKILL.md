---
name: dataverse-eppcdemo1fno-schema
description: |
  Discover Dataverse logical names for tables and columns in the EPPCDemo1FnO
  environment (https://eppcdemo1fno.crm.dynamics.com/api/mcp_preview). Two entry points:
  (1) By table: user gives a display name or partial; returns the table
  logical name plus column logical names, types, and flags for lookup /
  choice / primary key.
  (2) By solution: user gives a solution friendly or unique name; returns
  every table in that solution and their column logical names.

  Trigger phrases: "what is the logical name for [table]", "schema for
  [table]", "describe [table]", "columns on [table]", "what tables are in
  the [solution] solution", "logical name for [field]".

  Do NOT use for: querying row data (use dataverse-eppcdemo1fno-mcp), schema
  modifications (admin task), or other environments (install a separate
  env-scoped plugin).
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# Dataverse Schema Explorer: EPPCDemo1FnO

Discovery helper for the **EPPCDemo1FnO** Dataverse environment. Resolves
display names to logical names so the user (or another skill) can build
accurate queries without guessing. This skill is read-only; it never returns
row data and never writes. For data queries use the `dataverse-eppcdemo1fno-mcp` skill in
the same plugin.

## When NOT to Use

- Querying actual row data: use `dataverse-eppcdemo1fno-mcp`.
- Creating, updating, or deleting tables / columns: admin task.
- Discovering data in other environments: install a separate env-scoped plugin.

## Two Entry Points

### A) By table (display or partial name)

1. Call `describe("tables/")` once per session and cache it. Match the input
   against `DisplayName`, `DisplayCollectionName`, and `LogicalName`; prefer
   an exact display-name match, fall back to case-insensitive contains. Use
   `search("<input>")` for fuzzy disambiguation.
2. If multiple candidates match, surface them and ask which one.
3. Call `describe("tables/<logical_name>")` on the resolved logical name.
4. Return the table summary plus a compact column table.

### B) By solution (friendly or unique name)

1. `execute(operation='read', query="SELECT solutionid, friendlyname,
   uniquename, version, ismanaged FROM solution WHERE friendlyname =
   '<input>'")`. If no match, retry with `WHERE uniquename = '<input>'`.
2. `execute(operation='read', query="SELECT objectid, componenttype FROM
   solutioncomponent WHERE _solutionid_value = '<solutionid>' AND
   componenttype = 1")` to list its entity components.
3. For each `objectid` (the table MetadataId), resolve the logical name via
   `describe("tables/<name>")` or the cached `describe("tables/")` result.
4. For each table, call `describe("tables/<logical_name>")` to enumerate
   columns.
5. Return a structured listing: solution, then tables, then columns.

## Output Format

For a single table, lead with the table (display + logical name) then a
compact column table: Display name, Logical name, Type, Required, Notes. For
lookups surface the target table logical name. For choices surface the option
count (full option list on request). For a solution, return the table list
first (each with column count); expand columns on request.

## Resolution Rules

- Prefer logical names in returned data, but show display names alongside.
- Lookup columns surface in OData as `_<name>_value`; the metadata logical
  name is unprefixed (`<name>`). Return the metadata form and note the OData
  form when relevant.
- Choice columns: return the option count by default; list values as
  `LogicalValue (Label)` on request.
- Flag custom prefixes (for example `cr<xxx>_`, `new_`) and the
  `IsCustomEntity` / `IsCustomAttribute` flags so the user knows what is custom.

## Caching

Within a session, cache `describe("tables/")` and per-table
`describe("tables/<name>")`. Do not cache across sessions; schema can change.

## Confirmation Gates

Read-only. If asked for a schema change (add column, rename), decline and
explain that schema is administered in the Power Platform maker portal, not
through Cowork.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| Table not found | Typo or display-name mismatch | Run `describe("tables/")` and offer the closest matches |
| Solution not found | Friendly vs unique name | Try the other name field; list candidate solutions |
| Permission denied on `solution` | User lacks System Customizer or similar | Surface the role requirement; do not retry |
| Large solution (>50 tables) | Big dump | Page output; return the table list first |

## Tone

Concise and technical. Lead with the table or column listing; explanations
come after the data.
