# Episode 7: The Dataverse MCP face-lift, in Scout, on a schedule

**Status:** 🚧 In development · 🎬 Not yet recorded
**Features:** ⭐ The new Dataverse MCP tool shape (17 tools, 6 areas) · ⭐ File upload into Dataverse records · ⭐ Agentic search over uploaded file content (`search_data`) · ⭐ Business Skills authored *into* Dataverse via the MCP server · ⭐ Microsoft Scout Automations
**Layer:** 🟣 Layer 3 reach. The always-on agent surface
**Coding agent:** None for the demo. The "agent" in this episode is Microsoft Scout itself.
**Runtime:** Microsoft Scout (Frontier) desktop + Dataverse MCP Server (`/api/mcp`, GA) + the LaunchControl solution from Episodes 1–6

> 📖 **What changed under the covers.** The Dataverse MCP server moved from per-entity `list / get / create / update / delete` to a small, NL-driven shape. The authoritative catalog used in this episode is checked in as [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json). 17 tools across 6 areas: **Discovery** (`search`, `describe`), **Query** (`read_query`), **Records** (`create_record` / `update_record` / `delete_record`), **Tables** (`create_table` / `update_table` / `delete_table`), **Business Skills** (`upsert_skill` / `delete_skill` / `create_skill_resource`), and **Files** (`init_file_upload` / `commit_file_upload` / `file_download`), plus the new agentic **`search_data`** tool.

> 🆕 **Two net-new platform capabilities** ride on that shape:
> 1. **File uploads into records.** `init_file_upload` returns a SAS URL, you PUT the bytes, then `commit_file_upload` finalizes. The file lands on a file column of the target record.
> 2. **Agentic search over file content.** `search_data` returns hits based on **embeddings the platform built over those uploaded files**, not just column metadata. The right record can come back because a phrase appeared inside an attached PDF.

---

## The shape of the demo

Three beats, end-to-end inside Microsoft Scout. The skill is authored first, then run, then put on a schedule. Nothing in this episode is invented by hand. Every artifact, every line of skill body, every automation step is real and lives in Dataverse or in Scout's automation surface.

1. **Co-author the Business Skill with Scout in chat, then save it to Dataverse.** Hand Scout the goal in plain English ("sweep SharePoint and email for new issues reported on a launch, file a task per finding, attach the source"). Scout drafts the skill body inline. Iterate live. Then say *"save it."* Scout fires four MCP calls in order on the Launch Control server, `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`, and the skill lands as a row in the Dataverse `skill` table, discoverable by name from any MCP-aware agent.
2. **Run the skill on Q3 Widget Launch and watch dedup do its job.** Tell Scout *"run the Launch Readiness Sweep against Q3 Widget Launch."* Scout sweeps the LaunchControl SharePoint site and the Q3 mailbox. For each finding, Scout calls the new MCP **`search`** tool against the launch's existing tasks; `search` matches not just on column data but on the **content of files already attached** to those tasks. Findings that match an existing task get *enriched* (the new artifact is attached to the matching task, the description gets an "Update" line), not duplicated. Genuinely new findings get a fresh `lc_task` with the source attached. Then a single follow-up question (*"what did it find?"*) gets answered with a verbatim excerpt via `search_data`.
3. **Make it always-on.** Open the existing "Morning Launch Control update" Scout Automation (the daily report from Episode 6) and extend it: step 1 = discover and load the new skill, step 2 = run it, step 3 = DM the result. Save. Hit *Run now*. The Teams summary lands.

The narrative is "Scout is the surface. Dataverse is the brain." The new MCP shape is what makes that hand-off feel native, because authoring, discovery, and execution all happen through the same small tool set the agent already has.

---

## Part 1 · Co-author the Business Skill with Scout, then save it to Dataverse

> The headline of the new MCP shape. The agent doesn't load a pre-written skill. It writes one with you, then commits it. The rules live next to the data, authored where the data lives.

**🛠 Runs in:** Microsoft Scout desktop, Chat.

### The discovery prompt (paste verbatim into Scout chat first)

```
Check out the latest Dataverse MCP tool shapes.
```

This is a free beat. Scout calls the MCP server's introspection (`describe`, plus a `list-tools`-style read) and renders the 17 tools across the six areas. On camera it's the visual proof that the shape really did change. Hold the answer at 1x; the tool list scrolling past is the hero shot for the intro into Part 1.

### The seed prompt (paste verbatim into Scout chat)

```
Now let's build a skill that uses these. Sweep our LaunchControl
SharePoint site and our Q3 launch mailbox for issues reported on a
launch, like blockers, escalations, regressions, slips, can't-ship,
P0s.

The key rule: never file a duplicate. Before creating a task,
search the launch's existing tasks for a match, and have the search
look inside the files already attached to those tasks too. If
there's a match, attach the new collateral to the existing task
and append an update line. Only file a new task when there is no
match.

Draft the skill body inline. We'll iterate. When I say "save it,"
save it to Dataverse as Launch Readiness Sweep.
```

Notice what is still NOT in the prompt: tool names, upsert plumbing, unique-name. Scout picks the right MCP tools from the catalog it just discovered. What *is* in the prompt is the dedup intent, because dedup is the value beat and the dedup behavior is the whole reason the new `search` shape matters here.

### Iterate (one pass on camera)

Scout returns a draft. The draft will be close to (but not identical to) [`business-skills/launch-readiness-sweep.md`](../../business-skills/launch-readiness-sweep.md), which is the canonical reference body checked into this repo. Make one small edit so the iteration loop is visible:

- *"When there's a strong match, don't just attach: also append a one-line 'Update' to the existing task's description so the history is visible without opening the file."*

Scout amends the draft in place.

### Save

When the draft is close enough, type:

```
Looks good. Save it.
```

Scout's tool-use panel should show four MCP calls fire in order: **upsert_skill** → **create_skill_resource** → **init_file_upload** → **commit_file_upload**. The final reply summarises with the new skill's GUID.

### Verify

Open Power Apps → Tables → **Skill** → **Launch Readiness Sweep**. The body column shows the markdown from the chat draft. Open Related → **Skill Resources** to see the `launch-readiness-sweep.md` resource with the bytes attached.

### Non-Scout fallback (CI, headless tenants, or pre-Frontier evaluation)

If Scout is not available, the canonical reference body in `business-skills/launch-readiness-sweep.md` plus the four-call upsert are wrapped in [`scripts/upsert_launch_readiness_sweep.py`](../../scripts/upsert_launch_readiness_sweep.py). Run it once:

```powershell
cd C:\path\to\launch-control
python scripts/upsert_launch_readiness_sweep.py
```

The script uses `.env` `DATAVERSE_URL` + `AzureCliCredential` to mint the bearer for `/api/mcp`. It exists for environments where Scout is not available; the on-camera path is the co-authoring prompt above.

---

## Part 2 · Run the skill on Q3 Widget Launch and read inside what it filed

> The skill earns its keep. Scout invokes the skill body from Part 1, the sweep finds issues in SharePoint and email, each one becomes a tracked task with the source artifact attached, and then a single follow-up question answers from inside one of those attached files.

**🛠 Runs in:** Microsoft Scout desktop, Chat. No portal. No app.

**Pre-record:** seed the dedup baseline, then stage the on-camera findings.

- **Baseline tasks (run from this repo).** With your `.env` pointed at the demo environment and `az login` against the demo tenant, run:

  ```powershell
  pip install --quiet reportlab requests python-dotenv azure-identity
  python scripts/generate_q3_seed_artifacts.py
  python scripts/seed_q3_sample_tasks.py
  ```

  This creates 10 baseline `lc_task` rows on Q3 Widget Launch (idempotent: prior tasks whose title starts with `[SEED]` get cleared first; the seed identifier is the title prefix because `lc_task` has no `lc_source` column on it). Three of them have PDFs attached to **`lc_relateddocuments`**, including one whose attached PDF describes an *export-to-CSV crash* and one whose attached PDF describes a *pricing page mismatch*. Those two are the dedup targets the on-camera sweep will hit. The other seven exist so the `search` tool has a realistic corpus to score against. **Confirm `lc_relateddocuments` on `lc_task` has "Available for Search" turned on** so embeddings build over the attached collateral.

- **SharePoint (on-camera finding).** Upload `episodes/ep-07-scout-autopilot/sample-feedback.pdf` to the LaunchControl SharePoint site (`https://a365preview001.sharepoint.com/sites/LaunchControl/`) as `Q3-widget-feedack.pdf`. The PDF is seeded with `blocker`, `escalation`, `can't ship`, `customer impact`, and its content overlaps the seeded *export-to-CSV crash* baseline task. **The sweep should match it and attach to that existing task, not create a new one.**
- **Email (on-camera finding).** Forward yourself (or send to the Q3 launch team mailbox) one short message with subject like *"Q3 Widget Launch: pricing page disagrees with billing"* and a body containing `escalation`. Same idea: content overlaps the seeded *pricing mismatch* baseline. **Expected behavior: enrichment, not duplication.**

The mix matters for the story. The on-camera sweep should produce **2 findings, 0 new tasks, 2 enriched existing tasks**. The headline of the summary is the dedup, not the file count.

1. **Step 2a. Run the skill.** Paste this verbatim into Scout chat:

   ```
   Run the Launch Readiness Sweep against Q3 Widget Launch.
   ```

   Scout's tool-use panel should show, in order: `search('launch readiness sweep')` and `describe` to load the skill body, then the skill itself executing. The skill fires Scout's SharePoint and Outlook connectors, then on the Launch Control MCP server: `read_query` (resolve the launch), then for each finding the new MCP **`search`** tool scoped to `lc_task` on the launch (this is the dedup beat: the panel should show `search` returning hits that include excerpts from inside *already attached* PDFs), then `update_record` + the file-upload trio per matched task (`init_file_upload` → HTTP PUT → `commit_file_upload`). The chat closes with the skill's four-section summary (headline + new tasks + **enriched tasks** + no-ops). Wait ~30 seconds after the last commit so embeddings have time to build over the newly attached collateral.

2. **Step 2b. Read inside what got attached.** Paste:

   ```
   On Q3 Widget Launch, pull up the existing task that just got new
   collateral attached and tell me what the new source document
   actually says. Use the Launch Control MCP server. If a file is
   attached to that task, search inside it.
   ```

   Scout's first move should be `read_query` to find the most-recently-updated `lc_task` on the launch, then `search_data` scoped to that task. The answer should quote from inside the newly attached PDF (e.g. *"export crash"* or *"pricing page disagrees with billing"*).

---

## Part 3 · Make it always-on with a Scout Automation

> The arc of the series closes here. Episode 6 gave Cowork the plugin. Episode 7 gives Scout the schedule.

**🛠 Runs in:** Microsoft Scout desktop, Automations.

1. Open Scout → **Automations**.
2. Open the existing **Morning Launch Control update** automation (the daily report we set up around Episode 6). The current shape is one step: *"Send me today's daily LaunchControl launch report in Teams."*
3. Click **Edit Automation**.
4. Replace step 1 with the discovery + execution pair below. Keep the original "report in Teams" step as the closer.

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

5. Confirm the schedule is **Every weekday at 9am** and the model is **GPT-5.5 (default)**.
6. **Save**.
7. Click **Run now** to validate end-to-end. The Teams DM should land within ~30 seconds and should include the launch name, the verbatim `lc_risksummary`, and any new `lc_task` rows the sweep filed.

From this morning forward Scout owns the sweep. New artifacts uploaded onto launches automatically widen what the sweep sees, without any change to the skill or the automation.

---

## What ships in this episode

| Artifact | Path | Purpose |
|---|---|---|
| Business Skill (source) | [`business-skills/launch-readiness-sweep.md`](../../business-skills/launch-readiness-sweep.md) | Canonical body of the skill |
| Push script | [`scripts/upsert_launch_readiness_sweep.py`](../../scripts/upsert_launch_readiness_sweep.py) | One-shot, idempotent. Calls `upsert_skill` + `create_skill_resource` + file-upload via the new MCP server |
| Sample artifact (on-camera) | [`sample-feedback.pdf`](sample-feedback.pdf) | Uploaded to SharePoint as `Q3-widget-feedack.pdf` on camera; the sweep should match this against the *export-to-CSV crash* baseline task and enrich, not duplicate |
| PDF generator (sample) | [`scripts/generate_ep07_sample_pdf.py`](../../scripts/generate_ep07_sample_pdf.py) | Regenerate the on-camera sample if you want to change the seeded phrases |
| Baseline seeder | [`scripts/seed_q3_sample_tasks.py`](../../scripts/seed_q3_sample_tasks.py) | One-shot, idempotent. Creates 10 `lc_task` rows on Q3 Widget Launch (titles prefixed `[SEED]`), 3 with PDFs attached to `lc_relateddocuments`. Two are intentional dedup targets for the on-camera sweep. Uses the Dataverse Web API directly |
| Baseline artifact generator | [`scripts/generate_q3_seed_artifacts.py`](../../scripts/generate_q3_seed_artifacts.py) | Reportlab. Emits the 3 baseline PDFs to `seed-artifacts/` |
| Baseline artifacts | [`seed-artifacts/`](seed-artifacts/) | The 3 PDFs the seeder attaches; phrasing overlaps the on-camera findings so `search`-over-attachments finds them |
| Tool catalog | [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json) | Authoritative JSON-RPC `tools/list` response from the new MCP shape. Cited from this README and from the social post |
| This README | `episodes/ep-07-scout-autopilot/README.md` | Repro-only |
| Recording script | [`recording-script.md`](recording-script.md) | Producer cues, prompts, B-roll timing |

---

## Prerequisites

- Episodes 1–6 substrate present in the target environment: the `lc_launch` / `lc_milestone` / `lc_task` / `lc_statusupdate` tables, at least one launch in `At Risk` or `Blocked` state (`Q3 Widget Launch` is the standing demo data), and the Ep-5 `lc_risksummary` AI prompt column on `lc_launch`.
- **Files enabled** on the `lc_task` table (the seeder attaches to tasks, and the on-camera enrichment attaches to tasks) **and** on the `lc_launch` table. Each needs a file column with **"Available for Search"** turned on so the platform builds embeddings on commit. On `lc_task` the column is `lc_relateddocuments` (matches the seeder); on `lc_launch` the existing files column is fine.
- **Microsoft Scout** desktop, Frontier preview, signed in as a user with Dataverse access to the target environment.
- The **Launch Control MCP server** registered in Scout: Settings → Extensions → MCP Servers → `https://<your-org>.crm.dynamics.com/api/mcp`. Sign in. Tool count should be 17.

### Optional (only for the non-Scout fallback path)

If you cannot run Scout (CI machine, headless tenant, evaluation without Frontier enrollment) and want to use `scripts/upsert_launch_readiness_sweep.py` instead of the Part 1 Scout prompt:

- Python 3.10+ with `requests`, `python-dotenv`, `azure-identity`. (`reportlab` is only needed to regenerate the sample PDF.)
  ```powershell
  pip install requests python-dotenv azure-identity reportlab
  ```
- `.env` at the repo root with `DATAVERSE_URL` set.
- Azure CLI signed in (`az login`). The script uses `AzureCliCredential` to mint the token for the MCP server.

---

## References

- The Dataverse MCP server (`tools/list` JSON used in this episode): [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json)
- Microsoft Scout documentation hub: https://learn.microsoft.com/microsoft-scout/
- Microsoft Scout Automations (scheduled and condition-triggered runs): https://learn.microsoft.com/microsoft-scout/automations
- Dataverse MCP server overview: https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-overview
- The Ep-6 Cowork plugin episode (the on-demand surface that complements this episode's always-on one): [`../ep-06-cowork-plugin/`](../ep-06-cowork-plugin/)
