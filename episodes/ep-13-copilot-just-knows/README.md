# Episode 13 — Copilot Just Knows

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Dataverse Intelligence (preview) · ⭐ Native M365 Copilot grounding over `lc_launch` / `lc_milestone` / `lc_task` / `lc_teammember` — no agent, no plugin, no MCP
**Layer:** 🟣 Layer 3 (the conversational surface — but here, _Microsoft's_ surface)
**Coding agent:** _None._ This is the platform answering on its own.
**Runtime:** M365 Copilot (Word side panel, Teams, `copilot.microsoft.com`)

---

> **Hook:** *"Eight episodes building a system. Now I open M365 Copilot, ask in plain English, and it just answers — no agent, no plugin, no MCP."*

This is the smallest episode in the campaign and it's the one that lands the platform punchline. Every prior episode put **something** between the user and the data — a custom action (Ep 5), a Copilot Studio agent + MCP (Ep 9), an autonomous agent (Ep 10), a code-first agent (Ep 11), a generative page (Ep 12). Ep 13 takes all of it away.

The data model from Ep 1, the relationships from Ep 3, the prompt column from Ep 3, the team-member assignments from Ep 3 — Copilot reads them natively. **You built the schema. Microsoft handles the grounding.**

## Why this matters in the arc

This is the "you don't have to build everything" episode. After eight episodes of *making* — agents, skills, custom actions, virtual entities — the message is: **the moment your data is in Dataverse, the most popular Copilot in the world already knows how to read it.** No connector. No tool registration. No prompt engineering.

It also sets up the Ep 9 ↔ Ep 13 split-screen punchline: same business question, two surfaces. **Custom agent for control. Native Copilot for reach.**

## Pre-record gate (load-bearing)

Two toggles, in this order:

1. **M365 Admin Center** — confirm the tenant has Dataverse Intelligence (Copilot grounding) enabled. **Copilot → Settings → Connectors / Data sources** pane.
2. **PPAC (Power Platform Admin Center)** — environment-level toggle: *Features → Dataverse Intelligence* (preview). Flip on; **note the time.**

> **⚠ Indexing delay: 10–60 minutes.** Bake it into recording day. If you flip the env toggle and start filming, you will record three "I don't have access to that data" responses and a punchline-shaped hole.

**Smoke test before claiming the toggle works:**
Open M365 Copilot and ask `What's in the Launches table?` — if it returns column names, you're grounded. If after 60 min it still says "I don't have access," escalate.

### Prime the context (the step everyone skips and regrets)

Copilot grounds against the most-recently-used Power Apps **environment**, not the most-recently-used app. Day-of sequence:

1. Open the Ep 12 gen page (Launch Command Center) in the demo environment. Click around for 30 seconds.
2. Close the tab.
3. Open M365 Copilot. The cleanest visual is the Word side panel; Teams or `copilot.microsoft.com` also work.
4. Start the demo prompts.

Without this priming step, viewers re-trying the demo with a different MRU env see "I don't see any launches" and the punchline dies. **Document this in the script as a hard pre-record step.**

## The episode in 90 seconds

### Beat 1 — "I don't need a UI for this." (~20 sec)

Cold open from Ep 12: gen page is open, kanban is full, looks great. Pause.

> *"This is great when I'm in the Launch app. But I'm not always in the app. Sometimes I'm in Word writing a status update. Or in Teams in a 1:1. And I just want to ask — and get an answer."*

Switch to M365 Copilot in Word side panel.

### Beat 2 — Three prompts, three answers (~50 sec)

The prompts are designed to prove three things in order: **read works**, **cross-table traversal works**, **filter + free text works.**

**Prompt 1 — Read.**
> *"What's the status of the Q3 Widget Launch?"*

Expected: launch name, status (InProgress), target date (Sep 15, 2026), and a one-line description from `lc_description`. Maybe milestone counts if Copilot reaches into the relationship.

**Prompt 2 — Cross-table traversal.**
> *"Who's assigned to the most tasks for the Q3 Widget Launch?"*

Expected: `Alex Chen` and `Riley Nguyen` (15 each), then `Priya Patel` (10). Tests the `task → milestone → launch` chain plus the `task → teammember` lookup. Both directions of the data model from Ep 3 paying off.

**Prompt 3 — Filter + free text.**
> *"Show me the blocked tasks for the Q3 Widget Launch and why they're blocked."*

Expected: 8 tasks, each with a sentence of `lc_blockerreason` text. This is the prompt that makes the "free text columns just work" point — no SQL, no OData, no prompt engineering.

**Backup prompt** (only if one of the three flops on the day):
> *"Summarize the risks for the Q3 Widget Launch."*

Returns the prompt-column risk summary stored on the launch row from Ep 1. Different surface, same data.

**On-day fallback rule:** if a prompt returns "I don't have access," wait 5 min, re-prime context, retry. If it fails 3×, swap the failing prompt with the backup and document the gap as an Ep 15 follow-up. Never fight live.

### Beat 3 — The split-screen punchline (~20 sec)

Cut to a static frame held for ~6 sec:

```
┌──────────────────────────┬──────────────────────────┐
│  EP 6 — CUSTOM AGENT     │  EP 10 — NATIVE COPILOT  │
│  (Copilot Studio)        │  (M365 Copilot)          │
│                          │                          │
│  same question →         │  same question →         │
│  agent uses MCP +        │  Copilot just answers,   │
│  skill + verdict action  │  grounded on Dataverse   │
│                          │                          │
│  "When you need control" │  "When you need reach"   │
└──────────────────────────┴──────────────────────────┘
```

Caption / voiceover:

> *"Same data. Two surfaces. Pick the one that fits."*
> *"You don't always need an agent. You don't always not. Build for the surface your user is already in."*

Bridge to Ep 14 (one sentence, end of episode):

> *"Now the system is in production. The next episode is about managing it."*

## Why this is a doc-only commit

Ep 13 produces no code, no agent, and no app. The only artifact in the repo is this document, the recording, and the LinkedIn post. The "feature" being shown is **Microsoft's** — it ships with Dataverse Intelligence whether or not we touched anything.

That's the message: **the more your business state lives in Dataverse, the more leverage you get from things you didn't build.**

## Pre-record checklist

Run before the camera turns on:

- [ ] `python scripts/python/audit_ep11_prompts.py` — prompt-data preflight is green
- [ ] M365 Admin Center → Dataverse Intelligence enabled
- [ ] PPAC → demo env → Dataverse Intelligence on, indexing delay survived (≥ 60 min since flip)
- [ ] Smoke prompt (`What's in the Launches table?`) returns grounded answer
- [ ] Ep 12 gen page opened + clicked through in demo env (priming)
- [ ] Word + Copilot side panel open and signed in as the demo user
- [ ] Recording: prompts typed live, not pasted (pasting reads as "AI is filling the box")
- [ ] Backup prompt staged in clipboard in case one flops

## Files touched in this episode

- `episodes/ep-13-copilot-just-knows/README.md` (this file)
- `scripts/python/audit_ep11_prompts.py` — prompt-data preflight (no environment changes)

No solution components. No tables, columns, plugins, or actions. **The platform did the work.**

## Cross-references

- **Ep 3** — data model rows + the `lc_risksummary` prompt column on `lc_launch` feed the backup prompt
- **Ep 3** — task ↔ milestone ↔ launch wiring + teammember assignments make Prompt 2 (traversal) work
- **Ep 9** — custom Copilot Studio agent; the left side of the split-screen
- **Ep 12** — gen page used to prime context before recording

---

## Next up

**Episode 14 — Agentic Administration.** Native M365 Copilot proved the data
plane can answer without an agent. Episode 14 flips to the **management plane**:
capacity, audit, cleanup, and blast-radius — all agent-driven, all from the
terminal.
