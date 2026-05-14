# Playbook: Status Transitions

## Description
Extracted from §3 of the Contoso Product Launch Playbook
(`source/launch-playbook.docx`). Status changes look innocuous in a UI but they
are policy decisions. Each entity has its own status column with its own legal
transitions. The agent must respect these. Do **not** free-text statuses, and
do **not** operate on the staging tracker tables (`lc_trackera..lc_trackere`)
for live status questions — those are append-only landing zones.

## Instructions

### Canonical status columns (POLICY)

Each unified entity carries its own status column. Option-set integer codes are
entity-specific; mixing them up will yield HTTP 400 and a lot of confusion.

| Entity         | Status column        |
|----------------|----------------------|
| `lc_launch`    | `lc_launchstatus`    |
| `lc_milestone` | `lc_milestonestatus` |
| `lc_task`      | `lc_taskstatus`      |

### Launch transitions

Happy path: **Planning → In Progress → Ready for Launch → Launched**.

Additional rules:

- From any state **except** `Launched` and `Cancelled`, a launch may move to
  `On Hold`.
- From `On Hold`, the launch resumes to whichever state it was in.
- A launch may move to `Cancelled` from any non-terminal state, but
  cancellation **requires a written reason in the status notes**.

### Milestone transitions

Happy path: **Not Started → In Progress → Complete**.

Additional rules:

- A milestone may move into `At Risk` from `In Progress` when any of its tasks
  slip past their due date.
- A milestone moves to `Blocked` if any of its tasks are `Blocked`.
- Once `Complete`, a milestone is **terminal** — do not reopen. If you
  discover additional work, file a new milestone.

### Task transitions

Happy path: **Not Started → In Progress → Done**.

Additional rules:

- From `In Progress`, a task may move to `Blocked` at any time.
- From `Blocked`, a task returns to `In Progress` when the blocker clears.
- `Done` is **terminal**.

### What this skill is NOT

- It is **not** a readiness calculator. Status changes may invalidate the last
  readiness verdict — re-run the Launch Readiness playbook skill if a
  milestone status changes.
- It does **not** operate on the staging tracker tables. Those are append-only
  landing zones, not the source of live status.
