# Episode 14 — Agentic Administration

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Copilot CLI as the admin surface · ⭐ `dataverse@awesome-copilot v1.0.0` plugin · ⭐ Capacity / audit / cleanup / agent blast-radius — all by conversation
**Layer:** 🟠 Layer 4 (the management plane)
**Coding agent:** Copilot CLI (no new agent authored — today's tooling _is_ the admin agent)
**Runtime:** Copilot CLI + the `dataverse@awesome-copilot` plugin invoking `scripts/python/admin/` + episode scripts

---

> **Hook:** *"Eleven episodes ago, this launch was a spreadsheet. Tonight, the platform that runs it answers admin questions in chat."*

Every prior episode in this campaign builds **on** the platform — data model, business skills, agents, gen page, native Copilot grounding. Ep 14 turns the camera on the **platform itself**: auditing, capacity, cleanup, agent governance. The admin work that lived in admin centers and PowerShell scripts is now a conversation.

## Why this matters in the arc

This is the only episode that's about **operating** the platform rather than building **on** it. After ten episodes of "look what you can build," the question every admin in the audience is asking is *"…and how do I run this in production?"* Ep 14 answers it.

## The five proof points

These aren't five tools. They're five questions an admin asks every week — and five answers the management plane returns in the time it takes to type the question.

### 1. Auditing on by conversation

> *"Enable auditing on the launch environment so we can track every status change."*

Agent reads the current setting, shows the diff, asks for confirm, applies. The compliance toggle that used to be a four-tab navigation is now a sentence.

**Demo prep:** turn audit OFF on at least one table the night before, so the diff is visible.

### 2. Capacity by conversation

> *"What's burning capacity in this environment?"*
> *"Which environments in my tenant are closest to their limits?"*

Agent calls `episodes/ep-14-agentic-admin/capacity_report.py`, parses the structured output, presents the headline numbers. Three pools (Database, File, Log), per-environment + tenant-wide top-N.

**Live data we'll see on camera (verified by preflight):**

| Pool | Used | Allocated | Util |
|---|---|---|---|
| Database | 264.5 MB | 1.00 GB | 25.8% |
| **File** | **6.37 GB** | **6.37 GB** | **100% ← AT CAP** |
| Log | 0.07 MB | 0.07 MB | 100% |

**The on-camera moment:** the agent flags that the File pool is at cap — and answers the next question (*"which environments are worst?"*) by scanning all 35 envs in the tenant in one call. **Nobody answers this in 30 seconds today.**

### 3. Bulk cleanup, auditable not destructive

> *"Clean up StatusUpdate records from before Q1 2026."*

Agent flow:
1. Builds the FetchXML filter (`createdon < 2026-01-01`)
2. **Runs it as a count first** — *"Found 12 records matching."*
3. **Asks for confirmation** before deleting
4. Deletes; confirms 12 deleted

The on-camera beat is the agent showing the FetchXML it generated **before** running it. *"I trust this because I can see exactly what it's about to do."*

**Demo prep:** `seed_pre_q1_status_updates.py` already created 12 backdated `lc_statusupdate` rows with the `PreQ1Seed::` prefix, dated Oct–Dec 2025. The script uses `overriddencreatedon` so the actual `createdon` field stores 2025-10-03 etc. — the FetchXML filter selects them for real, not via a metadata workaround.

### 4. Agent blast-radius is one prompt away

> *"Show me everything the agents in this environment can read or write."*

Agents have spread through the campaign: Copilot Studio Coordinator (Ep 8), Sentinel autonomous agent (Ep 9), the code-first agent (Ep 10). An admin needs the **standing report**: what tables, what actions, by which agent — without crawling each one's settings page.

The pitch: *"Before I approve the next agent into production, what's the surface area of the ones I already have?"*

For the recording, the agent calls `episodes/ep-14-agentic-admin/agent_blast_radius.py`, which reads four Dataverse tables — `bot`, `botcomponent`, `workflow`, `connectionreference` — and emits a per-agent inventory: actions (MCP-backed flagged), generative-orchestration on/off, external triggers, knowledge sources, plus a tenant-wide connector-usage roll-up.

**Live data we'll see on camera (verified by preflight):** 3 custom agents in this env — **Launch Coordinator**, **Launch Sentinel**, plus the `Test` agent. Each one's MCP wiring, triggers, and gen-orchestration status are right there in the output. Sentinel's `Daily Trigger` + `When a task is blocked` make explicit what was implicit in Ep 9. Plus 31 pre-built Sales/Service template agents that any admin would also need to govern (collapsed by default with `--custom-only`).

The on-camera moment: *"This is every agent that can move data in this environment, and what each one can reach. One prompt. No portal navigation."*

### 5. The chat is the audit log

The fifth proof point isn't a separate command — it's the **frame** the other four sit in. Every prompt typed, every agent action, every diff and confirmation lives in one conversation. The conversation is exportable. The conversation is the record.

Voiceover beat:

> *"Whatever I just did to my environment — what changed, why I changed it, who saw it before I changed it — is in this chat. The chat IS the audit log."*

## The episode in 90 seconds

### Beat 1 — Cold open (~10 sec)

Visual: PPAC dashboard — the "old way" — split-screened with a terminal.

> *"This is how I run the platform today. This is how I want to run it tomorrow."*

### Beat 2 — Four prompts, four answers (~60 sec)

The four mutating/reading prompts (#1–#4 above). ~15 sec each. The capacity prompt (#2) gets the longest hold because the on-camera moment — agent says "File pool at cap, here's the tenant-wide view" — is the strongest single beat.

### Beat 3 — The audit-log frame (~15 sec)

Hold the chat scrollback. Voiceover lands #5: the chat IS the audit log.

```
┌──────────────────────────────────┬────────────────────────────────┐
│  PPAC                            │  COPILOT CLI                   │
│  (the old admin surface)         │  (the new admin surface)       │
│                                  │                                │
│  navigate, click, click, read,   │  ask. read the diff.           │
│  click, repeat                   │  approve. done.                │
│                                  │                                │
│  audit trail: SAS log somewhere  │  audit trail: this chat        │
└──────────────────────────────────┴────────────────────────────────┘
```

Caption: *"Same admin actions. Less navigation. Audit trail by default."*

### Beat 4 — Bridge to Ep 15 (~5 sec)

> *"The platform runs. The system runs. Next episode: shipping the launch."*

## Pre-record gate

**Agent runtime: Copilot CLI** with the existing `dataverse@awesome-copilot v1.0.0` plugin. Backing scripts live in `scripts/python/admin/`; the agent invokes them directly. No new skill is being authored for this episode — the point is that today's tooling already lets an admin run the management plane from chat.

Run before camera turns on:

```bash
python episodes/ep-14-agentic-admin/preflight.py
```

Six checks. All green at time of writing:

- ✅ Launch row exists
- ✅ Pre-Q1 seeded status updates ≥ 10 (cleanup beat)
- ✅ Every seeded row's `createdon` < 2026-01-01
- ✅ BAP admin API reachable (capacity beat)
- ✅ Demo env visible in tenant list
- ✅ Capacity endpoint returns ≥ 3 pools (currently flags File + Log at 100%)

Manual checks (not scripted):
- Audit setting OFF on at least one table (so the audit-on prompt has a visible diff)
- All 4 demo prompts rehearsed end-to-end at least once in Copilot CLI; capture exact agent output for the recording script

## Files in this episode

| Path | Role |
|---|---|
| `episodes/ep-14-agentic-admin/README.md` | This document |
| `episodes/ep-14-agentic-admin/preflight.py` | 6-check preflight harness |
| `scripts/python/seed_pre_q1_status_updates.py` | Backdated cleanup-target seeder |
| `episodes/ep-14-agentic-admin/capacity_report.py` | Capacity beat (#2) — env + tenant-top |
| `episodes/ep-14-agentic-admin/agent_blast_radius.py` | Agent governance beat (#4) — per-agent inventory |

No solution components. No new tables, columns, plugins, or actions. The only env mutation is 12 backdated status updates the demo deletes on camera.

## Follow-ups (not blockers for the doc, but blockers for recording)

- [ ] Toggle audit OFF on at least one table the night before so prompt #1 has a visible diff
- [ ] Capture exact agent transcript output from each of the 4 prompts for the LinkedIn caption

## Cross-references

- **Eps 6 / 7 / 8** — the three agent runtimes whose blast-radius proof point #4 reports on.
- **Ep 1** — `lc_statusupdate` was created here; the cleanup beat (#3) deletes pre-Q1 rows from this table.
- **Ep 15** — closes the campaign with the orchestra montage; Ep 14 is the last "individual capability" episode.

---

## Next up

**Episode 15 — Full Orchestra + Your Turn.** Six surfaces fire in sequence
on the same launch row — gen page, Custom API, Python report, GitHub issues
via the virtual entity, M365 Copilot, "Mark Shipped." Then the camera turns
to the viewer: `git clone`, one `python` command, a row in their own env.
The repo flips public the moment Ep 15 drops.
