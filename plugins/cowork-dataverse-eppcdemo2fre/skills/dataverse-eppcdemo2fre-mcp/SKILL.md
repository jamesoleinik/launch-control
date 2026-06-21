---
name: dataverse-eppcdemo2fre-mcp
description: |
  Query and update Microsoft Dataverse records in the EppcDemo2FRE environment
  (https://eppcdemo2fre.crm.dynamics.com/api/mcp_preview) via the preview Dataverse MCP endpoint. Read, search,
  create, and update rows in standard Dataverse tables (account, contact,
  lead, opportunity, incident) and custom tables in this environment.

  Trigger phrases:
  - "look up the [record] for [name]"
  - "show me open [records]"
  - "find the [record] [name] in Dataverse"
  - "create a new [record] in Dataverse"
  - "update the [field] of [record]"
  - "what [records] are assigned to me"
  - "search Dataverse for [keyword]"
  - "list rows in the [table] table"

  Scope: the EppcDemo2FRE environment ONLY. Do NOT use for other Dataverse
  environments, SharePoint lists, Excel files, or Power BI artifacts.
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# Dataverse MCP: EppcDemo2FRE

Connects Microsoft 365 Copilot Cowork to the **EppcDemo2FRE** Dataverse
environment through the native Dataverse MCP server (connector
`dataverse-eppcdemo2fre`). Authentication flows through Cowork's OAuthPluginVault: users
sign in once with their own Dataverse identity and Dataverse security roles
enforce access. This plugin instance is scoped to EppcDemo2FRE only; for other
environments, install a separate plugin instance.

## When NOT to Use

- Other Dataverse environments: install a separate env-scoped plugin.
- Logical-name discovery or solution dumps: use `dataverse-eppcdemo2fre-schema`.
- Business policy questions (valid status transitions, approvals, escalation):
  use `dataverse-eppcdemo2fre-business-skills`, which loads the authoritative policy rows
  from the Dataverse `skill` table.
- SharePoint lists, Excel / CSV, or Power BI: use the matching native tool.

## Core Concepts

- **Table**: the Dataverse equivalent of a SQL table. Standard tables include
  `account`, `contact`, `opportunity`, `lead`, `incident` (case). Custom
  tables are named per the environment.
- **Row**: a single record, identified by a GUID primary key.
- **Column**: a single property on a row.
- **Lookup**: a relationship column pointing to a row in another table.
- **Choice**: an enum-style column with a fixed set of integer-backed values.

## Tool Use: preview MCP (search / describe / execute)

You have access to the Dataverse MCP server backed by the preview endpoint
`https://eppcdemo2fre.crm.dynamics.com/api/mcp_preview`. Every operation is routed through one of three tools via a
filesystem-style path:

- **`search`**: keyword search across the environment. Returns paths for table
  schemas (`tables/<name>`), Business Skills (`skills/<name>`), and Custom APIs
  (`api/<name>`). Use first to discover; never hard-code paths.
- **`describe`**: full details for any path returned by `search`.
  - `describe("tables/")`: list every table in the env.
  - `describe("tables/<name>")`: full schema (columns, types, relationships,
    example queries). Call before querying when column names are unknown.
  - `describe("tables/<name>/records/<guid>")`: full single record.
  - `describe("skills/<name>")`: full Business Skill body.
  - `describe("api/<name>")`: Custom API input parameters and response shape.
- **`execute`**: perform an operation against a path. The verb is one of:
  - `read`: SQL SELECT against `tables/`. Supports SELECT, TOP, WHERE, ORDER
    BY, GROUP BY, JOIN, aggregates. Does not support subqueries, HAVING,
    DISTINCT, UNION, OFFSET. Always pass a `TOP` bound (default 25 to 100, max
    1000).
  - `create` / `update` / `delete`: row CRUD on
    `tables/<name>/records[/{guid}]`. Destructive operations require
    `hasUserApproved: true` in the query body.
  - Custom API invocation: see below.

## Invoking Custom APIs (preview MCP)

Some workflows depend on Dataverse Custom APIs (unbound actions). The preview
MCP exposes them through the same three tools:

1. `search("<intent>")` surfaces the Custom API path (for example
   `api/<publisher>_<Name>`).
2. `describe("api/<name>")` returns the input parameters (case-sensitive) and
   response shape.
3. `execute` runs the action with those parameters.

Rules: never invent an action; only call ones surfaced by `search` or named in
a Business Skill body or user prompt. Always `describe` before `execute`.
Treat actions as side-effecting. Do not hand-compute a result an action is
meant to produce; if it errors, surface the error verbatim.

## Workflow

1. Resolve the table the user is asking about. If ambiguous, ask or call
   `search` to disambiguate.
2. Resolve people or entity references before querying.
3. `describe` before querying when columns are unknown. For pure schema
   questions defer to `dataverse-eppcdemo2fre-schema`; for policy questions defer to
   `dataverse-eppcdemo2fre-business-skills`.
4. `execute` with operation `read` using the smallest filter that satisfies the
   request; prefer server-side WHERE and TOP over fetching everything.
5. Page through when the user asks for "all" rows.
6. For writes, confirm the target row and the changes before executing.

## Output Format

- List queries: a compact table with the 4 to 6 most relevant columns.
- Single-row lookups: a key/value summary of important fields plus the id.
- Writes: confirm the operation and surface the new or updated row id and URL.

## Confirmation Gates

- Before any create, update, or delete: state the table, the row (by name and
  id), and the changes. Proceed only after explicit confirmation in the
  current turn.
- For bulk operations (more than 5 rows affected): always confirm.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| 401 / unauthorized | OAuth token expired or scope missing | User reconnects to the plugin in Cowork |
| 403 / forbidden | Security role lacks privilege on the table | Admin grants the role; not a plugin issue |
| 404 / row not found | Stale id or row deleted | Re-search by name |
| 400 / invalid column | Logical vs display name mismatch | Use the logical name from `describe("tables/<name>")` or `dataverse-eppcdemo2fre-schema` |
| `@odata.bind not supported` on create / update | Tried OData lookup bind syntax | The preview MCP does not accept `@odata.bind`; set the lookup attribute directly to the GUID string |
