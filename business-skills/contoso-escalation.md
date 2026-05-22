# Contoso Playbook: Escalation

## Description
Extracted from §2 of the Contoso Product Launch Playbook
(`source/launch-playbook.docx`). A task or milestone marked `Blocked` is an
escalation candidate, but not every blocker requires a page — we have killed
enough Saturdays to know the difference. Trigger this skill when the user
asks "should we escalate this?", "who do I page for &lt;blocker&gt;?", or any
request that resolves to severity scoring and routing for a blocked task or
milestone. The agent's job is to decide **severity**, then **route**.

## Instructions

### Step 1: Verify the block before paging anyone (POLICY)

Before any escalation, cross-check Dataverse against the linked GitHub issue.
GitHub Issues are modelled as a virtual entity referenced by
`lc_GitHubIssueId` on `lc_task`.

- If a task is marked `Blocked` in Dataverse but the linked GitHub issue is
  **closed**, that is stale data, not a real blocker.
- **Do not escalate.** Recommend transitioning the task back to `In Progress`
  (per the Status Transitions skill) and re-running readiness.

(Q2 retro note: engineering asked us to stop trusting the Dataverse blocked
flag without checking GitHub. We agreed.)

### Step 2: Score severity

Severity is one of **Low**, **Medium**, **High**, or **Critical**. Combine
the inputs below; `Critical` is the ceiling.

| Input | Effect on severity |
|---|---|
| **GitHub label signal** — linked issue carries a `blocker` or `P0` label | Severity is at minimum **High**, possibly **Critical**. GitHub labels are a stronger signal than Dataverse blocker text alone, because engineering triages there first. |
| **Milestone proximity** — blocker within 7 days of the target date | Escalate one level. |
| **Milestone proximity** — blocker within 2 days of the target date | Escalate two levels. |
| **Cross-team dependency** — blocker requires another team to act | Severity floor is **Medium** even if proximity is far. Cross-team blockers rot when they're not visible. |

### Step 3: Route via the notification chain

| Severity     | Notification |
|--------------|--------------|
| **Low**      | Log only, no page. Mention in the next standup. |
| **Medium**   | Message the task owner directly. If no acknowledgement within **4 business hours**, escalate to the milestone owner. |
| **High**     | Page the task owner **and** the milestone owner on the same channel. Acknowledgement expected within **1 hour**. |
| **Critical** | Page the launch owner, the milestone owner, **and** the on-call. Open a war room channel. Acknowledgement expected within **15 minutes**. |

### Step 4: Critical + Conditional/No-Go combo rule (POLICY)

If the launch is currently in `CONDITIONAL` or `NO-GO` state **and** a
`Critical` blocker lands, the launch owner must trigger a go/no-go re-review
within **24 hours**, regardless of where we are in the cycle.

### What this skill is NOT

- It is **not** a status-change tool. Moving the task in or out of `Blocked`
  is governed by the Status Transitions skill.
- It does **not** modify GitHub — the `lc_GitHubIssueId` virtual entity is
  read-only.
- It does **not** compute the readiness verdict. If a re-review is required,
  invoke the Launch Readiness skill.
