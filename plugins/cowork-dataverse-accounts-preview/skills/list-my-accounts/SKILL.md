---
name: list-my-accounts
description: |
  List and look up rows in the standard Dataverse `account` table for the
  connected environment via the PREVIEW Dataverse MCP endpoint
  (https://org77c9659c.crm.dynamics.com/api/mcp_preview). Read-only: this
  sample reads accounts, it does not create, update, or delete.

  Trigger phrases:
  - "list my accounts"
  - "show me my accounts"
  - "how many accounts do I own"
  - "look up the account [name]"
  - "find accounts in [city]"
  - "show the most recently created accounts"
  - "what accounts can I see"

  Scope: the single connected Dataverse environment ONLY, and the `account`
  table specifically. Do NOT use for other tables, other Dataverse
  environments, SharePoint lists, Excel files, or Power BI artifacts.
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# List My Accounts — Dataverse (Cowork sample, preview MCP)

Connects Microsoft 365 Copilot Cowork to one Dataverse environment through the
**preview** Dataverse MCP server (`/api/mcp_preview`) and answers questions
about the standard `account` table. Authentication flows through Cowork's
OAuthPluginVault: the user signs in once with their own Dataverse identity, and
Dataverse security roles decide which account rows come back.

This is a deliberately small sample skill. It covers one table and read-only
questions. For anything else, defer or decline rather than improvising.

## Preview endpoint (3-tool surface)

The preview endpoint exposes three consolidated tools. For this skill you only
need the read path:

- **`search`** — discover what is available. `search("account")` returns a
  filesystem-style path such as `tables/account`. Use it first; never hard-code
  paths.
- **`describe`** — get full details for a path. `describe("tables/account")`
  returns the column logical names, types, and example queries. Call it before
  querying when a column name is uncertain. Never assume column names.
- **`execute`** — run an operation. For this read-only sample use
  `execute` with the `read` operation (a SQL-style SELECT against
  `tables/account`, with WHERE / ORDER BY / TOP). Do NOT use `create`,
  `update`, or `delete`.

This sample does not invoke Custom APIs. If a future need arises, the preview
`execute` tool can call unbound actions, but that is out of scope here.

## When NOT to Use

- Other Dataverse tables (contact, opportunity, lead, case): out of scope for
  this sample; say so.
- Other Dataverse environments: install a separate env-scoped plugin.
- Creating, updating, or deleting accounts: this sample is read-only.
- SharePoint lists, Excel / CSV, or Power BI: use the matching native tool.

## The account table

| Property | Value |
|---|---|
| Logical name | `account` |
| Primary key | `accountid` (GUID) |
| Primary name column | `name` |
| Owner lookup | `ownerid` (lookup to `systemuser` / `team`); on the wire it is `_ownerid_value` |

Commonly useful columns (select these by logical name; do not request `*`):

`name`, `accountnumber`, `emailaddress1`, `telephone1`, `address1_city`,
`address1_stateorprovince`, `address1_country`, `primarycontactid`,
`createdon`, `modifiedon`, `statecode`, `ownerid`.

## "My" accounts

"My accounts" means accounts **owned by the signed-in user**. In order of
preference:

1. If the MCP server exposes a built-in "current user" or "assigned to me"
   filter, use it.
2. Otherwise resolve the signed-in user id first (a `WhoAmI`-style call returns
   the caller's `UserId`), then read accounts filtered by owner:
   `_ownerid_value` equals that id.

Never assume an owner GUID. If the signed-in user id cannot be resolved, ask the
user to clarify whose accounts they mean instead of returning everyone's.

## Query patterns

| User asks | Plan (preview `execute` read) |
|---|---|
| "List my accounts" | Read `tables/account` where owner = signed-in user, select name + accountnumber + address1_city + emailaddress1 + telephone1, order by name, top 25. |
| "How many accounts do I own" | Same owner filter; return the count. Prefer a server-side count. |
| "Look up the account Contoso" | Read `tables/account` where name matches the term, top 10. If multiple match, list and ask which. |
| "Find accounts in Seattle" | Read where address1_city = 'Seattle', select name + address1_city + emailaddress1, top 25. |
| "Most recently created accounts" | Order by createdon desc, top 10, select name + createdon + ownerid. |

Always pass a bounded top (default 25, max a few hundred). Prefer a tight
server-side filter over fetching everything and filtering in the answer.

## Output format

- **List queries**: a compact table with 4 to 6 columns. Lead with `name`.
- **Single lookup**: a short key/value summary plus the row's id.
- **Counts**: a single sentence with the number.

For choice columns such as `statecode`, prefer the formatted display value over
the raw integer.

## Hard rules

1. **Respect Dataverse security.** A successful Cowork sign-in does not elevate
   the user. If the read returns no rows, the user cannot see those rows. Never
   fabricate accounts, owners, or contact details.
2. **Stay on the `account` table.** If asked about contacts, opportunities,
   budgets, or other tables, say this sample only covers accounts.
3. **Read-only.** Do not call `execute` with create / update / delete here.
4. **Use logical names.** Resolve any uncertain name via `describe` before
   querying.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| 401 / unauthorized | OAuth token expired or scope missing | User reconnects to the plugin in Cowork |
| 403 / forbidden | Dataverse security role lacks read on `account` | Admin grants the role; not a plugin issue |
| 400 / invalid column | Logical vs display name mismatch | Use the logical name from `describe("tables/account")` |
| MCP server unavailable | Preview MCP not enabled, or app not allowlisted | Enable env-level Dataverse MCP; confirm the allowed MCP client row |
