# Episode 12 — The Dashboard

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Generative Power Apps page · ⭐ `pac model genpage upload` (typed Dataverse access + Fluent UI) · ⭐ Model-driven app shell auto-generated from the Ep 1 tables
**Layer:** 🟣 Layer 3 (the visual surface)
**Coding agent:** Studio AI authoring (Option A) · Claude Code + PAC CLI (Option B)
**Runtime:** Generative page hosted inside a model-driven app

---

> **Hook:** *"I asked Power Apps for a launch command center in plain English. Watch what it built."*

This episode is the visual payoff. Eight episodes of plumbing — tables, skills, virtual entities, custom actions, three runtimes of agents — and now we render it all into a screen the launch room can actually use. Without writing any UI code.

## Why generative pages, not a code app

The original Episode 12 plan was a **two-act**: model-driven app first, then a Power Apps code-first ("code app") that we'd hand-design and ship. We built that code app. It works. It's archived at [`apps/launch-brain-hub/DEPRECATED.md`](../../apps/launch-brain-hub/DEPRECATED.md).

We pivoted because the gen-page narrative is **stronger and tighter**:

- **The story is shorter and louder.** "I described the page. AI built it." vs. "I scaffolded a TS+React app, wired five data sources, fixed a virtual-entity name, redesigned the layout, and pushed it past a governance gate."
- **It's on-brand for the campaign.** "Skills all the way down" — the data model was AI-authored (Ep 1), the agents were AI-authored (Eps 6-8), and now the UI is AI-authored too.
- **The viewer leaves with a take-home.** Generative pages are something a viewer can copy *today* without standing up a Vite project.

The code-first path stays in your back pocket for the day a customer asks for something gen pages can't do (heavy custom branding, mobile-tuned layouts, complex client-side logic). For a 90-second LinkedIn short, gen pages are the right answer.

## The episode in 90 seconds

### Beat 1 — Instant App callback (~20 sec)

Open the auto-generated model-driven app for `lc_launch` that we first glimpsed in Ep 3.

> *"This was free. Dataverse gave us a UI the moment we created the table back in Ep 1 — eight episodes ago, before we wrote a single line of UI code."*

Click through to the **Q3 Widget Launch** row. The viewer sees:

- 16 milestones (8 product initiatives from Tracker C + 8 release entries from Tracker E)
- 61 tasks linked to those milestones, status mix `26 Not Started · 22 In Progress · 8 Blocked · 5 Done`
- The custom action `lc_CalculateLaunchReadiness` returning a verdict and score

> *"This is enough for the team. But the launch room wants one screen, not a navigation tree. So let's just ask Power Apps to build that screen."*

### Beat 2 — Generative Page authoring (~50 sec) — the hero shot

We have **two narrative options** for Beat 2 — both work, pick based on production constraints:

#### Option A — Studio AI authoring on camera (original plan, kept as primary)

In the maker, **+ New page → Generative page**. Paste:

> Build a Launch Command Center page for the Q3 Widget Launch — readiness verdict at the top, milestones on a horizontal timeline color-coded by status, tasks grouped as kanban columns by status (Not Started / In Progress / Blocked / Done) with milestone tag, owner, and blocker reason on each card, and the agent activity feed (lc_statusupdate, newest first) in a side rail.

Hit Enter. Watch the AI author the page **in real time** — that's the on-camera moment. Publish.

Safety net: a CLI-deployed reference page already exists at sitemap position 1 (see Option B). If the on-camera Studio prompt produces something off-target, we can fall back to opening the pre-deployed page and narrating "and here's what I had Claude Code build earlier."

#### Option B — "Skills all the way down" CLI-deploy narrative (already shipped)

Open the existing **Launch Command Center** page (pre-deployed via `pac model genpage upload`). Narrate:

> *"I didn't even open the Studio for this. I described the page to Claude Code in my terminal, it wrote a single React component file, one PAC CLI command shipped it into this model-driven app — typed Dataverse access, Fluent UI, sitemap registration, all in 30 seconds."*

This option leans into the campaign's "skills all the way down" theme: data model AI-authored (Ep 1), agents AI-authored (Eps 6-8), and now the UI authored by a coding-agent skill against a typed Dataverse schema.

**Recommendation:** record both. Option A is the stronger hero shot for the LinkedIn cut (visible AI authoring); Option B becomes a bonus B-roll for the repo README and a developer-audience deep-dive post.

#### What the rendered page shows (either path)

- KPI strip at the top with milestones-done / open tasks / blocked / readiness score
- Readiness verdict pill computed client-side from milestone aggregates (GO / AT-RISK / NO-GO)
- Milestone timeline with the deepened data popping (16 chips, color-coded)
- Kanban with all four columns populated (no empty columns is critical — that's why we did the data deepening)
- Status updates in the side rail showing entries badged by source (Coordinator from Ep 9, Sentinel from Ep 10, Python agent from Ep 11, plus the System messages from Ep 3)

### Beat 3 — Cold-open setup for Ep 13 (~15 sec)

> *"Same Dataverse data we've been building since Ep 1. AI authored the agents. AI authored the page. Tomorrow — AI just answers from M365 Copilot, no app open."*

This line is load-bearing for Episode 13 — Dataverse Intelligence binds Copilot's environment to the most-recently-used Power Apps environment, so we *must* close Ep 12 having just opened the gen page if we want Ep 13 to land cleanly on camera.

## One-time setup before recording (fully scripted)

Two scripted phases create the **Launch Control** model-driven app, bind the 4 tables, assign roles, deploy the generative page, and set it as the default landing — all programmatically.

### Phase 1 — App shell + table bindings

```bash
python scripts/python/_finish_launch_app.py        # creates app + sitemap + AddAppComponents + PublishXml
python scripts/python/_assign_app_role.py          # grants the app to System Administrator
# Web API AddAppComponents can't bind specific tables (a platform limitation).
# Workaround: export the solution, patch <AppModuleComponents> XML with the real
# entity GUIDs, strip <Workflows>, bump version, reimport. See _import_minimal.py.
```

### Phase 2 — Generative page (also scripted, via PAC CLI)

```bash
# 1. Generate typed Dataverse schema for the gen-page runtime
pac model genpage generate-types \
  --data-sources "lc_launch,lc_milestone,lc_task,lc_statusupdate" \
  --output-file apps/launch-command-center/RuntimeTypes.ts

# 2. Author apps/launch-command-center/launch-command-center.tsx (committed in this repo)

# 3. Transpile locally with a global tsc (PAC's bundled npx-based transpile can hang on
#    Windows during first-run typescript install — see "Known issue" below).
cd apps/launch-command-center
tsc launch-command-center.tsx --target ES5 --module ES2020 --jsx react \
    "--lib" "ES2015,DOM" --skipLibCheck
mv launch-command-center.js launch-command-center.compiled.js

# 4. Upload + add to sitemap (skips PAC's transpile by passing the precompiled JS)
pac model genpage upload \
  --app-id 840766e6-cd4c-f111-bec6-00224805ff5f \
  --code-file ./launch-command-center.tsx \
  --compiled-code-file ./launch-command-center.compiled.js \
  --data-sources "lc_launch,lc_milestone,lc_task,lc_statusupdate" \
  --name "Launch Command Center" \
  --add-to-sitemap

# 5. Promote the gen page to be the FIRST SubArea (default landing)
python ../../episodes/ep-12-the-dashboard/set_genpage_default.py
```

After phase 2, the play URL lands directly on the Launch Command Center page:
`https://<your-org>.crm.dynamics.com/main.aspx?appid=<your-app-id>`

### Known issue — PAC `genpage transpile` hangs

`pac model genpage transpile` and the implicit transpile inside `pac model genpage upload` shell out to `npx -p typescript@5.3.2 tsc ...`. On Windows, that `npx` invocation can wedge during first-run install of TypeScript into the npx cache (CPU pinned at ~1%, no progress, no timeout from PAC). The workaround above pre-compiles with a globally-installed `tsc` and passes `--compiled-code-file` to `upload` to skip PAC's transpile entirely.

## Recording prerequisites

Run the preflight harness:

```bash
python episodes/ep-12-the-dashboard/preflight.py
```

It verifies:

| Check | Expected |
| --- | --- |
| Q3 Widget Launch exists | yes |
| Milestones linked to launch | ≥ 16 |
| Tasks total | ≥ 50 |
| All tasks linked to a launch milestone | yes (no orphans) |
| All four task-status buckets populated | yes |
| Status updates | ≥ 8 |
| Loop-prone cloud flows disabled | yes |

If any check fails, fix it before recording. The most common cause of failure is duplicate tasks — see "Why we disabled three cloud flows" below.

## How the demo data got rich (the Ep 3 backstory)

Ep 12's panels look populated only because Episode 3's pipeline does the work. The chain:

1. **Sample CSVs** in `datamodel/samples/` (`tracker-a.sample.csv`, `tracker-b.sample.csv`, `tracker-c.sample.csv`, `tracker-d.sample.csv`, `tracker-e.sample.csv`) — A/B/D each carry a `milestone` hint column added during the Ep 12 pivot so promoted tasks always link to a milestone.
2. **Bulk re-ingest** (`scripts/python/bulk_reingest.py`) lands all CSVs into staging tables `lc_TrackerA..E` under a single `lc_ImportRun`.
3. **Promotion** (`scripts/python/promote.py`) runs the milestone-trackers (C, E) first to seed `lc_milestone`, refreshes its name → id index, then runs the task-trackers (A, B, D), resolving each `milestone` hint to a real `lc_milestone` lookup via `_resolve_milestone()`.

Net result, every clean run: **16 milestones + 61 tasks (28 + 21 + 12), all linked, healthy status mix**.

The promotion script is idempotent (upserts via the back-reference lookup columns `lc_sourcestaging<x>id`), so re-running it is safe. The ingest script is **not** idempotent — always wipe staging before re-ingesting (use `scripts/python/wipe_demo_data.py`).

## Why we disabled three cloud flows

While iterating Ep 12, we caught the demo creating duplicate tasks during ingest (some `lc_TrackerA` source rows mapped to **9 copies** of the same task). The cause turned out to be three legacy Power Automate cloud flows wired up in earlier episodes that triggered on `lc_task` add/modify/delete and called Copilot Studio (Sentinel agent), which in turn — depending on its prompt and tools — could create new `lc_task` records, looping back through the trigger.

Disabled (via `scripts/python/_disable_flows.py`):

- `When a task is blocked` — fired Sentinel on `lc_isblocked = true`
- `When a row is added, modified or deleted` — fired Sentinel on any `lc_task` change
- `Daily Trigger` — recurrence-based Sentinel call

For the recording, leave them off. Re-enable after by flipping `statecode` back to `1` in the `workflows` table.

## Files touched in this episode

- `episodes/ep-12-the-dashboard/README.md` — this file
- `episodes/ep-12-the-dashboard/preflight.py` — preflight harness
- `episodes/ep-12-the-dashboard/set_genpage_default.py` — promotes the gen page to the first SubArea (default landing)
- `apps/launch-command-center/launch-command-center.tsx` — the gen page source (uploaded with `--compiled-code-file`)
- `apps/launch-command-center/RuntimeTypes.ts` — typed Dataverse schema generated by `pac model genpage generate-types`
- `scripts/python/_disable_flows.py` — turns the three loop-prone cloud flows off
- `apps/launch-brain-hub/DEPRECATED.md` — marker for the retired code-first scaffold

## What's *not* in this episode anymore

- No Vite, React, TypeScript, or `pac code push`.
- No virtual-entity wiring on the page (gen pages can include `github_issues` later if we point them at it; we punt that to a future bonus).
- No custom theming beyond what gen pages give us out of the box.

We get all of those back in Ep 15 ("Full Orchestra") if they're worth showing — but a 90-second LinkedIn short doesn't have room for them, and chasing them was eating the recording schedule.

## On-camera checklist

Before you hit record:

- [ ] `python episodes/ep-12-the-dashboard/preflight.py` returns all green
- [ ] Q3 Widget Launch page in the model-driven app loads without error
- [ ] You're authenticated to make.powerapps.com in the demo environment
- [ ] Browser zoom is 110-125% so the kanban columns and chips are readable on a phone
- [ ] You have the gen-page prompt copied to clipboard (Beat 2)
- [ ] You can produce a clean cut after Beat 3 — the next thing the viewer should see is Episode 13's M365 Copilot prompt

---

## Next up

**Episode 13 — Copilot Just Knows.** We close the dashboard tab. With
Dataverse Intelligence on, native M365 Copilot reads the same tables —
no agent, no plugin, no MCP. _"You built the schema. Microsoft handles
the grounding."_
