# Episode 2 — Process Modeling

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Business Skills as process · ⭐ `@microsoft/dataverse` CLI-driven authoring + ingestion
**Layer:** 🔵 Layer 2 (Intelligence) + 🟢 Layer 1 (Data)
**Coding agent:** GitHub Copilot · **Runtime:** `@microsoft/dataverse` CLI

---

## The hook

> _"Episode 1 modeled the data. Episode 2 models the process — the playbook every agent has to follow — and we let the CLI do the work."_

Every launch team has a process living in a Word doc nobody reads. In this episode we
turn that **literal Word doc** into something agents can actually execute: a coding
agent extracts it into structured **Business Skills**, the **`@microsoft/dataverse` CLI**
registers them into Dataverse, and the same CLI hydrates the staging tables the skills
will reason over.

The flow on camera, end to end:

1. Show the messy real-world input — [`business-skills/source/launch-playbook.docx`](../../business-skills/source/launch-playbook.docx)
2. The coding agent reads it and emits structured markdown skills
3. `npm run upload-skills` (CLI-driven) registers them into the environment
4. `npm run ingest` (CLI-driven) hydrates the staging tables

The CLI is the star of steps 3 and 4. The coding agent does step 2 — the *reasoning*
about what's a rule and what's just prose.

---

## Prerequisites · Install the `@microsoft/dataverse` CLI

The same CLI registers the skills (Part 1) and hydrates the staging tables (Part 2).
Install it once before running either step.

The CLI is published on npm as [`@microsoft/dataverse`](https://www.npmjs.com/package/@microsoft/dataverse).
Prerequisite: Node.js 18+.

```bash
# install globally (recommended — ~10–30s faster per call on Windows than npx)
npm install -g @microsoft/dataverse

# or run without installing (always picks up latest)
npx -y @microsoft/dataverse@latest <command>

# first-time auth against your environment
dataverse auth create --environment https://<your-org>.crm.dynamics.com/
dataverse auth list
```

Reference: [Microsoft Learn — Dataverse CLI](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/dataverse-cli).

---

## Part 1 · Process as Business Skills

The input is a real-world Contoso launch playbook —
[`business-skills/source/launch-playbook.docx`](../../business-skills/source/launch-playbook.docx) —
written the way these docs always look: mixed prose and headers, the occasional bullet
list, several intertwined policies buried among review notes and reorg references. The
kind of doc that lives on SharePoint and gets opened twice a year, usually in a panic.

The coding agent reads it and **decides** what skills to author. We don't hand it a
list of skill names; the agent identifies the distinct policies in the document and
emits one structured markdown file per policy in [`business-skills/`](../../business-skills/).
That's the whole point — the agent does the *process modeling*, not us.

**The prompt to the agent is intentionally one line:**

```
Read business-skills/source/launch-playbook.docx and extract its policies as
Dataverse Business Skills. One markdown file per skill in business-skills/.
Follow the existing skill style.
```

Once the markdown exists, the CLI script registers it:

```bash
cd scripts/cli
npm run upload-skills
```

Skills are surfaced through the **Dataverse MCP server** — once registered, every
MCP-aware agent (Copilot Studio, GitHub Copilot, Claude Code) can list them, read them,
and execute them against live Dataverse data without any per-agent integration work.

The process is **portable**: same markdown, every runtime.

> **What the agent produced in our run.** Seven skills came out — the three core
> policies extracted from the playbook (`playbook-launch-readiness.md`,
> `playbook-escalation.md`, `playbook-status-transitions.md`), plus four richer
> standing skills the agent decided to keep separate from the playbook trace
> (`launch-readiness-checklist.md`, `escalation-policy.md`,
> `status-transition-rules.md`, `launch-readiness-digest.md`). Your agent might
> split or merge differently as the playbook evolves. That's expected, and exactly
> why we don't prescribe.

> **Note on `dataverse skill upload` (as of v1.0.31).** The subcommand exists and accepts
> directories / `.zip` / `.skill` / `.md` files, but currently fails with
> `System.InvalidOperationException: Reflection-based serialization has been disabled
> for this application.` (an AOT/JSON source-generator bug in
> `SkillUploadCommand.CallUploadBusinessSkillAsync`). Re-test on each CLI release.
>
> **Workaround — go through `data create` / `data update`.** The `skill` table is a
> regular Dataverse entity (`EntitySetName=skills`, attributes `name`, `description`,
> `body`, `uniquename`, `ispersonal`) so the working `data` subcommand can upload
> the markdown directly, bypassing the broken serializer in `skill upload`.
> [`scripts/cli/upload-skills.mjs`](../../scripts/cli/upload-skills.mjs) walks
> `business-skills/`, reads the `# Title` and `## Description` from each markdown
> file, derives a `uniquename` from the file stem, and either **creates** the
> record or **updates** the existing one (matched by `uniquename`). Verify with
> `dataverse skill list`.

---

## Part 2 · The CLI as the orchestrator

Process modeling isn't just about authoring rules — it's about wiring them to real
data. The same `@microsoft/dataverse` CLI that registers the skills also hydrates the
staging tables they reason over.

### What runs

Five sample CSVs in [`datamodel/samples/`](../../datamodel/samples/) — one per tracker —
plus a single mapping file [`datamodel/mappings/unified_mapping.yaml`](../../datamodel/mappings/unified_mapping.yaml)
drive the entire ingestion. Adding a sixth tracker is a YAML edit, not a code change.

```bash
cd scripts/cli
npm install            # one-time
npm run setup-auth     # one-time per machine
npm run upload-skills  # business-skills/*.md → Dataverse skill table
npm run ingest         # datamodel/samples/*.csv → lc_stg_tracker_a..e
```

### What the CLI does, step by step

1. **Read mapping.** `unified_mapping.yaml` declares every tracker, its target table,
   its columns, and their types. The script translates the YAML's schema names
   (`lc_TrackerA`, `lc_SourceRowId`, `lc_Milestone`) to the env-actual logical names
   (`lc_stg_tracker_a`, `lc_sourceid`, `lc_milestonename`) via two override tables at
   the top of [`ingest.mjs`](../../scripts/cli/ingest.mjs).
2. **Per tracker:**
   - Parse the CSV (header-driven).
   - For each row, build a Dataverse-shaped JSON payload — coerced types, ISO dates,
     and the field renames above — write it to a temp file, and call
     `dataverse data create --table lc_stg_tracker_xs --data-file <tmp> --return --json`.
   - Stamp inline provenance onto every row: `lc_sourcefile` (filename),
     `lc_ingestedat` (UTC run start), and `lc_rawjson` (the full source row as JSON).
3. **Print a summary** — counts per tracker and a verify command. There is no
   `lc_importrun` / `lc_sourcefile` lookup table in this data model; provenance
   lives inline on each staging row.

### Why a Node.js wrapper around the CLI?

PowerShell orchestration was the original plan, but on Windows + cmd.exe the URL paths
needed for metadata lookups (`?$expand=...&$select=...`) are riddled with shell-control
characters. The Node wrapper applies tight quoting (anything outside `[A-Za-z0-9_\-./:@]`
gets quoted) and writes payloads to temp files instead of inline strings. **The CLI is
still the runtime** — Node just shells out to the installed `dataverse` binary for every
operation (falling back to `npx -y @microsoft/dataverse@latest` if no global install is
on PATH; the global is ~10–30s faster per call on Windows, which matters when looping
77 rows). Bash users can adapt easily; the patterns are unchanged.

---

## Provenance, end to end

Every staging row carries its own audit trail — no parent `lc_importrun` row, no
side `lc_sourcefile` table. Three columns on every `lc_stg_tracker_*` table do the work:

```sql
-- Where did this Tracker A row come from?
SELECT lc_title, lc_sourcefile, lc_ingestedat, lc_rawjson
FROM   lc_stg_tracker_a

-- All rows from one batch
SELECT *
FROM   lc_stg_tracker_a
WHERE  lc_ingestedat = '2026-05-14T03:14:56Z'
```

| Column | Type | What it captures |
|---|---|---|
| `lc_sourcefile`  | string   | The CSV filename (`tracker-a.sample.csv`) |
| `lc_ingestedat`  | datetime | UTC start of the ingest run — the batch key |
| `lc_rawjson`     | memo     | The full source row as JSON, exactly as the CSV parsed it |

Every staging row knows what file it came from, when it landed, and what the
original record looked like. That's the audit trail every business process needs —
and it falls out of the CLI workflow for free.

---

## What this unlocks

- **Process against real data.** The Launch Readiness Checklist can now actually walk
  live records. Episode 7 will plug an agent into the same skills.
- **Reproducible imports.** Drop a new CSV in `datamodel/samples/` and add a mapping —
  no code changes, full provenance.
- **A foundation for migration.** Episode 3 (Python SDK + pandas) will read these
  staging tables and migrate rows into the unified `lc_Launch` / `lc_Milestone` /
  `lc_Task` model.

---

## Files of interest

| Path | What it does |
|---|---|
| `business-skills/source/launch-playbook.docx` | The messy real-world input — Contoso launch playbook. Generated by `build_playbook.py`. |
| `business-skills/source/build_playbook.py` | Authors `launch-playbook.docx` via `python-docx` (re-runnable). |
| `business-skills/*.md` | Skill documents extracted from the playbook by the coding agent — three original skills (`escalation-policy.md`, `launch-readiness-checklist.md`, `status-transition-rules.md`), a fourth surfacing the daily digest path (`launch-readiness-digest.md`), and three playbook-traceable extracts (`playbook-*.md`). |
| `datamodel/mappings/unified_mapping.yaml` | Single source of truth for ingestion |
| `datamodel/samples/tracker-{a..e}.sample.csv` | Sanitized representative CSVs |
| `scripts/cli/ingest.mjs` | CLI orchestrator |
| `scripts/cli/lib/csv-to-json.mjs` | Row → Dataverse JSON payload |
| `scripts/cli/lib/dv.mjs` | CLI wrapper, metadata helpers, create/update |
| `scripts/cli/upload-skills.mjs` | Skill registration — uploads/updates every `business-skills/*.md` via `data create` / `data update` (workaround for the broken `skill upload`) |
| `scripts/cli/setup-auth.mjs` | One-time auth bootstrap |

---

## Run output (representative)

```
=== Launch Control — Business Skills upload ===
→ Discovered 7 skill file(s) in business-skills/
→ Reading existing skills from Dataverse…
✔ Existing skills in env: 0
✔ escalation-policy.md            → created (lc_escalation_policy = <guid>)
✔ launch-readiness-checklist.md   → created (lc_launch_readiness_checklist = <guid>)
✔ launch-readiness-digest.md      → created (lc_launch_readiness_digest = <guid>)
✔ playbook-escalation.md          → created (lc_playbook_escalation = <guid>)
✔ playbook-launch-readiness.md    → created (lc_playbook_launch_readiness = <guid>)
✔ playbook-status-transitions.md  → created (lc_playbook_status_transitions = <guid>)
✔ status-transition-rules.md      → created (lc_status_transition_rules = <guid>)
=== Summary ===
  Created: 7
  Updated: 0
  Failed:  0

=== Launch Control — Episode 2 ingestion ===
→ Target: https://YOUR-ORG.crm.dynamics.com
✔ Loaded 5 mapping(s) from unified_mapping.yaml
→ Run label: Ep2 CLI ingest 2026-05-14 03:14:56 UTC
=== Tracker → Tracker A (lc_stg_tracker_as) ===
→ 28 row(s) from tracker-a.sample.csv
✔   ↳ 1 → <guid>   … ✔   ↳ 28 → <guid>
=== Tracker → Tracker B (lc_stg_tracker_bs) ===  (21 rows)
=== Tracker → Tracker C (lc_stg_tracker_cs) ===  (8 rows)
=== Tracker → Tracker D (lc_stg_tracker_ds) ===  (12 rows)
=== Tracker → Tracker E (lc_stg_tracker_es) ===  (8 rows)
=== Summary ===
  Tracker A: 28/28
  Tracker B: 21/21
  Tracker C:  8/8
  Tracker D: 12/12
  Tracker E:  8/8
  Total inserted: 77
```

