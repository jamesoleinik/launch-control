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

Four beats, end-to-end inside Microsoft Scout. Nothing in this episode is invented by hand. Every "skill body," every artifact, every automation step is real and lives in Dataverse or in Scout's automation surface.

1. **Push the skill into Dataverse via the MCP server itself.** Run [`scripts/upsert_launch_readiness_sweep.py`](../../scripts/upsert_launch_readiness_sweep.py). That script calls `upsert_skill` and `create_skill_resource` against `/api/mcp`, then uses the file-upload tools to upload the canonical markdown body as the skill's resource. The skill is now a row in the Dataverse `skill` table, discoverable by name from any MCP-aware agent.
2. **Attach a real artifact to a launch.** Drag [`sample-feedback.pdf`](sample-feedback.pdf) onto the `Q3 Widget Launch` record. The PDF contains seeded risk phrases (`blocker`, `escalation`, `can't ship`, `customer impact`). The platform indexes the file content into embeddings on commit.
3. **Show the agentic search live.** In Scout chat, ask one question about the launch ("What is the top unresolved customer concern on Q3 Widget Launch?"). Scout calls `search_data`, gets back a content excerpt from inside the PDF, and answers from it.
4. **Make it always-on.** Open the existing "Morning Launch Control update" Scout Automation (the daily report from Episode 6) and extend it: step 1 = discover and load the new skill, step 2 = run it, step 3 = DM the result. Save. Hit *Run now*. The Teams summary lands.

The narrative is "Scout is the surface. Dataverse is the brain." The new MCP shape is what makes that hand-off feel native, because Scout's first move on any new request is `search` against Dataverse, just like a junior teammate would search the wiki.

---

## Part 1 · Push the Business Skill into Dataverse

> The skill body lives in source control. The skill itself lives in Dataverse. The push happens through the MCP server.

**🛠 Runs in:** your terminal (one-shot Python script).

### Defaults (the script should NOT ask for these)

| Input | Default | Source |
|---|---|---|
| Dataverse environment | The URL in your `.env` `DATAVERSE_URL` | `.env` |
| MCP endpoint | `/api/mcp` (GA) | hard-coded in [`upsert_launch_readiness_sweep.py`](../../scripts/upsert_launch_readiness_sweep.py) |
| Skill name | `Launch Readiness Sweep` | hard-coded |
| Skill unique name | `lc_launchreadinesssweep` | hard-coded |
| Skill body | [`business-skills/launch-readiness-sweep.md`](../../business-skills/launch-readiness-sweep.md) | hard-coded |

### Run it

```powershell
cd C:\path\to\launch-control
python scripts/upsert_launch_readiness_sweep.py
```

You should see four steps print:

```
Pushing 'Launch Readiness Sweep' to https://orgXXX.crm.dynamics.com via /api/mcp ...
  -> skill id <guid>
Registering resource 'launch-readiness-sweep.md' ...
  -> resource id <guid>
Initiating file upload for the resource body ...
Uploading bytes via PUT ...
Committing upload ...

Done.
```

Re-running the script is safe. `upsert_skill` updates in place on `uniquename`. The file upload overwrites the previous resource bytes.

### Verify

Open Power Apps → Tables → **Skill** → **Launch Readiness Sweep**. The body column should show the markdown from `business-skills/launch-readiness-sweep.md`. Open Related → **Skill Resources** to see the `launch-readiness-sweep.md` resource with the bytes attached.

---

## Part 2 · Attach an artifact to a launch

> This is the on-camera proof that file upload is real. After this step, the platform has built embeddings over the PDF and the next agentic search will find content from inside it.

**🛠 Runs in:** your browser, in Power Apps, against the `lc_launch` record for `Q3 Widget Launch`.

1. Open the LaunchControl model-driven app.
2. Open the **Q3 Widget Launch** record.
3. In the **Files** section (the file column on `lc_launch`), upload [`episodes/ep-07-scout-autopilot/sample-feedback.pdf`](sample-feedback.pdf).
4. Save the record.

Under the covers the maker portal calls the same `init_file_upload` / SAS PUT / `commit_file_upload` sequence the MCP server exposes. The embeddings are built asynchronously and are typically ready within a minute or two for a file this small.

> Want to upload via MCP instead of the portal? Any MCP-aware coding agent (Claude Desktop, the GitHub Copilot CLI with the Dataverse MCP server registered) can do it with one prompt: *"Upload `episodes/ep-07-scout-autopilot/sample-feedback.pdf` onto the Q3 Widget Launch record's file column using the Launch Control MCP server."*

---

## Part 3 · Search inside files from Scout chat

> The headline moment. The right answer comes from inside the PDF, not from any column you defined.

**🛠 Runs in:** Microsoft Scout desktop, Chat.

Make sure the Launch Control MCP server is registered in Scout: Settings → Extensions → MCP Servers → add `https://<your-org>.crm.dynamics.com/api/mcp` and sign in.

Then type into Scout chat:

```
What is the top unresolved customer concern on Q3 Widget Launch?
Use the Launch Control MCP server. If a file is attached to that
launch, search inside it.
```

Scout's first move should be `search` to find the launch's scope, then `search_data` with that scope. The answer should quote from inside `sample-feedback.pdf`. Both **"export crash"** and **"pricing page disagrees with billing"** are seeded for this query. Scout should surface at least one of them with a verbatim excerpt.

---

## Part 4 · Make it always-on with a Scout Automation

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
- **Python 3.10+** with `requests`, `python-dotenv`, `azure-identity`, and `reportlab` (only needed if you want to regenerate the sample PDF). Install:
  ```powershell
  pip install requests python-dotenv azure-identity reportlab
  ```
- `.env` at the repo root with `DATAVERSE_URL` set to the target environment.
- Azure CLI signed in (`az login`). The push script uses `AzureCliCredential` to mint the token for the MCP server.

---

## References

- The Dataverse MCP server (`tools/list` JSON used in this episode): [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json)
- Microsoft Scout documentation hub: https://learn.microsoft.com/microsoft-scout/
- Microsoft Scout Automations (scheduled and condition-triggered runs): https://learn.microsoft.com/microsoft-scout/automations
- Dataverse MCP server overview: https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-overview
- The Ep-6 Cowork plugin episode (the on-demand surface that complements this episode's always-on one): [`../ep-06-cowork-plugin/`](../ep-06-cowork-plugin/)
