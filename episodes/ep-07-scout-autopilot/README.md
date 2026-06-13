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

Three beats, end-to-end inside Microsoft Scout. Nothing in this episode is invented by hand. Every artifact, every line of skill body, every automation step is real and lives in Dataverse or in Scout's automation surface.

1. **Attach a real artifact to a launch and search inside it from chat.** Drag [`sample-feedback.pdf`](sample-feedback.pdf) onto the `Q3 Widget Launch` record. The PDF contains seeded risk phrases (`blocker`, `escalation`, `can't ship`, `customer impact`); the platform builds embeddings on commit. Then in Scout chat, ask one question about the launch. Scout calls `search_data` and answers with a verbatim excerpt from inside the PDF. This is the new capability that motivates everything else.
2. **Co-author a Business Skill with Scout in chat, then save it to Dataverse.** Hand Scout the goal in plain English. Scout drafts the skill body. Iterate live (one or two small edits). Then say *"save it as the Launch Readiness Sweep business skill."* Scout fires four MCP calls in order on the Launch Control server, `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`, and the skill lands as a row in the Dataverse `skill` table, discoverable by name from any MCP-aware agent.
3. **Make it always-on.** Open the existing "Morning Launch Control update" Scout Automation (the daily report from Episode 6) and extend it: step 1 = discover and load the new skill, step 2 = run it, step 3 = DM the result. Save. Hit *Run now*. The Teams summary lands.

The narrative is "Scout is the surface. Dataverse is the brain." The new MCP shape is what makes that hand-off feel native, because authoring, discovery, and execution all happen through the same small tool set the agent already has.

---

## Part 1 · Attach an artifact to a launch and search inside it

> This is the new capability. After this beat, the platform has built embeddings over the PDF and agentic search returns content from inside the file.

**🛠 Runs in:** Microsoft Scout desktop, Chat. No portal. No app.

The upload itself is an MCP call. Scout reads the PDF off disk with its filesystem tool, then fires `init_file_upload` → HTTP PUT to the returned SAS URL → `commit_file_upload` against the `lc_launch` file column. Same trio that Part 2 uses to attach the skill resource. Then a single `search_data` proves the embeddings landed.

1. **Step 1a. Upload the PDF via Scout.** Paste this into Scout chat (replace `<repo>` with the absolute path to the repo on your machine; do not type the angle brackets):

   ```
   Use the Launch Control MCP server. Read the file at
   <repo>/episodes/ep-07-scout-autopilot/sample-feedback.pdf and
   attach it to the lc_launch row whose lc_name is
   "Q3 Widget Launch" on its file column. Use init_file_upload to
   get a SAS URL, PUT the bytes to it with x-ms-blob-type: BlockBlob,
   then commit_file_upload. Tell me when commit returns.
   ```

   Scout's tool-use panel should show `search` (to find the launch row), then `init_file_upload`, then an HTTP PUT, then `commit_file_upload`. Wait ~30 seconds after commit for the platform to build embeddings.

2. **Step 1b. Ask the question.** Paste:

   ```
   What is the top unresolved customer concern on Q3 Widget Launch?
   Use the Launch Control MCP server. If a file is attached to that
   launch, search inside it.
   ```

   Scout's first move should be `search` to resolve the launch's scope, then `search_data` with that scope. The answer should quote from inside `sample-feedback.pdf`. Both **"export crash"** and **"pricing page disagrees with billing"** are seeded for this query.

> Prefer to upload through the portal? Open the LaunchControl model-driven app, open the **Q3 Widget Launch** record, drop the PDF on the file column, save. The rest of the beat is identical.

---

## Part 2 · Co-author the Business Skill with Scout, then save it to Dataverse

> The headline of the new MCP shape. The agent doesn't load a pre-written skill. It writes one with you, then commits it. The rules live next to the data, authored where the data lives.

**🛠 Runs in:** Microsoft Scout desktop, Chat.

### The seed prompt (paste verbatim into Scout chat)

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

### Iterate (two passes on camera)

Scout returns a draft. The draft will be close to (but not identical to) [`business-skills/launch-readiness-sweep.md`](../../business-skills/launch-readiness-sweep.md), which is the canonical reference body checked into this repo. Make two small edits, one at a time, so the iteration loop is visible:

- *"In the dedup step, match by URL or filename in the existing `lc_task.lc_description`, not just by exact-string compare."*
- *"In the Teams summary, include the verbatim `lc_risksummary` value for each at-risk launch."*

Scout amends the draft in place after each.

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
| Sample artifact | [`sample-feedback.pdf`](sample-feedback.pdf) | Seeded beta-tester report. Drag onto a launch on camera |
| PDF generator | [`scripts/generate_ep07_sample_pdf.py`](../../scripts/generate_ep07_sample_pdf.py) | Regenerate the sample if you want to change the seeded phrases |
| Tool catalog | [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json) | Authoritative JSON-RPC `tools/list` response from the new MCP shape. Cited from this README and from the social post |
| This README | `episodes/ep-07-scout-autopilot/README.md` | Repro-only |
| Recording script | [`recording-script.md`](recording-script.md) | Producer cues, prompts, B-roll timing |

---

## Prerequisites

- Episodes 1–6 substrate present in the target environment: the `lc_launch` / `lc_milestone` / `lc_task` / `lc_statusupdate` tables, at least one launch in `At Risk` or `Blocked` state (`Q3 Widget Launch` is the standing demo data), and the Ep-5 `lc_risksummary` AI prompt column on `lc_launch`.
- **Files enabled** on the `lc_launch` table. Specifically a file column with **"Available for Search"** turned on (the platform setting that triggers embedding generation on commit). If your column is named differently from the demo, no code change is needed; only the on-screen drag-and-drop target differs.
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
