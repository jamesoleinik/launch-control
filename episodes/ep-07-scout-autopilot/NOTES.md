# Microsoft Scout — research notes (carry-over from the planning round)

Captured 2026-06-04 from the Scout announcement and `learn.microsoft.com/microsoft-scout` so we don't have to redo this when access lands.

---

## What Scout is (one paragraph)

Microsoft Scout (Frontier preview) is the first in a new **"Autopilot"** agent category — always-on, runs in the background under its own **Entra identity**, takes action on the user's behalf within Purview / Intune policy boundaries. Ships as a **desktop app for Windows 11+ and macOS 12+** with deep M365 integration. Powered by an open-source core branded **OpenClaw**. Access requires Frontier enrollment + Intune policy + opt-in attestation + a GitHub Copilot license.

---

## Capability surface (what Scout can do for us)

| Capability | How LaunchControl could use it |
|---|---|
| **Custom skills** (drops a `SKILL.md` from your skills directory) | Hand Scout a `launch-control/SKILL.md` that points at the Ep-5 BYO MCP connector + the `lc_DraftLaunchBriefing` AI Prompt. |
| **M365 actions** (Teams send / read, calendar create/find-times, email, OneDrive, people search) | Post launch briefings into the sponsor's Teams DM; block calendar for risk reviews. |
| **WorkIQ** (cross-service synthesis) | *"What did Alex say about Q3 Widget Launch across email/Teams/docs?"* — synthesis answer fed to Scout's reasoning step. |
| **Automations** (scheduled or condition-triggered prompts) | Monday-morning launch readiness sweep. Condition: any `lc_milestone` going red. |
| **Heartbeat** (every 15–120 min within work hours) | Short, conservative version of the automation — separate, more-restrictive permission policy. |
| **Sub-agents** (research / task / code-review / explore / general-purpose) | Spin parallel work for multi-launch analysis. |
| **Shell + filesystem (MCP)** | Run our existing Python deploy / teardown scripts (`scripts/*.py`). |
| **Browser control (Playwright)** | Edit a Loop page; pull data from the maker portal if needed. |
| **Approval tiers** (auto / prompt / deny) | Show the trust story: writing to Teams prompts; reading is auto-approve. |
| **Sensitivity-label awareness** | Demonstrate that a Confidential-labeled briefing won't get written to an unprotected destination. |
| **Memory + session history search** | Scout remembers the sponsor's preferences across sessions. |

---

## Top-3 LaunchControl-meets-Scout ideas

These were ranked in the planning round. **Idea A** is the locked core demo for this episode. Ideas B and C are filed here for later.

### A. **Launch Sponsor Skill** (✅ core demo)
A 30-line `launch-control/SKILL.md` that teaches Scout to:
1. Query `lc_launch` / `lc_milestone` via the Ep-5 BYO MCP connector.
2. Invoke `lc_DraftLaunchBriefing` (Ep-5 AI Prompt) via the Dataverse connector's bound `Predict` action.
3. DM the result to the sponsor in Teams.

Demo prompt (live in Teams): *"Give me a GO/HOLD/NO-GO on Q3 Widget Launch and DM it to the sponsor."*

### B. **Launch Heartbeat automation** (stretch / follow-up)
Saved Scout automation, schedule trigger "Every Monday 08:00":
> *Query lc_launch via the Launch Control MCP. For any launch with ≥1 open lc_milestone whose target_date is within the next 7 days, draft a briefing via lc_DraftLaunchBriefing and DM it to the launch owner in Teams. If the briefing says HOLD or NO-GO, block 15 min on my calendar today titled "Risk review — &lt;launch name&gt;".*

Shows the two surfaces unique to Scout (autonomy + calendar/Teams writes) on top of the same substrate.

### C. **"Recording assistant" meta-skill** (cute, optional)
Point Scout at the repo's `episodes/` directory. Every episode in this series already ships a `SKILL.md` written for the human producer. Scout can ingest those verbatim and become the recording producer: runs the right teardown script before a session, fires the right deploy script during prep, drafts the LinkedIn outline into OneDrive. Meta-narrative: the SKILL.md files we've been shipping for humans also work for Autopilot agents.

---

## Pre-recording checklist

- [ ] Frontier enrollment confirmed for the tenant
- [ ] Intune policy applied per `learn.microsoft.com/microsoft-scout/admin-intune-setup`
- [ ] Opt-in attestation completed by the demo user
- [ ] GitHub Copilot license attached to the demo user
- [ ] Scout desktop installed on the recording machine
- [ ] Ep-5 substrate present (BYO MCP custom connector + `lc_DraftLaunchBriefing` AI Prompt published in the LaunchControl solution)
- [ ] At least one launch with milestones loaded (`Q3 Widget Launch` is the existing demo data)

---

## Open questions for when access lands

- Does the Scout skill loader accept relative imports from a folder, or one flat `SKILL.md`? (Docs imply flat `SKILL.md`.)
- Can a Scout skill declare a hard requirement on a specific MCP server, or do we list the connector in the prompt and trust Scout to pick it?
- What's the auth shape for the Ep-5 BYO custom connector when called from inside Scout? (Connection reference, OAuth on first use, or pre-shared?)
- Does Scout's Dataverse access use the user's Entra token or an Autopilot service identity? (Affects whether RBAC from Ep 8 applies as expected.)
