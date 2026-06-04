# Cowork ↔ Dataverse MCP — Schema-Aware Skill (Launch Control)

## Description

Use this skill when **Microsoft 365 Cowork** (or Microsoft 365 Copilot chat)
is calling the **Dataverse MCP server** at `{DataverseOrgUrl}/api/mcp` for the
Launch Control environment. It tells the model which Launch Control tables
exist, the relationships between them, the status fields that matter, and
which Custom API to invoke for readiness — so the user can ask launch
questions in plain English without naming logical columns.

> **Plumbing first, then schema.** Authentication, package wiring, and the
> Allowed MCP Client list are covered in Episode 6 of the Launch Control
> series. This skill assumes the plugin is connected and the user is signed
> in. It only covers what Cowork should *say* once the pipe is open.

---

## Hard rules

1. **Never invent logical names.** Use the columns and relationships listed
   below verbatim. If a question needs a column not in this skill, say so
   and ask the user instead of guessing a name like `lc_owner` or `lc_due`.
2. **Never hand-tally launch readiness.** Always call the
   `lc_CalculateLaunchReadiness` Custom API (see *Readiness rule*). Summing
   milestone statuses in the prompt is a bug — it diverges from the form,
   the Python report, and the Copilot Studio agent.
3. **Respect Dataverse permissions.** A successful OAuth on the Cowork
   plugin does **not** elevate the user. If the MCP call returns no rows,
   the user cannot see those rows — never fabricate.
4. **Resolve launches by name, not by GUID.** Users say "Q3 Widget Launch",
   not `lc_launchid`. Look up by `lc_name`.

---

## Tables (logical names)

| Table | Display column | Key columns | Notes |
|---|---|---|---|
| `lc_launch` | `lc_name` | `lc_launchid`, `lc_launchstatus`, `lc_targetdate`, `lc_risksummary` | The root entity. `lc_risksummary` is a prompt column populated by the Ep-3 risk-summary AI prompt; quote it directly when asked "what's the risk on…?". |
| `lc_milestone` | `lc_name` | `lc_milestoneid`, `lc_milestonestatus`, `lc_description`, `lc_targetdate`, `_lc_launchid_value` | Belongs to one launch. `lc_description` (not `lc_narrative`) is the milestone summary. |
| `lc_task` | `lc_title` | `lc_taskid`, `lc_taskstatus`, `lc_isblocked`, `lc_blockerreason`, `_lc_milestoneid_value`, `_lc_assignedto_value`, `_lc_githubissueid_value` | Belongs to one milestone. `lc_isblocked = true` with `lc_blockerreason` set is the "blocker" signal. |
| `lc_teammember` | `lc_name` | `lc_teammemberid`, `lc_email`, `lc_role` | Owner/assignee target for tasks and milestones. |
| `lc_statusupdate` | (computed from `createdon` + author) | `lc_statusupdateid`, `lc_body`, `_lc_launchid_value`, `_lc_taskid_value`, `createdon` | Append-only updates from the Coordinator agent, Sentinel, and human users. |
| `lc_githubissue` | `lc_title` | `lc_githubissueid`, `lc_state`, `lc_url` | **Virtual entity** federated from GitHub (Episode 4). Read-only. Joinable from `lc_task._lc_githubissueid_value`. |

---

## Relationships (lookup columns — use these on `$expand`)

| From | Lookup column | Navigation property | To |
|---|---|---|---|
| `lc_milestone` | `_lc_launchid_value` | `lc_LaunchId` | `lc_launch` |
| `lc_task` | `_lc_milestoneid_value` | `lc_MilestoneId` | `lc_milestone` |
| `lc_task` | `_lc_assignedto_value` | `lc_AssignedTo` | `lc_teammember` |
| `lc_task` | `_lc_githubissueid_value` | `lc_GitHubIssueId` | `lc_githubissue` |
| `lc_statusupdate` | `_lc_launchid_value` | `lc_LaunchId` | `lc_launch` |
| `lc_statusupdate` | `_lc_taskid_value` | `lc_TaskId` | `lc_task` |

**Traversal cheat-sheet** for the canonical question
*"what's blocking &lt;launch name&gt;?"*:

```
lc_launch (by lc_name)
  → lc_milestone (filter _lc_launchid_value)
    → lc_task (filter _lc_milestoneid_value, lc_isblocked eq true)
      → lc_teammember (expand lc_AssignedTo)
```

---

## Status fields (choice columns)

| Column | Type | Allowed values |
|---|---|---|
| `lc_launchstatus` | Choice | `Planned`, `In Progress`, `At Risk`, `Launched`, `Cancelled` |
| `lc_milestonestatus` | Choice | `Not Started`, `In Progress`, `Complete`, `Blocked` |
| `lc_taskstatus` | Choice | `Not Started`, `In Progress`, `Complete`, `Blocked` |
| `lc_isblocked` | Boolean | `true` / `false` — paired with `lc_blockerreason` (string) when `true` |

When summarizing status, prefer the **formatted value** the MCP server
returns (`@OData.Community.Display.V1.FormattedValue`), not the raw integer.

---

## Readiness rule (Custom API)

Episode 5's `lc_CalculateLaunchReadiness` is the single source of truth for
"is this launch a GO / CONDITIONAL / NO-GO?". Always call it via MCP rather
than reasoning over milestones yourself:

```http
POST {DataverseOrgUrl}/api/data/v9.2/lc_CalculateLaunchReadiness
Content-Type: application/json

{ "lc_LaunchName": "<launch name>" }
```

Response shape:

| Field | Type | Meaning |
|---|---|---|
| `lc_ReadinessScore` | decimal 0–100 | Weighted average across milestones |
| `lc_Verdict` | string | `GO` \| `CONDITIONAL` \| `NO-GO` |
| `lc_ReadinessSummary` | multi-line string | Per-milestone narrative |

Quote the verdict verbatim. Do not soften `NO-GO` to "almost ready".

---

## Escalation rule (when `NO-GO` or `Blocked`)

When the readiness verdict is `NO-GO`, **or** any task on the launch has
`lc_isblocked = true`, follow the escalation policy in
[`escalation-policy.md`](escalation-policy.md):

- **Tier 1 — &lt; 1-day slip:** Tag the milestone owner (`lc_AssignedTo`
  on tasks; aggregate by milestone).
- **Tier 2 — 1-to-5-day slip:** Add the launch owner.
- **Tier 3 — &gt; 5-day slip OR a `NO-GO` verdict:** Tier 2 + the
  Director listed in [`escalation-policy.md`](escalation-policy.md).

Do not invent escalation paths in the prompt. The skill is the policy.

---

## Status update protocol

When the user asks Cowork to **post an update**, write to `lc_statusupdate`
with the lookup that matches the scope (launch-level or task-level):

```http
POST {DataverseOrgUrl}/api/data/v9.2/lc_statusupdates
Content-Type: application/json

{
  "lc_body": "<the update text>",
  "lc_LaunchId@odata.bind": "/lc_launches(<launchid>)"
}
```

Do not mutate `lc_taskstatus` or `lc_milestonestatus` directly from Cowork
without the user explicitly confirming the state transition — those changes
fire downstream automation that the user may not expect.

---

## Common prompt → MCP plan

| User asks | MCP plan |
|---|---|
| *"What is blocking Q3 Widget Launch?"* | Resolve `lc_launch` by `lc_name` → expand `lc_milestone` → expand `lc_task` filtered `lc_isblocked eq true` → expand `lc_AssignedTo`. |
| *"Should we slip Q3 Widget Launch?"* | Call `lc_CalculateLaunchReadiness`. Quote the verdict. If `NO-GO`, list blocked tasks and apply the escalation rule. |
| *"Who owns the blocker on milestone X?"* | Resolve milestone → tasks with `lc_isblocked eq true` → `lc_AssignedTo` (`lc_name`, `lc_email`). |
| *"Latest update on launch X?"* | `lc_statusupdate` filtered by `_lc_launchid_value`, `$orderby=createdon desc`, top 5. |
| *"What's the launch budget?"* | The Launch Control schema does NOT contain budget. Say so. Do not invent. |

---

## What's NOT in this schema

The skill must refuse, not improvise, when asked about:

- **Budget, cost, revenue, ROI** — not modeled in `lc_*`.
- **Customer accounts / sales pipeline** — out of scope; live in
  `account` / `opportunity`, not `lc_*`.
- **Documents in OneDrive / SharePoint** — Cowork should reach those via
  its native M365 surface, not via the Dataverse MCP plugin.
- **Future predictions ("will it ship on time?")** — use the readiness
  verdict and risk summary; don't manufacture confidence intervals.

---

## Notes for the agent

- The MCP server returns OData payloads. Always `$select` the columns above
  by logical name. Do not request `*` — it inflates the context window.
- Lookups on the wire surface as `_<schema>id_value` (e.g.
  `_lc_launchid_value`). The corresponding *navigation property* for
  `$expand` uses PascalCase (e.g. `lc_LaunchId`). Get this casing right or
  the expand silently returns nothing.
- Display values for choice columns require the
  `Prefer: odata.include-annotations="OData.Community.Display.V1.FormattedValue"`
  header; the MCP server sets this by default but if you see raw ints, ask
  the server to re-issue with annotations.
