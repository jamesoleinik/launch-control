---
name: dataverse-launchcontrol-mcp
description: |
  Query and update Microsoft Dataverse rows in the LaunchControl environment
  (https://org1077ae7c.crm.dynamics.com/api/mcp_preview) via the preview
  Dataverse MCP endpoint. The endpoint exposes a three-tool surface
  (search / describe / execute) with a limited SQL subset over standard and
  custom tables. Use this skill to read, search, create, and update rows on
  lc_* tables — and to answer launch readiness questions per the hard rule
  below.

  Trigger phrases:
  - "is [launch] ready to ship" / "go / no-go on [launch]"
  - "what's the readiness for [launch]"
  - "what's blocking [launch]"
  - "show me open tasks for [launch|milestone]"
  - "find the team member [name]"
  - "create a status update on [launch]"
  - "update [task] to [status]"
  - "search Dataverse for [keyword]"

  Scope: LaunchControl environment ONLY. Do NOT use for other Dataverse
  environments, SharePoint lists, Excel files, or Power BI artifacts.
license: MIT
metadata:
  author: Launch Control
  version: "1.4"
---

# Dataverse MCP — LaunchControl (preview)

Connects Microsoft 365 Copilot Cowork to the **LaunchControl** Dataverse
environment via the **preview MCP endpoint** `/api/mcp_preview`.
Authentication flows through Cowork's `OAuthPluginVault` — each user signs
in with their own Dataverse identity and Dataverse security roles enforce
access.

This plugin instance is **scoped to LaunchControl only**. For other
environments, install a separate plugin instance.

## When NOT to use

- Other Dataverse environments → install a separate env-scoped plugin
- SharePoint / Excel / Power BI → use the respective skills
- Schema discovery (column logical names, `$expand` nav properties) →
  use `dataverse-launchcontrol-schema`
- Business policy questions (status transitions, escalation, briefings) →
  use `dataverse-launchcontrol-business-skills`

## Tool surface — three consolidated tools

Every operation is routed through one of three tools via a filesystem-style
path. Do not invent tool names.

- **`search(query)`** — keyword search across the environment. Returns
  paths for table schemas (`tables/<name>`), Business Skills
  (`skills/<name>`), and Custom APIs (`api/<name>`). Use first to discover
  what's available; never hard-code paths.
- **`describe(path)`** — full details for any path returned by `search`.
  - `describe("tables/")` — list every table in the env
  - `describe("tables/<name>")` — full schema (columns, types,
    relationships, `$expand` nav properties, example queries). Always call
    before querying when column names are unknown.
  - `describe("tables/<name>/records/<guid>")` — full single record
  - `describe("skills/<name>")` — full Business Skill body
- **`execute(operation, path?, query)`** — perform an operation. The
  operation verb is one of `read`, `create`, `update`, `delete`, or one of
  the file ops (`initialize_upload`, `commit_upload`, `download`). For
  `create` / `update` / `delete`, pass `hasUserApproved: true` in the query
  body. Use the path conventions in the table below.

### Path conventions for `execute`

| Intent | `operation` | `path` | `query` |
|---|---|---|---|
| SELECT | `read` | _(omit)_ | SQL string |
| Insert row | `create` | `tables/<name>/records` | JSON object |
| Update row | `update` | `tables/<name>/records/<guid>` | JSON object |
| Delete row | `delete` | `tables/<name>/records/<guid>` | `{"hasUserApproved": true}` |
| Upload file column | `initialize_upload` → `commit_upload` | `file` | see preview MCP docs |

## Limited SQL subset (operation `read`)

The preview MCP accepts a **limited SQL dialect** over the path
`tables/`. Stay inside this subset:

**Supported**

- `SELECT`, `SELECT TOP n`
- `FROM <logical_table_name>` — always single table; resolve joins via
  the lookup-flattening idiom below
- `WHERE` — `=`, `<>`, `<`, `>`, `<=`, `>=`, `LIKE`, `IN`, `AND`, `OR`,
  `NOT`, `IS NULL`, `IS NOT NULL`
- `ORDER BY <col> [ASC|DESC]`
- `GROUP BY` with aggregates `COUNT`, `SUM`, `MIN`, `MAX`, `AVG`
- `JOIN ... ON` (small, lookup-driven joins only)

**Not supported** — work around with extra queries or use the schema skill's
`$expand` nav properties on the OData layer (not via this SQL surface):

- Subqueries (`SELECT … WHERE x IN (SELECT …)`)
- `HAVING`
- `DISTINCT`
- `UNION` / `UNION ALL`
- `OFFSET` / window functions / CTEs

**Always**

- Pass a `TOP` bound. Default 25–100. Hard cap 1000.
- Reference lookup columns by their underscore-prefixed OData attribute:
  `_lc_launchid_value`, not `lc_launchid` (the schema skill spells these
  out per table).
- Filter on choice columns by the **integer value**, not the label
  (e.g. `lc_taskstatus = 922960002` for "Blocked").

Example:

```sql
SELECT TOP 50 lc_taskid, lc_name, lc_taskstatus, lc_isblocked,
              _lc_launchid_value, _lc_milestoneid_value
FROM lc_task
WHERE lc_isblocked = true
ORDER BY modifiedon DESC
```

## Hard rule — launch readiness

**Readiness for a launch is sourced from exactly two places. Never
hand-tally milestones or improvise a score.**

1. **`lc_launch.lc_risksummary`** — the AI prompt column on `lc_launch`
   computed by the prompt registered in Episode 13. Treat its current
   value as the authoritative narrative for go / no-go, risks, and the
   recommended decision.
2. **The set of `lc_task` rows where `lc_isblocked = true`** scoped to the
   target launch (filter on `_lc_launchid_value`). Treat these as the
   authoritative list of blockers.

Canonical query pair for "is [launch X] ready":

```sql
-- 1. Risk narrative (authoritative)
SELECT TOP 1 lc_launchid, lc_name, lc_risksummary, lc_launchstatus,
             lc_targetshipdate
FROM lc_launch
WHERE lc_name = '<launch name>'
```

```sql
-- 2. Authoritative blocker list
SELECT TOP 100 lc_taskid, lc_name, lc_taskstatus, lc_isblocked,
                _lc_milestoneid_value, _lc_assignedtoid_value, modifiedon
FROM lc_task
WHERE _lc_launchid_value = '<launchid from query 1>'
  AND lc_isblocked = true
ORDER BY modifiedon DESC
```

Then answer:

- Lead with `lc_risksummary` verbatim (or a faithful condensation if too
  long for the response).
- List the blocked tasks underneath as the supporting evidence.
- If `lc_risksummary` is empty or stale (`modifiedon` older than the most
  recent task / milestone change), say so explicitly and recommend the
  user trigger a refresh — do **not** substitute a hand-rolled score.

What you **must not** do:

- Do not sum milestone statuses, count `lc_task` rows by status, or
  compute a percentage in the prompt and call it "the readiness score".
- Do not call any other Custom API as a readiness substitute. The
  preview MCP's three tools (`search` / `describe` / `execute`) plus the
  two columns above are the entire surface for readiness.
- Do not paraphrase `lc_risksummary` to soften its verdict.

The `dataverse-launchcontrol-business-skills` skill enforces the same rule
at the policy layer; if its body ever conflicts, ask the user which to
follow before answering.

## Workflow

1. **Resolve the table** the user is asking about. If ambiguous, ask or
   call `search` to disambiguate.
2. **Resolve people / launch / milestone references** to GUIDs before
   querying child tables.
3. **`describe("tables/<name>")` before querying** when columns aren't
   known. For repeated schema lookups defer to
   `dataverse-launchcontrol-schema`.
4. **`execute(operation='read', query=…)`** with the smallest filter that
   satisfies the request; prefer server-side `WHERE` + `TOP` over fetching
   everything.
5. **Page through** when the user asks for "all" rows (re-issue with a
   shifted `WHERE` clause, since `OFFSET` isn't supported).
6. **For writes**: confirm the target row and the changes before executing.
   Set lookup attributes directly to the GUID string
   (`"lc_launchid": "<guid>"`); the preview MCP does **not** accept
   `@odata.bind` syntax.

## Output format

- **Readiness questions**: lead with the `lc_risksummary` narrative, then
  the blocker table.
- **List queries**: compact table with the 4–6 most relevant columns.
- **Single-row lookups**: key/value summary.
- **Writes**: confirm the operation and surface the new/updated row's ID.

## Confirmation gates

- Before any **create**, **update**, or **delete**: state the table, the
  row (by name + ID), and the changes. Proceed only after explicit
  confirmation in the current turn.
- For bulk writes (>5 rows affected): always confirm.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| 401 / unauthorized | OAuth token expired or scope missing | User re-consents to the plugin in Cowork |
| 403 / forbidden | Dataverse security role lacks privilege | Admin grants the role |
| 404 / row not found | Stale ID or row deleted | Re-search by name |
| 400 / invalid column | Logical-vs-display name mismatch | Use the logical name from `describe("tables/<name>")` |
| `@odata.bind not supported` | Tried OData bind syntax on create/update | Set lookup attribute directly to the GUID string |
| `subquery not supported` / `HAVING not supported` | SQL outside the limited subset | Split into two reads or use the schema skill's `$expand` guidance |
