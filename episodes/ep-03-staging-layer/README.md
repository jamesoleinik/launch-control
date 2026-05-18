# Episode 3 — Migration & Analysis

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Migration with the Python SDK · ⭐ pandas DataFrames over Dataverse · ⭐ AI prompt column on `lc_launch`
**Layer:** 🟠 Layer 3 (Operations) + 🟢 Layer 1 (Data — finally connected end-to-end)
**Coding agent:** GitHub Copilot · **Runtime:** `PowerPlatform-Dataverse-Client` (Python SDK)

---

## The hook

> _"Last episode the CLI ingested five tracker tables — all isolated. Today the Python SDK migrates them into one unified Launch model, lets us analyze the result with pandas, and lights up an AI prompt column that Episode 10 will read natively."_

Episode 1 modeled the unified core (`lc_launch`, `lc_milestone`, `lc_task`, `lc_teammember`, `lc_statusupdate`).
Episode 2 used the CLI to ingest five raw shadow trackers (`lc_stg_tracker_a…e`) — each carrying full inline provenance (`lc_sourceid`, `lc_sourcefile`, `lc_ingestedat`, `lc_rawjson`).
But the unified tables were still empty — staging didn't connect to the brain.

Episode 3 closes that loop using the **official Microsoft Dataverse Python SDK**
(`PowerPlatform-Dataverse-Client`) — and shows that the same SDK turns Dataverse into
a first-class analytics surface via pandas DataFrames.

The Python SDK is the star. One client, two superpowers: **bulk migration** and
**in-process analysis**. Then a maker-portal beat — we add an AI **prompt
column** on the launch row *before* migrating, so the migration itself
becomes the event that makes Dataverse write its own risk summary.

---

## The narrative beat

The opening callback is literal. The viewer sees five staging tables full of
rows on the left and the unified `lc_task` / `lc_milestone` tables sitting at
zero on the right (the seeded Q3 Widget Launch row from Ep 1 is still on
`lc_launch`, but the milestones and tasks that should hang off it haven't
crossed the bridge yet). The question on screen:

> _"Do these connect to the main model?"_

Then: _"Let's connect them — in Python."_

---

## Schema map (reference for the rest of this episode)

Every unified row that comes from staging carries a **back-reference
lookup** to the staging row it came from. Provenance is a real
relationship, not a synthesized string — which means a view, a gen page,
or an Ep 6 agent can `$expand` from a unified row straight back to its
origin row with one query.

| Source staging table | Back-reference lookup on the target | Target unified table |
|---|---|---|
| `lc_stg_tracker_a` | `lc_task.lc_sourcestagingaid` | `lc_task` |
| `lc_stg_tracker_b` | `lc_task.lc_sourcestagingbid` | `lc_task` |
| `lc_stg_tracker_c` | `lc_milestone.lc_sourcestagingcid` | `lc_milestone` |
| `lc_stg_tracker_d` | `lc_task.lc_sourcestagingdid` | `lc_task` |
| `lc_stg_tracker_e` | `lc_milestone.lc_sourcestagingeid` | `lc_milestone` |

After Ep 3 finishes, the 16 milestones (8 from Tracker C product
initiatives + 8 from Tracker E release entries) all roll up to the **one**
`lc_launch` row — Q3 Widget Launch — via `lc_milestone.lc_launchid`. The
61 tasks roll up to those milestones via `lc_task.lc_milestoneid` and to
the launch directly via `lc_task.lc_launchid`. The episode's three parts
explain how that happens.

---

## Part 1 · Analysis — the pandas tour (`dataframe_tour.py`)

Before migrating anything, the SDK's pandas surface gets a five-stop tour to make
one point: **the Python SDK isn't just for writes; it's a query and analysis engine**.

### The on-camera Copilot prompt

The `dataframe_tour.py` script is written by the coding agent during the
recording. Open Copilot CLI (or Claude Code) in the repo with the
`dataverse@awesome-copilot` plugin loaded, then type:

> _"Write a five-stop pandas tour over our unified Launch model in
> `scripts/python/dataframe_tour.py`. The five staging tables are
> `lc_stg_tracker_a`..`lc_stg_tracker_e`; the unified tables are `lc_task`,
> `lc_milestone`, `lc_launch`. Use `client.dataframe.get(...)` for reads,
> `client.query.sql(...)` for a T-SQL TOP query, and `pd.merge` to join a
> staging row to its promoted twin **on the back-reference lookup**
> (`_lc_sourcestagingaid_value` etc.). Last stop: a provenance pivot
> counting how many unified rows came from each tracker. Use the auth
> helpers in `scripts/auth.py`."_

The agent figures out the column-rename quirks (`lc_sourceid`,
`lc_sourcefile`), the SDK's typed surface, and the pandas merge keys on
its own. Re-prompt only if it forgets the back-reference syntax.

### What the tour produces

| Stop | What it shows | API |
|---|---|---|
| 0 | Snapshot of unified row counts (`lc_launch` / `lc_milestone` / `lc_task`) — the headline before/after the migration | `client.dataframe.get(table, select=[pk])` × 3 |
| 1 | Read a staging table as a DataFrame | `client.dataframe.get("lc_stg_tracker_a", select=[...])` |
| 2 | Profile row counts across all five staging tables | `dataframe.get` in a loop, then `pd.DataFrame(rows)` |
| 3 | Run a T-SQL query for the top recent tasks | `client.query.sql("SELECT TOP 5 ... ORDER BY ...")` |
| 3b | Join staging + unified rows with a pandas merge — **on the lookup column itself** | `staging.merge(tasks, left_on="lc_stg_tracker_aid", right_on="_lc_sourcestagingaid_value")` |
| 4 | Read the unified `lc_task` view filtered to promoted rows (any `_lc_sourcestaging*_value` non-null) | `dataframe.get("lc_task", select=["lc_isblocked", ...])` |
| 5 | Group promoted rows by which staging-source lookup is populated | `df[lookup_col].notna().sum()` per tracker |

Run the tour twice — once before `promote.py`, once after. Stop 0 flips
from `lc_milestone=0 / lc_task=0` to `lc_milestone=16 / lc_task=61`, and
Stop 5's provenance pivot fills in to sum to **77**. That's the "it
works" beat the rest of the episode rides on.

A handful of SDK gotchas worth flagging out loud — both the well-known ones
and a couple that bit us while writing the tour:

- **`client.query.sql()` only supports relationship-based JOINs.** Joining on
  a computed expression returns `"No valid link found in JOIN condition"`.
  The lookup-based design above means we don't need a computed JOIN — but
  if you ever did, `pd.merge` is the answer.
- **`UNION ALL` isn't supported.** Pull each side and `pd.concat`.
- **`client.query.sql()` needs the TDS endpoint** enabled on the environment.
  The script catches the failure and prints a friendly notice — the pandas
  merge in 3b carries the join story either way.
- **`client.query.sql()` returns `list[Record]`, not a DataFrame.** Each
  `Record` exposes a `.data` dict; convert with
  `pd.DataFrame([r.data for r in result])`. Treating it as a DataFrame
  raises `AttributeError: 'list' object has no attribute 'to_string'`.
- **Lookup columns must be selected by their `_<logical>_value` projection.**
  `client.dataframe.get("lc_task", select=["lc_sourcestagingaid"])` silently
  drops the lookup; ask for `_lc_sourcestagingaid_value` instead. (The
  same rule applies inside `promote.py`'s upsert-index reader — get it
  wrong and re-runs duplicate every row instead of updating in place.)

These are great teaching moments. **Analysis where the data lives, no export step.**

---

## Part 2 · The prompt column — added by hand in the maker portal

**This step lands before the migration.** Why? Because the column needs to
exist when `promote.py` runs — Dataverse triggers the prompt evaluation
whenever a related row (a milestone, a task, a status update) changes. With
the column wired up first, the migration itself becomes the trigger that
populates the AI risk summary. The viewer sees cause → effect in one beat.

**What an AI prompt column is.** A column whose value is generated by an
LLM every time the row's data changes — the prompt body is part of the
column metadata, and Dataverse re-evaluates it server-side. Pick from
**nine out-of-the-box models** spanning OpenAI and Anthropic, or point the
column at **your own endpoint from Azure AI Foundry**. No external
orchestration, no plumbing — model choice is a column setting.

### The on-camera moment (no script — clicks in PPAC)

Dataverse prompt columns are a distinct column **type** in the maker
portal, not a Memo column you wire a prompt to after the fact. They
have to be created interactively. The full Web API surface for
prompt-column metadata isn't published yet — when it is, this beat
collapses into a script call. Until then, the on-camera moment is
deliberately a maker-portal click-through:

1. https://make.powerapps.com → **LaunchControl** solution → **Tables**
   → **Launch** → **Columns** → **+ New column**.
2. Display name: **Risk Summary**.
3. Data type: **Prompt** (under the AI-built-in types).
4. Paste the prompt body below into the prompt-authoring panel.
5. Save. The column logical name lands as `lc_risksummary` (publisher
   prefix `lc_`); Dataverse stamps `lc_risksummary_promptcolumndetails`
   and `lc_risksummary_promptcolumnstatus` companion fields automatically.

### The prompt body (copy verbatim)

```
You are a product launch risk analyst. Analyze the following launch data and
generate a brief risk assessment.

Launch Name: {{lc_launch.lc_name}}
Launch Status: {{lc_launch.lc_launchstatus}}

Related Milestones: {{lc_launch.Launch (lc_milestone).lc_milestonestatus}}
Related Status Updates: {{lc_launch.Launch (lc_statusupdate).lc_title}}

Instructions:
1. Identify any milestones that are "Blocked" or "At Risk"
2. Flag any concerning patterns in status updates
3. Provide a one-sentence overall risk summary

Keep the response under 3 sentences.
```

The `{{lc_launch.Launch (lc_milestone).lc_milestonestatus}}` syntax is
Dataverse's prompt-column DSL for following the 1:N relationship named
`Launch` (the relationship Ep 1 created from `lc_milestone.lc_launchid` →
`lc_launch`) and pulling the milestone status from every related row.
Same shape for the status-update traversal.

Right after saving, the Q3 Widget Launch row still has an **empty**
`lc_risksummary` — there are no related milestones or tasks yet. That's
the setup. The payoff comes the moment `promote.py` writes the first
batch of related rows.

**Why this beat is in Ep 3, not Ep 1:** Ep 1 is about modeling the *human*
shape of the data. The prompt column needs **rows** to summarize — and
Ep 3 is the first episode that puts real, related rows into the unified
model. With the column added first, the migration is what makes the AI
write.

---

## Part 3 · Migration — the promotion script (`promote.py`)

### The on-camera Copilot prompt

Same coding agent as Part 1. Type:

> _"Write scripts/python/promote.py to migrate our five staging trackers
> into the unified Launch model. Topology: tracker A/B/D → `lc_task`,
> tracker C/E → `lc_milestone`. The upsert key is the **back-reference
> lookup** on each unified table — `lc_sourcestaging<x>id` — bound with
> `@odata.bind`. Read with `client.dataframe.get`, dedupe by `lc_sourceid`
> keeping the latest `modifiedon`, map staging string statuses (`NotStarted`,
> `InProgress`, `Blocked`, `AtRisk`, `OnTrack`, etc.) onto the unified
> picklist option-set ints, set `lc_isblocked = True` and `lc_blockerreason`
> on Blocked tasks. **Last step: touch the lc_launch row with a no-op
> update so Dataverse re-evaluates the prompt column.** Support
> `--dry-run` and `--tracker NAME`. Idempotent — re-runs should update
> in place. Use the auth helpers in `scripts/auth.py`."_

The agent will write the recipes, the dedupe, the option-set maps, and the
upsert. Re-prompt if it tries to invent a string staging-source key — point
it at the back-reference lookups.

### What the script does

The `--tracker NAME` and `--dry-run` flags survive into the final script,
but the headline behavior is: **the back-reference lookup IS the upsert
key**. Concretely, for each tracker (milestones first, so task trackers
can resolve milestone hints against the freshly-promoted set):

1. **Read** every row from staging via `client.dataframe.get(...)` (with
   `lc_sourceid`, `lc_ingestedat`, and `modifiedon` so we can dedupe).
2. **Dedupe** by `lc_sourceid`, keeping the most-recently-modified row
   (last-writer-wins). Staging is append-only — every `npm run ingest`
   re-inserts the same logical row. Dedup is non-negotiable.
3. **Map** the staging string statuses onto the target unified picklist
   option-set ints (`10600301`..`10600304` for tasks, `10600201`..`10600205`
   for milestones).
4. **Build** an upsert payload. The back-reference lookup
   (`lc_sourcestaging<x>id@odata.bind`, per the schema map at the top of
   this episode) is the upsert key. Tracker A's `lc_status == "Blocked"`
   rows also get `lc_isblocked = True` and an `lc_blockerreason` (the
   staging `lc_notes`) for Ep 9's red-banner card.
5. **Look up** the existing unified row by the back-reference lookup; if
   found → `client.records.update(...)`. If not → `client.records.create(...)`.
6. **Forward provenance** automatically — the lookup IS the provenance.
7. **Touch `lc_launch`** as the final step. Dataverse prompt columns
   recompute only when a column on the row they live on changes — not
   when *related* rows change. So after the 77 staging rows have been
   written under the launch, `promote.py` writes the launch's `lc_name`
   back to itself. That stamps `modifiedon`, fires the prompt-column
   evaluator, and 30–60 seconds later the AI summary appears.

The dedup + lookup-key story is the unsung hero. It's why a re-run of
`promote.py` produces `0 created, 77 updated` instead of `+77 duplicates`.
Idempotency without ceremony — and the SDK's typed client surface keeps the
upsert logic short (~30 lines for the actual hot loop).

### The AI payoff

The moment `promote.py` finishes, Dataverse sees 16 new milestones and
61 new tasks all rolling up to the Q3 Widget Launch row. Within 30–60
seconds it evaluates the prompt and writes back to `lc_risksummary`.
Refresh the launch row in the maker portal — the cell that was empty
before the migration now holds a generated paragraph like:

> *"Two milestones at risk (App Insights workspace blocked; Frankfurt
> region capacity request blocked). Several status updates show schedule
> slip on Tracker B marketing tasks. Overall: high risk to GA date."*

**The Python SDK fed the data. Dataverse wrote its own summary.** That's
the punchline.

---

## What's deliberately NOT in this episode

- **`CalculateLaunchReadiness` custom action** — that's Episode 5, where it
  belongs alongside BYO MCP. Pulling it forward would muddy the "Python SDK
  migration + analysis + prompt column" story.
- **Scripting the prompt-column creation.** Dataverse prompt columns are
  preview and the type isn't surfaced through the metadata Web API yet.
  When it lands, this beat collapses into a script call. Until then it's
  an honest maker-portal click — which is *also* the shortest way to
  show the feature exists.

---

## What you see on screen

1. The unified tables, mostly empty (only the seeded Q3 Widget Launch row).
   The staging tables, full (77 rows total). The disconnect.
2. GitHub Copilot writes `dataframe_tour.py` from the Part 1 prompt.
   `python scripts/python/dataframe_tour.py` runs end-to-end. Stop 0
   prints a tidy three-row snapshot — `lc_launch=1, lc_milestone=0,
   lc_task=0` — and the script even hints at running `promote.py` because
   the unified side is empty. The remaining stops scroll through the
   staging profile (A=28, B=21, C=8, D=12, E=8 → 77 rows total), the TDS
   `TOP 5` query, the pandas merge (which currently matches zero rows —
   the unified side hasn't been populated yet), and the provenance pivot
   (all zeros so far). The viewer sees the **Python SDK + pandas**
   operating on real Dataverse data — no export, no ETL job.
3. In the maker portal: `lc_launch` → **+ New column** → type **Prompt**,
   display name **Risk Summary**, paste the prompt body from Part 2 above,
   save. Refresh the Q3 Widget Launch row — `lc_risksummary` is **empty**.
   No related rows yet, nothing to summarize.
4. Copilot writes `promote.py` from the Part 3 prompt. Quick scroll.
5. `python scripts/python/promote.py --dry-run` prints
   `Before:  lc_milestone=0   lc_task=0`, then per-tracker
   `read=N  deduped=N  created=N  updated=0  skipped=0` for C/E/A/B/D,
   and finally `=== Promotion complete ===  rows read 77  rows created 77`.
6. `python scripts/python/promote.py` (the real run) ends with
   `After:   lc_milestone=16  lc_task=61   (delta: +16 / +61)` and prints
   `Touched lc_launch (Q3 Widget Launch) to trigger prompt-column refresh.`
   right before the totals.
7. Re-run the dataframe tour. Stop 0 now reads `lc_milestone=16,
   lc_task=61`. The pandas merge in Stop 3b matches **28** rows (all of
   Tracker A). Stop 4 reports `61 / 61` tasks carry a back-reference
   lookup. Stop 5's provenance pivot sums to **77** (28 + 21 + 8 + 12 + 8).
8. Re-run `promote.py`. Output flips to `created=0 updated=N` for every
   tracker; totals are `0 created, 77 updated`. Idempotent.
9. Wait ~45 seconds (or splice). Refresh the Q3 Widget Launch row —
   `lc_risksummary` now holds a generated paragraph. The cell that was
   empty before the migration just filled itself.
10. **The punchline:**
    > _"The SDK reads, analyzes, and migrates — same client, same session.
    > And the column we added before the migration writes itself the
    > moment the data arrives. The brain grounds itself."_

---

## Files in this episode

| File | Role |
|---|---|
| [`scripts/python/promote.py`](../../scripts/python/promote.py) | The migration. Topology-driven, dedupes, upserts via lookup columns. |
| [`scripts/python/dataframe_tour.py`](../../scripts/python/dataframe_tour.py) | Five-stop pandas tour over the live data. |
| [`scripts/python/_reshape_env_for_ep3.py`](../../scripts/python/_reshape_env_for_ep3.py) | Off-camera prep: brings the env into the topology this episode expects (drops one stray lookup, adds the milestone-side staging-E lookup + the `lc_isblocked`/`lc_blockerreason` columns). Run once per env. |
| [`scripts/auth.py`](../../scripts/auth.py) | Shared `load_env` / `get_credential` (re-used from earlier episodes). |
| [`datamodel/mappings/unified_mapping.yaml`](../../datamodel/mappings/unified_mapping.yaml) | `promote_to:` hints + Ep 2 CLI ingestion config. |
| *(no script)* Prompt column on `lc_launch.lc_risksummary` | Added by hand in the maker portal. See **Part 2** for the prompt body. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'
pip install -r scripts/python/requirements.txt

# (one-time per env) bring the env's lookup topology in line with this episode
python scripts/python/_reshape_env_for_ep3.py

# tour the SDK's pandas surface (BEFORE: Stop 0 shows lc_milestone=0, lc_task=0)
python scripts/python/dataframe_tour.py

# add the prompt column BEFORE migrating so the migration triggers
# Dataverse to populate it — done by hand in the maker portal:
#   make.powerapps.com -> LaunchControl -> Tables -> Launch
#   -> + New column -> Type: Prompt -> name "Risk Summary"
#   -> paste the prompt body from this README's Part 2 -> Save.

# migrate staging -> unified — fires the prompt evaluation when it lands
python scripts/python/promote.py --dry-run    # preview: 77 to create
python scripts/python/promote.py              # real: 77 created, lc_milestone=16, lc_task=61

# tour again (AFTER: Stop 0 shows lc_milestone=16, lc_task=61; Stop 5 sums to 77)
python scripts/python/dataframe_tour.py
```

Re-run `promote.py` as often as you like. It's idempotent — re-runs
report `0 created, 77 updated`.

---

## Why Ep 3 matters for Ep 9 (the Launch Command Center)

Episode 9's hero shot — the Launch Command Center generative page with all four
kanban columns full, every task showing a milestone tag + owner, and Blocked
cards displaying their red reason banner — only works because Ep 3 populates
the data with enough breadth and depth. The CSVs in `datamodel/samples/`
are deliberately sized to land:

- **16 milestones** spanning the milestone-status buckets (NotStarted /
  Planned, InProgress / OnTrack, AtRisk, Blocked / Delayed, Done) on the
  Q3 Widget Launch — 8 from Tracker C (product initiatives) + 8 from
  Tracker E (release entries).
- **61 tasks** distributed across the kanban columns with at least 3 cards
  per column so no kanban column reads as empty on camera — 28 from
  Tracker A + 21 from Tracker B + 12 from Tracker D.
- Every task carries a real owner (resolves to `lc_teammember` via
  Trackers A/B/D's `owner` email column).
- Every Tracker A `Blocked` task carries an `lc_blockerreason` string
  (the staging `lc_notes` field) so the red banner on the gen-page card
  has content. Trackers B/D fall back to a `[Category] (no detail in source)`
  reason — still better than NULL.

The Ep 9 preflight (`python episodes/ep-09-the-dashboard/preflight.py`) verifies
all of the above on the live env. If it ever fails after a fresh ingest, fix it
in the **Ep 3 sample CSVs**, not in Ep 9 — Ep 9 only renders what Ep 3 lands.

## Why Ep 3 matters for Ep 10 (Copilot Just Knows)

Ep 10's narrative — "I just ask M365 Copilot, no agent, no plugin, no MCP"
— only works because Ep 3:

- Lands the rows that Copilot needs to ground against (without rows,
  Copilot truthfully responds "I don't have any launches to summarize").
- Adds the `lc_risksummary` prompt column. The Ep 10 backup prompt
  ("Summarize the risks for the Q3 Widget Launch") reads it directly.
- Stamps every promoted row with a queryable back-reference lookup, so
  Copilot's grounding pulls the right related-record context when asked
  "where did this task come from?"

Ep 10 promises native intelligence; Ep 3 is where you earn it.
