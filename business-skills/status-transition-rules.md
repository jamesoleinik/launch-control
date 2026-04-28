# Status Transition Rules

## Description
Defines valid state transitions for launches, milestones, and tasks. Prevents invalid status changes and enforces business rules.

## Instructions

These rules govern which status transitions are valid for launches, milestones, and tasks. Before changing any status, verify the transition is allowed.

### Launch Status Transitions
- **Planning** → In Progress (when first milestone starts)
- **In Progress** → Ready for Launch (when ALL milestones are Complete)
- **In Progress** → On Hold (when a Critical escalation is active)
- **Ready for Launch** → Launched (when launch sponsor gives final approval)
- **On Hold** → In Progress (when all Critical blockers are resolved)
- **INVALID:** Planning → Launched (cannot skip stages)
- **INVALID:** Launched → any other status (launches are final)

### Milestone Status Transitions
- **Not Started** → In Progress (when first task in milestone starts)
- **In Progress** → Complete (when ALL tasks in milestone are Done)
- **In Progress** → At Risk (when any task is overdue or blocker count > 0)
- **In Progress** → Blocked (when a Critical-severity blocker exists)
- **At Risk** → In Progress (when overdue tasks are resolved)
- **At Risk** → Blocked (when severity escalates to Critical)
- **Blocked** → In Progress (when all blockers are resolved)
- **INVALID:** Not Started → Complete (cannot skip In Progress)
- **INVALID:** Complete → any other status (milestones are final)

### Task Status Transitions
- **Not Started** → In Progress (when work begins)
- **In Progress** → Done (when work is complete)
- **In Progress** → Blocked (when a blocker is identified)
- **Blocked** → In Progress (when blocker is resolved)
- **INVALID:** Not Started → Done (cannot skip In Progress)
- **INVALID:** Done → any other status (tasks are final)

### Enforcement
When asked to change a status, ALWAYS check if the transition is valid before executing. If the transition is invalid, explain why and suggest the correct path.
