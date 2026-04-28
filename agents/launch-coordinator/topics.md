# Agent Topics

These are the conversation topics the Launch Coordinator agent handles.
Each topic maps to a business skill and a set of Dataverse queries.

## Topic 1: Launch Status Check

**Trigger phrases:**
- "What's the status of [launch name]?"
- "How is [launch name] going?"
- "Give me an update on [launch name]"
- "Status report for [launch name]"

**Actions:**
1. Query `lc_launch` for the named launch
2. Query `lc_milestone` filtered by launch ID, ordered by due date
3. Query `lc_task` to count completion stats
4. Format: launch name, status, target date, milestone summary, task progress, blockers

---

## Topic 2: Go/No-Go Readiness Check

**Trigger phrases:**
- "Is [launch name] ready for go/no-go?"
- "Run the readiness checklist for [launch name]"
- "Can we launch [launch name]?"
- "Go/no-go for [launch name]"

**Actions:**
1. Invoke the **Launch Readiness Checklist** business skill
2. For each gate: query the corresponding milestone and its tasks
3. Assess each gate as PASSED / AT RISK / BLOCKED
4. Provide final verdict: GO / NO-GO / CONDITIONAL

---

## Topic 3: Escalate a Blocker

**Trigger phrases:**
- "Escalate the [task/milestone] blocker"
- "The [task name] is blocked, what should we do?"
- "Follow the escalation policy for [blocker]"

**Actions:**
1. Invoke the **Escalation Policy** business skill
2. Query the blocked task/milestone and its due date
3. Assess severity (Low/Medium/High/Critical)
4. Recommend notification chain
5. Offer to create a status update record

---

## Topic 4: Update Task Status

**Trigger phrases:**
- "Mark [task name] as done"
- "Update [task name] status to [status]"
- "Complete the [task name] task"

**Actions:**
1. Invoke the **Status Transition Rules** business skill
2. Query the current task status
3. Validate the requested transition
4. If valid: confirm with user, then update via MCP
5. If invalid: explain why and suggest the correct path

---

## Topic 5: Cross-System View

**Trigger phrases:**
- "Show me the GitHub issues for the launch"
- "What's happening in GitHub?"
- "Are there any open engineering issues?"

**Actions:**
1. Query `lc_githubissue` virtual table
2. List issues with title, state, assignee, URL
3. Highlight any that relate to launch blockers

---

## Topic 6: Team Overview

**Trigger phrases:**
- "Who's on the [launch name] team?"
- "Show me the team members"
- "Who owns the marketing milestone?"

**Actions:**
1. Query `lc_teammember` filtered by launch
2. List members with name, role, email
3. Cross-reference with task assignments if asked about specific milestones
