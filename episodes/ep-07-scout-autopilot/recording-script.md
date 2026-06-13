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
| **0:07–0:18** ⭐ **Intro · The new tool shape (11s)** | Cut between the tool catalog still and `dataverse-mcp-tools.json` open in VS Code. Highlight `search`, `describe`, `search_data`. | "The shape moved from CRUD per table to discovery. Search, describe, read. Agents ask in English, the server finds the right thing." | ⬇ **Search. Describe. Read.** |
| **0:18–1:05** ⭐ **Part 1 · Discover the tools live, co-author the skill, save it (47s)** | Scout chat fullscreen. James pastes the Part 1a discovery prompt; Scout renders the 17-tool catalog inline. Cut tight. James pastes the Part 1b seed prompt (short, no tool names). Scout drafts the skill body inline; markdown scrolls. James types one iteration. Scout amends. James types "Save it." Tool-use panel fires four MCP calls: `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`. Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → the resource attached. | "First I had Scout check the latest Dataverse MCP tool shapes. Seventeen tools across six areas, all live. Then I told Scout what I wanted: sweep SharePoint and email for issues on a launch, file a task per finding, attach the source. I didn't name a single tool. Scout drafted it, we tightened one rule, I said save it. Four MCP calls. The skill is a row in Dataverse." | ⬇ **'Check the tool shapes.'** → 0:30 **17 tools, live.** → 0:42 **Tell Scout what you want.** → 0:55 **Say "save it."** → 1:02 **Skill = row in Dataverse.** |
| **1:05–1:35** ⭐ **Part 2 · Run the skill on Q3, read inside what it filed (30s)** | Scout chat. James pastes `Run the Launch Readiness Sweep against Q3 Widget Launch.` Tool-use panel: `search`/`describe` to load the skill, then the skill executes: SharePoint search + Outlook search + MCP `read_query` + `create_record` × N + the file-upload trio per task. Speed-ramp 3x through the panel. Drop to 1x on the skill's three-section summary. James pastes the Part 2b question. Answer streams a verbatim quote from inside the attached PDF. | "Then I ran it on Q3. Scout swept SharePoint and our team mailbox, filed a task per finding, attached the source document to each one. Then I asked what the newest task actually said and the answer came from inside that PDF, in the same chat." | ⬇ **Run the skill.** → 1:15 **SharePoint + email swept.** → 1:24 **Tasks filed. Files attached.** → 1:30 **Answer from inside the PDF.** |
| **1:35–1:55** ⭐ **Part 3 · Always-on Scout (20s)** | Scout → Automations → open "Morning Launch Control update". Edit. Paste the 3 new step bodies (2x speed on the typing). Save. Click Run now. Cut to Teams · the summary DM lands with launch name, the new task names, and the verbatim risk excerpt. | "Then Scout puts it on a schedule. Discover the skill. Run it. DM me the result. Every weekday at nine." | ⬇ **Step 1: discover.** → 1:42 **Step 2: run.** → 1:48 **Step 3: report.** → 1:52 **Always on.** |
| **1:55–2:00** | End card. *"Next: Episode 8: RBAC."* `github.com/jamesoleinik/launch-control` | "Same data. Same security. Now always on." | ⬇ **Episode 8 next: RBAC.** |

---

## Why the watcher should care

- **Problem they have today:** Agents over enterprise data hit two walls. (1) The integration shape is per-table CRUD. The agent has to be told the schema before it can do anything useful. (2) The data the agent needs is half-structured: the spec PDF, the beta report, the support transcript. Even with the best MCP integration, that content is invisible because nothing has indexed it.
- **What this episode unlocks:** Three wins. (1) The new tool shape is NL-driven. `search` and `describe` let the agent discover the right table or skill instead of being hand-pointed. (2) Files upload directly onto records and the platform builds embeddings, so `search_data` finds content from inside the file. (3) Business Skills are first-class Dataverse rows, authored through the same MCP server, so the rules live next to the data and any MCP-aware agent (Scout, Cowork, Claude, the CLI) can find them.
- **Why now / why this matters:** This is the substrate Microsoft Scout was waiting on. Scout's Automations let an agent run unattended; the new MCP shape lets the agent figure out what to run and against what; and the file capabilities let the agent answer questions that previously required a human to skim a PDF. The combination is the first credible "always-on data steward" pattern on top of Dataverse.

---

## ⭐ Prompts to type on camera

Two prompts back to back, one iteration line, and three automation-step bodies. All verbatim. Dry-run each one before recording so the four-call MCP panel and the streaming chat answers are warm.

### Part 1 prompts: Discover the tools, then co-author the skill (0:25–1:05)

Three prompts. The first is a free discovery beat. The second is the seed for the skill (deliberately under-specified now that Scout has just seen the tool catalog). The third saves it.

#### Step 1a. "Check out the latest Dataverse MCP tool shapes." (paste verbatim, one sentence)

```
Check out the latest Dataverse MCP tool shapes.
```

Scout introspects the MCP server and renders the 17 tools across six areas. Hold the answer at 1x; the rendered tool list scrolling past is the visual proof that the shape really did change. Cut tight at the moment the list finishes rendering.

#### Step 1b. Seed the skill (paste verbatim, deliberately short)

```
Now let's build a skill that uses these. Sweep our LaunchControl
SharePoint site and our Q3 launch mailbox for issues reported on a
launch, like blockers, escalations, regressions, slips, can't-ship,
P0s. For each finding, file a task on the matching launch in
Dataverse and attach the source document or email to the task so
the collateral lives next to the work. Don't re-file what's already
there.

Draft the skill body inline. We'll iterate. When I say "save it,"
save it to Dataverse as Launch Readiness Sweep.
```

No tool names. No upsert plumbing. The point of the take is that Scout, having just seen the catalog, picks the right tools on its own. Let the draft stream at 1x for ~10s; the markdown body scrolling is the hero shot.

#### Step 1c. One iteration on camera

Type one short message:

```
For email findings, dedup by message subject plus sender, not just
subject. Two people can file the same complaint.
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

Tool-use panel sequence: Scout calls `search('launch readiness sweep')` then `describe` to load the skill body, then follows the body. That means: Scout's SharePoint search and read, Scout's Outlook search and read, then on the Launch Control MCP server `read_query` (resolve the launch), `read_query` (dedup), `create_record` × N (one task per finding), and per task `init_file_upload` → HTTP PUT → `commit_file_upload`. Speed-ramp 3x through the panel; the volume of bubbles is the visual proof. Drop to 1x on the skill's three-section summary at the end.

#### Step 2b. Read inside what got attached (paste verbatim, 1x, no speed-ramp)

```
On Q3 Widget Launch, pull up the newest sharepoint-sweep task and
tell me what the source document actually says. Use the Launch
Control MCP server. If a file is attached to that task, search
inside it.
```

Scout's first move should be `read_query` to find the newest `lc_task` with `lc_source = 'sharepoint-sweep'` on the launch, then `search_data` scoped to that task. The verbatim excerpt from the PDF is the hero shot of Part 2.

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
Control MCP server. Follow it exactly. Do not paraphrase.
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
- [ ] **Launch Control MCP server** registered in Scout: Settings → Extensions → MCP Servers → `https://<your-org>.crm.dynamics.com/api/mcp`. Signed in. Tool count shows 17.
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
- [ ] **Files column on `lc_launch`** enabled and "Available for Search" is on. (The platform setting that triggers embedding indexing.)
- [ ] **No `Launch Readiness Sweep` skill row exists yet** in the Dataverse `skill` table. (The Part 1 "Save it." beat is the hero shot. Delete the row from Power Apps if it exists from a prior take.)
- [ ] **At least one Q3 issue staged on SharePoint** at `https://a365preview001.sharepoint.com/sites/LaunchControl/` (the demo uses `Q3-widget-feedack.pdf`). The PDF lives in this repo at `episodes/ep-07-scout-autopilot/sample-feedback.pdf` as the source of truth; copy it to SharePoint and rename if you want the on-camera filename to match.
- [ ] **At least one Q3 issue staged by email.** Send yourself (or the Q3 launch team mailbox) one short message with subject like `Q3 Widget Launch: pricing page mismatch` and a body containing the word `escalation`. Two sources in Part 2's sweep summary is more compelling than one.
- [ ] **`lc_task` has a file column** enabled with "Available for Search" turned on so the platform builds embeddings on commit. (If your file column is on `lc_launch` instead, swap the attachment target in the skill body and the search target in Step 2b.)
- [ ] **No prior sweep-filed tasks on Q3 Widget Launch.** Delete any `lc_task` rows where `lc_source IN ('sharepoint-sweep', 'email-sweep')` and the parent launch is `Q3 Widget Launch` so the Part 2 `create_record` × N is visibly new.
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

# 2. Remove any sweep-filed tasks on Q3 Widget Launch so the Part 2
#    create_record fan-out is visibly new.
#    (Manual: Power Apps -> Tables -> Task -> filter on
#     lc_source IN ('sharepoint-sweep','email-sweep') -> Delete.)

# 3. Revert the "Morning Launch Control update" automation to its single
#    starting step. (Scout -> Automations -> Edit -> delete added steps, restore
#    the original "Send me today's daily LaunchControl launch report in
#    Teams" step.)

# 4. (Optional) Re-stage the SharePoint doc or the email if you've removed them.
#    The pre-record checklist above lists the seeded variants.
```

**Rules of the reset:**

- Never delete `lc_launch` / `lc_milestone` rows. Those are load-bearing from Eps 1–3.
- Re-uploading the PDF triggers fresh embedding generation. Wait ~30 seconds before re-recording Part 2.
- The Scout Automation **Run now** button is safe to use any number of times during reset. Each run is logged separately under the automation's history.
