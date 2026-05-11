# Episode 12 — Full Orchestra + Your Turn

> **Hook (Part 1):** *"Twelve episodes. One launch. Watch every piece play together."*
> **Hook (Part 2):** *"Now it's your turn. Clone, paste, ship."*

The closer. Two parts. Part 1 is the **orchestra montage** — every capability built across Eps 1–11 firing in sequence on the same launch. Part 2 is **Your Turn** — viewer goes from `git clone` to a row in their own Dataverse env in under 30 seconds. The repo flips public the moment this drops.

## Why this matters in the arc

Eleven episodes have argued *"this is real, look at this slice."* Ep 12 closes the loop with two assertions:

1. **The slices are one system.** When the gen page (Ep 9), the autonomous Sentinel (Ep 7), the M365 Copilot grounding (Ep 10), and the management plane (Ep 11) all light up against the same record, the audience sees the platform — not eleven feature demos.
2. **It's all in your hands now.** The repo isn't a marketing artifact. It's a runnable system. Cloning it gives you the same launch-control rig in your env in minutes. The CTA isn't *"go read the docs"* — it's *"go clone the repo."*

## Pre-record state — "perfect launch week"

The demo env must be in this exact state before camera turns on. `episodes/ep-12-full-orchestra/orchestra/setup_launch_week.py` enforces it idempotently — re-runnable between takes.

| Thing | Required state |
|---|---|
| Q3 Widget Launch · `lc_launchstatus` | `ReadyForLaunch` (the demo flips it to `Launched` on camera) |
| 16 milestones · `lc_milestonestatus` | All `Complete` |
| 61 tasks · `lc_taskstatus` | All `Done`; `lc_isblocked = false`; `lc_blockerreason` cleared |
| Status updates | A fresh `Ep12Setup::All gates passed` row exists |
| Q4 Holiday Feature launch | **Does not exist yet** (the teaser creates it on camera) |

To rehearse a different take from messy state, run `teardown_launch_week.py --apply` first (restores 12 Complete + 2 AtRisk + 2 Blocked milestones, ~10% blocked tasks with reasons, removes the setup status update row). Then `setup_launch_week.py --apply` again to reset.

Both scripts default to `--dry-run` for safety; pass `--apply` to actually write.

## Part 1 — Orchestra montage (~60 sec)

Six surfaces fire in sequence. Each ~10 sec including a 1-sec lead/tail. Every shot uses the **same launch row** to make the unified-platform point obvious.

| # | Surface | Episode it came from | Beat |
|---|---|---|---|
| 1 | **Gen page dashboard** | Ep 9 | Re-establishing shot. Opens green across the board. *"Same record we built piece by piece — here's the whole picture."* |
| 2 | **Custom action `lc_CalculateLaunchReadiness`** | Ep 4 + Ep 8 | Invoke from terminal via the code-first agent. Returns verdict `GO`, score ≥90. *"The business logic that decides 'ship it' is one call."* |
| 3 | **Python pandas report** | Ep 3 | `python scripts/python/status_report.py` — table prints all milestones at 100%, zero blockers. *"Same data, scripted."* |
| 4 | **GitHub issues via virtual entity** | Ep 4 | Dataverse view of `lc_githubissue` — every issue closed. *"External system, in our table."* |
| 5 | **M365 Copilot** | Ep 10 | Exec-style prompt: *"Is the Q3 Widget Launch ready to ship?"* → "All gates passed." *"No agent. Just Copilot grounded in this data."* |
| 6 | **Mark Shipped** | Ep 1 + Ep 9 | Toggle `lc_launchstatus` to `Launched` from chat. Confetti. Gen page repaints. *"And this is what shipped looks like."* |

**Bookend:** cut back to the Ep 1 cold-open spreadsheet chaos shot for 2 sec, then back to the all-green dashboard. Caption: *"From this — to this. Twelve episodes."*

## Part 2 — Your Turn (~30 sec)

The CTA. Six shots, sped-up where noted.

1. Terminal: `git clone https://github.com/<owner>/launch-control` (~5 sec)
2. `cd launch-control && cat .env.example` — the placeholders are visible (~5 sec)
3. `cp .env.example .env` + an editor flash showing one URL pasted in (~5 sec)
4. `python episodes/ep-12-full-orchestra/orchestra/spin_up_launch.py "My First Launch" --apply` (~8 sec, sped up to ~3 on screen)
5. Output: a new launch row with 5 starter milestones in the viewer's env (~2 sec)
6. CTA card: *"Star it. Fork it. Ship it."* + repo URL + LinkedIn handle (~5 sec)

`spin_up_launch.py` benchmarked: ~7 mutations, finishes well under 5 sec on a normal connection. If it ever runs slow on camera, pre-create the launch row off-camera and let the script just refresh — no demo-day surprises.

## Q4 Holiday Feature teaser (between Part 1 and Part 2)

Bridges the two parts in ~5 sec. From chat: *"Start a new launch called Q4 Holiday Feature."* The agent calls `spin_up_launch.py "Q4 Holiday Feature" --apply`. New launch row appears in the gen page within seconds. *"…and the next one starts."*

This is the same script Part 2 uses, just pointed at a name James cares about instead of the viewer's "My First Launch." Two birds, one script.

## Pre-record gate

```bash
python episodes/ep-12-full-orchestra/preflight.py
```

Twelve checks. **All green at time of writing:**

- ✅ All 3 orchestra scripts run `--dry-run` cleanly
- ✅ `lc_CalculateLaunchReadiness` custom action present, unbound
- ✅ Q3 Widget Launch exists
- ✅ Capacity / BAP admin API reachable (Ep 11 carryover; capacity may flash in montage)
- ✅ `Q4 Holiday Feature` launch does **not** yet exist (teaser must create it live)
- ✅ OSS readiness files at root: `LICENSE`, `README.md`, `CHANGELOG.md`, `.env.example`, `.gitignore`

## Open-source readiness checklist

The repo flips public when Ep 12 drops. Audit before that moment:

- [x] `LICENSE` (MIT) at root
- [x] `README.md` at root
- [x] `CHANGELOG.md` at root
- [x] `.env.example` at root
- [x] `.gitignore` at root
- [ ] `SECURITY.md` — even a 5-line "report privately to X" suffices (Microsoft OSS template)
- [ ] `CODE_OF_CONDUCT.md` — Microsoft OSS standard template
- [ ] `CONTRIBUTING.md` — confirm contribution flow makes sense for an "example repo"
- [ ] `.github/ISSUE_TEMPLATE/` — `bug.yml`, `question.yml`, `episode-suggestion.yml`
- [ ] **Sensitive-data sweep** — `git grep` for tenant ID, env GUIDs, org URL, internal URLs. Zero hits.
- [ ] **README links** — top-level README links to `docs/episodes/` index + LinkedIn series URL
- [ ] **CHANGELOG entry per episode** — Eps 1–12 each have a tagged entry
- [ ] **Episode tags** — `git tag ep-1` … `ep-12` for each episode commit, pushed to origin
- [ ] **Repo description + topics** on GitHub: short tagline, topics like `dataverse`, `power-platform`, `copilot`, `mcp`, `agents`, `dynamics-365`

## Files in this episode

| Path | Role |
|---|---|
| `episodes/ep-12-full-orchestra/README.md` | This document |
| `episodes/ep-12-full-orchestra/preflight.py` | 12-check preflight harness |
| `episodes/ep-12-full-orchestra/orchestra/_common.py` | Shared `DV` client + status-code enums |
| `episodes/ep-12-full-orchestra/orchestra/setup_launch_week.py` | Forces "perfect launch week" state |
| `episodes/ep-12-full-orchestra/orchestra/teardown_launch_week.py` | Restores "messy mid-launch" for re-rehearsal |
| `episodes/ep-12-full-orchestra/orchestra/spin_up_launch.py` | Creates a new launch (teaser + Your Turn) |

No new tables, columns, plugins, actions, or agents. Ep 12 is pure orchestration of what's already shipped.

## Follow-ups (not blockers for the doc; blockers for going public)

- [ ] Add `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/*.yml`
- [ ] Run sensitive-data sweep (env GUIDs, tenant ID, internal URLs)
- [ ] Tag commits `ep-1` through `ep-12`; push tags
- [ ] Write LinkedIn copy for Ep 12 + the pinned-post version that lives at the top of James's profile through the campaign window
- [ ] Schedule the recording day (Part 1 + Part 2 + teaser in a single half-day session)

## Cross-references

- **Every prior episode.** The whole point.
- **Ep 1 cold open** — the bookend cut.
- **Ep 9 dashboard** — the re-establishing shot for surface #1 of the montage.
- **Ep 11** — the capacity beat may make a cameo if a frame opens up; otherwise omitted to keep Ep 12 focused on launch state, not env state.
