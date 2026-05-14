# Episode 3 — Migration & Analysis

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Migration with the Python SDK · ⭐ pandas DataFrames over Dataverse
**Layer:** 🟠 Layer 3 (Operations) + 🟢 Layer 1 (Data — finally connected end-to-end)
**Coding agent:** GitHub Copilot · **Runtime:** `PowerPlatform-Dataverse-Client` (Python SDK)

---

## The hook

> _"Last episode the CLI ingested five tracker tables — all isolated. Today the Python SDK migrates them into one unified Launch model and lets us analyze the result with pandas."_

Episode 1 modeled the unified core (`lc_Launch`, `lc_Milestone`, `lc_Task`).
Episode 2 used the CLI to ingest five raw shadow trackers (`lc_TrackerA…E`) with full provenance.
But the unified tables were still empty — staging didn't connect to the brain.

Episode 3 closes that loop using the **official Microsoft Dataverse Python SDK**
(`PowerPlatform-Dataverse-Client`) — and shows that the same SDK turns Dataverse into
a first-class analytics surface via pandas DataFrames.

The Python SDK is the star. One client, two superpowers: **bulk migration** and
**in-process analysis**.

---

## The narrative beat

The opening callback is literal. The viewer sees five staging tables full of rows
and three unified tables sitting empty. The question on screen:

> _"Do these connect to the main model?"_

Then: _"Let's connect them — in Python."_

---

## Part 1 · Analysis — the pandas tour (`dataframe_tour.py`)

Before migrating anything, the SDK's pandas surface gets a five-stop tour to make
one point: **the Python SDK isn't just for writes; it's a query and analysis engine**.

| Stop | What it shows | API |
|---|---|---|
| 1 | Read a staging table as a DataFrame | `client.dataframe.get("lc_trackera", select=[...])` |
| 2 | Profile row counts across all five staging tables | `dataframe.get` in a loop, then `pd.DataFrame(rows).set_index(...)` |
| 3 | Run a T-SQL query for the top recent tasks | `client.query.sql("SELECT TOP 5 ... ORDER BY ...")` |
| 3b | Join staging + unified rows with a pandas merge | `pd.merge(staging_df, unified_df, on=..., suffixes=...)` |
| 4 | Read the unified `lc_task` view filtered to migrated rows | `dataframe.get("lc_task", select=["lc_stagingsource", ...])` |
| 5 | Group migrated rows by source tracker | `combined.groupby(["source", "target"]).size()` |

Two SDK gotchas worth flagging out loud (because the script catches them in real time):

- **`client.query.sql()` only supports relationship-based JOINs.** Joining on a
  computed expression like `ON t.col = CONCAT('lc_trackera:', a.col)` returns
  `"No valid link found in JOIN condition"`. Workaround: pull each side as a
  DataFrame and use `pd.merge`.
- **`UNION ALL` isn't supported either.** Pull each side and `pd.concat`.

These are great teaching moments — the SDK's pandas surface fills exactly the
gap that Dataverse SQL leaves. **Analysis where the data lives, no export step.**

---

## Part 2 · Migration — the promotion script (`promote.py`)

The migration is driven entirely by `unified_mapping.yaml`. Each staging tracker
already has a `promote_to:` block declaring the target table and field map. The
Python script reads that, then for each tracker:

1. **Read** every row from staging via `client.dataframe.get(...)` (with `modifiedon`
   so we can dedupe).
2. **Dedupe** by `lc_sourcerowid`, keeping the most-recently-modified row
   (last-writer-wins). Staging tables are append-only snapshots — every
   `ImportRun` re-inserts the same logical row. Dedup is non-negotiable.
3. **Map** option-set ints from staging-side schema (`10600105…128…145`) to
   unified-side schema (`10600020…23` for tasks, `10600010…14` for milestones).
   Each tracker has its own mapping, hard-coded in the script.
4. **Build** a payload keyed by `lc_StagingSource = "<staging_table>:<sourcerowid>"`.
   This becomes the upsert key.
5. **Look up** the existing unified row by `lc_StagingSource` via `client.entity.get(...)`.
   If found → `client.entity.update(...)`. If not → `client.entity.create(...)`.
6. **Forward provenance** via `lc_ImportRunId@odata.bind`.

The dedup story is the unsung hero. It's why a re-run of `promote.py` produces
`5 updated, 0 created` instead of `+5 duplicates`. Idempotency without ceremony —
and the SDK's typed client surface makes the upsert logic ~20 lines, not 200.

---

## What's deliberately NOT in this episode

- **`CalculateLaunchReadiness` custom action** — that's Episode 5, where it
  belongs alongside BYO MCP. Pulling it forward would muddy the "Python SDK
  migration + analysis" story.
- **Auto-linking migrated milestones to a launch.** Currently milestones land
  with a NULL `lc_launchid`. The narrative for this episode is "staging →
  unified migration" — proving the round-trip is idempotent and provenance-aware.
  Wiring milestones to their parent launch is a small follow-up that can
  ship out-of-band without its own episode beat.

---

## What you see on screen

1. The unified tables, empty. The staging tables, full. The disconnect.
2. `python scripts/python/dataframe_tour.py` runs end-to-end. Five stops, all
   green. The viewer sees the **Python SDK + pandas** operating on real Dataverse
   data — no export, no ETL job.
3. GitHub Copilot writes `promote.py` from `unified_mapping.yaml`. Quick scroll.
4. `python scripts/python/promote.py --dry-run` → "11 read, 5 unique."
5. `python scripts/python/promote.py` → "5 created."
6. The unified tables now have rows. Each one carries `lc_stagingsource =
   "lc_trackera:1"` (or b/c/d/e). Provenance preserved across the migration.
7. Re-run. `5 updated, 0 created.` Idempotent.
8. **The punchline:**
   > _"The SDK reads, analyzes, and migrates — same client, same session.
   > Dataverse holds the memo."_

---

## Files in this episode

| File | Role |
|---|---|
| [`scripts/python/promote.py`](../../scripts/python/promote.py) | The migration. Reads `unified_mapping.yaml`, dedupes, upserts via the Python SDK. |
| [`scripts/python/dataframe_tour.py`](../../scripts/python/dataframe_tour.py) | Five-stop pandas tour over the live data. |
| [`scripts/python/_add_staging_source.py`](../../scripts/python/_add_staging_source.py) | One-time helper that adds `lc_StagingSource` to `lc_Task` + `lc_Milestone`. |
| [`scripts/auth.py`](../../scripts/auth.py) | Shared `load_env` / `get_credential` (re-used from earlier episodes). |
| [`datamodel/mappings/unified_mapping.yaml`](../../datamodel/mappings/unified_mapping.yaml) | The `promote_to:` hints drive everything. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'
pip install -r scripts/python/requirements.txt

# (one-time) ensure lc_StagingSource exists on lc_task + lc_milestone
python scripts/python/_add_staging_source.py

# tour the SDK's pandas surface
python scripts/python/dataframe_tour.py

# migrate staging -> unified
python scripts/python/promote.py --dry-run
python scripts/python/promote.py
```

Re-run `promote.py` as often as you like. It's idempotent.


## Why Ep 3 matters for Ep 9 (the Launch Command Center)

Episode 9's hero shot — the Launch Command Center generative page with all four
kanban columns full, every task showing a milestone tag + owner, and Blocked
cards displaying their red reason banner — only works because Ep 3 populates
the data with enough breadth and depth. The CSVs in `datamodel/samples/`
are deliberately sized to land:

- 16 milestones spanning 5 milestone-status buckets (NotStarted, InProgress,
  AtRisk, Blocked, Complete) on the Q3 Widget Launch
- 61 tasks distributed across all 4 kanban columns (NotStarted 26 · InProgress
  22 · Blocked 8 · Done 5) with at least 3 cards per column so no kanban
  column reads as empty on camera
- Every task carries a real owner (resolves to `lc_teammember` via Tracker A/B)
- Every Blocked task carries a `lc_blockerreason` string (so the red banner
  on the gen-page card has content)
- 36 `lc_statusupdate` rows spanning multiple agent sources (System,
  Coordinator from Ep 6, Sentinel from Ep 7, Python agent from Ep 8) so the
  side rail in the gen page never reads as quiet

The Ep 9 preflight (`python episodes/ep-09-the-dashboard/preflight.py`) verifies all of
the above on the live env. If it ever fails after a fresh ingest, fix it in
the **Ep 3 sample CSVs**, not in Ep 9 — Ep 9 only renders what Ep 3 lands.
