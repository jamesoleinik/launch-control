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
| **0:07–0:27** ⭐ **Part 1 · The new tool shape (20s)** | Cut between the tool catalog still and `dataverse-mcp-tools.json` open in VS Code. Highlight `search`, `describe`, `search_data`. | "The shape moved from CRUD per table to discovery: search, describe, read. Agents ask in English, the server finds the right table or skill." | ⬇ **Search. Describe. Read.** |
| **0:27–0:52** ⭐ **Part 2 · Upload + agentic search (25s)** | Browser, Power Apps, Q3 Widget Launch record. Drag the `sample-feedback.pdf` onto the file column. Cut to Scout chat. Type the Part 2 prompt. The answer streams a quote from inside the PDF. | "Files now land directly on Dataverse records. The platform builds embeddings over them. So when I ask Scout what's blocking Q3, the answer comes from inside the PDF I just dropped on the record." | ⬇ **Drop file. Embeddings built.** → 0:42 **Search finds content, not columns.** |
| **0:52–1:17** ⭐ **Part 3 · The skill is a row in Dataverse (25s)** | Microsoft Scout chat. James types the **Part 3 prompt** (the upsert prompt). Scout's tool-use panel shows four calls fire in order: `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`. Hard cut to Power Apps → Skill table → the new `Launch Readiness Sweep` row → the resource attached. | "Business Skills live in Dataverse too. One Scout prompt authors the skill through the same MCP server we just used. Four tool calls. The skill is a row. Any agent that finds it can run it." | ⬇ **Scout writes the skill.** → 1:08 **Skill = row in Dataverse.** |
| **1:17–1:52** ⭐ **Part 4 · Always-on Scout (35s)** | Scout → Automations → open "Morning Launch Control update". Edit. Paste the 3 new step bodies (cut for time, 2x speed on the typing). Save. Click Run now. Cut to Teams · the summary DM lands with launch name, risk summary, and the new task names. | "Then Scout puts it on a schedule. Step one, discover the skill. Step two, run it. Step three, DM me the result. Every weekday at nine. The morning sweep runs itself. New artifacts get indexed automatically. The agent surface keeps up." | ⬇ 1:17 **Step 1: discover the skill.** → 1:27 **Step 2: run it.** → 1:37 **Step 3: DM the summary.** → 1:47 **Always on.** |
| **1:52–2:00** | End card. *"Next: Episode 8: RBAC."* `github.com/jamesoleinik/launch-control` | "Same data. Same security. Now always on." | ⬇ **Episode 8 next: RBAC.** |

---

## Why the watcher should care

- **Problem they have today:** Agents over enterprise data hit two walls. (1) The integration shape is per-table CRUD. The agent has to be told the schema before it can do anything useful. (2) The data the agent needs is half-structured: the spec PDF, the beta report, the support transcript. Even with the best MCP integration, that content is invisible because nothing has indexed it.
- **What this episode unlocks:** Three wins. (1) The new tool shape is NL-driven. `search` and `describe` let the agent discover the right table or skill instead of being hand-pointed. (2) Files upload directly onto records and the platform builds embeddings, so `search_data` finds content from inside the file. (3) Business Skills are first-class Dataverse rows, authored through the same MCP server, so the rules live next to the data and any MCP-aware agent (Scout, Cowork, Claude, the CLI) can find them.
- **Why now / why this matters:** This is the substrate Microsoft Scout was waiting on. Scout's Automations let an agent run unattended; the new MCP shape lets the agent figure out what to run and against what; and the file capabilities let the agent answer questions that previously required a human to skim a PDF. The combination is the first credible "always-on data steward" pattern on top of Dataverse.

---

## ⭐ Prompts to type on camera

Three prompts and three automation-step bodies. All verbatim. Dry-run
each one before recording so caches are warm and auth is past.

### Part 2 prompt: Scout finds content inside the PDF (0:38–0:52)

The drag-and-drop happens first. Wait ~30 seconds after the file
commits before recording this beat so embeddings are ready.

Type into Scout chat:

```
What is the top unresolved customer concern on Q3 Widget Launch?
Use the Launch Control MCP server. If a file is attached to that
launch, search inside it.
```

Hold the streaming answer at 1x. The verbatim excerpt from the PDF
is the hero shot. Do not speed-ramp.

### Part 3 prompt: Scout authors the skill in Dataverse (0:52–1:17)

Type into Scout chat. Replace `<repo>` with the absolute path to the repo on the recording machine before recording (do not type the angle brackets on camera).

```
Use the Launch Control MCP server. Read the file at
<repo>/business-skills/launch-readiness-sweep.md and upsert it as
a Business Skill in Dataverse with name "Launch Readiness Sweep",
unique name "lc_launchreadinesssweep", and a one-sentence
description summarising what the skill does. Then create a skill
resource for that skill named launch-readiness-sweep.md and upload
the same file contents into the resource's filecontent column via
init_file_upload, an HTTP PUT to the returned SAS URL, then
commit_file_upload.
```

Scout's tool-use panel should show four MCP calls fire in order:
`upsert_skill` → `create_skill_resource` → `init_file_upload` →
`commit_file_upload`. Hold on the panel through the four calls,
then cut to Power Apps on the new Skill row at the moment of the
final reply. Do not speed-ramp this beat. The four tool-use bubbles
are the hero shot.

> Fallback: the same four MCP calls are wrapped in
> `scripts/upsert_launch_readiness_sweep.py`. Useful for tenants
> that have not yet enrolled Scout but not used on camera.

### Part 4: three automation step bodies (1:17–1:47)

In Scout → Automations → Morning Launch Control update → Edit, paste
each of these into a separate step in order. The first replaces the
existing single step.

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
