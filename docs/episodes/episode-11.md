# Episode 11 — Agentic Administration

> **Hook:** *"I built the system. Now an agent runs the back office of it. From my terminal, in plain English, with a refusal when it should refuse."*

After ten episodes of building a system **on top of** Dataverse, Episode 11 turns the camera on the **administration of** Dataverse itself. The protagonist is the `dv-admin` skill — a GitHub Copilot CLI plugin that wraps the Dataverse Admin CLI. The point is not the tool; it's the shape of the work: **the platform's own admin surface is now agentic.**

## Why this matters in the arc

By Ep 10, the audience has seen agents on top of business data. Ep 11 closes the loop: even the **operations** of the platform — auditing, plugin trace, cleanup, governance — are conversational. And critically, when you ask the agent to do something dangerous, it **refuses out loud**. That refusal is the safety beat that makes the rest of the episode credible.

If Eps 6–8 prove "agents can read your data," Ep 11 proves "agents can run your admin — with guardrails."

## Pre-record gate

The env needs to be in a specific state for the demo to land. Run the preflight harness first:

```bash
python scripts/test_ep11_locally.py
```

It checks:
- Launch row exists (narrative anchor)
- ≥ 10 backdated `lc_statusupdate` rows tagged `PreQ1Seed::` (so the FetchXML cleanup beat has data to delete)
- Every seeded row's `createdon` is < 2026-01-01 (so the FetchXML filter actually selects them)

If the seeded rows are missing, run:

```bash
python scripts/python/seed_pre_q1_status_updates.py
```

This idempotently creates 12 status updates dated Oct–Dec 2025 with the `PreQ1Seed::` prefix in `lc_title`. Backdating uses Dataverse's `overriddencreatedon` field — the rows really do show `createdon = 2025-10-03` etc., not a backdated metadata column. That's what makes the FetchXML demo realistic.

The remaining manual checks (not scripted, you do them by eye):
- `/plugin list` in Copilot CLI confirms `dv-admin` is installed; capture the version string for the doc
- Audit setting drift exists between the two scopes you'll compare (env-vs-env or table-vs-table — see C2 below)
- All five commands rehearsed end-to-end against the demo env at least once

## The 5-command demo

Each command is a turn in a real Copilot CLI session. The agent confirms before mutating, and the user types the exact prompt below — no shorthand, no preset.

### Command 1 — Enable auditing

**Demo prep:** the night before, turn audit *off* on `lc_task` (or the whole env).

**Prompt:**
> *"Enable auditing on the launch environment so we can track every status change."*

**Expected:** agent reads current setting, shows the diff, asks for confirm, applies. Concise structured output with a green check.

### Command 2 — Plugin trace settings: drift compare

**Risk:** the demo env is a single environment. We may not have a second.

**Two framings, decide on Day -5:**

| Framing | Use when | Demo effect |
|---|---|---|
| **Env vs env** | Second demo env exists | "Drift between dev and prod plugin trace settings — is that intentional?" |
| **Table vs table** *(fallback)* | Single env only | "`lc_task` audits everything; `lc_milestone` audits nothing — is that intentional?" |

Either way, the punchline is the same: **config drift detection at scale, in conversation.** Bake the chosen framing into `episode-11.md` Section 3 once decided.

**Prompt (env-vs-env):**
> *"Compare plugin trace settings between dev and prod and tell me anything that's different."*

**Prompt (two-table):**
> *"Compare audit settings between the lc_task and lc_milestone tables in this environment."*

### Command 3 — FetchXML cleanup

**Demo prep:** done by `seed_pre_q1_status_updates.py` (12 rows, `PreQ1Seed::` prefix, dated Oct–Dec 2025).

**Prompt:**
> *"Clean up StatusUpdate records that were created before Q1 2026."*

**Expected agent flow:**
1. Builds FetchXML with `condition attribute="createdon" operator="lt" value="2026-01-01"`
2. Runs the FetchXML as a count first — *"Found 12 records matching."*
3. **Asks for confirmation** before deleting
4. Deletes; confirms 12 deleted

The on-camera moment is the agent showing the FetchXML it generated **before** running it. That's the "I trust this because I can see it" beat.

### Command 4 — Refused bulk delete (the safety beat)

**Prompt:**
> *"Delete all records in the Launches table."*

**Expected:** agent **refuses**. The exact refusal text gets pulled into the LinkedIn caption — that's the on-camera quote we're looking for. Something to the effect of: *"I'm not going to do that. Bulk-deleting the Launches table would remove your entire launch history. If you really want this, here's the shape of the FetchXML — review it and run it yourself."*

This is the most important beat in the episode. **Without it, "agents can run your admin" sounds reckless. With it, it sounds responsible.**

### Command 5 — Read-only close

**Prompt:**
> *"What's the plugin trace log retention setting on this environment?"*

A small read to close on a positive note. Demonstrates that the agent does the small things too, not just the dramatic ones.

## The episode in 90 seconds

### Beat 1 — Hook (~10 sec)

Cold open: terminal, blinking prompt. Voiceover: *"My business runs on Dataverse. Agents help my team do the work. But who runs the platform?"*

### Beat 2 — Five commands (~60 sec)

Cuts of the five commands. Each one ~10–12 sec, structured terminal output framed center-stage. **The refusal is held longer than the others** — the agent's exact refusal text fills the screen for ~5 sec.

### Beat 3 — Browser-vs-chat split-frame (~15 sec)

Static frame:

```
┌──────────────────────────┬──────────────────────────┐
│  THE OLD WAY             │  EP 11 — DV-ADMIN        │
│  Power Platform Admin    │  Copilot CLI             │
│  Center                  │                          │
│                          │                          │
│  navigate, click, click, │  type the question.      │
│  read, click, repeat     │  agent shows the diff.   │
│                          │  agent asks before        │
│                          │  changing anything.       │
└──────────────────────────┴──────────────────────────┘
```

Caption: *"Same admin actions. Less navigation. Audit trail by default."*

### Beat 4 — Bridge to Ep 12 (~5 sec)

> *"The platform runs the system. The system runs the launch. Next episode: shipping it."*

## Risks & guardrails callout

In the doc and the recording, dedicate ~10 sec to the refusal — what it means, why it matters, what the agent's actual policy boundary is. This is where viewers' "but isn't this dangerous?" question gets answered before they ask it.

## Files touched

- `docs/episodes/episode-11.md` (this file)
- `scripts/test_ep11_locally.py` — preflight harness (4 checks)
- `scripts/python/seed_pre_q1_status_updates.py` — backdated demo data seeder

No solution components. No new tables, columns, plugins, or actions. The only env mutation is 12 backdated `lc_statusupdate` rows the demo will then delete on camera.

## Cleanup after recording

The FetchXML cleanup demo deletes the 12 seeded rows on camera. To re-rehearse:

```bash
python scripts/python/seed_pre_q1_status_updates.py            # idempotent, no-op if 12+ exist
python scripts/python/seed_pre_q1_status_updates.py --force    # wipes + re-creates
```

## Cross-references

- **Ep 5 / Ep 7 / Ep 8** — three runtimes of agents on top of Dataverse. Ep 11 is the **fourth** runtime: an agent for Dataverse itself.
- **Ep 9** — gen page is unaffected by audit/plugin-trace toggles; this is admin work that doesn't touch app surfaces.
- **Ep 12** — closes the campaign with the orchestra montage; Ep 11 is the last "individual capability" episode.
