# Agent Topics

These are the conversation topics the **Launch Coordinator** Copilot Studio
agent handles. Each topic maps to one or more business skills, the
`lc_CalculateLaunchReadiness` Custom API, and/or the Ep 5 BYO MCP connectors
(Learn MCP, GitHub MCP). Field names below are the **actual Dataverse
logical names** confirmed against the solution XML.

---

## Topic 1: Launch Status Check

**Trigger phrases:**
- "What's the status of [launch name]?"
- "How is [launch name] going?"
- "Status report for [launch name]"

**Actions:**
1. Query `lc_launchs` filtered on `lc_name`, select `lc_launchstatus`, `lc_targetdate`, `lc_description`
2. Query `lc_milestones` filtered by `_lc_launchid_value`, ordered by `lc_duedate`, select `lc_name`, `lc_milestonestatus`, `lc_duedate`
3. Query `lc_tasks` to count completion stats — group by `lc_taskstatus` and by `_lc_milestoneid_value`
4. Format: launch name, status, target date, milestone summary, task progress, blockers (where `lc_isblocked=true`)

---

## Topic 2: Go/No-Go Readiness Check

**Trigger phrases:**
- "Is [launch name] ready for go/no-go?"
- "Run the readiness checklist for [launch name]"
- "Can we launch [launch name]?"

**Actions:**
1. **Invoke the `lc_CalculateLaunchReadiness` Custom API** (single call) with `lc_LaunchName`
2. Read `lc_Verdict`, `lc_ReadinessScore`, `lc_ReadinessSummary` from the response
3. If user wants per-gate detail, expand by querying `lc_milestones` + their child `lc_tasks` for the launch
4. Surface `lc_ReadinessSummary` as the headline; back it up with the structured breakdown

> Do NOT re-implement the scoring loop in the agent — the Custom API is the source of truth (Ep 5 plugin).

---

## Topic 3: Escalate a Blocker (cross-system)

**Trigger phrases:**
- "Escalate the [task] blocker"
- "The [task name] is blocked, what should we do?"
- "Follow the escalation policy for [blocker]"

**Actions:**
1. Resolve the task: `GET /lc_tasks(<id>)?$select=lc_title,lc_taskstatus,lc_isblocked,lc_blockerreason,_lc_milestoneid_value,_lc_assignedtoid_value&$expand=lc_GitHubIssueId($select=lc_issuenumber,lc_state,lc_labels,lc_url)`
2. **Cross-check:** if `lc_GitHubIssueId.lc_state = closed`, recommend transitioning the task back to InProgress instead of escalating (stale Dataverse state)
3. Resolve assignee email: expand `_lc_assignedtoid_value` → `lc_teammember(lc_name,lc_email)`
4. Get the milestone's `lc_duedate` to compute days remaining
5. Apply the **Escalation Policy** business skill severity matrix
6. Offer to write a `lc_statusupdates` row (`lc_name="[<Severity>] <task title> blocked"`, `lc_LaunchId@odata.bind=/lc_launchs(<id>)`)

---

## Topic 4: Update Task Status

**Trigger phrases:**
- "Mark [task name] as done"
- "Update [task name] status to [status]"

**Actions:**
1. Look up the task by `lc_title` (NOT `lc_name`)
2. Read current `lc_taskstatus`
3. Validate the transition per **Status Transition Rules** skill
4. **If transitioning to Done AND task has `_lc_githubissueid_value`:** expand the VE first; refuse if `lc_state=open`
5. **If transitioning to Blocked:** also set `lc_isblocked=true` and prompt for `lc_blockerreason`
6. PATCH `/lc_tasks(<id>)` with `{ "lc_taskstatus": <code>, ... }`

---

## Topic 5: Cross-System View (GitHub VE)

**Trigger phrases:**
- "Show me the GitHub issues for the launch"
- "Are there any open engineering issues?"
- "Which tasks have GitHub issues that are still open?"

**Actions:**
1. Query `lc_tasks` with `$expand=lc_GitHubIssueId` and `$filter=_lc_githubissueid_value ne null`
2. List: task `lc_title`, GitHub `lc_issuenumber`, `lc_state`, `lc_labels`, `lc_url`
3. Highlight any where Dataverse `lc_taskstatus != Done` AND VE `lc_state = closed` (work-state mismatch)

---

## Topic 6: Team Overview

**Trigger phrases:**
- "Who's on the [launch name] team?"
- "Who owns the marketing milestone?"

**Actions:**
1. From the launch's tasks/milestones, collect distinct `_lc_assignedtoid_value` values
2. Resolve each via `lc_teammembers(<id>)?$select=lc_name,lc_email,lc_role`
3. Cross-reference with their assigned task/milestone titles

---

## Topic 7: External Lookups (Ep 5 BYO MCP connectors)

**Trigger phrases:**
- "How do I [Power Platform / Dataverse concept]?" (→ Learn MCP)
- "Find the GitHub issue about [topic]" (→ GitHub MCP)
- "Search the launch-control repo for [text]"

**Actions:**
1. **Learn MCP connector** — invoke `microsoft_docs_search` (or equivalent tool exposed by the connector) for "how-to" / documentation queries; cite returned URLs
2. **GitHub MCP connector** — invoke search/issues tools for free-text repo queries that go beyond what the `lc_githubissue` virtual entity exposes (e.g., search across multiple repos, code search, PRs)
3. These complement the in-Dataverse data — use them when the answer is NOT in the launch's transactional state
