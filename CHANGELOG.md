# Changelog

All notable changes to **Launch Control** are documented here, organized by episode. Each entry corresponds to a git tag (`ep-01` through `ep-13`): `git checkout ep-NN` to see the repo as it was at the end of that episode.

> **Tag history note (May 2026).** The series was originally a 13-episode arc, and the immutable git tags `ep-01..ep-13` reflect that numbering. One episode was later inserted: Cowork Plugin at position 7. That shifts the arc to 14 visible episodes. Existing tags are **not** renamed (that would rewrite published history); the table below maps each existing tag to the folder that held it.
>
> | Tag | Original # | Held in folder (now) |
> |---|---|---|
> | `ep-07` | 7 | `episodes/archive/ep-09-the-agent/` |
> | `ep-08` | 8 | `episodes/archive/ep-10-autonomous-agents/` |
> | `ep-09` | 9 | `episodes/archive/ep-11-code-first-agent/` |
> | `ep-10` | 10 | `episodes/archive/ep-12-the-dashboard/` |
> | `ep-11` | 11 | `episodes/ep-14-convergence/` (was `ep-13-copilot-just-knows`) |
> | `ep-12` | 12 | `episodes/ep-15-agentic-admin/` |
> | `ep-13` | 13 | `episodes/ep-16-full-orchestra/` |

> **Better Together restructure (June 2026).** The arc was reframed as a multi-series story (Season 1 Build the Foundation, Season 2 Dataverse Better Together, Season 3 Operate It). Season 2 took over numbers **9 to 13**: ep 9 Dataverse + F&O, ep 10 Dataverse + Web IQ, ep 11 Dataverse + Fabric IQ, ep 12 Dataverse + Foundry IQ, ep 13 Convergence. The original built agent/dashboard episodes (declarative agent, autonomous Sentinel, code-first agent, generative dashboard) were moved to `episodes/archive/` and their capabilities **absorbed** as the runtimes for Season 2. Immutable tags `ep-01..ep-13` are unchanged; only the docs were reorganized. New tags from here use the new numbering.
>
> **Agent identity insertion (August 2026).** Agent Quality Gate was inserted at Episode 11. The then-current Episodes 11 to 15 moved to 12 to 16. Immutable tags and archived episode folders remain unchanged.

Episode docs live in [`episodes/ep-NN-<slug>/README.md`](episodes/README.md).

## [ep-13]: Full Orchestra + Your Turn _(now Episode 16)_

- Added `episodes/ep-16-full-orchestra/orchestra/`: six-surface demo runner that exercises MCP, SDK, CLI, declarative agent, autonomous agent, and code-first agent in a single timed sequence.
- Added `episodes/ep-16-full-orchestra/preflight.py` to validate every surface is recording-ready.
- Open-source CTA: SECURITY.md, CODE_OF_CONDUCT.md, issue templates, sensitive-data sweep, per-episode folder restructure, episode tags `ep-01..ep-13`.

## [ep-12]: Agentic Administration _(now Episode 15)_

- New theme: the **management plane** is agent-driven, not just the data plane.
- Added `episodes/ep-15-agentic-admin/agent_blast_radius.py`: enumerates every Dataverse object an agent identity can read/write in an environment.
- Added `episodes/ep-15-agentic-admin/capacity_report.py`: pulls capacity + storage telemetry programmatically (no portal scraping).
- Locked runtime: Copilot CLI + `dataverse@awesome-copilot v1.0.0` plugin as the canonical admin surface.
- Backdated seed data so the audit/cleanup beats have something real to chew on.

## [ep-11]: Copilot Just Knows (Dataverse Intelligence) _(now Episode 14)_

- Episode doc + `prompt-data` preflight covering the three demo prompts + one backup.
- Showcase: native M365 Copilot answers about Launches/Milestones/Tasks with **no agent in the middle**: Dataverse Intelligence is the wiring.

## [ep-10]: The Dashboard _(now Episode 12)_

- Shipped `apps/launch-command-center/`: a generative Power Apps page deployed via `pac model genpage upload` (programmatic, no maker-portal click-ops).
- Discovered + documented the `pac model genpage` path; set the page as the default landing for the model-driven app.
- `episodes/ep-12-the-dashboard/{set_genpage_default.py, inspect_sitemap.py, preflight.py}`.

## [ep-09]: The Code-First Agent _(now Episode 11)_

- `agents/launch-coordinator-py/`: a Python agent that pulls the **same business skills** the declarative agent uses, proving the skills are runtime-portable.
- Demonstrates: Dataverse as the skill registry; any runtime (Copilot Studio, Claude, custom Python) can consume.

## [ep-08]: Autonomous Agents _(now Episode 10)_

- `agents/launch-sentinel/`: event-triggered autonomous agent with an explicit escalation policy.
- Refined the escalation rules in `business-skills/` so both the declarative coordinator and the autonomous sentinel route the same way.

## [ep-07]: The Agent _(now Episode 9)_

- `agents/launch-coordinator/`: declarative Copilot Studio agent grounded on Dataverse + the knowledge substrate.
- Added `data/knowledge/` (sanitized KB articles) and the `episodes/ep-09-the-agent/{setup_table.py, upload_knowledge.py}` ingestion path.

## [ep-06]: Roles & Reach (Simple RBAC)

- `scripts/python/setup_simple_rbac.py`: four flat roles authored by the coding agent: **lc Member** (User-level CRU), **lc Owner** (BU-level CRU), **lc Viewer** (BU-level Read), **lc Admin** (team-membership management). One owner-team per role.
- Coverage spans Eps 1–5: `lc_*` tables, the SharePoint + GitHub virtual entities (Ep 4), the `CalculateLaunchReadiness` Custom API + the two BYO MCP connectors (Ep 5).
- Doctrine baked into the docstring: layer on top of OOB `Basic User`; Append on both sides for M:N; root-BU roles propagate to children.
- `scripts/python/rbac_validate.py`: end-to-end primitives probe (test BU, owner team, role clone, role bind, `MSCRMCallerID` impersonation, cleanup).

## [ep-05]: Custom Tools

- `CalculateLaunchReadiness` Custom API + idempotent registration script.
- Two BYO MCP servers registered as Power Platform custom connectors via `paconn`.
- Plugin assembly + types registered; harness with `--plan` / `--run` modes.

## [ep-04]: Extending & Enforcing the Model (Virtual Entities + Server-Side Business Rule)

- Custom **GitHub Issues** virtual entity provider: issues show up in Dataverse as real records, no replication.
- Wired GitHub Issues VE as a lookup target on `lc_task` so a task can point directly at a live issue.
- Companion VE setup guide.
- **The enforcement beat:** Claude Code authors a Dataverse **server-side business rule** on `lc_task` (`workflow` row, `category=2`, Entity scope, XAML body): when `lc_blockerreason` is set, the rule flips `lc_taskstatus` to **Blocked** on every write, including writes from the agent layer we build in later episodes. Proof that declarative guardrails and code-first are the same row, two doors.

## [ep-03]: Promoting the Staging Layer

- `scripts/python/promote.py`: pandas-driven staging → unified promotion (Python SDK).
- Visualization scripts (Sankey, ERD, flow) for the episode video.
- Expanded demo dataset to a 46-row Smart Widget Pro narrative.

## [ep-02]: Your Playbook & Ingestion

- Business Skills authored via MCP.
- Mapping-driven CLI ingestion path so the playbook can absorb new sources without code changes.

## [ep-01]: AI-Powered Data Modeling

- **Unified core**: Launches, Milestones, Tasks, TeamMembers, StatusUpdates tables with relationships.
- **Dataverse skill format for coding agents**: same skill format Dataverse uses for runtime Business Skills is also packaged as Microsoft-shipped plugins: `dataverse@awesome-copilot` for GitHub Copilot / Copilot CLI, and the `dataverse` plugin in Claude's official marketplace for Claude Code. Install either and the coding agent knows how to do Dataverse modeling. `scripts/modeling_skill.py` is the agent's output: it reads `unified_mapping.yaml` and creates 5 staging tables (TrackerA–E) with typed columns, choice fields, and stable option-set integers per `(table, field)`.
- **Provenance from day one**: `lc_ImportRun` + `lc_SourceFile` tables, plus four provenance columns (`lc_SourceSystem`, `lc_SourceFilename`, `lc_SourceRowHash`, `lc_NeedsManualReview`) appended to every staging table.
- **Prompt column**: `Risk Summary` on `lc_Launch` populated by an LLM from row context.
- **Seed data**: sanitized sample CSVs (`datamodel/samples/*.sample.csv`) + generated seed rows.
- Switched auth to `AzureCliCredential`. Initial repo: README, LICENSE, folder structure.
