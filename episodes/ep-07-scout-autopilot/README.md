# Episode 7: The Dataverse MCP face-lift, in Scout, on a schedule

**Status:** 🚧 In development · 🎬 Not yet recorded
**Features:** ⭐ The new Dataverse MCP **preview** tool shape (18 tools, NL-driven) · ⭐ Semantic search across records *and* attached file content in one call (`search_data`) · ⭐ Custom API invocation from the agent (`invoke_api`) · ⭐ AI Prompt execution from the agent (`execute_prompt`) · ⭐ Business Skills authored *into* Dataverse via the MCP server · ⭐ Microsoft Scout Automations
**Layer:** 🟣 Layer 3 reach. The always-on agent surface
**Coding agent:** None for the demo. The "agent" in this episode is Microsoft Scout itself.
**Runtime:** Microsoft Scout (Frontier) desktop + Dataverse MCP Server (`/api/mcp_preview`, **preview**) + the LaunchControl solution from Episodes 1–6

> 📖 **What changed under the covers.** The Dataverse MCP server moved from per-entity `list / get / create / update / delete` to a small, NL-driven shape. The authoritative catalog used in this episode is checked in as [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json). On the preview endpoint the shape splits into **Discovery** (`search`, `describe`, **`search_data`**), **Query** (`read_query` — the "execute" surface), **Custom logic** (**`invoke_api`**, **`execute_prompt`**), **Records** (`create_record` / `update_record` / `delete_record`), **Tables** (`create_table` / `update_table` / `delete_table`), **Business Skills** (`upsert_skill` / `delete_skill` / `create_skill_resource`), and **Files** (`init_file_upload` / `commit_file_upload` / `file_download`).

> 🆕 **Three net-new preview-only capabilities** ride on that shape, and they are the reason this episode targets `/api/mcp_preview` instead of GA `/api/mcp`:
> 1. **`search_data` — semantic search over records *and* attached file content in one call.** Scope-bound to a Dataverse search model. Returns row paths (e.g. `tables/lc_task/records/<guid>`) plus matched content excerpts from inside file columns that have *Available for Search* enabled. This is what powers the dedup beat in Part 2: one call decides whether a finding is already covered, including when the evidence is inside a PDF on a task's `lc_relateddocuments`.
> 2. **`invoke_api` — call a Dataverse Custom API by name.** Lets the agent invoke server-side logic without dropping out to Web API plumbing (the natural place to expose Episodes 4-5 graders, retry orchestrators, or any other Custom API).
> 3. **`execute_prompt` — run an AI Prompt by id.** The agent can fire `lc_risksummary` (or any other Prompt column) on demand, not just on row save.
>
> Files still ride along too: `init_file_upload` → PUT → `commit_file_upload` attaches bytes to a record's file column, and `file_download` pulls them back into the agent's context as a fallback when `search_data`'s excerpt is not enough.

---

## The shape of the demo

Three beats, end-to-end inside Microsoft Scout. The skill is authored first, then run, then put on a schedule. Nothing in this episode is invented by hand. Every artifact, every line of skill body, every automation step is real and lives in Dataverse or in Scout's automation surface.

1. **Co-author the Business Skill with Scout in chat, then save it to Dataverse.** Hand Scout the goal in plain English ("sweep SharePoint and email for new issues reported on a launch, file a task per finding, attach the source"). Scout drafts the skill body inline. Iterate live. Then say *"save it."* Scout fires four MCP calls in order on the Launch Control server, `upsert_skill` → `create_skill_resource` → `init_file_upload` → `commit_file_upload`, and the skill lands as a row in the Dataverse `skill` table, discoverable by name from any MCP-aware agent.
2. **Run the skill on Q3 Widget Launch and watch dedup do its job.** Tell Scout *"run the Launch Readiness Sweep against Q3 Widget Launch."* Scout sweeps the LaunchControl SharePoint site and the Q3 mailbox. For each finding, Scout calls **`read_query`** to pull the open tasks on the launch and decides, in-context, whether any existing task already covers it. When a candidate's title and notes are not enough to decide, Scout calls **`file_download`** on that task's attached collateral and reads inside before committing. Findings that match an existing task get *enriched* (the new artifact is attached to the matching task, the description gets an "Update" line), not duplicated. Genuinely new findings get a fresh `lc_task` with the source attached.
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

This is a free beat. Scout calls the MCP server's introspection (`describe`, plus a `list-tools`-style read) and renders the **18 preview tools** across the eight areas. On camera it's the visual proof that the shape really did change, and that `search_data`, `invoke_api`, and `execute_prompt` are the three the GA endpoint does not yet have. Hold the answer at 1x; the tool list scrolling past is the hero shot for the intro into Part 1.

### The seed prompt (paste verbatim into Scout chat)

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

> 💡 Swap `<tenant>` for your real M365 tenant short name (e.g. `contoso`) and the site path for wherever the LaunchControl docs actually live. The on-camera env uses `https://m365cpi13620341.sharepoint.com/sites/LaunchControl`.

Notice what is still NOT in the prompt: tool names, upsert plumbing, unique-name. Scout picks the right MCP tools from the catalog it just discovered. What *is* in the prompt is the dedup intent, because dedup is the value beat and the dedup behavior is the whole reason the new tool shape matters here.

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

The script uses `.env` `DATAVERSE_URL` + `AzureCliCredential` to mint the bearer for `/api/mcp_preview`. It exists for environments where Scout is not available; the on-camera path is the co-authoring prompt above.

---

## Part 2 · Run the skill on Q3 Widget Launch and read inside what it filed

> The skill earns its keep. Scout invokes the skill body from Part 1, the sweep finds issues in SharePoint and email, each one becomes a tracked task with the source artifact attached, and then a single follow-up question answers from inside one of those attached files.

**🛠 Runs in:** Microsoft Scout desktop, Chat. No portal. No app.

**Setup:** seed the dedup baseline on Q3 Widget Launch.

With your `.env` pointed at the demo environment and `az login` against the demo tenant, run:

```powershell
pip install --quiet reportlab requests python-dotenv azure-identity
python scripts/generate_q3_seed_artifacts.py
python scripts/seed_q3_sample_tasks.py
```

This creates 10 baseline `lc_task` rows on Q3 Widget Launch (idempotent: prior tasks whose title starts with `[SEED]` get cleared first; the seed identifier is the title prefix because `lc_task` has no `lc_source` column on it). Three of them have PDFs attached to **`lc_relateddocuments`**, including one whose attached PDF describes an *export-to-CSV crash* and one whose attached PDF describes a *pricing page mismatch*. Those two are the dedup targets the sweep will hit when the new SharePoint and email findings come in on the same topics. The other seven exist so the agent has a realistic candidate set to reason over.

1. **Step 2a. Run the skill.** Paste this verbatim into Scout chat:

   ```
   Run the Launch Readiness Sweep against Q3 Widget Launch.
   ```

   Scout's tool-use panel should show, in order: `search('launch readiness sweep')` and `describe` to load the skill body, then the skill itself executing. The skill fires Scout's SharePoint and Outlook connectors, then on the Launch Control MCP server: `read_query` (resolve the launch and fetch its `lc_risksummary`), and then **`search_data`** once per finding, scope-bound to the `lc_Model` search scope. `search_data` returns the dedup decision in a single call, because the response includes both candidate row paths (`tables/lc_task/records/<guid>`) and excerpts of matched content from inside the `lc_relateddocuments` PDFs on those rows. Optional `file_download` only fires when an excerpt is ambiguous. Then `update_record` + the file-upload trio (`init_file_upload` → HTTP PUT → `commit_file_upload`) per matched task. The chat closes with the skill's four-section summary (headline + new tasks + **enriched tasks** + no-ops).

2. **Step 2b. Read inside what got attached.** Paste:

   ```
   On Q3 Widget Launch, pull any task that just got created or
   updated and tell me what the new source document actually says.
   Use the Launch Control MCP server.
   ```

   Scout's first move should be `read_query` to find the most-recently-updated `lc_task` on the launch, then `file_download` against that task's `lc_relateddocuments` to read the bytes. The answer should quote from inside the newly attached PDF. (`search_data` returns excerpts but not the full file; this beat shows the file-download path is still the right tool when you need the whole document.)

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
| Sample artifact | [`sample-feedback.pdf`](sample-feedback.pdf) | A SharePoint-style feedback PDF whose content overlaps the *export-to-CSV crash* baseline task. Use it to verify the sweep matches and enriches rather than duplicating |
| PDF generator (sample) | [`scripts/generate_ep07_sample_pdf.py`](../../scripts/generate_ep07_sample_pdf.py) | Regenerate the sample if you want to change the seeded phrases |
| Baseline seeder | [`scripts/seed_q3_sample_tasks.py`](../../scripts/seed_q3_sample_tasks.py) | One-shot, idempotent. Creates 10 `lc_task` rows on Q3 Widget Launch (titles prefixed `[SEED]`), 3 with PDFs attached to `lc_relateddocuments`. Two are intentional dedup targets for the sweep. Uses the Dataverse Web API directly |
| Baseline artifact generator | [`scripts/generate_q3_seed_artifacts.py`](../../scripts/generate_q3_seed_artifacts.py) | Reportlab. Emits the 3 baseline PDFs to `seed-artifacts/` |
| Baseline artifacts | [`seed-artifacts/`](seed-artifacts/) | The 3 PDFs the seeder attaches; phrasing overlaps the sweep findings so dedup lands |
| Seed-prefix cleanup | [`scripts/remove_seed_prefix.py`](../../scripts/remove_seed_prefix.py) | One-shot, idempotent. Strips the `[SEED] ` title prefix from the seeded tasks once you no longer need the marker (e.g. before sharing the environment) |
| Tool catalog | [`dataverse-mcp-tools.json`](dataverse-mcp-tools.json) | Authoritative JSON-RPC `tools/list` response from the new MCP shape. Cited from this README and from the social post |
| This README | `episodes/ep-07-scout-autopilot/README.md` | Repro-only |
| Recording script | [`recording-script.md`](recording-script.md) | Internal: producer cues, prompts, B-roll timing, pre-record setup, between-takes reset |

---

## Prerequisites

- Episodes 1–6 substrate present in the target environment: the `lc_launch` / `lc_milestone` / `lc_task` / `lc_statusupdate` tables, at least one launch in `At Risk` or `Blocked` state (`Q3 Widget Launch` is the standing demo data), and the Ep-5 `lc_risksummary` AI prompt column on `lc_launch`.
- **Files enabled** on the `lc_task` table (the seeder attaches to tasks, and the enrichment path attaches to tasks) **and** on the `lc_launch` table. On `lc_task` the column is `lc_relateddocuments` (matches the seeder); on `lc_launch` the existing files column is fine.
- **`Available for Search` enabled** on the `lc_relateddocuments` file column of `lc_task` (Power Apps → Tables → Task → Columns → `Related Documents` → *Searchable*). This is the toggle that lets `search_data` index the PDF body content; without it, the dedup beat collapses to title + notes only.
- **Microsoft Scout** desktop, Frontier preview, signed in as a user with Dataverse access to the target environment.
- The **Launch Control MCP server** registered in Scout: Settings → Extensions → MCP Servers → `https://<your-org>.crm.dynamics.com/api/mcp_preview`. Sign in.

> **Why `/api/mcp_preview` and not `/api/mcp`.** This episode uses the **preview** endpoint because the dedup story depends on three preview-only tools: `search_data` (semantic search over rows *and* indexed file content in one call), `invoke_api` (call a Custom API by name from the agent), and `execute_prompt` (run an AI Prompt by id from the agent). GA `/api/mcp` is a strict subset (15 tools); it does not yet expose those three. Episode 6's Cowork plugin uses the same `/api/mcp_preview` endpoint, so Scout and Cowork are pointing at the same surface — the difference is just the wrapper. Note the underscore in `mcp_preview`; `/api/mcp/preview` (slash) does not exist.

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
