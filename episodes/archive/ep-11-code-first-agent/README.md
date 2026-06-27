# Episode 11 — The Code-First Agent

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ GitHub Copilot SDK · ⭐ Microsoft Agent Framework · ⭐ Dataverse MCP server (stdio) · ⭐ Skills hydrated from Dataverse on every run
**Layer:** 🔵 Layer 2 (skills portability proven across **three** runtimes)
**Coding agent:** the agent we build IS the artifact (Python, ~250 LOC including the rich-rendered UX)

---

## The hook

> _"Episode 9 was Copilot Studio. Episode 10 was the autonomous Sentinel. Today's agent? Pure Python. Different runtime, different stack — same brain. Three agents. One source of truth. Edit the skill in Dataverse, all three change."_

Episodes 6 and 7 lived inside Copilot Studio's hosted runtime. Beautiful demos, but viewers naturally ask: _"yeah but I write code — what does this look like in my editor?"_ Episode 11 is the answer. We rebuild the Launch Coordinator as a **code-first Python agent** using:

- **GitHub Copilot SDK** as the LLM brain (`github-copilot-sdk`)
- **Microsoft Agent Framework** as the agent abstraction (`agent-framework-github-copilot`)
- **Dataverse MCP server** as the tool surface (`npx @microsoft/dataverse mcp <orgUrl>`, stdio)
- **Same business skills** as Episodes 6 and 7, pulled live from Dataverse on every run

The point isn't to do anything the hosted agents can't. The point is: **the brain is portable**. Skill markdown stored in Dataverse drives behavior across three completely different runtimes — Copilot Studio chat (Ep 9), Copilot Studio autonomous (Ep 10), and now a 250-line Python program (Ep 11).

---

## The narrative beat

```
$ python agents/launch-coordinator-py/agent.py

╭──── Launch Coordinator (Python) ────────────────────────╮
│ Three runtimes, one brain.                              │
│ LLM brain      github-copilot-sdk + agent-framework     │
│ Editable brain Dataverse skills (pulled on every run)   │
│ Tool surface   Dataverse MCP server (stdio)             │
│ Environment    https://&lt;your-org&gt;.crm.dynamics.com         │
╰──── Episode 11 - the code-first agent ───────────────────╯

⠋ Pulling skills from Dataverse...

🧠  Skills synced from Dataverse
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Skill                      ┃ Unique name                   ┃ Lines ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Launch Readiness Checklist │ lc_launch_readiness_checklist │    38 │
│ Escalation Policy          │ lc_escalation_policy          │   257 │
│ Status Transition Rules    │ lc_status_transition_rules    │    34 │
│ Launch Readiness Digest    │ lc_launch_readiness_digest    │   164 │
└────────────────────────────┴───────────────────────────────┴───────┘

Prompt: Run the launch readiness checklist for the launch named 'Q3 Widget Launch'.

──── Agent run ────
⠹ starting Dataverse MCP server, model warming up...
(first token after 23.4s)

I'll invoke the Custom API per the skill's instructions and report the result.

## Launch Readiness — Q3 Widget Launch
**Verdict: NO-GO**
**Score: 38.8 / 100**
...

╭──── Verdict ────╮
│ Verdict: NO-GO  │
╰─────────────────╯
```

The **brain-sync table** is the Episode 11 money shot. Every line in that table came from a `GET /api/data/v9.2/skills` call against the Dataverse environment, two seconds before the agent started. Edit a skill in Dataverse, re-run, the line counts shift — and so does the verdict downstream.

---

## What's in the repo

```
agents/launch-coordinator-py/
├── agent.py            # ~250 LOC: GitHubCopilotAgent + MCP wiring + rich UI
├── sync_skills.py      # ~90 LOC: GET /skills, write ./.skills/<slug>.md
├── requirements.txt    # agent-framework-github-copilot, rich, python-dotenv, requests
├── .env.example        # DATAVERSE_URL only - everything else is cached creds
├── README.md           # prerequisites, run instructions, troubleshooting
└── .skills/            # gitignored - hydrated on every run
    ├── INDEX.md
    ├── launch-readiness-checklist.md
    ├── escalation-policy.md
    ├── status-transition-rules.md
    └── launch-readiness-digest.md
```

---

## Architecture decisions worth pointing at on camera

### 1. Skills are pulled at startup, not discovered via MCP

The Dataverse MCP server *does* expose skills — `describe('skills/<Name>')` works in Copilot Studio (Eps 6, 7). But for a code-first runtime, we made a different call:

> **At agent startup, run `sync_skills.py` to pull every skill record over REST and write `./.skills/<slug>.md` to disk. The agent's instructions tell it to read from disk, not from MCP.**

Why? Three reasons:

1. **It's recording-friendly.** The brain-sync table is a clean visual moment. "Here are the skills that just landed in this terminal session, freshly pulled from Dataverse."
2. **It's deterministic.** No flakiness around whether the underlying Copilot CLI's MCP plumbing surfaces tool calls back to the host process — and no race conditions where the agent decides to `describe` a skill at minute 3 of a long reasoning trace instead of minute 0.
3. **It cleanly mirrors how production engineering teams ship behavior.** Source-of-truth lives in a managed system (Dataverse), runtime caches it locally, runtime is reproducible. Same shape as feature flags, same shape as config services.

The local `.skills/` folder is `.gitignored` and rewritten on every run. Mutate it manually and your edits vanish — exactly like a cache should behave.

### 2. The MCP server is still wired in

We keep the Dataverse MCP stdio server registered with the agent (`mcp_servers["dataverse"]`) because the skill _itself_ tells the agent to call `lc_CalculateLaunchReadiness` (a Custom API) and run `read_query` against `lc_launch` / `lc_milestone`. Skills do behavior; MCP does data.

### 3. Permission gating — the gotcha

GitHub Copilot SDK denies _all_ actions by default unless you register an `on_permission_request` handler. Without it, the agent's first MCP call comes back as "permission denied" and the agent (correctly) gives up. We register `PermissionHandler.approve_all` (auto-approve everything). For production you'd narrow this; for a single-purpose agent that the developer launches, approve-all is the right default.

```python
from copilot.session import PermissionHandler

agent = GitHubCopilotAgent(default_options={
    "instructions": INSTRUCTIONS,
    "mcp_servers": {"dataverse": {...}},
    "on_permission_request": PermissionHandler.approve_all,
    "timeout": 300,
})
```

### 4. Streaming + rich-rendered UX

The agent uses `agent.run(prompt, stream=True)` and renders tool calls (`→ read_query  {...}`), tool results (`← {result}`), and assistant text deltas live with the `rich` library. A spinner runs during the warmup gap so the user can see the agent is alive even when the first token takes 20 seconds.

---

## Three runtimes, one brain

| Runtime | Episode | Edit surface | Auth | Skill load |
| --- | --- | --- | --- | --- |
| **Copilot Studio chat** | Ep 9 | `make.powerautomate.com` UI | M365 user | MCP `describe('skills/...')` |
| **Copilot Studio autonomous** | Ep 10 | Same UI, autonomous binding | Service principal (CIB) | MCP `describe('skills/...')` |
| **Python (code-first)** | Ep 11 | VS Code, your editor | GitHub Copilot OAuth + Azure CLI | REST `GET /skills` → `./.skills/*.md` |

All three:
- Read the same `Launch Readiness Checklist` skill record in Dataverse
- Call the same `lc_CalculateLaunchReadiness` Custom API
- Return the same verdict for the same launch
- Update behavior the moment the skill's `body` is edited in Dataverse

---

## Recording cues

| Beat | Camera focus | Talking point |
| --- | --- | --- |
| 0:00 | VS Code: `agents/launch-coordinator-py/agent.py` | "About 250 lines. That's the whole agent." |
| 0:15 | Terminal: `python agent.py` | "Watch the brain land." |
| 0:30 | Brain-sync table appears | "Four skills, just pulled from Dataverse." |
| 0:45 | Spinner running | "Spawning the MCP server, warming up the model." |
| 1:00 | First token, then streamed response | "Same logic Ep 9 ran. Same verdict Ep 10 emails." |
| 1:30 | Verdict panel: NO-GO | "Edit the skill in Dataverse — watch the verdict change." |
| 1:45 | Power Apps: edit Launch Readiness Checklist body | (cut) |
| 2:00 | Terminal: re-run agent, line count shifts | "One brain. Three agents. Code-first or low-code, your choice." |

---

## Prerequisites for replication

- Windows / macOS / Linux with **Python 3.11+** and **Node 18+** (for `npx @microsoft/dataverse`)
- `pip install -r agents/launch-coordinator-py/requirements.txt`
- `copilot auth login` (one-time GitHub OAuth)
- `pac auth list` showing the target Dataverse environment authenticated
- `npx @microsoft/dataverse auth create` cached for the same environment (used by the MCP subprocess)
- `.env` with `DATAVERSE_URL=https://<your-org>.crm.dynamics.com`

---

## Test harness

`episodes/ep-11-code-first-agent/preflight.py` is the preflight equivalent of Ep 10's harness. It verifies:

- **P1** `agent.py` imports cleanly
- **P2** `sync_skills.py` exposes `sync()` with the expected signature
- **P3** `agent.py` contains the skills-as-brain literal (`./.skills/launch-readiness-checklist.md`)
- **P4** `agent.py` registers the Dataverse MCP server with the right command shape
- **P5** `agent.py` registers `PermissionHandler.approve_all` (the auto-approve gotcha)
- **P6** `requirements.txt` pins `agent-framework-github-copilot`, `rich`, `python-dotenv`, `requests`
- **P7** `agents/launch-coordinator-py/.skills/` is in `.gitignore`
- **S1** Live: run `sync_skills.sync()` against the configured environment, assert ≥1 skill written

```
python episodes/ep-11-code-first-agent/preflight.py
```

---

## Next up

**Episode 12 — The Dashboard.** Three agents are populating the same tracker.
Time to surface it. We describe a Launch Command Center in plain English to
Power Apps and ship it as a **generative Power Apps page** via
`pac model genpage upload` — typed Dataverse access, Fluent UI, sitemap
registration, no Vite project. The data model and the agents were AI-authored;
now the UI is too.
