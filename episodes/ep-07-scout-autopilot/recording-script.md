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
| **0:07–0:25** ⭐ **Intro · The new tool shape (18s)** | Cut between the tool catalog still and `dataverse-mcp-tools.json` open in VS Code. Highlight `search`, `describe`, `search_data`. | "The shape moved from CRUD per table to discovery: search, describe, read. Agents ask in English, the server finds the right table or skill." | ⬇ **Search. Describe. Read.** |
| **0:25–0:50** ⭐ **Part 1 · Upload + agentic search (25s)** | Browser, Power Apps, Q3 Widget Launch record. Drag `sample-feedback.pdf` onto the file column. Save. Cut to Scout chat. Type the Part 1 prompt. The answer streams a quote from inside the PDF. | "Files now land directly on Dataverse records. The platform builds embeddings over them. So when I ask Scout what's blocking Q3, the answer comes from inside the PDF I just dropped on the record." | ⬇ **Drop file. Embeddings built.** → 0:40 **Search finds content, not columns.** |
| **0:50–1:30** ⭐ **Part 2 · Co-author the skill, save it to Dataverse (40s)** | Scout chat. James pastes the Part 2 seed prompt. Scout drafts the skill body inline; the markdown scrolls in the answer pane. James types one short iteration ("In the dedup step, match by filename in the existing lc_task description"). Scout amends in place. James types "Save it." Scout's tool-use panel fires four MCP calls in order: `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`. Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → the resource attached. | "Then I built the morning skill with Scout. Same chat. I said what I want, Scout drafted the steps in markdown, we tightened the dedup rule together, then I said save it. Four tool calls. The skill is a row in Dataverse now. Any agent that finds it can run it." | ⬇ 0:50 **Tell Scout what you want.** → 1:05 **Iterate in chat.** → 1:18 **Say "save it."** → 1:25 **Skill = row in Dataverse.** |
| **1:30–1:55** ⭐ **Part 3 · Always-on Scout (25s)** | Scout → Automations → open "Morning Launch Control update". Edit. Paste the 3 new step bodies (2x speed on the typing). Save. Click Run now. Cut to Teams · the summary DM lands with launch name, risk summary, and the new task names. | "Then Scout puts it on a schedule. Discover the skill. Run it. DM me the result. Every weekday at nine. The morning sweep runs itself." | ⬇ 1:30 **Step 1: discover.** → 1:38 **Step 2: run.** → 1:46 **Step 3: report.** → 1:52 **Always on.** |
| **1:55–2:00** | End card. *"Next: Episode 8: RBAC."* `github.com/jamesoleinik/launch-control` | "Same data. Same security. Now always on." | ⬇ **Episode 8 next: RBAC.** |

---

## Why the watcher should care

- **Problem they have today:** Agents over enterprise data hit two walls. (1) The integration shape is per-table CRUD. The agent has to be told the schema before it can do anything useful. (2) The data the agent needs is half-structured: the spec PDF, the beta report, the support transcript. Even with the best MCP integration, that content is invisible because nothing has indexed it.
- **What this episode unlocks:** Three wins. (1) The new tool shape is NL-driven. `search` and `describe` let the agent discover the right table or skill instead of being hand-pointed. (2) Files upload directly onto records and the platform builds embeddings, so `search_data` finds content from inside the file. (3) Business Skills are first-class Dataverse rows, authored through the same MCP server, so the rules live next to the data and any MCP-aware agent (Scout, Cowork, Claude, the CLI) can find them.
- **Why now / why this matters:** This is the substrate Microsoft Scout was waiting on. Scout's Automations let an agent run unattended; the new MCP shape lets the agent figure out what to run and against what; and the file capabilities let the agent answer questions that previously required a human to skim a PDF. The combination is the first credible "always-on data steward" pattern on top of Dataverse.

---

## ⭐ Prompts to type on camera

Two prompts, one iteration line, and three automation-step bodies. All verbatim. Dry-run each one before recording so the four-call MCP panel and the streaming chat answers are warm.

### Part 1 prompt: Scout finds content inside the PDF (0:36–0:50)

The drag-and-drop in Power Apps happens first. Wait ~30 seconds after the file commits before recording this beat so embeddings are ready.

Type into Scout chat:

```
What is the top unresolved customer concern on Q3 Widget Launch?
Use the Launch Control MCP server. If a file is attached to that
launch, search inside it.
```

Hold the streaming answer at 1x. The verbatim excerpt from the PDF is the hero shot. Do not speed-ramp.

### Part 2 prompt: Co-author the skill in Scout chat (0:50–1:30)

This is the longest beat and the new hero of the episode. The flow is **seed → draft → one iteration → save**. The producer's job is to make sure the four MCP tool-use bubbles land on camera at the end.

#### Step 2a. Paste the seed prompt verbatim into Scout chat (~5s on screen)

```
I want a Business Skill that runs every weekday morning and tells me
what changed on my at-risk launches overnight.

Pull the at-risk launches from Dataverse via the Launch Control MCP
server (read_query). For each one, use search_data scoped to the
launch to look inside any attached files for risk language: blocker,
escalation, can't ship, customer impact. De-duplicate against
existing lc_task rows on the launch. For each surviving finding,
create an lc_task with lc_source = 'file-sweep'. Post one Teams
summary at the end.

Draft the markdown body of that skill now. Show me the draft inline
before you save anything. We will iterate together. When I say
"save it," upsert it as a Dataverse Business Skill on the Launch
Control MCP server with name "Launch Readiness Sweep" and unique
name "lc_launchreadinesssweep". Attach the same markdown as a
skill resource via create_skill_resource + init_file_upload +
commit_file_upload.
```

Scout drafts the markdown body inline. Let the draft stream at 1x for ~10s, scrolling so the viewer sees that it really is multi-step skill body markdown. The draft will be close to the canonical reference in `business-skills/launch-readiness-sweep.md`.

#### Step 2b. One iteration on camera (~10s)

Type one short message:

```
In the dedup step, match by filename in the existing lc_task
description, not just by exact-string compare.
```

Scout amends the draft. The amendment shows up in the chat as a diff or a re-rendered section. Hold for ~5s.

#### Step 2c. Save (~10s)

Type:

```
Looks good. Save it.
```

Scout's tool-use panel fires four MCP calls in order. Hold on the panel through all four:

1. **upsert_skill** (name=`Launch Readiness Sweep`, uniquename=`lc_launchreadinesssweep`)
2. **create_skill_resource** (filename=`launch-readiness-sweep.md`)
3. **init_file_upload** (tablename=`skillresource`, fileAttributeName=`filecontent`)
4. **commit_file_upload**

Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → Related → Skill Resources → the attached file. Do not speed-ramp this cut. The four tool-use bubbles plus the new Skill row are the hero shots.

> Fallback: if Scout is unavailable, the same canonical body and four-call upsert are wrapped in `scripts/upsert_launch_readiness_sweep.py`. Reference body: `business-skills/launch-readiness-sweep.md`.

### Part 3: three automation step bodies (1:30–1:52)

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
- [ ] **No `Launch Readiness Sweep` skill row exists yet** in the Dataverse `skill` table. (The Part 3 push is the hero shot. Delete the row from Power Apps if it exists from a prior take.)
- [ ] **No `sample-feedback.pdf` attached to Q3 Widget Launch** in the file column. (The Part 2 drag-and-drop is the hero shot. Remove any prior attachment.)
- [ ] **The "Morning Launch Control update" Scout Automation exists** with its current single step ("Send me today's daily LaunchControl launch report in Teams"). The hero shot is editing it in place.
- [ ] **Browser windows + apps pre-loaded:**
  1. Power Apps, on the `Q3 Widget Launch` record, scrolled to the Files section.
  2. Power Apps, second tab, on the Skill table (for the Part 3 cut).
  3. Microsoft Scout desktop, Chat panel open.
  4. Microsoft Scout desktop, second window, Automations panel open on "Morning Launch Control update" in view mode.
  5. Teams, DM with self (or the launch-team channel), scrolled to bottom.
  6. **VS Code** at repo root with `dataverse-mcp-tools.json` open in a tab (Part 1 still). No terminal needed on camera. The Scout chat replaces every terminal beat from prior episodes.
- [ ] **Title / end cards** at 1920×1080 in `social/video-scripts/assets/`:
  - `ep07-end-card.png`: *"Next: Episode 8: RBAC.\n\ngithub.com/jamesoleinik/launch-control"*

---

## Pre-record reset (between takes)

If you take 2+ runs:

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Remove the skill row so the Part 3 push is the hero shot again.
#    (Manual: Power Apps -> Tables -> Skill -> Launch Readiness Sweep -> Delete.
#     There is no Dataverse MCP `delete_skill` call wired into our scripts on
#     purpose: the delete is rare and operator-confirmed.)

# 2. Remove the attached sample-feedback.pdf from Q3 Widget Launch.
#    (Manual: Power Apps -> Q3 Widget Launch -> Files section -> X on the file.)

# 3. Revert the "Morning Launch Control update" automation to its single
#    starting step. (Scout -> Automations -> Edit -> delete added steps, restore
#    the original "Send me today's daily LaunchControl launch report in
#    Teams" step.)

# 4. If a prior take filed `lc_task` rows with source = 'file-sweep',
#    remove them so the Step 5 inserts in the next take are visibly new.
#    (Manual: Power Apps -> Tables -> Task -> filter on lc_source = 'file-sweep' -> Delete.)
```

**Rules of the reset:**

- Never delete `lc_launch` / `lc_milestone` rows. Those are load-bearing from Eps 1–3.
- Re-uploading the PDF triggers fresh embedding generation. Wait ~30 seconds before re-recording Part 2.
- The Scout Automation **Run now** button is safe to use any number of times during reset. Each run is logged separately under the automation's history.
