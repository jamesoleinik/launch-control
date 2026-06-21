# Episode 8: Recording script

Producer cues, the verbatim prompts to type on camera, B-roll timing, and
pre-record / between-takes resets. The README is the "how do I reproduce this"
doc, [`REBUILD.md`](REBUILD.md) is the ordered build runbook, and this file is
the "what do I do on camera" doc.

Target length: **~2:10** (matches the recorded video). One framing beat (Part 0),
three build parts, one runtime payoff in Cowork, plus an 11s intro and an 8s
outro. Recorded beats: 11s intro · 18s P0 · 19s P1 · 26s P2 · 23s P3 · 25s payoff
· 8s outro. Spoken VO is ~310 words at roughly 2.4 words per second, the same
cadence as Episodes 6 and 7.

---

## Intro (0:00–0:11)

**Shape:** Value-first, live in Cursor. One 8-second beat. We open inside Cursor,
live on our Dataverse environment through the Dataverse skills plugin: the
`dataverse-security` skill referenced in the composer and `DATAVERSE_URL` printed
in the terminal. A stacked
preview on the right is the two consumers we are about to govern with one model:
on top the RBAC visualizer app (`apps/rbac-visualizer/`) with the row-count panel
and the PII team table; below it a Cowork chat answer listing the launch team
with **emails redacted** (`a#########@example.test`). Launch name `Q3 Widget
Launch` visible. A small `EPISODE 08` badge in the top-left corner from frame 1.

**Intro VO (written form, also opens the LinkedIn post; the beat table has the tighter on-camera cut):**

> *"If you are building AI around sensitive business data and business-critical
> processes, this one is for you. Our Dataverse skills plugin is now live in
> Cursor, and I am going to use that integration to build one security model for
> enterprise scale: the same rules govern the application and the AI agents beside
> it, so the platform, not each client, decides which rows, which columns, and
> which values come back masked for every one of them."*

---

## What the viewer sees, second by second

| Time | What's on screen | VO line | On-screen overlays (self-contained, readable without audio) |
|---|---|---|---|
| **0:00–0:11** ⭐ **Intro · Live in Cursor · 11s** | Cursor open and live on Dataverse through the Dataverse skills plugin (the `dataverse-security` skill in the composer, `DATAVERSE_URL` in the terminal). A stacked preview on the right shows the two consumers we govern with one model: the RBAC visualizer app and a Cowork answer with emails redacted. `EPISODE 08` badge top-left from frame 1. | "Building AI on sensitive data? Our Dataverse plugin is now live in Cursor, and I use it to build one security model for the app and its agents." | ⬇ 0:00 **Live in Cursor, using the Dataverse skills plugin** → 0:05 **One security model for an enterprise app and its AI agents** |
| **0:11–0:29** ⭐ **Part 0 · One skill, the whole model (18s)** | Cursor open. `@`-mention the `dataverse-security` skill and `REBUILD.md`. Cursor confirms it has the model (row-level, column-level, masking, and per-agent) and prints `DATAVERSE_URL` from `.env`. Hold on the confirmation. | "Security in Dataverse works three ways: which rows come back, which columns come back, and whether a value comes back masked. I taught Cursor that model once as a skill. Now it builds the whole thing from the runbook, against a clean environment." | ⬇ **Dataverse can implement any security model: securing rows, columns, and masking values** |
| **0:29–0:48** ⭐ **Part 1 · Row-level: same query, different lens (19s)** | Cursor authors and runs `setup_simple_rbac.py`: four roles, four owner teams. Hard cut to the visualizer. Flip the persona dropdown: Member shows **4 tasks**, Owner and Viewer **12**, Admin **blank**. Same query each time. | "Part one, row-level. Four roles, each tied to an owner team at a different depth. I run one launch query as four personas. The Member sees only the four tasks they own; the Owner and Viewer see all twelve. Same query, different lens, enforced by the role." | ⬇ **Row-level security: a Member sees 4 tasks, an Owner sees all 12** |
| **0:48–1:14** ⭐ **Part 2 · Column-level: mask the email, hide the name (26s)** | Cursor authors and runs `setup_field_security.py`. Cut to the visualizer PII table reading as a non-admin profile member. Flip the email toggle: `lc_email` goes from clear to `a#########@example.test`. Flip the name toggle: `lc_fullname` disappears. `lc_name` stays as `TM-001`. | "Part two, column-level, on the team's personal data. Two different levers. The email gets a masking rule, so it comes back redacted on every read. The full name gets pure column security, so it is omitted entirely for anyone outside the profile. The primary key is just a non-personal ID, so the table is still useful with zero PII exposed." | ⬇ **Column-level security: the email comes back masked, the full name hidden** |
| **1:14–1:37** ⭐ **Part 3 · Per-agent: scope the agent itself (23s)** | Cursor runs `setup_agent_security.py`. Output shows `removed role: System Administrator`, `ensured role: Basic User`, `ensured role: lc Owner`. Then the read-back: `teammembers=4  fullname=<omitted>`. | "Part three, the agent is a user too. The Cowork connection is a real application user that until now inherited System Administrator, which bypasses column security. So I scope it down. Now it reads every row it needs, but the secured name comes back omitted. Effective access is the intersection of the human and the agent." | ⬇ **Define the security model once in Dataverse; every connected agent inherits it (even Cowork)** _(this single overlay holds through the Payoff and end card)_ |
| **1:37–2:02** ⭐ **Payoff · Runtime enforcement in Cowork (25s)** | Cowork chat fullscreen, signed in as the launch-owner demo account. Paste the team prompt. Answer lists four members, emails **redacted**. Cut to a terminal: run `toggle_email_mask.py --off`. Re-ask the **same** prompt. The four real addresses come back in cleartext. | "Now the payoff. Notice I am not building anything; I am watching Dataverse enforce it at runtime through Cowork. I ask for the team's emails. Masking on, they come back redacted. I turn masking off and ask the exact same question. Same agent, same human, same prompt. Cleartext. The platform enforced it on the read, not the agent." | ⬇ _(same overlay holds: **Define the security model once in Dataverse; every connected agent inherits it (even Cowork)**)_ |
| **2:02–2:10** | End card. *"Next: Episode 9: The Agent."* `github.com/jamesoleinik/launch-control` | "Connect any agent you like; what it reads is the platform's call. Security model complete, now we start building the agent fleet." | ⬇ _(same overlay holds: **Define the security model once in Dataverse; every connected agent inherits it (even Cowork)**)_ |

---

## Why the watcher should care

- **Problem they have today:** Every new agent over enterprise data is a new way
  to leak it. On most stacks, authorization lives in the client or in a bespoke
  API layer in front of the data, so each agent re-implements (and re-mistakes)
  access control. Personal data is the sharpest version: the agent often has no
  notion of "this column is off-limits to this caller."
- **What this episode unlocks:** Security is a property of the data platform, not
  the agent. Dataverse enforces three independent controls on every request:
  row-level (roles, teams, depth), column-level (secured columns and profiles),
  and data masking (masking rules that redact values in place). Because agents
  and people share one identity model, the same controls bind to an application
  user. Effective access is the intersection of the human's clearance and the
  agent's. You author it once and every MCP-aware client (Cowork, Copilot,
  Claude, the CLI) inherits it.
- **Why now / why this matters:** The interactive Cowork connection is delegated,
  so it reads as the signed-in human and you watch the human's clearance enforced
  live. The headless per-agent intersection is the same idea one layer deeper. No
  second authorization system, no shared over-scoped key. That is the whole pitch:
  the more agents you connect, the more that single, platform-enforced model pays
  off.

---

## ⭐ Prompts to type on camera

All verbatim. Dry-run each one before recording so the visualizer caches are warm
and Cowork's first call does not pay the cold-start tax.

### Part 0 prompt: load the skill and the runbook (paste verbatim, hold on the confirm)

```
Load the dataverse-security skill and REBUILD.md into this session.
Confirm you have the model (row-level, column-level, per-agent) in
context, print DATAVERSE_URL from .env, and stop before any write so
I can confirm the environment on camera.
```

Cursor confirms the model and prints the environment. Do not let it write yet;
the confirm is the beat.

### Part 1 prompt: row-level (paste verbatim)

```
Use the dataverse-security skill. Implement row-level security: the
four lc roles (lc Owner at Business Unit depth, lc Member at User
depth, lc Viewer read-only at BU depth, lc Admin), each bound to its
own owner team, on the lc_* tables. Idempotent.
```

Produces `scripts/python/setup_simple_rbac.py`. After it runs, cut to the
visualizer and flip the persona dropdown. The row counts are the proof.

### Part 2 prompt: column-level (paste verbatim)

```
Use the dataverse-security skill. Implement column-level security on
the lc_teammember PII. Mask lc_email with a masking rule so every
role but the admin reads it redacted. Hide the full name with pure
column security: the real name lives in lc_fullname, secure it and
revoke the read grant so it is omitted outside the lc Sensitive
Readers profile. lc_name stays a non-PII ID.
```

Produces `scripts/python/setup_field_security.py`. Cut to the visualizer reading
as a non-admin profile member and flip both PII toggles.

### Part 3 prompt: per-agent (paste verbatim)

```
Use the dataverse-security skill. Implement per-agent security: the
Cowork application user inherits System Administrator. Scope it down
to Basic User + lc Owner, leave it out of lc Sensitive Readers, and
re-grant the solution and publisher reads the MCP needs on connect.
Then read lc_teammember as the agent versus as me and show the
secured column omitted for the agent.
```

Produces `scripts/python/setup_agent_security.py`. The read-back is the proof.

### Payoff prompt: the live Cowork question (paste verbatim, ask it twice)

```
Who is on the Q3 Widget Launch team? List each member with their
email address.
```

Ask it once with masking **on** (emails redacted), run the toggle, ask the same
prompt again with masking **off** (cleartext). The mask toggle is one command:

```powershell
python scripts/python/toggle_email_mask.py --on      # redacted (a#########@example.test)
python scripts/python/toggle_email_mask.py --off     # cleartext
python scripts/python/toggle_email_mask.py --status
```

---

## Lower-third captions

| Moment | Caption |
|---|---|
| Cold open | `One agent, one question, and Dataverse decides what data comes back` |
| Part 0 | `Dataverse security works three ways: the rows, the columns, and masking the values` |
| Part 1 | `Row-level security: one launch query returns 4 tasks for a Member, 12 for an Owner` |
| Part 2 | `Column-level security: the email is returned masked and the full name is hidden` |
| Part 3 | `The agent is its own user, so removing its admin role applies the same column limits` |
| Payoff | `Masking on returns redacted emails; masking off returns cleartext, same agent and prompt` |
| Outro | `Define the security model once in Dataverse and every connected agent inherits it` |

---

## Pre-record setup (do once)

- [ ] **Cursor** open at the repo root with the `dataverse-security` skill and
  `REBUILD.md` available to `@`-mention.
- [ ] **`.env`** at repo root points at the demo environment (`DATAVERSE_URL`).
  The environment is a **Managed Environment** (masking rules require one) and
  the signed-in admin holds **System Administrator**.
- [ ] **Clean slate.** Run Step 0 of `REBUILD.md` so the camera starts with no
  `lc` roles, no secured columns, and the Cowork app user back on System
  Administrator:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  python scripts/python/teardown_security.py            # dry-run
  python scripts/python/teardown_security.py --confirm  # reset
  ```
- [ ] **Data substrate present** (untouched by teardown):
  ```
  lc_launch         1  (Q3 Widget Launch)
  lc_task          12
  lc_teammember     4
  ```
- [ ] **The PII reshape is done** once: real names live in `lc_fullname` and
  `lc_name` is a non-PII ID (`TM-001` ...). Dataverse refuses field security on
  the primary name (`0x8004f501`), which is why the name moved. `setup_field_security.py`
  assumes this reshape and only (re)secures.
- [ ] **Demo persona assignment** (local-only `seed_ep08_demo.py`, gitignored;
  re-create from the Step 3 prompt in `REBUILD.md` if missing): Member → Walt
  Perry, Owner → Vivian Sun, Viewer → Rick Brighenti, with task ownership varied
  so the Member sees 4 of 12.
- [ ] **Cowork sign-in account** (`<demo-user>@<your-tenant>.onmicrosoft.com`) is
  ready and, by the time the payoff beat records, holds the **Owner lens**:
  `Basic User` + `lc Owner` + the `lc Owners` team, **in** the `lc Sensitive
  Readers` profile. The row-level role is load-bearing: with only `Basic User`,
  Cowork 403s on every `lc_*` read and sees no launch at all.
- [ ] **Cowork plugin connected** to the Dataverse preview MCP endpoint
  (`/api/mcp_preview`) and signed in as the demo account.
- [ ] **RBAC visualizer running** live:
  ```powershell
  python apps/rbac-visualizer/app.py    # http://127.0.0.1:5000
  ```
  Warm it once (the first live load builds the persona/policy caches). The header
  **Refresh cache** button clears them between authoring steps.
- [ ] **Browser windows + apps pre-loaded:**
  1. Cursor, repo root (Parts 0 to 3 hero window).
  2. The RBAC visualizer in a browser, fullscreen-ready (Parts 1 and 2 proof).
  3. Cowork chat, signed in as the demo account, plugin connected (payoff).
  4. A terminal at the repo root for the `toggle_email_mask.py` flip.
  5. PowerApps on the `lc_teammember` table, kept in reserve for optional B-roll.
- [ ] **Title / end cards** at 1920×1080 in `social/video-scripts/assets/`:
  - `ep08-end-card.png`: *"Next: Episode 9: The Agent.\n\ngithub.com/jamesoleinik/launch-control"*

---

## Pre-record reset (between takes)

```powershell
$env:PYTHONIOENCODING="utf-8"
# Back to a clean slate, then the camera rebuilds from Part 1.
python scripts/python/teardown_security.py --confirm

# Demo personas (local-only) if the teardown removed team membership.
python scripts/python/seed_ep08_demo.py
```

- [ ] **Recording-ready default for the payoff beat:** email mask **on** (so the
  first ask is redacted and the toggle reveals cleartext), `lc_fullname`
  **visible** (grant present), `<demo-user>` **in** the `lc Sensitive Readers`
  profile and on the `lc Owners` team.
- [ ] **Click Refresh cache** in the visualizer after every authoring step that
  changes roles, the profile, or masking. The two PII toggles already update live
  per request; the persona and policy panels are cached per process.
- [ ] **Allow a few seconds** after any profile or role change before re-asking
  Cowork; field-security membership propagates with a short cache delay.

---

## Troubleshooting table for filming

| Symptom | Likely cause | Fix before next take |
|---|---|---|
| Visualizer still shows old roles after a build step | Persona/policy cache is per process | Click **Refresh cache** (or restart the app) |
| Cowork says it can't access the launch table | Sign-in human has only `Basic User`, no row role | Add `<demo-user>` to the `lc Owners` team |
| Cowork 403s right after the agent scope-down | `prvReadSolution` / `prvReadPublisher` stripped with System Administrator | `setup_agent_security.py` re-grants them on `lc Owner`; re-run it |
| Full name still shows for a "hidden" toggle | Reading as the signed-in admin, who bypasses column security | The visualizer reads as a non-admin profile member by design; verify the PII reader resolved |
| Email won't reveal cleartext in Cowork | A masking rule always masks a plain read | Flip the rule with `toggle_email_mask.py --off`, not an unmask permission |
| Visualizer 500s after the env changed | Stale empty-state cache from before the build | Restart the app, then warm it with one live load |

---

## End-card copy

```text
Episode 8: Security

Row-level and column-level security in Dataverse, built from Cursor with one
skill, and enforced at runtime through Cowork. The agent is a user. The platform
decides what it sees.
```
