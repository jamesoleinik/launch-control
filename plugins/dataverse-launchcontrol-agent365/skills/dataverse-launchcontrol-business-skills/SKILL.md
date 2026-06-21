---
name: dataverse-launchcontrol-business-skills
description: |
  Authoritative LaunchControl business policies — launch readiness,
  status transitions, escalation, briefings — live as rows in the
  Dataverse `skill` table (entity set `skills`) in the LaunchControl
  environment. Before answering any LaunchControl business question,
  this skill instructs Cowork to load and follow those policies at the
  start of the session rather than improvise.

  Trigger phrases:
  - "is [launch] ready to ship" / "go / no-go on [launch]"
  - "what's the readiness for [launch]"
  - "this task is blocked, what do I do" / "escalate [task|milestone]"
  - "can I move [launch|milestone|task] from [status] to [status]"
  - "draft a launch briefing for [launch]"
  - "what's our policy on [topic]"
  - "what business skills are loaded" / "list LaunchControl policies"

  Do NOT use for: ad-hoc CRUD over Dataverse rows (use the
  dataverse-launchcontrol-mcp skill) or schema discovery (use
  dataverse-launchcontrol-schema).
license: MIT
metadata:
  author: Launch Control
  version: "1.4"
---

# LaunchControl Business Skills — Policy Loader

LaunchControl ships a curated set of **business skills** (playbooks,
policies, rules) that live as rows in the Dataverse **`skill`** table
(OData entity set: **`skills`**). Each row contains the full policy
markdown in the `body` column. **Editing a row in Dataverse changes
agent behavior — the markdown in this plugin is not the source of
truth.**

This skill tells Cowork to **discover, fetch, and follow** those rows
before improvising answers about launch readiness, status transitions,
escalation, or briefings.

## When NOT to use

- Ad-hoc record reads / writes → `dataverse-launchcontrol-mcp`
- Logical-name discovery / `$expand` nav properties →
  `dataverse-launchcontrol-schema`
- Non-LaunchControl topics → other plugins

## The `skill` table

| Column | Type | Purpose |
|---|---|---|
| `skillid` | GUID | Primary key |
| `uniquename` | String | Stable identifier (e.g. `launch_readiness_checklist`) |
| `name` | String | Display name |
| `description` | String | One-line summary — match user intent against this |
| `body` | Memo | Full policy markdown — read and follow verbatim |

OData entity set: `skills`. Logical name: `skill`.

## Session bootstrap — load the catalog at session start

On the **first LaunchControl business question of a session**, fetch the
full catalog and cache it for the rest of the session. Do this before
attempting to answer the user's question.

```
execute
  operation: read
  query: SELECT TOP 200 skillid, uniquename, name, description FROM skill
```

If the read returns zero rows, surface the gap explicitly (`skill` table
empty or user lacks read access) and stop — do **not** fall back to
embedded policies.

Refresh the cache when:

- The session has been open long enough that policies may have changed.
- The user says something like "the policy changed" or "reload the
  skills".
- A policy body references another policy by `uniquename` that isn't in
  the cache.

## Workflow per question

1. **Bootstrap** — ensure the catalog is loaded (above).
2. **Match intent** against the cached `description` column. Prefer the
   skill whose `description` most directly covers the user's intent;
   tie-break on `name`. If two or more skills look plausible, name them
   and ask which one applies — do not silently merge.
3. **Fetch the body** of the chosen skill:

   ```
   describe
     path: skills/<uniquename>
   ```

4. **Follow the body verbatim**. If the body lists valid status
   transitions, reject any transition not on the list. If it defines
   an escalation chain, follow it in order. If it references other
   tables, columns, or nav properties, use the exact names it provides.
5. **Cite the skill** when answering — e.g. *"Per the **Launch Readiness
   Checklist** skill, …"* — so the user can trace the answer back to the
   Dataverse row.

## Hard rules

1. **Launch readiness is sourced from `lc_launch.lc_risksummary` plus the
   `lc_task` rows where `lc_isblocked = true`.** Never hand-tally
   milestones, count tasks by status, or compute a percentage in the
   prompt and call it "the readiness score". The
   `dataverse-launchcontrol-mcp` skill carries the canonical query pair;
   if a `skill` row body conflicts with that rule, ask the user which to
   follow before answering.
2. **Never invent business policy.** If no skill row covers the
   question, tell the user the policy isn't defined and ask whether
   they want to proceed without one.
3. **Always operate on unified `lc_*` tables**, never on the staging
   trackers (`lc_stg_tracker_a..e`) — those were promoted into the
   unified model in Episode 3.
4. **Respect Dataverse permissions.** If `execute(operation='read')` on
   `skill` returns nothing, the user lacks read access. Tell them — do
   not fall back to embedded copies in this skill or in the plugin
   bundle.
5. **Cite, don't paraphrase.** Lead with the policy's verdict and cite
   the `name` + `uniquename` of the skill row that governed the answer.

## Known skills (illustrative — always re-discover via the `skill` table)

The authoritative list is whatever the session-start read returns. The
list below exists only to orient you:

- **Launch Readiness Checklist** — go / no-go via `lc_risksummary` +
  blocked `lc_task` rows.
- **Status Transition Rules** — valid transitions per entity
  (`lc_launchstatus`, `lc_milestonestatus`, `lc_taskstatus`).
- **Escalation Policy** — what to do when a task or milestone is
  blocked; includes GitHub-issue cross-check via `lc_GitHubIssueId`.
- **Launch Readiness Digest** — periodic summary format.
- **Cowork ↔ Dataverse MCP — Schema-Aware Skill** — pointer to
  `dataverse-launchcontrol-schema` for `$expand` nav lookups.
- Tenant variants (e.g. `contoso-*`) — prefer these over the generic
  versions when both are present.

## Output format

- For policy answers: lead with the **verdict / action** the policy
  prescribes, then cite the skill.
- For "what policies do we have": render a compact table of `name` +
  `description` from the cached catalog.
- For multi-step playbooks (escalation, readiness digest): walk the
  steps in order, calling the listed tools / queries at each step.

## Confirmation gates

- Read-only on the `skill` table itself — no confirmations for catalog
  / body fetches.
- Any writes the *body* instructs you to perform (e.g. updating
  `lc_taskstatus`, creating an `lc_statusupdate`) follow the
  confirmation gates in `dataverse-launchcontrol-mcp`.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| `skill` table not found | Wrong environment, or skills not installed | Confirm env URL; ask admin to run the skill upload script |
| Empty catalog | User lacks read on `skill` | Surface the permission gap; do not improvise |
| `body` references a table or column that doesn't exist | Skill row is stale | Tell the user; ask whether to proceed without it |
| Multiple matching skills | Overlapping descriptions | Name them, ask which to apply |

## Tone

Operational. The audience is a launch manager or PM who wants the
**policy-correct** answer, not a model's opinion. Lead with what the
policy says to do; explain reasoning only if asked.
