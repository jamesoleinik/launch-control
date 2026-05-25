# Status Transition Rules

## Description
Defines valid state transitions for launches, milestones, and tasks in the
unified `lc_*` model. The agent must operate on each entity's
**entity-specific status column** (listed below) — never on the staging
tracker tables (`lc_trackera..lc_trackere`) or on legacy per-gate columns.
Those staging columns were promoted into the unified status columns in
Episode 2 (Promoting the Staging Layer); the agent should never read or
write them directly when answering live status questions.

## Instructions

These rules govern which status transitions are valid for launches,
milestones, and tasks. Before changing any status, verify the transition
is allowed.

### Where status lives (the canonical columns)

Each unified entity has its own status column. The codes are different
per entity — do not mix them up.

| Entity         | Status column        | Title column |
|----------------|----------------------|--------------|
| `lc_launch`    | `lc_launchstatus`    | `lc_name`    |
| `lc_milestone` | `lc_milestonestatus` | `lc_name`    |
| `lc_task`      | `lc_taskstatus`      | `lc_title`   |

### Launch status transitions

`lc_launchstatus` choice codes:

| Code | Status |
|---|---|
| 10600001 | Planning |
| 10600002 | In Progress |
| 10600003 | Ready for Launch |
| 10600004 | Launched |
| 10600005 | On Hold |

| From | To | Trigger |
|---|---|---|
| Planning           | In Progress       | First milestone moves to In Progress |
| In Progress        | Ready for Launch  | All milestones are Complete |
| In Progress        | On Hold           | A Critical escalation is active (see Escalation Policy) |
| Ready for Launch   | Launched          | Launch sponsor gives final approval |
| On Hold            | In Progress       | All Critical blockers resolved |

**Invalid:**
- Planning → Launched (cannot skip stages)
- Launched → anything (launches are final)

### Milestone status transitions

`lc_milestonestatus` choice codes:

| Code | Status |
|---|---|
| 10600010 | Not Started |
| 10600011 | In Progress |
| 10600012 | Complete    |
| 10600013 | At Risk     |
| 10600014 | Blocked     |

| From | To | Trigger |
|---|---|---|
| Not Started | In Progress | First task in milestone starts |
| In Progress | Complete    | All tasks in milestone are Done |
| In Progress | At Risk     | Any task is overdue OR open blocker count > 0 |
| In Progress | Blocked     | A Critical-severity blocker exists |
| At Risk     | In Progress | Overdue tasks resolved AND no Critical blocker |
| At Risk     | Blocked     | Severity escalates to Critical |
| Blocked     | In Progress | All blockers resolved (verify via the Escalation Policy skill) |

**Invalid:**
- Not Started → Complete (must pass through In Progress)
- Complete → anything (milestones are final once Complete)

### Task status transitions

`lc_taskstatus` choice codes (note: different range from milestones):

| Code | Status |
|---|---|
| 10600020 | Not Started |
| 10600021 | In Progress |
| 10600022 | Done    |
| 10600023 | Blocked |

| From | To | Trigger |
|---|---|---|
| Not Started | In Progress | Work begins |
| In Progress | Done        | Work is complete |
| In Progress | Blocked     | Blocker identified — also set `lc_isblocked = true` and write `lc_blockerreason` |
| Blocked     | In Progress | Blocker resolved — also clear `lc_isblocked = false` |

**Invalid:**
- Not Started → Done (must pass through In Progress)
- Done → anything (tasks are final once Done)

### Cross-system tasks (virtual entity linkage)

Some tasks link to a GitHub issue via the `lc_GitHubIssueId` lookup on
`lc_task` (Episode 4 — Extending & Enforcing the Model). Before transitioning a
linked task to `Done`, **verify the GitHub issue is closed** by reading
the virtual entity:

```
GET /api/data/v9.2/lc_tasks(<id>)
   ?$expand=lc_GitHubIssueId($select=lc_state)
```

Rules:

- If `lc_GitHubIssueId.lc_state` is `open`, refuse to mark the task `Done`.
  Recommend either closing the GitHub issue first, or unlinking it.
- If the lookup is empty, no extra check is needed.
- Never write back to GitHub from this skill — the virtual entity is
  read-only by design.

### Cascading effects

When a status transition is allowed, the agent must also:

1. **Recompute readiness if the change affects a milestone.** Invoke
   `lc_CalculateLaunchReadiness` (see Launch Readiness Checklist skill) —
   the verdict may change.
2. **Update the milestone's status if all its tasks are Done.** Per the
   table above, this triggers a milestone transition to Complete.
3. **Surface any invalid downstream transitions** rather than silently
   blocking them. Example: marking a task Done that would push a
   milestone past At Risk while the launch is On Hold.

### Enforcement

When asked to change a status, ALWAYS:

1. Read the current status from the entity's canonical status column
   (`lc_launchstatus` / `lc_milestonestatus` / `lc_taskstatus`).
2. Check the table above for validity.
3. If invalid, explain why and suggest the correct path. Do not write.
4. If the entity is a task with a GitHub issue link, run the cross-system
   check.
5. Make the change with a single PATCH that updates only the canonical
   status column (and `lc_isblocked` / `lc_blockerreason` for tasks
   moving in or out of Blocked).
6. Run any cascading recompute (readiness, milestone roll-up).

### Output format

```
Transition: lc_task('Wire payment provider') In Progress → Done
Validation: ALLOWED  (cross-system check passed: GitHub #4 is closed)
Result: PATCH /lc_tasks(<id>) { "lc_taskstatus": 10600022 }
Cascade: milestone 'Engineering Sign-off' is now 8/8 Done — recommending
         transition to Complete (run again to apply)
```
