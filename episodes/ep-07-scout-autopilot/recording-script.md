# Episode 7: Recording script

Producer cues, the verbatim prompts to type on camera, B-roll
timing, and pre-record / between-takes resets. The README is the
"how do I reproduce this" doc; this file is the "what do I do on
camera" doc.

Target length: **~2:00**. Four beats, plus 7s of hook and 5s of
outro. Same screen-recording-with-voiceover format as Episodes 1–6.

---

## Hook (0:00–0:07)

**Hook-shape:** value-first cold open → proof in the second clause.

**Visual (0:00–0:03):** A still of the new Dataverse MCP tool list (the
6-area, 17-tool table). A small `EPISODE 07` badge in the top-left
corner from frame 1.

**Visual (0:03–0:07):** Hard cut to a Microsoft Scout chat window with
a streaming answer card: a verbatim excerpt from *inside* the
`sample-feedback.pdf` (e.g. *"We can't ship this to enterprise with
the export crash."*). The launch name `Q3 Widget Launch` is visible.

**Hook VO line (verbatim, also opens the LinkedIn post):**

> *"The Dataverse MCP server grew up. And it brought files with it."*

---

## What the viewer sees, second by second

| Time | What's on screen | VO line | On-screen overlays (≤7 words) |
|---|---|---|---|
| **0:00–0:03** | Still · the 17-tool, 6-area MCP catalog. | "The Dataverse MCP server grew up." | ⬇ **The MCP server grew up.** |
| **0:03–0:07** | Hard cut to a Scout chat answer streaming a verbatim PDF excerpt. | "And it brought files with it." | ⬇ **And it brought files with it.** |
| **0:07–0:18** ⭐ **Intro · The new preview tool shape (11s)** | Cut between the tool catalog still and `dataverse-mcp-tools.json` open in VS Code. Highlight `search`, `describe`, `read_query`, **`search_data`**, `invoke_api`, `execute_prompt`. | "The preview shape moved from CRUD per table to discovery, query, and a search tool that reads inside attachments. Eighteen tools today, three of them preview-only. Agents ask in English, the server finds the right thing, including matches inside the PDFs you attached." | ⬇ **Search. Describe. Read inside files.** |
| **0:18–1:05** ⭐ **Part 1 · Discover the tools live, co-author the skill, save it (47s)** | Scout chat fullscreen. James pastes the Part 1a discovery prompt; Scout renders the tool catalog inline. Cut tight. James pastes the Part 1b seed prompt (short, no tool names, but with the dedup-via-read-then-read-inside rule called out). Scout drafts the skill body inline; markdown scrolls. James types one iteration. Scout amends. James types "Save it." Tool-use panel fires four MCP calls: `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`. Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → the resource attached. | "First I had Scout check the latest Dataverse MCP tool shapes. Discovery, query, records, tables, business skills, files. Then I told Scout what I wanted: sweep SharePoint and email for issues on a launch, and never file a duplicate. Pull the launch's open tasks, compare, and if the title and notes aren't enough, open the attached PDF and read inside before deciding. I didn't name a single tool. Scout drafted it, we tightened one rule, I said save it. Four MCP calls. The skill is a row in Dataverse." | ⬇ **'Check the tool shapes.'** → 0:30 **New shape, six areas.** → 0:42 **Tell Scout: never file a duplicate.** → 0:55 **Say "save it."** → 1:02 **Skill = row in Dataverse.** |
| **1:05–1:35** ⭐ **Part 2 · Run the skill on Q3, watch `search_data` do dedup, read inside what got attached (30s)** | Scout chat. James pastes `Run the Launch Readiness Sweep against Q3 Widget Launch.` Tool-use panel: `search`/`describe` to load the skill, then the skill executes. The new beat: per finding, **`search_data`** fires once against the LaunchControl model scope and returns matching `lc_task` row paths *plus the excerpt from inside the attached PDF* that triggered the match. That's the dedup moment, one call. Then `update_record` + the file-upload trio attaches the new source to the matched task. Speed-ramp 3x through the panel; drop to 1x on the `search_data` call (zoom on the excerpt block in the result) and on the closing summary, which should call out *N enriched, 0 new*. James pastes the Part 2b question. Answer streams a verbatim quote from inside the newly attached PDF via `file_download`. | "Then I ran it on Q3. For every finding, Scout called `search_data` once. It searched task fields *and inside the attached PDFs* in one shot, and returned the excerpt that matched. Both findings matched. So the new collateral got attached to the existing tasks instead of filing duplicates. No noise added to the queue." | ⬇ **Run the skill.** → 1:13 **One call, matches inside the PDF.** → 1:23 **2 enriched, 0 duplicates.** → 1:30 **Answer from inside the new PDF.** |
| **1:35–1:55** ⭐ **Part 3 · Always-on Scout (20s)** | Scout → Automations → open "Morning Launch Control update". Edit. Paste the 3 new step bodies (2x speed on the typing). Save. Click Run now. Cut to Teams · the summary DM lands with launch name, the new task names, and the verbatim risk excerpt. | "Then Scout puts it on a schedule. Discover the skill. Run it. DM me the result. Every weekday at nine." | ⬇ **Step 1: discover.** → 1:42 **Step 2: run.** → 1:48 **Step 3: report.** → 1:52 **Always on.** |
| **1:55–2:00** | End card. *"Next: Episode 8: RBAC."* `github.com/jamesoleinik/launch-control` | "Same data. Same security. Now always on." | ⬇ **Episode 8 next: RBAC.** |

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
Connect to the Launch Control Dataverse MCP server and give me a
full inventory of the tools it exposes today. For each tool: the
exact tool name, a one-line description of what it does, the
required arguments (name and type), and which of the eight tool
areas it belongs to (discovery, query, custom logic, records,
tables, business skills, files, or other). At the end, call out
which tools are preview-only versus also on the GA endpoint, and
which tool is the one I'd reach for to find an existing task whose
attached PDF mentions a specific phrase. Format the answer as a
table grouped by area.
```

Scout introspects the MCP server, calls `describe` against each tool, and renders a grouped table across all eight areas (discovery, query, custom logic, records, tables, business skills, files, other) with the required-argument signatures and the preview-vs-GA call-out. Hold at 1x while the table renders; the call-out line that names `search_data` as the inside-PDF tool is the lead-in to Part 1. Cut tight at the moment the table finishes.

#### Step 1b. Seed the skill (paste verbatim, deliberately short)

```
Now let's build a skill that uses these. Sweep our LaunchControl
SharePoint site at <https://<tenant>.sharepoint.com/sites/LaunchControl>
for issues reported on a launch, like blockers, escalations,
regressions, slips, can't-ship, P0s.

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

> Before the take, swap `<tenant>` for the real M365 short name and confirm the site path matches where the LaunchControl docs actually live (on-camera env: `https://m365cpi13620341.sharepoint.com/sites/LaunchControl`). Leaving the literal angle brackets in is fine on camera if the take is a private rehearsal; for the published take, paste the real URL.

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

Two prompts back to back. The skill from Part 1 is doing the work now; Scout is just the host. Wait ~30 seconds between Step 2a's last `commit_file_upload` and Step 2b so embeddings have time to build over the attached collateral.

#### Step 2a. Run the skill (paste verbatim, one short sentence)

```
Run the Launch Readiness Sweep against Q3 Widget Launch.
```

Tool-use panel sequence: Scout calls `search('launch readiness sweep')` then `describe` to load the skill body, then follows the body. That means: Scout's SharePoint search and read, Scout's Outlook search and read, then on the Launch Control MCP server `read_query` (resolve the launch and fetch `lc_risksummary`), then **`search_data`** once per finding (scope `new_dvtablesearch_aiplugin_model_lc_Model`). The result panel for `search_data` is the visual proof — hold at 1x and zoom on the matched-content excerpt block, which is text *from inside the attached PDF*, not from the task's columns. Then `update_record` + `init_file_upload` → HTTP PUT → `commit_file_upload` per matched task. Optional `file_download` only if a `search_data` excerpt is ambiguous (not expected on camera). Drop to 1x on the closing four-section summary (headline + new + **enriched** + no-ops). The expected mix for the on-camera take is **2 findings, 0 new tasks, 2 enriched**.

#### Step 2b. Read inside what got attached (paste verbatim, 1x, no speed-ramp)

```
On Q3 Widget Launch, pull any task that just got created or updated
and tell me what the new source document actually says. Use the
Launch Control MCP server.
```

Scout's first move should be `read_query` to find the most-recently-updated `lc_task` on the launch, then `file_download` against that task's `lc_relateddocuments` column. The verbatim excerpt from the newly attached PDF (e.g. *"export crash"* or *"pricing page disagrees with billing"*) is the hero shot of Part 2.

### Part 3: three automation step bodies (1:35–1:55)

In Scout → Automations → Morning Launch Control update → Edit, paste each of these into a separate step in order. Step 1 replaces the existing single step.

**Step 1. Discover and load the skill:**

```
Use the Launch Control MCP server. Call search('launch readiness
sweep') against it, take the top result of type skill, then call
describe on that path to load the skill body verbatim. Hold the
body for the next step.
```

**Step 2. Execute the skill:**

```
Run the skill body loaded in the previous step against the Launch
Control MCP server. Run it against every active launch whose
lc_status is At Risk or Blocked (the skill's built-in fallback
when no launch is named). Follow the body exactly. Do not
paraphrase.
```

**Step 3. Report:**

```
Send me the Teams summary the skill produced in Step 2. Keep the
formatting from the skill output.
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
  This creates **10 `lc_task` rows on Q3 Widget Launch** with titles prefixed `[SEED]` (idempotent: any prior `[SEED]`-prefixed rows on Q3 get cleared first; the title prefix is the seed identifier because `lc_task` has no `lc_source` column). **Three of them ship with PDFs attached to `lc_relateddocuments`**, including the two intentional dedup targets: *Bug: Export to CSV crashes* (matches the SharePoint PDF below) and *Bug: Pricing page disagrees with billing* (matches the email below).
- [ ] **SharePoint finding staged** at `https://a365preview001.sharepoint.com/sites/LaunchControl/`. Upload `episodes/ep-07-scout-autopilot/sample-feedback.pdf` as `Q3-widget-feedack.pdf`. Its content overlaps the seeded *export-to-CSV crash* baseline task; the on-camera sweep should match and enrich, not duplicate.
- [ ] **Email finding staged.** Send yourself (or the Q3 launch team mailbox) one short message with subject like `Q3 Widget Launch: pricing page disagrees with billing` and a body containing the word `escalation`. Content overlaps the seeded *pricing mismatch* baseline; same enrichment behavior expected.
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

# 5. (Optional) Re-stage the SharePoint doc or the email if you've removed them.
#    The pre-record checklist above lists the seeded variants.
```

**Rules of the reset:**

- Never delete `lc_launch` / `lc_milestone` rows. Those are load-bearing from Eps 1–3.
- The Scout Automation **Run now** button is safe to use any number of times during reset. Each run is logged separately under the automation's history.
