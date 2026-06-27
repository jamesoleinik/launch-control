# Episode 13: Convergence (native Copilot and the three IQ agents, together)

**Status:** ✍️ Reworked draft (Season 2 finale) · 🎬 Not yet recorded
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Native M365 Copilot grounding over Dataverse (Dataverse intelligence / Work IQ) · ⭐ The Web IQ, Fabric IQ, and Foundry IQ agents from Eps 10 to 12 collaborating on one launch · ⭐ One question, four answers, one platform
**Layer:** 🟣 Layer 3, the conversational surface, where everything converges
**Coding agent:** _None for the native beat._ The platform answers on its own. The three agents come from Eps 10 to 12.
**Runtime:** M365 Copilot + the three Season 2 agents

---

## The hook

> *"Four episodes, four pairings. Now the same launch question goes to all of
> them at once: native Copilot for reach, and the Web IQ, Fabric IQ, and Foundry
> IQ agents for depth. One platform, answering in concert."*

This is the Season 2 finale and the payoff of the "better together" thesis. The
prior episodes each paired Dataverse with one partner. Here they converge on a
single launch:

- **Native M365 Copilot** reads Dataverse directly, no agent in the middle.
- **The Web IQ agent (Ep 10)** brings the live external risk.
- **The Fabric IQ agent (Ep 11)** brings the semantic anomaly read.
- **The Foundry IQ agent (Ep 12)** brings the cited, document-grounded judgment.

## Beat 1: Native Copilot, zero agents

The smallest, most load-bearing beat. After three episodes of building agents,
take them all away and show the platform answering on its own. The moment your
business state lives in Dataverse, the most widely used Copilot already reads it.

### Pre-record gate (load-bearing): refreshed for the current UX

Three toggles, in order. The first two are the enablement the rest of the demo
depends on.

**a) M365 Admin Center: allow the right users.**
Copilot → Settings → **"Dataverse data available in Microsoft 365 Copilot."**
- **Step 1:** "Allow users to access Dataverse data in M365 Copilot" →
  **No users / All users / Specific groups**. For the demo, scope to a security
  group to show least-privilege. This grants org-wide connect permission.
- **Step 2:** the pane points to PPAC for the environment-level step (below).

**b) Power Platform Admin Center: enable the environment.**
Environments → (demo env) → Manage → **Dataverse intelligence (Preview)**:
- check **"Allow data availability in Microsoft 365 Copilot"**
- check **"Turn on Dataverse intelligence (Work IQ) for agents and AI
  experiences"**
- choose which **tables are search-enabled** (`lc_launch`, `lc_milestone`,
  `lc_task`, `lc_teammember`). **Note the time.**

> **⚠ Indexing delay: 10 to 60 minutes.** Flip the toggles well before filming.
> If you start recording immediately you will capture "I don't have access to
> that data" and a punchline-shaped hole.

**c) Use it in M365 Copilot.** Supported surfaces (per the maker doc,
https://learn.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-data-copilot):
Copilot Chat, Power Apps sidecar, Word, Outlook, Teams. Preview nuances to call
out: **Outlook needs "Default mode"** and **Word needs "Chat only"** to query
Dataverse data.

### Prime the context (the step everyone skips)

Copilot grounds against the most-recently-used Power Apps **environment**, not the
most-recently-used app. Day-of: open a launch app/page in the demo env, click
around for 30 seconds, close it, then open M365 Copilot.

### Smoke test

Ask `What's in the Launches table?` and column names back means you are grounded.
If after 60 minutes it still says "I don't have access," escalate.

### The three native prompts (read -> traverse -> filter)

1. **Read.** *"What's the status of the Q3 Widget Launch?"*
2. **Cross-table traversal.** *"Who's assigned to the most tasks for the Q3 Widget
   Launch?"*
3. **Filter + free text.** *"Show me the blocked tasks for the Q3 Widget Launch
   and why they're blocked."*

Backup: *"Summarize the risks for the Q3 Widget Launch."* (the `lc_risksummary`
prompt column).

## Beat 2: The three agents, on the same launch

Now bring the agents back. Same launch, one question to each, and watch the depth
native cannot reach:

| Agent | Source | Answer it uniquely gives |
|---|---|---|
| **Native Copilot** | Dataverse only | the facts: status, owners, blocked tasks |
| **Web IQ (Ep 10)** | + live web | the CDN vendor had an outage; the security blocker maps to a live CVE |
| **Fabric IQ (Ep 11)** | + semantic baseline | 8 blockers is a statistical outlier for this phase |
| **Foundry IQ (Ep 12)** | + federated docs | the cited security standard and vendor SLA behind the judgment |

The point: **reach and depth are a spectrum, not a choice.** Native Copilot gives
everyone an answer with zero build. Each agent adds one more partner when the
decision needs it.

## Beat 3: The punchline

> *"Same launch. Same platform. Native Copilot for reach, three agents for depth.
> You don't pick one. You build the surface your user needs and let Dataverse be
> the thing they all agree on."*

Bridge to Season 3: *"The system is in production across every surface. Next, we
manage it."*

## Pre-record checklist

- [ ] M365 Admin Center → "Dataverse data available in M365 Copilot" → users
      scoped (Step 1).
- [ ] PPAC → demo env → "Allow data availability" + "Turn on Dataverse
      intelligence (Work IQ)"; tables search-enabled; indexing delay survived
      (>= 60 min since flip).
- [ ] Smoke prompt returns a grounded answer.
- [ ] Demo env primed (launch app opened + clicked through).
- [ ] The three Season 2 agents (Eps 10 to 12) published and reachable.
- [ ] Prompts typed live, not pasted; backup prompt staged.

## Cross-references

- **Ep 3:** the data model, relationships, and `lc_risksummary` prompt column
  that native grounding reads.
- **Eps 10 to 12:** the Web IQ, Fabric IQ, and Foundry IQ agents that join native
  Copilot here.
- **Season 3** (Agentic Administration): managing the system this season built.
