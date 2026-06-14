# Episode 7: Recording script

Producer cues, the verbatim prompts to type on camera, B-roll
timing, and pre-record / between-takes resets. The README is the
"how do I reproduce this" doc; this file is the "what do I do on
camera" doc.

Target length: **~2:05**. One MCP-shape beat (Part 0), three demo parts, plus an 8s split-screen intro and a 5s outro. Recorded beats: 8s intro · 27s P0 · 28s P1 · 30s P2 · 27s P3 · 5s outro. Same screen-recording-with-voiceover format as Episodes 1–6.

---

## Intro (0:00–0:08)

**Shape:** Value-first split-screen. One 8-second beat. Left half is the Dataverse MCP server map (the 16-tool, 5-area visual from the README intro). Right half is a Microsoft Scout chat window mid-`search_data` answer with a verbatim excerpt from inside the seeded PDF on a `lc_task` row, *"We can't ship this to enterprise with the export crash."* Launch name `Q3 Widget Launch` visible. A small `EPISODE 07` badge in the top-left corner from frame 1.

**Intro VO line (verbatim, also opens the LinkedIn post):**

> *"Our launch playbook lives in Dataverse. Now Scout runs it for us."*

---

## What the viewer sees, second by second

| Time | What's on screen | VO line | On-screen overlays (≤7 words) |
|---|---|---|---|
| **0:00–0:08** ⭐ **Intro · Split-screen · 8s** | Split-screen: left half is the Dataverse MCP server map (16 tools, 5 areas); right half is a Scout chat window streaming a `search_data` result with a verbatim excerpt from inside the seeded PDF. `EPISODE 07` badge top-left from frame 1. | "Our launch playbook lives in Dataverse. Now Scout runs it for us." | ⬇ 0:00 **Our launch playbook lives in Dataverse.** → 0:04 **Now Scout runs it for us.** |
| **0:08–0:35** ⭐ **Part 0 · What Scout is, what the MCP server became (27s)** | Scout chat fullscreen. James pastes the Part 1a discovery prompt. Scout renders the area-grouped tool catalog inline. Then the HTML server visual opens and lists tool names vertically. Hold at 1x. Cut tight when the visual opens. | "Microsoft Scout is Microsoft's first always-on Autopilot agent, built on the OpenClaw open-source stack. And on the Dataverse side, the server itself just changed shape: from CRUD per table to an agentic surface where the agent can find tools by intent, search inside attached files, and call server-side logic on its own." | ⬇ **New shape. New agentic tools (search, invoke API & prompt).** |
| **0:35–1:03** ⭐ **Part 1 · Co-author the Business Skill with Scout, then save it (28s)** | Scout chat. James pastes the Part 1b seed prompt (short, no tool names, but with the dedup-via-read-then-read-inside rule called out). Scout drafts the skill body inline; markdown scrolls. James types one iteration. Scout amends. James types "Save it." Tool-use panel fires four MCP calls: `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`. Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → the resource attached. | "Scout honors business skills, so I co-authored one to automate how I evaluate risk on every launch. Sweep Outlook and Teams for issues, never file a duplicate, ask the server if anything already covers it (including inside attached PDFs), and update the source of truth in Dataverse. Scout drafted, we tightened one rule, I said save it." | ⬇ **New skill co-authored with Scout. Saved as a business skill to Dataverse.** |
| **1:03–1:33** ⭐ **Part 2 · Prove `search_data` solo, then run the skill (30s)** | Scout chat. James pastes the Step 2a natural-language question. Tool-use panel: one call, `search_data`. Result panel shows three different `lc_task` row paths for Q3 Widget Launch about the same export-to-CSV crash, plus a matched-content excerpt quoted from inside the attached PDF on the one row that has collateral. Hold at 1x on the row paths and the excerpt. Then James pastes `Run the Launch Readiness Sweep against Q3 Widget Launch.` Tool-use panel: `search`/`describe` loads the skill, then it executes. Per finding, **`search_data`** fires once and returns matching row paths plus the excerpt that triggered the match. Then `update_record` + the file-upload trio per task touched. Speed-ramp 3x through the panel; drop to 1x on the four-section summary, which should call out **1 new, 1 enriched**. James pastes Step 2c. Answer streams a verbatim quote from inside the newly attached PDF via `file_download`. | "I asked one question: any open tasks for export issues on Q3? Scout fired `search_data` once and surfaced three duplicates, plus a line from inside an attached PDF. That's what an agent-ready Dataverse prevents. Then I ran the skill we authored. Scout, with Dataverse's agentic tools, did the whole sweep at scale: one new, one enriched, zero duplicates added." | ⬇ **Zero duplicate tasks, zero manual review. All unlocked by the new DV server and agentic search tool.** |
| **1:33–2:00** ⭐ **Part 3 · Always-on Scout (27s)** | Scout → Automations → open "Morning Launch Control update". Edit. Paste the 3 new step bodies (2x speed on the typing). Save. Click Run now. Cut to Teams · the summary DM lands with launch name, the new task names, and the verbatim risk excerpt. | "Then Scout puts it on a schedule with an Automation. Three steps: discover the skill we just authored, run it against every active launch, and send the summary to Teams. Every weekday at nine. The launch readiness process now runs whether I'm at my desk or not." | ⬇ **My launch readiness process, now automated.** |
| **2:00–2:05** | End card. *"Next: Episode 8: RBAC."* `github.com/jamesoleinik/launch-control` | "More agents, more security risk. Not on Dataverse. Episode 8 next." | ⬇ **More agents, more risk. Not on Dataverse.** |

---

## Why the watcher should care

- **Problem they have today:** Agents over enterprise data hit two walls. (1) The integration shape is per-table CRUD. The agent has to be told the schema before it can do anything useful. (2) The data the agent needs is half-structured: the spec PDF, the beta report, the support transcript. Even with the best MCP integration, that content is invisible because nothing has indexed it.
- **What this episode unlocks:** Three wins. (1) The new preview tool shape is NL-driven, 18 tools today. `search` and `describe` let the agent discover the right table or skill instead of being hand-pointed. (2) **`search_data`** searches across rows *and* inside indexed file columns in one call, so the dedup beat ("does an open task already cover this finding?") returns the matching excerpt directly, no per-candidate file_download dance. `file_download` is still there when the agent needs the whole document. (3) Business Skills are first-class Dataverse rows, authored through the same MCP server, so the rules live next to the data and any MCP-aware agent (Scout, Cowork, Claude, the CLI) can find them. Bonus: `invoke_api` and `execute_prompt` open the door to firing readiness Custom APIs and AI Prompt columns on demand from chat.
- **Why now / why this matters:** This is the substrate Microsoft Scout was waiting on. Scout's Automations let an agent run unattended; the new MCP shape lets the agent figure out what to run and against what; and the file capabilities let the agent answer questions that previously required a human to skim a PDF. The combination is the first credible "always-on data steward" pattern on top of Dataverse.

---

## ⭐ Prompts to type on camera

Two prompts back to back, one iteration line, and three automation-step bodies. All verbatim. Dry-run each one before recording so the four-call MCP panel and the streaming chat answers are warm.

### Part 1 prompts: Discover the tools, then co-author the skill (0:25–1:05)

Three prompts. The first is a free discovery beat. The second is the seed for the skill (deliberately under-specified now that Scout has just seen the tool catalog). The third saves it.

#### Step 1a. Discover and inventory the tool shape (paste verbatim, hold at 1x while the table renders)

```
Inventory every tool on the Launch Control Dataverse MCP server as
a single markdown table, sorted by area then name. Columns: Area,
Tool, Description (max 12 words). Areas: discovery, query, custom
logic, records, tables, business skills, files, other.

Below the table, add a short "Preview-only" section that breaks out
these three net-new tools with a 2-3 sentence description each,
explaining what each one unlocks for an agent:

- search_data — semantic search over records and attached file
  content in one call. Note the scope arg, the row-path return
  shape, and the Available-for-Search prereq for inside-file hits.
- invoke_api — call a Dataverse Custom API by name. Call out that
  it lets the agent fire server-side logic (graders, retry
  orchestrators) without Web API plumbing.
- execute_prompt — run an AI Prompt by id. Call out that the agent
  can fire lc_risksummary or any other Prompt column on demand,
  not just on row save.

No other prose.
```

Scout introspects the MCP server, calls `describe` against each tool, and renders a grouped table across all eight areas (discovery, query, custom logic, records, tables, business skills, files, other) with the required-argument signatures and the preview-vs-GA call-out. Hold at 1x while the table renders; the call-out line that names `search_data` as the inside-PDF tool is the lead-in to Part 1. Cut tight at the moment the table finishes.

#### Step 1b. Seed the skill (paste verbatim, deliberately short)

```
Now let's build a skill that uses these. Sweep my Outlook inbox and
my Microsoft Teams messages for issues reported on a launch, like
blockers, escalations, regressions, slips, can't-ship, P0s.

The key rule: never file a duplicate. Before creating a task, ask
the MCP server whether any open task on this launch already covers
the finding. The search must look inside the attached collateral on
existing tasks too, not just at task titles and notes, because the
matching evidence will often live inside a PDF. If there's a match,
attach the new collateral to the existing task and append an update
line. Only file a new task when there is no match.

Draft the skill body inline. We'll iterate. When I say "save it,"
save it to Dataverse as Launch Readiness Sweep.
```

No tool names, no upsert plumbing. The dedup rule *is* in the prompt because dedup is the value beat of the episode. Let the draft stream at 1x for ~10s; the markdown body scrolling is the hero shot.

#### Step 1c. One iteration on camera

Type one short message:

```
When there's a strong match, don't just attach: also append a
one-line "Update" to the existing task's description so the history
is visible without opening the file.
```

Scout amends the draft. Hold for ~5s.

#### Step 1d. Save

Type:

```
Looks good. Save it.
```

Scout's tool-use panel fires four MCP calls in order. Hold on the panel through all four:

1. **upsert_skill** (name=`Launch Readiness Sweep`, uniquename inferred by Scout)
2. **create_skill_resource** (filename=`launch-readiness-sweep.md`)
3. **init_file_upload** (tablename=`skillresource`, fileAttributeName=`filecontent`)
4. **commit_file_upload**

Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → Related → Skill Resources → the attached file. Do not speed-ramp this cut.

> Fallback: if Scout is unavailable, the same canonical body and four-call upsert are wrapped in `scripts/upsert_launch_readiness_sweep.py`. Reference body: `business-skills/launch-readiness-sweep.md`.

### Part 2 prompts: Run the skill on Q3, then read inside what it filed (1:05–1:35)

Three prompts back to back. The skill from Part 1 is doing the work now; Scout is just the host. Wait ~30 seconds between the `seed_q3_sample_tasks.py` run and Step 2a so embeddings have time to build over the seeded PDFs.

#### Step 2a. Prove `search_data` works on its own (paste verbatim, hold at 1x)

```
Do I have any open tasks for export issues with the Q3 Widget Launch
```

This is the hero shot for Part 2 and it lands two beats at once. First, Scout fires exactly one MCP call, `search_data`, and the response includes **three different `lc_task` row paths for Q3 Widget Launch**, all about the same export-to-CSV crash (the baseline was seeded with intentional duplicates: QA blocker with a PDF attached, Field Eng repro off Northwind, CSM intake off a customer escalation). Hold at 1x on the three row paths so the audience sees the chaos: three tasks in the queue today for one bug, because three reporters had no way to know it was already filed. Second, the row that has the attached PDF returns a matched-content excerpt **quoted from inside the PDF** — proof that `search_data` indexes file content, not just columns, and the exact signal the skill in Step 2b uses to prevent the next duplicate. Zoom the excerpt block at 1x.

#### Step 2b. Run the skill (paste verbatim, one short sentence)

```
Run the Launch Readiness Sweep against Q3 Widget Launch.
```

Tool-use panel sequence: Scout calls `search('launch readiness sweep')` then `describe` to load the skill body, then follows the body. That means: Scout's Outlook search and read, Scout's Teams search and read, then on the Launch Control MCP server `read_query` (resolve the launch and fetch `lc_risksummary`), then **`search_data`** once per finding (scope `new_dvtablesearch_aiplugin_model_lc_Model`). The result panel for `search_data` is the visual proof again, this time inside the skill loop. Then `update_record` + `init_file_upload` → HTTP PUT → `commit_file_upload` per task touched. Optional `file_download` only if a `search_data` excerpt is ambiguous (not expected on camera). Drop to 1x on the closing four-section summary (headline + new + **enriched** + no-ops). The expected mix for the on-camera take is **2 findings, 1 new task (mobile auth callback), 1 enriched (export-to-CSV crash)**.

#### Step 2c. Read inside what got attached (paste verbatim, 1x, no speed-ramp)

```
Summarize the changes you just made for the Q3 Widget Launch.
```

Scout's first move should be `read_query` to find the most-recently-updated `lc_task` on the launch, then `file_download` against that task's `lc_relateddocuments` column. The verbatim excerpt from the newly attached PDF (e.g. *"export crash"* or *"pricing page disagrees with billing"*) is the hero shot of Part 2.

### Part 3: three automation step bodies (1:35–1:55)

In Scout → Automations → Morning Launch Control update → Edit, paste each of these into a separate step in order. Step 1 replaces the existing single step.

**Step 1. Discover and load the skill:**

```
Find the Launch Readiness Sweep skill on the Launch Control MCP
server and load its body. Hold it for the next step.
```

**Step 2. Execute the skill:**

```
Run the Launch Readiness Sweep against every active launch that
is At Risk or Blocked.
```

**Step 3. Report:**

```
DM me the Teams summary the sweep produced.
```

Save. Click **Run now**. Hold on the Teams DM when it lands.

---

## Pre-record setup (do once)

- [ ] **Microsoft Scout** desktop installed, Frontier enrollment confirmed for the demo tenant, signed in.
- [ ] **Launch Control MCP server** registered in Scout: Settings → Extensions → MCP Servers → `https://<your-org>.crm.dynamics.com/api/mcp_preview`. Signed in.
- [ ] **`.env`** at repo root points at the same environment (`DATAVERSE_URL`).
- [ ] **Azure CLI** signed in (`az login` against the demo tenant). Only required if you fall back to the non-Scout Python push script. The on-camera path uses Scout's own MCP session and does not need it.
- [ ] **Eps 1–6 substrate present**:
  ```
  lc_launch         1  (Q3 Widget Launch, state = At Risk)
  lc_milestone     16
  lc_task          61
  lc_teammember     4
  lc_statusupdate   4
  ```
  Re-run `scripts/python/promote.py` if any counts are off.
- [ ] **Files column on `lc_launch`** enabled. (Used by the daily report path from prior episodes.)
- [ ] **`lc_relateddocuments` file column on `lc_task`** enabled, **with *Available for Search* turned on** on that column. The seeder and the on-camera enrichment both attach to this column, and `search_data` only returns inside-the-file excerpts for file columns that have *Available for Search* enabled. `file_download` remains available as a fallback that does not require the Searchable toggle.
- [ ] **No `Launch Readiness Sweep` skill row exists yet** in the Dataverse `skill` table. (The Part 1 "Save it." beat is the hero shot. Delete the row from Power Apps if it exists from a prior take.)
- [ ] **Baseline tasks seeded.** From the repo root, with `.env` pointed at the demo environment and `az login` against the demo tenant:
  ```powershell
  pip install --quiet reportlab requests python-dotenv azure-identity
  python scripts/generate_q3_seed_artifacts.py
  python scripts/seed_q3_sample_tasks.py
  ```
  This creates **12 `lc_task` rows on Q3 Widget Launch** with titles prefixed `[SEED]` (idempotent: any prior `[SEED]`-prefixed rows on Q3 get cleared first; the title prefix is the seed identifier because `lc_task` has no `lc_source` column). Critically, **three of those rows are about the same export-to-CSV crash**, filed by three different reporters (QA blocker with attached PDF, Field Eng off Northwind, CSM intake off a customer escalation). That triple is the visual mess Step 2a leans on: one `search_data` call returns all three plus the inside-PDF excerpt from the one with collateral, which is the *exact* signal the skill in Step 2b uses to prevent the next duplicate.
- [ ] **Trigger emails sent to the on-camera demo inbox `jamesol@a365preview001.onmicrosoft.com`** within ~10 minutes of the take. Send two short messages from a different account (any external-looking sender):
  - **Email A (enrich).** Subject: `Q3 Widget Launch - export to CSV crashes the app for Northwind`. Body: 2-3 sentences naming `Q3 Widget Launch` in the first line and describing the export-to-CSV crash on a large composition. Attach a short PDF named `Q3-widget-export-crash-northwind.pdf` repeating the same text. Topic overlaps the seeded *export-to-CSV crash* baseline task whose attached PDF the dedup beat should match.
  - **Email B (new task).** Subject: `Q3 Widget Launch - mobile auth callback fails after SSO`. Body: 2-3 sentences naming `Q3 Widget Launch` in the first line and describing a mobile OAuth callback that 500s after the IdP redirect. Attach `Q3-widget-mobile-auth-callback.pdf` repeating the description. No seed task covers this; should file a fresh `lc_task`.
- [ ] **Trigger Teams posts (optional but recommended).** Post the same two messages into a channel the runner is in (with the PDFs as channel attachments) so the Teams sweep beat also has live data.
- [ ] **No prior sweep-filed tasks on Q3** beyond the `[SEED]` baseline. The on-camera sweep should produce **2 findings, 0 new, 2 enriched** (the seed PDFs win the dedup match). If a prior take left non-`[SEED]` tasks behind that contain `escalation`/`blocker` phrasing, delete them so the headline count stays clean.
- [ ] **The "Morning Launch Control update" Scout Automation exists** with its current single step ("Send me today's daily LaunchControl launch report in Teams"). The hero shot is editing it in place.
- [ ] **Browser windows + apps pre-loaded:**
  1. Microsoft Scout desktop, Chat panel open, fullscreen-ready (the Part 1 and Part 2 hero windows).
  2. Microsoft Scout desktop, second window, Automations panel open on "Morning Launch Control update" in view mode.
  3. Power Apps, on the Skill table (for the Part 1 closing cut to the new `Launch Readiness Sweep` row).
  4. Power Apps, second tab, on the `Q3 Widget Launch` record's Tasks section (kept in reserve for the optional B-roll cut after the Part 2 sweep, and for between-takes cleanup).
  5. Teams, DM with self (or the launch-team channel), scrolled to bottom.
  6. **VS Code** at repo root with `dataverse-mcp-tools.json` open in a tab (Intro still). No terminal needed on camera. Scout chat replaces every terminal beat from prior episodes.
- [ ] **Title / end cards** at 1920×1080 in `social/video-scripts/assets/`:
  - `ep07-end-card.png`: *"Next: Episode 8: RBAC.\n\ngithub.com/jamesoleinik/launch-control"*

---

## Pre-record reset (between takes)

If you take 2+ runs:

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Remove the skill row so the Part 1 "Save it." is the hero shot again.
#    (Manual: Power Apps -> Tables -> Skill -> Launch Readiness Sweep -> Delete.
#     There is no Dataverse MCP `delete_skill` call wired into our scripts on
#     purpose: the delete is rare and operator-confirmed.)

# 2. Re-seed the baseline tasks on Q3 (idempotent; deletes prior
#    [SEED]-prefixed rows on Q3 then re-creates them and re-attaches
#    the 3 PDFs). This restores the dedup baseline for the next take.
python scripts/seed_q3_sample_tasks.py

# 3. Remove any non-[SEED] sweep-filed tasks on Q3 so the Part 2
#    summary's "enriched" counts are clean.
#    (Manual: Power Apps -> Tables -> Task -> filter on
#     lc_title not starting with '[SEED]' AND parent launch is
#     Q3 Widget Launch AND created in this session -> Delete.)

# 4. Revert the "Morning Launch Control update" automation to its single
#    starting step. (Scout -> Automations -> Edit -> delete added steps, restore
#    the original "Send me today's daily LaunchControl launch report in
#    Teams" step.)

# 5. (Optional) Re-send the two trigger emails (and re-post in Teams) if you've cleared the prior inbox state.
#    The pre-record checklist above lists the seeded variants.
```

**Rules of the reset:**

- Never delete `lc_launch` / `lc_milestone` rows. Those are load-bearing from Eps 1–3.
- The Scout Automation **Run now** button is safe to use any number of times during reset. Each run is logged separately under the automation's history.
