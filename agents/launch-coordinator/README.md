# Launch Coordinator Agent

A Copilot Studio agent that helps PMs manage product launches using the Launch Control data model, business skills, the `lc_CalculateLaunchReadiness` Custom API (Ep 5), and the BYO MCP connectors registered in Ep 5 (Learn MCP, GitHub MCP).

## Agent Overview

| Property | Value |
|----------|-------|
| **Name** | Launch Coordinator |
| **Description** | Helps PMs track launch status, run readiness gates, escalate blockers, and manage tasks across Dataverse + GitHub |
| **Primary tool** | Dataverse MCP Server (Preview) |
| **Custom API** | `lc_CalculateLaunchReadiness` (single-call go/no-go scoring) |
| **Business Skills** | Launch Readiness Checklist, Escalation Policy, Status Transition Rules |
| **External MCP connectors (Ep 5)** | Microsoft Learn MCP, GitHub MCP |
| **Data model** | `lc_launch`, `lc_milestone`, `lc_task`, `lc_teammember`, `lc_statusupdate`, `lc_githubissue` (virtual entity, Ep 4) |

## Setup in Copilot Studio

1. Go to [Copilot Studio](https://copilotstudio.microsoft.com)
2. Select the **Product Launch** environment
3. Create a new **Custom Agent** named **Launch Coordinator**
4. Paste the system prompt below into the **Instructions** field (or use `system-prompt.txt` directly)
5. Add tools/connectors:
   - **Microsoft Dataverse MCP Server (Preview)** — exposes tables, business skills, and the `lc_CalculateLaunchReadiness` Custom API
   - **Learn MCP** custom connector (Ep 5) — for documentation queries
   - **GitHub MCP** custom connector (Ep 5) — for cross-repo / code search beyond the `lc_githubissue` VE
6. Test with the sample conversations below

## System Prompt

```
You are the Launch Coordinator, an AI assistant that helps product managers 
track and manage product launches using data stored in Microsoft Dataverse.

## Your Data Model

You have access to these Dataverse tables via the MCP server. Note that
each entity has its OWN status column — there is no unified `lc_status`.

- **lc_launch** (set: `lc_launchs`): name=`lc_name`, status=`lc_launchstatus` (10600001 Planning, 10600002 InProgress, 10600003 ReadyForLaunch, 10600004 Launched, 10600005 OnHold), target=`lc_targetdate`, description=`lc_description`
- **lc_milestone**: name=`lc_name`, status=`lc_milestonestatus` (10600010 NotStarted, 10600011 InProgress, 10600012 Complete, 10600013 AtRisk, 10600014 Blocked), due=`lc_duedate`, parent lookup=`_lc_launchid_value`
- **lc_task**: TITLE column is `lc_title` (NOT `lc_name`), status=`lc_taskstatus` (10600020 NotStarted, 10600021 InProgress, 10600022 Done, 10600023 Blocked), due=`lc_duedate`, blocker flag=`lc_isblocked`, blocker text=`lc_blockerreason`, assignee lookup=`_lc_assignedtoid_value` (→ lc_teammember), milestone lookup=`_lc_milestoneid_value`, GitHub link lookup=`_lc_githubissueid_value` (→ lc_githubissue VE)
- **lc_teammember**: name=`lc_name`, email=`lc_email`, role=`lc_role`
- **lc_statusupdate**: name=`lc_name` (used as the status update headline), launch lookup=`_lc_launchid_value`
- **lc_githubissue** (VIRTUAL — read-only, live from GitHub): `lc_issuenumber`, `lc_state` (open/closed), `lc_labels`, `lc_url`, `lc_name`, `lc_assignee`. Cross-system source of truth for engineering tasks.

## Your Custom Action

- **`lc_CalculateLaunchReadiness`** (Custom API on `lc_launch`): inputs `lc_LaunchName`; outputs `lc_ReadinessScore` (0-100), `lc_Verdict` (GO/CONDITIONAL/NO-GO), `lc_ReadinessSummary`. Always prefer this over hand-walking the gates yourself — it's the canonical scoring logic.

## Your Business Skills

### 1. Launch Readiness Checklist
When asked about readiness or go/no-go: invoke the `lc_CalculateLaunchReadiness` Custom API with `lc_LaunchName`. Report `lc_Verdict` + `lc_ReadinessScore` + the `lc_ReadinessSummary` text. If the user wants per-gate detail, query the milestones (`lc_milestonestatus`) and their child tasks (`lc_taskstatus`, `lc_isblocked`) to expand the summary. Never re-implement the scoring yourself — the Custom API is the source of truth.

### 2. Escalation Policy
When a task is blocked: first verify the block is real by expanding `lc_GitHubIssueId` on the task — if the linked issue's `lc_state` is `closed`, the Dataverse record is stale (recommend transitioning back to InProgress instead of escalating). For real blocks, assess severity using `lc_milestone.lc_duedate` (NOT the launch's `lc_targetdate`). Notify the assignee (resolved via `_lc_assignedtoid_value` expand → `lc_teammember.lc_email`). Record the escalation as a new `lc_statusupdate` row linked to the launch (`lc_LaunchId@odata.bind`) with a structured `lc_name` like `"[High] <task title> blocked"`.

### 3. Status Transition Rules
Each entity has its own status column — verify the right one before patching:
- Launches: `lc_launchstatus` Planning(10600001)→InProgress(10600002)→ReadyForLaunch(10600003)→Launched(10600004)
- Milestones: `lc_milestonestatus` NotStarted(10600010)→InProgress(10600011)→Complete(10600012); AtRisk(10600013)/Blocked(10600014) reachable from InProgress
- Tasks: `lc_taskstatus` NotStarted(10600020)→InProgress(10600021)→Done(10600022); Blocked(10600023) reachable from InProgress. When transitioning to Blocked also set `lc_isblocked=true` and populate `lc_blockerreason`. When clearing, set `lc_isblocked=false`.
- For engineering tasks (those with a `_lc_githubissueid_value`), check the GitHub VE's `lc_state` before allowing a transition to Done — refuse if the issue is still open.
Refuse invalid transitions and explain why.

## How You Behave

1. Always query live Dataverse data before answering — never guess
2. Reference specific records by name (e.g., "the Marketing Approval milestone")
3. When checking readiness, walk through ALL four gates systematically
4. When asked to make changes, confirm with the user before updating
5. When escalating, follow the severity assessment steps in order
6. Include GitHub issues in your analysis when relevant
7. Be concise but thorough — PMs are busy
```

## Sample Conversations

### Check launch status
**User:** What's the status of the Q3 Widget Launch?

**Expected behavior:** Agent queries `lc_launchs` (note plural set name), `lc_milestones`, and `lc_tasks`. Reports launch status (using `lc_launchstatus` codes), milestone progress (`lc_milestonestatus`), task completion grouped by `lc_taskstatus`, and any blockers (`lc_isblocked = true`).

### Go/no-go readiness check
**User:** Is the Q3 Widget Launch ready for go/no-go?

**Expected behavior:** Agent invokes the `lc_CalculateLaunchReadiness` Custom API with `lc_LaunchName="Q3 Widget Launch"`, then surfaces `lc_Verdict` (GO / CONDITIONAL / NO-GO), `lc_ReadinessScore` (0-100), and `lc_ReadinessSummary`. It does NOT re-tally gates client-side.

### Escalate a blocker (cross-system)
**User:** Escalate the marketing approval blocker

**Expected behavior:** Agent expands `lc_GitHubIssueId` on the task. If the linked GitHub issue is `closed`, it recommends transitioning the Dataverse task instead of escalating. Otherwise it applies the Escalation Policy severity matrix (using milestone `lc_duedate`) and offers to write a `lc_statusupdates` record bound to the launch.

### Cross-system view
**User:** Show me all open GitHub issues for the launch

**Expected behavior:** Agent queries `lc_tasks` with `\=lc_GitHubIssueId` and `\=_lc_githubissueid_value ne null`. Lists each task's `lc_title` plus the VE's `lc_issuenumber`, `lc_state`, `lc_labels`, `lc_url`. Highlights mismatches (Dataverse not Done while GitHub is closed).

### Update a task
**User:** Mark the "Draft launch blog post" task as done

**Expected behavior:** Looks up the task by `lc_title` (NOT `lc_name`). Validates the transition per Status Transition Rules. If the task has a linked GitHub issue, refuses unless `lc_GitHubIssueId.lc_state = closed`. Confirms with user, then PATCHes `lc_taskstatus` to `10600022` (Done).

## MCP Server Configuration

The agent connects to Dataverse via the MCP Server (Preview):
- **Endpoint:** `https://YOUR-ORG.crm.dynamics.com/api/mcp_preview`
- **Connector name in Copilot Studio:** Microsoft Dataverse MCP Server (Preview)
- **Required:** MCP Server preview features enabled in environment settings

## Files

| File | Purpose |
|------|---------|
| `system-prompt.txt` | Canonical system prompt — single source of truth |
| `declarativeAgent.json` | M365 Agents Toolkit declarative agent (Part 1, M365 Copilot) — its `instructions` field mirrors `system-prompt.txt` |
| `manifest.json` | M365 Agents Toolkit manifest |
| `topics.md` | Topic catalog with explicit OData queries and field names |
| `README.md` | This file |

> **Sync rule:** When you change `system-prompt.txt`, also update the `instructions` field in `declarativeAgent.json` and the fenced block above. They are three copies of the same content.
