# Episode 7 — The Agent

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Copilot Studio agent · ⭐ Dataverse MCP Server (Preview) · ⭐ Dataverse Knowledge (grounded retrieval) · ⭐ Custom API as a tool · ⭐ Declarative agent for M365 Copilot
**Layer:** 🟣 Layer 3 (the conversational surface)
**Coding agent:** Copilot Studio UI + Agents Toolkit (declarative agent)
**Runtime:** Copilot Studio (Part 2) + M365 Copilot (Part 1)

---

## The hook

> _"Five episodes building a data model, a virtual entity, a custom action, and
> two registered MCP servers — all without a single line of agent code. Now
> we point an agent at it. The agent code is **zero lines**. The capability
> we're about to demo is everything we've already built, made conversational."_

Episodes 1–5 built the **substrate** — entities, virtual entities, custom
actions, BYO connectors, and knowledge articles. Episode 7 binds it all to an
agent surface. Twice.

1. **Declarative Agent for M365 Copilot** (Part 1) — a lightweight wrapper
   that lives inside M365 Copilot. Users invoke it by name from any Copilot
   surface (Word, Teams, Edge sidebar). Tool-light, knowledge-rich.
2. **Custom Copilot Studio Agent** (Part 2) — the full operational agent.
   Dataverse MCP for live state, the `lc_CalculateLaunchReadiness` Custom API
   as a first-class tool, and **Dataverse Knowledge** grounded on
   `lc_knowledgearticle` for policy/playbook/spec/postmortem questions.

Same data. Same skills. Two surfaces.

---

## The narrative beat

Everything the agent does, you've already seen the platform do — but now via
natural language. Three demo questions, three different routing decisions,
all from one agent:

```
User → "What's the status of Q3 Widget Launch?"
        Agent  ▶  Dataverse MCP query on lc_launch / lc_milestone / lc_task
        Agent  ◀  "Score 38.8 / NO-GO. 2 milestones blocked: Security review,
                   CDN provisioning. Marketing Approval is at risk."
```

```
User → "What's our policy on slipping a launch by a week?"
        Agent  ▶  Dataverse Knowledge tool (grounded on lc_knowledgearticle)
        Agent  ◀  "Per the Escalation Policy article, slips of <1 week
                   require Director approval; >1 week requires VP signoff."
```

```
User → "Should we slip Q3 Widget Launch?"
        Agent  ▶  Dataverse Knowledge (slip rules) + MCP (live readiness)
        Agent  ▶  Custom API lc_CalculateLaunchReadiness
        Agent  ◀  "NO-GO today (score 38.8, 2 blockers). Per the Escalation
                   Policy, this is a >1-week slip requiring VP signoff.
                   Recommend escalation; here are the blockers..."
```

The third one is the money shot. **The agent doesn't know — or care — that
one tool is OData-over-MCP, one is a grounded knowledge index, and one is a
sandboxed C# plugin.** From the prompt, they're all "tools."

---

## Part 1 · Declarative Agent for M365 Copilot

> Tool-light, knowledge-rich. Lives inside M365 Copilot.

The simplest possible surface. A declarative agent is a JSON manifest
([declarativeAgent.json](../../agents/launch-coordinator/declarativeAgent.json))
loaded into M365 Copilot via the Agents Toolkit. Users invoke it by name
(`@Launch Coordinator`) from Word, Teams, Outlook, the Edge sidebar.

```json
{
  "version": "v1.6",
  "name": "Launch Coordinator",
  "description": "Helps PMs track launch status, run readiness gates, escalate blockers...",
  "instructions": "You are the Launch Coordinator...",
  "capabilities": [
    {
      "name": "Dataverse",
      "knowledge_sources": [
        {
          "host_name": "YOUR-ORG.crm.dynamics.com",
          "tables": [
            { "table_name": "lc_launch" },
            { "table_name": "lc_milestone" },
            { "table_name": "lc_task" },
            ...
          ]
        }
      ]
    }
  ],
  "conversation_starters": [...]
}
```

The `Dataverse` capability is what's new (Aug 2025 GA): M365 Copilot can
read directly from Dataverse tables you list, governed by the user's row-level
permissions. No MCP server registration, no Copilot Studio agent, no Power
Platform license required for the consumer.

### What it _can_ do

- Answer "what's the status of X" by reading from the listed tables.
- Use the agent's `instructions` (the system prompt) for tone, routing, and
  business-skill guidance.
- Cite Dataverse records by name.

### What it _can't_ do

- Invoke Custom APIs (`lc_CalculateLaunchReadiness`).
- Use BYO MCP connectors.
- Write back to Dataverse.
- Trigger flows.

That's exactly the point of Part 2.

### Ship it

```powershell
# from launch-control/
cd agents/launch-coordinator

# Replace YOUR-ORG with the real environment hostname
# (or run scripts/render_agent_manifest.py if/when we add it)

# Sideload via the M365 Agents Toolkit extension in VS Code:
#   Cmd-Shift-P → "Teams: Provision" → pick declarativeAgent.json
# Or upload the manifest.json zip via the Microsoft 365 Admin Center.
```

Once provisioned, the agent shows up in M365 Copilot as `@Launch Coordinator`.

---

## Part 2 · Custom Copilot Studio Agent

> The full operational agent. Tools, knowledge, write-back.

Where the declarative agent is read-only and tool-light, the Copilot Studio
agent is the working surface — the one a PM lives in during launch week.

### What's wired up

| Tool | Source | What it does |
|---|---|---|
| **Dataverse MCP Server (Preview)** | Built-in connector in CS | Live OData over `lc_launch`, `lc_milestone`, `lc_task`, `lc_teammember`, `lc_statusupdate`, **`lc_githubissue`** (the VE from Ep 4 — looks identical to a native table) |
| **`lc_CalculateLaunchReadiness`** | Custom API from Ep 5 | Single-call go/no-go scoring with `Score` + `Verdict` + `Summary` |
| **Dataverse Knowledge** | Ep 3 Part 2 | Grounded retrieval over `lc_knowledgearticle` (4 docs: playbook, policy, spec, postmortem). Fields: `lc_summary` (multiline) + `lc_document` (file column with the full markdown). |
| **Learn MCP** _(optional)_ | Custom connector from Ep 5 | `learn.microsoft.com/api/mcp` — for "how do I X in Power Platform" questions |
| **GitHub MCP** _(optional)_ | Custom connector from Ep 5 | Cross-repo / code search beyond the issues already projected via the VE |

The system prompt
([system-prompt.txt](../../agents/launch-coordinator/system-prompt.txt)) is
the source of truth — both Part 1's `instructions` field and the CS agent's
`Instructions` are copies of it. **Sync rule:** if you change the file, paste
into both places and re-publish.

### Four business skills baked into the prompt

1. **Launch Readiness Checklist** — _always_ invoke `lc_CalculateLaunchReadiness`
   for go/no-go questions; never re-tally gates client-side.
2. **Escalation Policy** — verify a block is real (check the linked
   `lc_githubissue.lc_state` first), then write a `lc_statusupdate` row with
   structured headline (`"[High] <task title> blocked"`).
3. **Status Transition Rules** — each entity has its own status column;
   reject illegal transitions; for engineering tasks, refuse Done unless the
   linked GitHub issue is `closed`.
4. **Knowledge Grounding** _(new in this episode)_ — route questions to
   either Knowledge (background/process), MCP (live state), or **both**
   (questions that mix policy and state). Always cite the article title.

### The Knowledge routing rules in plain English

| Question | Tool |
|---|---|
| _"What's our policy on slipping?"_ | Knowledge → Escalation Policy |
| _"How do we run a launch?"_ | Knowledge → Launch Readiness Playbook |
| _"What did we learn from Q1 Mini?"_ | Knowledge → Postmortem |
| _"What's the status of Q3?"_ | MCP → `lc_launch` |
| _"Which tasks are blocked?"_ | MCP → `lc_task` filter |
| _"Is Q3 ready to ship?"_ | MCP → `lc_CalculateLaunchReadiness` |
| _"Should we slip Q3?"_ | **Both** — Knowledge for policy + MCP for state |
| _"Are we repeating Q1 Mini's mistakes?"_ | **Both** — Postmortem + live tasks |

### Setup in Copilot Studio

1. [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) → your
   environment → **Create** → **New agent**.
2. Name it `Launch Coordinator`. Description: see
   [README](../../agents/launch-coordinator/README.md).
3. **Instructions** field → paste `system-prompt.txt` verbatim.
4. **Tools** → **+ Add** → **Microsoft Dataverse MCP Server (Preview)** →
   pick the same Dataverse env. Tools auto-discovered from your tables and
   Custom APIs (including `lc_CalculateLaunchReadiness`).
5. **Knowledge** → **+ Add** → **Dataverse** → table = `lc_knowledgearticle` →
   include `lc_title`, `lc_summary`, `lc_document` as searchable fields.
   _(Requires the tenant-level "Search support for multiline text and file
   data types" preview flag in PPAC → Environments → your env → Settings →
   Product → Features.)_
6. _(Optional)_ Add the Learn MCP and GitHub MCP custom connectors from Ep 5.
7. **Test** in the right-hand chat panel.
8. **Publish** → **Make available** → toggle the channels you want
   (Teams, Microsoft 365, web).

---

## Part 3 · Local validation

Just like Ep 5, we need a way to verify the agent's _capabilities_ are
correctly wired before pointing a PM at it.
[`episodes/ep-07-the-agent/preflight.py`](../../episodes/ep-07-the-agent/preflight.py) is a
two-mode harness:

```powershell
python episodes/ep-07-the-agent/preflight.py --plan       # Markdown plan for review
python episodes/ep-07-the-agent/preflight.py --run        # Execute, print summary
```

Note: we **can't programmatically invoke** a Copilot Studio agent from a
script (no public eval endpoint yet). What we _can_ do is exhaustively verify
the **substrate** the agent depends on, then ship a manual prompt set for the
in-product Test panel.

### What the harness checks

| # | Pre-flight | Validates |
|---|---|---|
| P1 | `lc_knowledgearticle` table is in `LaunchControl` solution | Knowledge source is exportable |
| P2 | At least 4 `lc_knowledgearticle` records present | All sample docs uploaded |
| P3 | Every record has a non-empty `lc_summary` and a populated `lc_document` | File column upload succeeded |
| P4 | All four categories represented (Policy, Playbook, Spec, Postmortem) | Routing scenarios are covered |
| P5 | `lc_CalculateLaunchReadiness` Custom API exists (re-checking Ep 5) | Custom-API tool is callable |
| P6 | `system-prompt.txt`, `declarativeAgent.json`, README's fenced prompt all match | Sync rule honored |

| # | Smoke tests | Validates |
|---|---|---|
| T1 | OData query: every Knowledge record has searchable text | `lc_summary` is fts-eligible |
| T2 | Smoke-call `lc_CalculateLaunchReadiness("Q3 Widget Launch")` | The agent's go/no-go tool is live |
| T3 | OData query: `lc_githubissue` virtual entity returns rows | Cross-system state still works |

The harness then prints a numbered list of **prompt scenarios** (pulled from
the system prompt's Knowledge Grounding routing table) for you to run
manually in the Copilot Studio Test panel — Knowledge-only, MCP-only, and
"both" — and a checklist of expected behaviors (cite article title, invoke
Custom API, call Knowledge tool first, etc.).

Output (current environment):

```
[ OK ] P1: lc_knowledgearticle in LaunchControl solution           (1842ms)
[ OK ] P2: >=4 lc_knowledgearticle records                          (892ms)
       found 4: Launch Readiness Playbook, Escalation Policy, Q3
       Widget Pro - Product Launch Brief, Postmortem - Q1 Widget Mini
[ OK ] P3: All records have summary + document populated            (734ms)
[ OK ] P4: All 4 categories represented                             (612ms)
[ OK ] P5: CustomAPI lc_CalculateLaunchReadiness exists           (4431ms)
[ OK ] P6: system-prompt is in sync across files                    (12ms)
[ OK ] T1: Knowledge OData query returned content                   (842ms)
[ OK ] T2: Smoke — Score=38.8, Verdict=NO-GO                      (1248ms)
[ OK ] T3: lc_githubissue virtual entity returns rows               (1402ms)

8/8 passing | Manual prompt set: episodes/ep-07-the-agent/test_ep6_prompts.md
```

---

## What's deliberately NOT in this episode

- **Autonomous behavior.** Triggers, flows, scheduled actions land in
  Episode 8. Today's agent is reactive: the user asks, it answers.
- **Skills as standalone artifacts.** The skills are inline in the system
  prompt; pulling them into separate `.skill` files (or the new Power
  Platform Business Skill catalog) is part of the larger skills story.
- **Custom UI.** The agent runs in CS Test, M365 Copilot, and Teams. The
  dashboard surface — a generative Power Apps page deployed via
  `pac model genpage upload` — lands in Episode 10.
- **Code-first runtime.** A Python rebuild of this agent — same skills,
  different stack (GitHub Copilot SDK + Microsoft Agent Framework + the
  Dataverse MCP server) — lands in Episode 9.

---

## What you see on screen

1. **Hook** — a PM pings the agent in Teams: _"Q3 Widget Launch — go or
   no-go?"_ Agent answers in <2s with verdict + summary.
2. **Part 1, M365 Copilot** — open Word, type `@Launch Coordinator what's
   the status of Q3 Widget Launch?` — agent answers from Dataverse.
3. **Part 2, Copilot Studio canvas** — show the agent definition, the four
   tools attached (Dataverse MCP, Custom API, Knowledge, optional MCP
   connectors), and the system prompt with the four business skills.
4. **The three demos** in order:
   - MCP-only: status query → see the tool call in the trace panel
   - Knowledge-only: policy question → tool call to Dataverse Knowledge,
     citation in the response
   - Both: _"Should we slip?"_ → trace panel shows Knowledge call THEN
     Custom API call, synthesized answer
5. **The Test panel's tool-call trace** — _"This isn't pattern-matching.
   These are real tool calls against a governed data plane."_
6. **Test harness** — `python episodes/ep-07-the-agent/preflight.py --plan` to show
   the substrate checklist, then `--run` for green output, then the manual
   prompt set in `test_ep6_prompts.md`.
7. **The punchline:**
   > _"The agent code is zero lines. Everything it can do, the platform
   > already did. The agent just translates conversation into tool calls."_

---

## Files in this episode

| File | Role |
|---|---|
| [`agents/launch-coordinator/system-prompt.txt`](../../agents/launch-coordinator/system-prompt.txt) | Canonical system prompt — single source of truth (paste into CS Instructions field) |
| [`agents/launch-coordinator/declarativeAgent.json`](../../agents/launch-coordinator/declarativeAgent.json) | Part 1 — M365 Copilot declarative agent manifest |
| [`agents/launch-coordinator/manifest.json`](../../agents/launch-coordinator/manifest.json) | M365 Agents Toolkit container manifest |
| [`agents/launch-coordinator/topics.md`](../../agents/launch-coordinator/topics.md) | Topic catalog with explicit OData queries (reference) |
| [`agents/launch-coordinator/README.md`](../../agents/launch-coordinator/README.md) | Setup walkthrough and sample conversations |
| [`data/knowledge/index.yaml`](../../data/knowledge/index.yaml) | Metadata index (title/summary/category/launch) for KB docs |
| [`data/knowledge/*.md`](../../data/knowledge/) | Four sanitized KB articles (playbook, policy, spec, postmortem) |
| [`episodes/ep-07-the-agent/upload_knowledge.py`](../../episodes/ep-07-the-agent/upload_knowledge.py) | Idempotent uploader: upserts records, uploads files via SDK |
| [`episodes/ep-07-the-agent/setup_table.py`](../../episodes/ep-07-the-agent/setup_table.py) | Idempotent table creator (Ep 3 Part 2) |
| [`episodes/ep-07-the-agent/preflight.py`](../../episodes/ep-07-the-agent/preflight.py) | This episode's substrate harness — `--plan` and `--run` |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# (One time) Ensure Ep 3 Part 2 ran:
python episodes/ep-07-the-agent/setup_table.py
python episodes/ep-07-the-agent/upload_knowledge.py

# Verify the substrate is ready
python episodes/ep-07-the-agent/preflight.py --run

# Then in Copilot Studio:
#   1. Create agent "Launch Coordinator"
#   2. Paste agents/launch-coordinator/system-prompt.txt into Instructions
#   3. Tools → + Microsoft Dataverse MCP Server (Preview)
#   4. Knowledge → + Dataverse → lc_knowledgearticle
#      (search: lc_title, lc_summary, lc_document)
#   5. Publish
#
# In M365 Agents Toolkit (VS Code):
#   1. Open agents/launch-coordinator/manifest.json
#   2. Teams: Provision → sideload to your tenant
```

---

## Pitfalls collected during the build

These bit us first time and are now handled by the scripts / documented:

- **`lc_knowledgearticle` not appearing in CS Knowledge picker** — the
  table needs to be in the `LaunchControl` solution AND the tenant-level
  preview flag _"Search support for multiline text and file data types"_
  must be enabled in PPAC. Both are checked by `episodes/ep-07-the-agent/preflight.py`.
- **Lookup `@odata.bind` keys are schema-cased** —
  `lc_LaunchId@odata.bind`, not `lc_launchid@odata.bind`. The lowercase
  form fails with _"undeclared property 'lc_launchid'"_. Affects any code
  that writes a knowledge record with a launch link.
- **Entity set names don't follow naive pluralization** — `lc_launchs`,
  not `lc_launches`. Same gotcha bit Ep 4 + Ep 5 already.
- **Custom API name in CS tool list** — appears as
  `lc_CalculateLaunchReadiness` once you attach the Dataverse MCP server.
  Don't manually configure it as an OpenAPI action — let MCP discover it.
- **`system-prompt.txt` is the source of truth, but Copilot Studio holds a
  copy in the Instructions field** — there's no auto-sync. After every
  prompt change you must paste + Save + Publish manually. The README has
  a "Sync rule" callout.
- **f-string + backslashes** — `getattr(col, "AttributeType", "?")` works
  in `.py` files, breaks in `python -c "..."` one-liners. The diagnostic
  scripts under `scripts/` use real files for this reason.
- **Knowledge cites are only in answers, not the trace** — to verify the
  agent _used_ Knowledge (vs. hallucinating), look at the right-hand trace
  panel for a `Dataverse Knowledge` step. The cite in the body alone is
  not proof.
- **Categories chosen at 10600100+** to leave room above the existing
  `LaunchStatus`/`MilestoneStatus`/`TaskStatus` ranges from Ep 1.

---

## What this unlocks for the rest of the series

- Ep 8 (Autonomous Agents) reuses _exactly_ these business skills and the
  same Dataverse MCP server, but fronts them with event + recurrence
  triggers on **Launch Sentinel**. The conversation surface becomes
  optional — the agent acts without being asked.
- Ep 9 (Code-First Agent) takes the same skill definitions and runs them
  inside ~250 lines of Python — GitHub Copilot SDK as the brain, Microsoft
  Agent Framework as the abstraction, the Dataverse MCP server (stdio) as
  the tool surface. Same skills, different runtime — skills portability
  proven by reuse.
- Ep 10 (Dashboard) renders a generative Power Apps page over the same
  Dataverse — shipped via `pac model genpage upload`, no code-app required.
  Three surfaces (Copilot Studio chat, autonomous, Python) plus a UI — all
  pointed at one substrate.

---

## Next up

**Episode 8 — Autonomous Agents.** Same skills, same MCP server, but now
event-triggered. The Launch Sentinel agent fires when `lc_task.lc_isblocked`
flips to `true` and on a Mon–Fri 08:00 recurrence — writing escalations and
posting digests without anyone in the chat.
