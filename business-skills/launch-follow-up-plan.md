# Launch Follow-up Plan

## Purpose

Turn confirmed open blockers on one Launch Control launch into a small,
reviewable set of follow-up tasks. This skill does not change the launch's
readiness decision.

## Process

1. Resolve the named launch from the connected Dataverse source. If there is
   more than one match, ask which one.
2. Read its current readiness evidence, milestones, and open tasks. Use the
   configured authoritative readiness operation when available. Do not
   calculate a verdict from incomplete data.
3. Propose one follow-up task per confirmed blocker. Prefix each new task title
   with `[EP12-DEMO]` so the test records can be identified for cleanup. Reuse
   the blocker title and source relationship where available. Do not invent an
   owner, due date, milestone, or status. Ask the user when required values are
   missing.
4. Check for an existing follow-up task for the same blocker before proposing
   a new one. Do not duplicate or overwrite unrelated tasks.
5. Show the user each proposed task's title, description, parent launch or
   milestone, owner, due date, and status update text. Identify values that
   are not available instead of guessing.
6. Wait for the user's explicit approval of the exact proposal. Approval of a
   general goal is not approval to write.
7. Use only the current authorized business-app operation that was confirmed
   for this environment. If no supported create operation is available, stop
   and present the plan without claiming that anything was saved.
8. Read every created task back and verify its values and relationship. Then
   create one concise status update titled `[EP12-DEMO] Follow-up plan`
   describing the work, if that operation was also confirmed and approved.
   Read it back as well.
9. Report each created, reused, or failed item. Do not say the launch is ready
   unless a fresh readiness check independently returns that result.

## Never do

- Change the launch's status, readiness score, verdict, or milestone state.
- Close or clear a blocker merely to improve the readiness result.
- Create an unassigned or undated task when the connected process requires
  those values.
- Send messages, schedule meetings, publish agents, or make unrelated writes.
- Claim an update's client or author from its title or wording alone.
- Create demo tasks or updates without the `[EP12-DEMO]` marker.
- Continue after an unclear target, denied permission, partial write, or
  mismatched read-back.
