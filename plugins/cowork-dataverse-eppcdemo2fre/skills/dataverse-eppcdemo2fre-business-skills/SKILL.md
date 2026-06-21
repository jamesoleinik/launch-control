---
name: dataverse-eppcdemo2fre-business-skills
description: |
  Authoritative EppcDemo2FRE business policies (approvals, valid status
  transitions, escalation, briefing formats) live as rows in the Dataverse
  `skill` table (entity set `skills`) in the EppcDemo2FRE environment. Before
  answering any EppcDemo2FRE business or policy question, this skill instructs
  Cowork to discover and follow those rows rather than improvise.

  Trigger phrases:
  - "what is our policy on [topic]"
  - "can I move [record] from [status] to [status]"
  - "this [record] is blocked, what do I do" / "escalate [record]"
  - "draft a [briefing|summary] for [record]"
  - "what business skills are loaded" / "list EppcDemo2FRE policies"

  Do NOT use for: ad-hoc CRUD over rows (use `dataverse-eppcdemo2fre-mcp`), schema
  discovery (use `dataverse-eppcdemo2fre-schema`), or topics outside EppcDemo2FRE policy.
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# EppcDemo2FRE Business Skills: Policy Catalog

EppcDemo2FRE may ship a curated set of business skills (playbooks, policies,
rules) stored as rows in the Dataverse **`skill`** table (OData entity set
**`skills`**). Each row contains the full policy markdown in the `body`
column. Editing a row in Dataverse changes agent behavior; the markdown in
this plugin is not the source of truth. This skill tells Cowork to discover,
fetch, and follow those rows before improvising answers about EppcDemo2FRE
policy.

## When NOT to Use

- Ad-hoc record reads or writes: use `dataverse-eppcdemo2fre-mcp`.
- Logical-name discovery or solution dumps: use `dataverse-eppcdemo2fre-schema`.
- Non-EppcDemo2FRE topics: use other plugins.

## The `skill` table

| Column | Type | Purpose |
|---|---|---|
| `skillid` | GUID | Primary key |
| `uniquename` | String | Stable identifier (for example `approval_policy`) |
| `name` | String | Display name |
| `description` | String | One-line summary; match user intent against this |
| `body` | Memo | Full policy markdown; read and follow verbatim |

OData entity set: `skills`. Logical name: `skill`.

## Workflow

### Step 1: Catalog (once per session)

On the first EppcDemo2FRE business question of a session, fetch the catalog and
cache it:

```
execute
  operation: read
  query: SELECT TOP 200 skillid, uniquename, name, description FROM skill
```

If the `skill` table does not exist in this environment, tell the user that no
business-skill catalog is installed here and answer from the data skill only;
do not invent a policy.

### Step 2: Match intent

Match the question against the cached `description` column. Prefer the skill
whose description most directly covers the intent; tie-break on `name`. If two
or more look plausible, name them and ask which applies. If nothing matches,
say so and do not invent a policy.

### Step 3: Fetch the body

```
describe
  path: skills/<uniquename>
```

### Step 4: Follow the body verbatim

Treat the `body` markdown as authoritative instructions. In particular:

- If the body says always invoke Custom API X, invoke it via the
  `search -> describe -> execute` chain. Never hand-compute the result.
- If the body lists valid status transitions, reject any transition not on the
  list.
- If the body defines an escalation chain, follow it in order.
- If the body references other tables, columns, or Custom APIs, use the exact
  logical names it provides.

### Step 5: Cite the skill

Briefly cite which skill governed the answer (for example "Per the Approval
Policy skill, ..."). This lets the user trace the answer back to the row.

## Hard Rules

1. Never invent business policy. If no skill row covers the question, tell the
   user the policy is not defined and ask whether to proceed without one.
2. Never hand-compute a value a Custom API is meant to produce. Invoke the
   action named by the policy body.
3. Respect Dataverse permissions. If reading `skill` returns nothing, the user
   lacks read access; say so rather than falling back to an embedded copy.
4. Refresh on staleness. If a session has been open long enough that policies
   may have changed (or the user says the policy changed), re-fetch the catalog
   before answering.

## Output Format

- For policy answers: lead with the verdict or action the policy prescribes,
  then cite the skill.
- For "what policies do we have": render a compact table of `name` and
  `description` from the cached catalog.
- For multi-step playbooks: walk the steps in order, calling the listed tools
  or APIs at each step.

## Confirmation Gates

Reading the `skill` table is read-only; no confirmation needed for catalog or
body fetches. Any writes the body instructs you to perform follow the
confirmation rules in `dataverse-eppcdemo2fre-mcp`.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| `skill` table not found | No business-skill catalog installed in this env | Answer from the data skill; tell the user policies are not defined here |
| Empty catalog | User lacks read on `skill` | Surface the permission gap; do not improvise |
| `body` references a missing table or Custom API | Stale skill row | Tell the user; ask whether to proceed without it |
| Multiple matching skills | Overlapping descriptions | Name them; ask which to apply |

## Tone

Operational. Lead with what the policy says to do; explain the reasoning only
if asked.
