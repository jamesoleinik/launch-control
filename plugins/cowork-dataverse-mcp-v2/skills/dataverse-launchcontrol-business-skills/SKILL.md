---
name: dataverse-launchcontrol-business-skills
description: |
  Authoritative LaunchControl business policies: launch readiness, status
  transitions, escalation, briefings: live as rows in the Dataverse `skill`
  table (entity set `skills`) in the LaunchControl environment. Before
  answering any LaunchControl business question, this skill instructs Cowork
  to discover and follow those policies rather than improvise.

  Trigger phrases:
  - "is [launch] ready to ship" / "go / no-go on [launch]"
  - "what's the readiness score for [launch]"
  - "this task is blocked, what do I do" / "escalate [task|milestone]"
  - "can I move [launch|milestone|task] from [status] to [status]"
  - "draft a launch briefing for [launch]"
  - "what's our policy on [topic]"
  - "what business skills are loaded" / "list LaunchControl policies"

  Do NOT use for: ad-hoc CRUD over Dataverse rows (use the
  `dataverse-launchcontrol-mcp` skill), schema discovery (use
  `dataverse-launchcontrol-schema`), or topics outside LaunchControl
  policy.
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# LaunchControl Business Skills: Policy Catalog

LaunchControl ships a curated set of **business skills** (playbooks,
policies, rules) that live as rows in the Dataverse **`skill`** table
(OData entity set: **`skills`**) in the LaunchControl environment. Each
row contains the full policy markdown in the `body` column. Editing a
row in Dataverse changes agent behavior: the markdown in this plugin
is *not* the source of truth.

This skill tells Cowork to **discover, fetch, and follow** those rows
before improvising answers about launch readiness, status transitions,
escalation, or briefings.

## When NOT to Use

- Ad-hoc record reads / writes → `dataverse-launchcontrol-mcp` skill
- Logical-name discovery / solution dumps → `dataverse-launchcontrol-schema` skill
- Non-LaunchControl topics → other plugins

## The `skill` table

| Column        | Type   | Purpose |
|---------------|--------|---------|
| `skillid`     | GUID   | Primary key |
| `uniquename`  | String | Stable identifier (e.g. `launch_readiness_checklist`) |
| `name`        | String | Display name |
| `description` | String | One-line summary: match user intent against this |
| `body`        | Memo   | Full policy markdown: read and follow verbatim |

OData entity set: `skills`. Logical name: `skill`.

## Workflow

### Step 1: Catalog (once per session)

On the first LaunchControl business question of a session, fetch the
catalog and cache it for the rest of the session:

```
execute
  operation: read
  query: SELECT TOP 200 skillid, uniquename, name, description FROM skill
```

### Step 2: Match intent

Match the user's question against the cached `description` column.

- Prefer the skill whose `description` most directly covers the user's
  intent. Tie-break on `name`.
- If two or more skills look plausible, name them and ask the user
  which one applies: do not silently merge their guidance.
- If nothing matches, say so. **Do not invent a policy.**

### Step 3: Fetch the body

```
describe
  path: skills/<uniquename>
```

### Step 4: Follow the body verbatim

Treat the `body` markdown as authoritative instructions. In particular:

- If the body says **"always invoke Custom API X"**, invoke it. Never
  hand-compute the result in the prompt.
- If the body lists **valid status transitions**, reject any transition
  not on the list.
- If the body defines an **escalation chain**, follow it in order.
- If the body references **other tables, columns, or Custom APIs**, use
  the exact logical names it provides: do not paraphrase.

### Step 5: Cite the skill

When answering, briefly cite which skill governed the answer, e.g.
*"Per the **Launch Readiness Checklist** skill, …"*. This lets the
user trace the answer back to the policy row in Dataverse.

## Hard Rules

1. **Never hand-tally launch readiness.** Always call the
   `lc_CalculateLaunchReadiness` Custom API via the preview MCP
   `search → describe → execute` chain. Summing milestone statuses
   in the prompt is a known bug and diverges from the form, the Python
   report, and the Copilot Studio agent.
2. **Never invent business policy.** If no skill row covers the
   question, tell the user the policy isn't defined and ask whether
   they want to proceed without one.
3. **Always operate on unified `lc_*` tables**, never on the staging
   trackers (`lc_trackera`..`lc_trackere`): those were promoted into
   the unified model in Episode 2.
4. **Respect Dataverse permissions.** If `execute(operation='read')`
   on `skill` returns nothing, the user lacks read access. Tell them -
   do not fall back to embedded copies.
5. **Refresh on staleness.** If a session has been open long enough
   that policies may have changed (or the user says "the policy
   changed"), re-fetch the catalog before answering.

## Known skills (illustrative: always re-discover via `skill` table)

These are the policies currently expected in the environment. The
authoritative list is whatever `execute(operation='read')` on `skill`
returns: treat this list only as orientation:

- **Launch Readiness Checklist**: go / no-go via
  `lc_CalculateLaunchReadiness` Custom API.
- **Status Transition Rules**: valid transitions per entity
  (`lc_launchstatus`, `lc_milestonestatus`, `lc_taskstatus`).
- **Escalation Policy**: what to do when a task or milestone is
  blocked; includes GitHub issue cross-check.
- **Launch Readiness Digest**: periodic summary format.
- **Cowork ↔ Dataverse MCP: Schema-Aware Skill**: the LaunchControl
  table catalog and lookup shortcuts.
- Contoso variants (`contoso-*`): tenant-specific overrides; prefer
  these over the generic versions when both are present.

## Output Format

- For policy answers: lead with the **verdict / action** the policy
  prescribes, then cite the skill.
- For "what policies do we have": render a compact table of `name` +
  `description` from the cached catalog.
- For multi-step playbooks (escalation, readiness): walk the steps in
  order, calling the listed tools/APIs at each step.

## Confirmation Gates

- Read-only on the `skill` table itself: no confirmations needed for
  catalog / body fetches.
- Any writes the *body* instructs you to perform (e.g. updating
  `lc_taskstatus`, creating an `lc_statusupdate`) follow the
  confirmation rules in `dataverse-launchcontrol-mcp`.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| `skill` table not found | Wrong environment, or skills not installed | Confirm env URL; ask admin to run `scripts/cli/upload-skills.mjs` |
| Empty catalog | User lacks read on `skill` | Surface the permission gap; do not improvise |
| `body` references a table or Custom API that doesn't exist | Skill row is stale | Tell the user; ask whether to proceed without it |
| Multiple matching skills | Overlapping descriptions | Name them, ask which to apply |

## Tone

Operational. The audience is a launch manager or PM who wants the
**policy-correct** answer, not a model's opinion. Lead with what the
policy says to do; explain the reasoning only if asked.
