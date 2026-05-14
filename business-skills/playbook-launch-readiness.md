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

### Step 2: Compute readiness via the Custom API (POLICY)

Readiness is the weighted average of all milestone completion states on the
launch. The PMO does **NOT** hand-tally gates in a slide or a chat message.
The launch readiness score is calculated server-side by the
`lc_CalculateLaunchReadiness` Custom API in Dataverse, which has full
visibility of every milestone and task.

The agent must invoke that API and report its three return values verbatim:

| Field                 | Type              | Meaning |
|-----------------------|-------------------|---------|
| `lc_ReadinessScore`   | decimal 0–100     | Weighted milestone score |
| `lc_Verdict`          | string            | `GO` \| `CONDITIONAL` \| `NO-GO` |
| `lc_ReadinessSummary` | multi-line string | Per-milestone narrative |

### Step 3: Apply the verdict thresholds

| Score          | Verdict       | Meaning |
|----------------|---------------|---------|
| ≥ 85           | **GO**          | Cleared to ship. |
| 65 – 84 (incl.) | **CONDITIONAL** | Leadership sign-off required. Treat as GO with a documented mitigation plan. |
| < 65           | **NO-GO**       | Do not ship. |

`CONDITIONAL` is the official answer to "can we override a single At Risk
milestone?" — there is no other override path. (Q1 retro note.)

### Step 4: Report the result

When reporting back to the user, always:

- State the verdict in the first sentence.
- Quote the score with one decimal place.
- Surface any milestone that is `At Risk` or `Blocked`, by name.
- If verdict is `CONDITIONAL`, name who needs to sign off.

### What this skill is NOT

- It is **not** a status report — it answers "are we ready to ship?".
- It does **not** modify any data.
- It does **not** escalate. If the verdict surfaces blocked milestones, hand
  them to the Escalation playbook skill.
