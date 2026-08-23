---
name: dataverse-launchcontrol-mcp
description: |
  Query and update Microsoft Dataverse records in the LaunchControl
  environment (https://org40ae6a46.crm.dynamics.com/api/mcp) via the native Dataverse MCP endpoint.
  Read, search, create, and update rows in standard Dataverse tables
  (account, contact, lead, opportunity, case) and custom tables in this
  environment.

  Trigger phrases:
  - "look up the account for [name]"
  - "show me open opportunities"
  - "find the contact [name] in Dataverse"
  - "create a new case in Dataverse"
  - "update the status of [record]"
  - "what cases are assigned to me"
  - "search Dataverse for [keyword]"
  - "list rows in the [table] table"

  Scope: LaunchControl environment ONLY. Do NOT use for other Dataverse
  environments, SharePoint lists, Excel files, or Power BI artifacts.
license: MIT
metadata:
  author: Launch Control
  version: "1.3"
---

# Dataverse MCP: LaunchControl

Connects Microsoft 365 Copilot Cowork to the **LaunchControl** Dataverse
environment through the native Dataverse MCP server. Authentication flows
through Cowork's OAuthPluginVault: users sign in once with their
own Dataverse identity and Dataverse security roles enforce access.

This plugin instance is **scoped to LaunchControl only**. For other
environments, install a separate plugin instance.

## When NOT to Use

- Other Dataverse environments → install a separate env-scoped plugin
- SharePoint lists or document libraries → use SharePoint tools
- Excel / CSV files → use the `xlsx` skill
- Power BI semantic models or reports → use Power BI tools
- Microsoft Lists (non-Dataverse) → use SharePoint tools

## Core Concepts

- **Table** (formerly entity): the Dataverse equivalent of a SQL table.
  Standard tables include `account`, `contact`, `opportunity`, `lead`,
  `incident` (case). Custom tables are named per the environment.
- **Row**: a single record in a table, identified by a GUID primary key.
- **Column** (formerly field/attribute): a single property on a row.
- **Lookup**: a relationship column pointing to a row in another table.
- **Choice** (formerly optionset): an enum-style column with a fixed set
  of integer-backed values.

## Tool Use: Dataverse MCP (preview endpoint)

You have access to the Dataverse MCP server (connector
`dataverse-launchcontrol`) backed by the **preview endpoint**
`/api/mcp_preview`. The server exposes **three consolidated tools** -
every operation is routed through one of them via a filesystem-style
path:

- **`search`**: keyword search across the environment. Returns
  filesystem-style paths for: table schemas (`tables/<name>`), Business
  Skills (`skills/<name>`), and Custom APIs (`api/<name>`: see the
  "Invoking Custom APIs" section). Use first to discover what's
  available; never hard-code paths.
- **`describe`**: get full details for any path returned by `search`.
  - `describe("tables/")`: list every table in the env
  - `describe("tables/<name>")`: full schema (columns, types,
    relationships, example queries) for a table; call before querying
    when column names, choice values, or relationships are unknown.
    Never assume column names.
  - `describe("tables/<name>/records/<guid>")`: full single record
  - `describe("skills/<name>")`: full Business Skill body
  - `describe("api/<name>")`: Custom API input parameters + response
    shape
- **`execute`**: perform an operation against a path. The operation
  verb is one of:
  - `read`: SQL SELECT against `tables/`. Supports SELECT, TOP,
    WHERE, ORDER BY, GROUP BY, JOIN, aggregates. Does **not** support
    subqueries, HAVING, DISTINCT, UNION, OFFSET. Always pass a `TOP`
    bound; default 25-100, max 1000.
  - `create` / `update` / `delete`: row CRUD on
    `tables/<name>/records[/{guid}]`; also creates/updates/deletes
    skills and tables themselves. **Destructive ops require
    `hasUserApproved: true` in the query body.**
  - File ops (`initialize_upload`, `commit_upload`, `download`) for
    `file` columns.
  - Custom API invocation: see the "Invoking Custom APIs" section
    below.

## Invoking Custom APIs (preview MCP)

Some LaunchControl workflows depend on **Dataverse Custom APIs** -
unbound actions that compute or mutate something the basic CRUD tools
can't. The canonical one is `lc_CalculateLaunchReadiness`, which
aggregates milestones, tasks, and blockers into a single `Score` +
`Decision` verdict.

The preview MCP exposes Custom APIs through the **same three tools** -
no new tool is added. The flow is:

1. **`search`**: surfaces the Custom API alongside table schemas and
   skills in its results. Example: `search("calculate launch readiness")`
   should return a path like `api/lc_CalculateLaunchReadiness` (or the
   tenant's equivalent path prefix) in addition to any related skills
   and tables.

2. **`describe`**: call against the path returned by `search` to get
   the input request parameters, their types, and the response shape.
   Example: `describe("api/lc_CalculateLaunchReadiness")` reveals its
   parameter (`lc_LaunchName`, string: the launch's `lc_name`) and
   response shape.

3. **`execute`**: run the API with the parameters discovered in step 2.
   Use whichever operation the `describe` output specifies. Example
   payload:

   ```json
   {
     "lc_LaunchName": "<launch name, matches lc_launch.lc_name>"
   }
   ```

When a Business Skill body says *"invoke the Dataverse MCP unbound
action `lc_CalculateLaunchReadiness`"*, follow the `search` →
`describe` → `execute` chain above.

Rules:

1. **Never invent an action.** Only call Custom APIs surfaced by
   `search` or named explicitly in a Business Skill body / user prompt.
2. **Always `describe` before `execute`.** Parameter names are
   case-sensitive (`lc_LaunchName`, not `launchname` or `LaunchName`)
   and `describe` is the canonical source of truth for casing.
3. **Treat actions as side-effecting.** Even read-style actions consume
   API capacity and may write telemetry. Don't loop-call.
4. **Don't hand-compute the result.** If `execute` errors, surface the
   error verbatim and continue per the calling skill's partial-failure
   rules: do not fall back to summing milestone statuses in your head.
5. **If `search` doesn't surface the API yet,** the preview MCP
   orchestrator may not have indexed it. Fall back to reading the
   launch's existing `lc_risksummary` column (an AI prompt column on
   `lc_launch`) as the best-available readiness signal, and note the
   degraded mode in the response. Do not retry endlessly.

## Workflow

1. **Resolve the table** the user is asking about. If ambiguous, ask
   which table or call `search` to disambiguate.
2. **Resolve people / entity references** before querying.
3. **`describe` before querying** when columns aren't known. For schema
   discovery questions ("what columns are on X", "what tables are in
   solution Y"), defer to the companion `dataverse-launchcontrol-schema` skill.
   For **business policy** questions (launch readiness, status
   transitions, escalation, briefings) defer to the
   `dataverse-launchcontrol-business-skills` skill: it loads the
   authoritative policy rows from the Dataverse `skill` table and
   tells you which Custom APIs (e.g. `lc_CalculateLaunchReadiness`)
   to invoke. Do not hand-compute readiness here.
4. **Call `execute` with operation `read`** with the smallest filter
   that satisfies the request; prefer server-side `WHERE`/`TOP` over
   fetching everything.
5. **Page through** when the user asks for "all" rows.
6. **For writes**: confirm the target row and the changes before
   executing. Dataverse writes via `execute` are immediate.

## Output Format

- **List queries**: compact table with the 4–6 most relevant columns
- **Single-row lookups**: key/value summary of important fields
- **Writes**: confirm the operation and surface the new/updated row's
  ID and URL

## Confirmation Gates

- Before any **create**, **update**, or **delete**: state the table,
  the row (by name + ID), and the changes. Proceed only after explicit
  confirmation in the current turn.
- For bulk operations (>5 rows affected): always confirm.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| 401 / unauthorized | OAuth token expired or scope missing | User re-consents to the plugin in Cowork |
| 403 / forbidden | Dataverse security role lacks privilege on table | Admin grants the role; not a plugin issue |
| 404 / row not found | Stale ID or row deleted | Re-search by name |
| 400 / invalid column | Column name mismatched (logical vs display) | Use the logical name from `describe("tables/<name>")` (or the `dataverse-launchcontrol-schema` skill) |
| `@odata.bind not supported` (or similar) on `execute(operation='create'\|'update')` | Tried to set a lookup using the OData `<lookup>@odata.bind` syntax | The preview MCP does NOT accept `@odata.bind`. Set the lookup attribute directly to the GUID string: `"lc_launchid": "<guid>"`, not `"lc_launchid@odata.bind": "/lc_launchs(<guid>)"` |
