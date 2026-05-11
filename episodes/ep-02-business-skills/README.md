# Episode 2 — Your Playbook & Ingestion

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Business Skills · ⭐ Mapping-driven CLI ingestion
**Layer:** 🔵 Layer 2 (Intelligence) + 🟢 Layer 1 (Data)
**Coding agent:** GitHub Copilot · **Runtime:** `@microsoft/dataverse` CLI

---

## The hook

> _"My team's launch process lives in a Word doc on SharePoint that nobody reads. And the actual work? Spread across five different shadow trackers. What if AI agents could follow the playbook AND read the data?"_

Episode 1 created the brain — the unified data model with five staging tables (TrackerA…E)
ready for whatever shape your shadow trackers come in. Episode 2 makes it usable in two ways:

1. **Codify the playbook** as Business Skills in Dataverse so any agent (Copilot Studio, Claude Code, M365 Copilot) can follow it.
2. **Hydrate the staging tables** from real CSVs using a mapping-driven CLI workflow, with full provenance.

---

## Part 1 · Business Skills

Three skills are authored as plain markdown in [`business-skills/`](../../business-skills/) and registered in the environment:

| Skill | Purpose |
|---|---|
| `launch-readiness-checklist.md` | Walk a launch through go/no-go gates |
| `escalation-policy.md` | Decide who gets paged, when, and how |
| `status-transition-rules.md` | Govern how task and milestone statuses evolve |

Skills are surfaced through the **Dataverse MCP server** — once registered, every MCP-aware
agent (Copilot Studio, GitHub Copilot, Claude Code) can list them, read them, and execute
them against live Dataverse data without any per-agent integration work.

> **Note on the CLI `skill upload` command.** The `@microsoft/dataverse` CLI has a
> `skill upload` subcommand intended for this. It is broken in the current public release
> ("Cannot read properties of undefined"). Until it ships, this episode registers skills
> directly via the MCP server. The narrative is unchanged: skills are first-class,
> portable, and live in source control.

---

## Part 2 · Mapping-driven Ingestion

Five sample CSVs in [`datamodel/samples/`](../../datamodel/samples/) — one per tracker —
plus a single mapping file [`datamodel/mappings/unified_mapping.yaml`](../../datamodel/mappings/unified_mapping.yaml)
drive the entire ingestion. Adding a sixth tracker is a YAML edit, not a code change.

### What runs

```bash
cd scripts/cli
npm install        # one-time
npm run setup-auth # one-time per machine
npm run ingest
```

### What happens

1. **Read mapping.** `unified_mapping.yaml` declares every tracker, its target table, its
   columns, types, and any choice fields.
2. **Prefetch option metadata.** For every choice column (priority/status), the script
   queries
   `EntityDefinitions(LogicalName='lc_trackera')/Attributes(LogicalName='lc_priority')/Microsoft.Dynamics.CRM.PicklistAttributeMetadata`
   via `dataverse api request`. Each tracker has its own option set, so the cache is
   keyed `(table, attribute)` — using the wrong table's options yields HTTP 400 with a
   helpful "Accepted Values: …" error. Ask me how I learned that.
3. **Create an import run.** A single `lc_importrun` record (`Status=Running`) anchors
   provenance for the whole batch.
4. **Per tracker:**
   - Compute SHA-256 checksum of the CSV.
   - Create an `lc_sourcefile` record linked to the import run.
   - For each row, build a Dataverse-shaped JSON payload (coerced types, choice labels →
     integer values, ISO dates), write it to a temp file, and call
     `dataverse data create --table <set> --data-file <tmp> --return --json`.
   - Each tracker row is stamped with `lc_SourceSystem`, `lc_SourceFilename`,
     `lc_SourceRowHash`, and an `lc_ImportRunId` lookup back to the run.
5. **Finalize the run.** Mark `lc_importrun` as Succeeded with the row count.
6. **Verify.** Print a `dataverse data query --sql` snippet to confirm the run.

### Why a Node.js wrapper instead of pure shell?

PowerShell orchestration was the original plan, but on Windows + cmd.exe the URL paths
needed for metadata lookups (`?$expand=...&$select=...`) are riddled with shell-control
characters. The Node wrapper applies tight quoting (anything outside `[A-Za-z0-9_\-./:@]`
gets quoted) and writes payloads to temp files instead of inline strings. The CLI is still
the runtime — Node just shells out to `npx -y @microsoft/dataverse@latest …` for every
operation. Bash users can adapt easily; the patterns are unchanged.

---

## Provenance, end to end

After a successful run you can ask Dataverse:

```sql
-- Latest import run
SELECT lc_name, lc_recordsprocessed, lc_statusname
FROM   lc_importrun
ORDER BY createdon DESC

-- Files in that run
SELECT lc_filename, lc_rowcount, lc_checksum
FROM   lc_sourcefile
WHERE  lc_importrunid = '<run-id>'

-- Where did this TrackerA row come from?
SELECT lc_title, lc_sourcesystem, lc_sourcefilename, lc_sourcerowhash, lc_importrunid
FROM   lc_trackera
```

Every staging row knows what file it came from, when it landed, and as part of which
batch. That's the audit trail every business process needs.

---

## What this unlocks

- **Skills against real data.** The Launch Readiness Checklist can now actually walk live
  records. Episode 6 will plug an agent into the same skills.
- **Reproducible imports.** Drop a new CSV in `datamodel/samples/` and add a mapping —
  no code changes, full provenance.
- **A foundation for normalization.** Episode 3 (Python SDK + pandas) will read these
  staging tables and promote rows into the unified `lc_Launch` / `lc_Milestone` /
  `lc_Task` model with conflict resolution and dedup.

---

## Files of interest

| Path | What it does |
|---|---|
| `business-skills/*.md` | Three skill documents, plain markdown |
| `datamodel/mappings/unified_mapping.yaml` | Single source of truth for ingestion |
| `datamodel/samples/tracker-{a..e}.sample.csv` | Sanitized representative CSVs |
| `scripts/cli/ingest.mjs` | Orchestrator |
| `scripts/cli/lib/csv-to-json.mjs` | Row → Dataverse JSON payload |
| `scripts/cli/lib/dv.mjs` | CLI wrapper, metadata helpers, create/update |
| `scripts/cli/setup-auth.mjs` | One-time auth bootstrap |

---

## Run output (representative)

```
=== Launch Control — Episode 2 ingestion ===
→ Target: https://YOUR-ORG.crm.dynamics.com
✔ Loaded 5 mapping(s) from unified_mapping.yaml
→ Fetching choice option metadata for picklists…
✔ Cached option sets for 8 choice fields
→ Creating lc_importrun: Ep2 CLI ingest …
✔ lc_importrun created
=== Tracker → Tracker A (lc_trackeras) ===
✔ lc_sourcefile created
✔   ↳ row 1 → <guid>
… (B, C, D, E) …
=== Finalizing import run ===
✔ lc_importrun marked Succeeded (records=5)
```
