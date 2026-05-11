# Episode 1 — AI-Powered Data Modeling

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Dataverse skill format consumed by a coding agent · ⭐ Mapping-driven schema · ⭐ Provenance from day one
**Layer:** 🟢 Layer 1 (Data) — the foundation
**Coding agent:** GitHub Copilot (with the Dataverse skill plugin) · **Runtime:** `PowerPlatform-Dataverse-Client` (Python)

---

## The hook

> _"Every team has shadow trackers — spreadsheets, Notion pages, Loop tabs — and they drift. Before any agent can help, we need one model that tells the truth."_

I didn't draw this data model in the maker portal. I described the business in
plain English to a coding agent, and the agent did the work — proposed the
tables, wrote the Python, ran it against the environment, iterated when
something broke. That's possible because **Dataverse ships a skill format
that coding agents (GitHub Copilot, Claude Code, the Copilot CLI) consume
directly.** The `dataverse-skills` plugin packages a *Modeling* skill in that
format. The coding agent loads the skill and now it knows how to model on
Dataverse — typed columns, choices, lookups, provenance, solution membership,
the lot.

The Python files you see in this repo (`create_datamodel.py`,
`modeling_skill.py`, `ep1_provenance.py`, `seed_data.py`) are what the coding
agent *produced* using the skill. Re-runnable, idempotent, in source control.

---

## What gets built

### Unified model (created by `scripts/create_datamodel.py`)
| Table | Purpose |
|---|---|
| `lc_Launch` | The product launch (root) |
| `lc_Milestone` | Phase gates that roll up to a launch |
| `lc_Task` | Owned work items under a milestone |
| `lc_TeamMember` | People assigned to a launch |
| `lc_StatusUpdate` | Time-series narrative updates |

### Provenance (created by `scripts/ep1_provenance.py`)
| Table | Purpose |
|---|---|
| `lc_ImportRun` | One row per ingestion (status, count, notes) |
| `lc_SourceFile` | Per-file metadata (name, row count, checksum) |

Plus an `lc_ImportRun` lookup added to every core and staging table.

### Staging tables (created by `scripts/modeling_skill.py` from `unified_mapping.yaml`)
| Table | Source tracker | Promotes to |
|---|---|---|
| `lc_TrackerA` | `tracker-a.sample.csv` | `lc_Task` |
| `lc_TrackerB` | `tracker-b.sample.csv` | `lc_Task` |
| `lc_TrackerC` | `tracker-c.sample.csv` | `lc_Milestone` |
| `lc_TrackerD` | `tracker-d.sample.csv` | `lc_Task` |
| `lc_TrackerE` | `tracker-e.sample.csv` | `lc_Milestone` |

> Tracker names are intentionally generic. Every team has 5+ shadow trackers
> with slightly different shapes — these placeholders represent the *kinds* of
> sheets you'll find (feature lists, planning sheets, roadmap tabs, tooling
> logs, release plans) without leaking specifics.

> The filename `modeling_skill.py` is a nod to what produced it — the
> Modeling skill the coding agent applied. The script itself is just typed
> Python that calls the SDK. The "skill" is the plugin instruction; the
> script is the output.

Every staging table automatically gets four provenance columns
(`lc_SourceSystem`, `lc_SourceFilename`, `lc_SourceRowHash`,
`lc_NeedsManualReview`) and an `lc_ImportRun` lookup.

---

## How it works

`datamodel/mappings/unified_mapping.yaml` is the single source of truth for
the staging schema — *one* file the coding agent and I worked on together,
not five tables created click-by-click in the maker portal:

```yaml
- source: tracker-a.sample.csv
  target_entity: lc_TrackerA
  primary_column: lc_Title
  promote_to: lc_Task
  fields:
    title:    { schema: lc_Title,      type: string,  display: Title }
    priority: { schema: lc_Priority,   type: choice,  display: Priority,
                options: [Low, Medium, High, Critical] }
    status:   { schema: lc_Status,     type: choice,  display: Status,
                options: [NotStarted, InProgress, Blocked, Done] }
```

`scripts/modeling_skill.py` walks this file and calls
`client.tables.create(...)` for each tracker, building columns by type and
assigning stable option-set integers (fixed offsets per `(table, field)`).
The provenance fields are appended uniformly. After all tables exist, it
adds the `lc_ImportRun` lookup using lowercase logical names. All of that
boilerplate the Modeling skill taught the coding agent to handle.

---

## Reproduce

```pwsh
# 1. Core unified model
python scripts/create_datamodel.py

# 2. Provenance tables + lookups
python scripts/ep1_provenance.py

# 3. Staging tables generated from unified_mapping.yaml
python scripts/modeling_skill.py

# 4. Seed sanitized rows + capture an lc_ImportRun
python scripts/seed_data.py
```

The exported, sanitized solution lives at
`datamodel/solutions/ep1_unified_model/` (re-exportable with `pac solution
export --name LaunchControl`).

---

## What this episode showcases

1. **Dataverse's skill format is portable across coding agents.** The same
   skill format Dataverse uses for runtime Business Skills (see Episode 2)
   is also packaged in plugins like `dataverse-skills` so build-time coding
   agents (GitHub Copilot, Claude Code, Copilot CLI) can pick it up. One
   format. Two consumption modes. That's the real news in this episode.
2. **AI-powered modeling, not click-ops.** The Modeling skill turns *"here
   are my trackers, here's a mapping"* into a typed Dataverse schema — choice
   columns, lookups, provenance, solution membership. The coding agent does
   the SDK calls; you stay in the conversation.
3. **Provenance from day one.** Every row knows where it came from
   (`lc_SourceSystem`, `lc_SourceFilename`, `lc_SourceRowHash`,
   `lc_ImportRun`). No spreadsheet detective work later.
4. **Sanitized & shareable.** Only sample CSVs and the mapping file ship in
   the repo; raw trackers are git-ignored.

---

## Files in this episode

- `datamodel/mappings/unified_mapping.yaml`
- `datamodel/samples/*.sample.csv`
- `datamodel/seed-data/*.seed.csv` *(generated by `seed_data.py`)*
- `datamodel/solutions/ep1_unified_model/` *(unpacked LaunchControl solution)*
- `scripts/create_datamodel.py`
- `scripts/ep1_provenance.py`
- `scripts/modeling_skill.py`
- `scripts/seed_data.py`

---

## Next up

**Episode 2 — Your Playbook & Ingestion.** Episode 1 used Dataverse's skill
format to give a *coding agent* what it needs to build the schema. Episode 2
flips the consumer: the same skill format now packages **Business Skills**
that *runtime agents* (Copilot Studio, Claude, M365 Copilot) follow at run
time to actually operate the launch — readiness checks, escalation policies,
status transitions. One skill format, both ends of the agent lifecycle.
