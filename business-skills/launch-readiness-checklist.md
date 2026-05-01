# Launch Readiness Checklist

## Description
Use this skill to evaluate whether a product launch is ready for go/no-go.
**Always invoke the `lc_CalculateLaunchReadiness` Custom API — never hand-tally
gates or compute readiness in the agent prompt.** The Custom API runs
server-side in Dataverse, has access to every milestone and task, and
returns an authoritative score, narrative, and verdict.

## Instructions

You are evaluating launch readiness for a product launch.

### Step 1: Resolve the launch

If the user names a launch (e.g. "Q3 Widget Launch"), use it directly. If
they don't, query `lc_launch` and ask which one — do not guess.

```
GET /api/data/v9.2/lc_launchs?$select=lc_launchid,lc_name,lc_launchstatus,lc_targetdate&$filter=statecode eq 0
```

### Step 2: Invoke the Custom API

There is exactly one correct way to compute readiness:

```http
POST /api/data/v9.2/lc_CalculateLaunchReadiness
Content-Type: application/json

{ "lc_LaunchName": "<launch name>" }
```

The response contains three fields:

| Field | Type | Meaning |
|---|---|---|
| `lc_ReadinessScore`   | decimal 0–100 | Average milestone weight |
| `lc_Verdict`          | string        | `GO` \| `CONDITIONAL` \| `NO-GO` |
| `lc_ReadinessSummary` | multi-line string | Per-milestone narrative |

**Do NOT** sum milestone statuses yourself. **Do NOT** call the milestone
table directly to compute a score. The Custom API is the single source of
truth for readiness math; if you compute it differently, you will get a
different answer than the Power Apps form, the Python report, and the
Copilot Studio agent — and that is a bug.

### Step 3: Interpret the verdict

Verdicts come from the Custom API's deterministic logic:

- **NO-GO** — at least one milestone is `Blocked` (status code 10600014).
  Surface the blocked milestones from `lc_ReadinessSummary` and recommend
  invoking the `Escalation Policy` skill against them.
- **GO** — score ≥ 90 _and_ no milestone is `AtRisk`. Confirm and stop.
- **CONDITIONAL** — score is high but at least one milestone is at risk.
  Surface the at-risk milestones and recommend an action.

### Step 4: (Optional) Drill into a milestone

If the user wants detail on a specific milestone, query it directly:

```
GET /api/data/v9.2/lc_milestones
   ?$select=lc_name,lc_milestonestatus,lc_duedate
   &$filter=_lc_launchid_value eq <launchid>
```

Milestone status codes (`lc_milestonestatus` choice):

| Code | Status | Weight in score |
|---|---|---:|
| 10600010 | Not Started | 20 |
| 10600011 | In Progress | 60 |
| 10600012 | Complete    | 100 |
| 10600013 | At Risk     | 50 |
| 10600014 | Blocked     | 0 |

For tasks under that milestone:

```
GET /api/data/v9.2/lc_tasks
   ?$select=lc_title,lc_taskstatus,lc_isblocked,lc_blockerreason,lc_duedate,_lc_githubissueid_value
   &$filter=_lc_milestoneid_value eq <milestoneid>
```

Task status codes (`lc_taskstatus` choice — note: different range from milestone):

| Code | Status |
|---|---|
| 10600020 | Not Started |
| 10600021 | In Progress |
| 10600022 | Done    |
| 10600023 | Blocked |

### Output format

Always lead with the verdict, then the score, then the narrative. Example:

```
Verdict: NO-GO
Score: 38.8 / 100

Reason: 2 milestones are Blocked
  - Security review (CDN provisioning waiting on vendor)
  - Marketing launch page (legal hold on copy)

[Full narrative from lc_ReadinessSummary follows]
```

### What this skill is NOT

- It is **not** a status report. Status comes from the Power Apps dashboard
  and the entity-specific status columns (`lc_launchstatus` /
  `lc_milestonestatus` / `lc_taskstatus`). This skill answers _"are we
  ready to ship?"_
- It does **not** modify any data. Readiness is read-only. Use the
  `Status Transition Rules` skill if a status needs to change as a result.
- It does **not** escalate. If the verdict is NO-GO or CONDITIONAL, hand
  the blocked milestones to the `Escalation Policy` skill — that's its job.
