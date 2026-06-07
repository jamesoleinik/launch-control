# Playbook: Launch Readiness (Go / No-Go)

## Description
Extracted from §1 of the Contoso Product Launch Playbook (`source/launch-playbook.docx`).
Every launch passes through a readiness review before we ship. The PMO evaluates
the launch against a set of milestone gates and produces a verdict of **GO**,
**CONDITIONAL**, or **NO-GO**. The verdict is not a vibe — it is computed.

## Instructions

### Step 1: Resolve the launch in question

If the user names a launch (e.g. "Q3 Widget Launch"), use that. If they don't
name one, query `lc_launch` and **ask** which one — do not guess and do not
pick the most recent one silently.

### Step 2: Web-search community feedback and file new tasks first

Before scoring readiness, refresh the picture. Use Cowork's web-search
capability to look for public chatter about the launch (product name, version,
key features) **since the prior readiness review** — Reddit threads, Hacker
News posts, X/Twitter posts, dev-forum threads, blog comments, public issue
trackers. The goal is to surface issues that affect ship-readiness — perf
regressions, customer confusion, pricing/legal concerns, blocking dependencies
called out in public.

For each material signal, **create a new `lc_task` in Dataverse** with:

- `lc_name` = a one-line summary of the feedback
- `lc_description` = the source quote + the public URL Cowork found it at
- `lc_status` = `Open`
- `lc_priority` = `High` if the signal blocks shipping, otherwise `Normal`
- `lc_launch` = the launch resolved in Step 1
- `lc_source` = `community-feedback`

Do **not** create duplicates. Before filing, query `lc_task` filtered to the
current launch and skip any item whose `lc_description` already references the
same URL.

This step runs **before** the readiness API call so the score reflects
everything the community has surfaced — the API is invoked once, against the
full picture, not before-and-after.

### Step 3: Compute readiness via the Custom API (POLICY)

Readiness is the weighted average of all milestone completion states on the
launch. The PMO does **NOT** hand-tally gates in a slide or a chat message.
The launch readiness score is calculated server-side by the
`lc_CalculateLaunchReadiness` Custom API in Dataverse, which has full
visibility of every milestone and task — including the new tasks filed in
Step 2.

The agent must invoke that API and report its three return values verbatim:

| Field                 | Type              | Meaning |
|-----------------------|-------------------|---------|
| `lc_ReadinessScore`   | decimal 0–100     | Weighted milestone score |
| `lc_Verdict`          | string            | `GO` \| `CONDITIONAL` \| `NO-GO` |
| `lc_ReadinessSummary` | multi-line string | Per-milestone narrative |

### Step 4: Apply the verdict thresholds

| Score          | Verdict       | Meaning |
|----------------|---------------|---------|
| ≥ 85           | **GO**          | Cleared to ship. |
| 65 – 84 (incl.) | **CONDITIONAL** | Leadership sign-off required. Treat as GO with a documented mitigation plan. |
| < 65           | **NO-GO**       | Do not ship. |

`CONDITIONAL` is the official answer to "can we override a single At Risk
milestone?" — there is no other override path. (Q1 retro note.)

### Step 5: Report the result

When reporting back to the user, always:

- State the verdict in the first sentence.
- Quote the score with one decimal place.
- Surface any milestone that is `At Risk` or `Blocked`, by name.
- Name every `lc_task` created from community feedback in this run.
- If verdict is `CONDITIONAL`, name who needs to sign off.

### What this skill is NOT

- It is **not** a status report — it answers "are we ready to ship?".

When reporting back to the user, always:

- State the verdict in the first sentence.
- Quote the score with one decimal place.
- Surface any milestone that is `At Risk` or `Blocked`, by name.
- Name every `lc_task` created from community feedback in this run.
- If verdict is `CONDITIONAL`, name who needs to sign off.

### What this skill is NOT

- It is **not** a status report — it answers "are we ready to ship?".
- It does **not** modify launch or milestone records — the only writes it
  performs are `lc_task` inserts in Step 4.
- It does **not** escalate. If the verdict surfaces blocked milestones, hand
  them to the Escalation playbook skill.
