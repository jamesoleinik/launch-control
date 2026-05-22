# Changelog

All notable changes to **Launch Control** are documented here, organized by episode. Each entry corresponds to a git tag (`ep-01` through `ep-13`) — `git checkout ep-NN` to see the repo as it was at the end of that episode.

Episode docs live in [`episodes/ep-NN-<slug>/README.md`](episodes/README.md).

## [ep-13] — Full Orchestra + Your Turn

- Added `episodes/ep-13-full-orchestra/orchestra/` — six-surface demo runner that exercises MCP, SDK, CLI, declarative agent, autonomous agent, and code-first agent in a single timed sequence.
- Added `episodes/ep-13-full-orchestra/preflight.py` to validate every surface is recording-ready.
- Open-source CTA: SECURITY.md, CODE_OF_CONDUCT.md, issue templates, sensitive-data sweep, per-episode folder restructure, episode tags `ep-01..ep-13`.

## [ep-12] — Agentic Administration

- New theme: the **management plane** is agent-driven, not just the data plane.
- Added `episodes/ep-12-agentic-admin/agent_blast_radius.py` — enumerates every Dataverse object an agent identity can read/write in an environment.
- Added `episodes/ep-12-agentic-admin/capacity_report.py` — pulls capacity + storage telemetry programmatically (no portal scraping).
- Locked runtime: Copilot CLI + `dataverse@awesome-copilot v1.0.0` plugin as the canonical admin surface.
- Backdated seed data so the audit/cleanup beats have something real to chew on.

## [ep-11] — Copilot Just Knows (Dataverse Intelligence)

- Episode doc + `prompt-data` preflight covering the three demo prompts + one backup.
- Showcase: native M365 Copilot answers about Launches/Milestones/Tasks with **no agent in the middle** — Dataverse Intelligence is the wiring.

## [ep-10] — The Dashboard

- Shipped `apps/launch-command-center/` — a generative Power Apps page deployed via `pac model genpage upload` (programmatic, no maker-portal click-ops).
- Discovered + documented the `pac model genpage` path; set the page as the default landing for the model-driven app.
- `episodes/ep-10-the-dashboard/{set_genpage_default.py, inspect_sitemap.py, preflight.py}`.

## [ep-09] — The Code-First Agent

- `agents/launch-coordinator-py/` — a Python agent that pulls the **same business skills** the declarative agent uses, proving the skills are runtime-portable.
- Demonstrates: Dataverse as the skill registry; any runtime (Copilot Studio, Claude, custom Python) can consume.

## [ep-08] — Autonomous Agents

- `agents/launch-sentinel/` — event-triggered autonomous agent with an explicit escalation policy.
- Refined the escalation rules in `business-skills/` so both the declarative coordinator and the autonomous sentinel route the same way.

## [ep-07] — The Agent

- `agents/launch-coordinator/` — declarative Copilot Studio agent grounded on Dataverse + the knowledge substrate.
- Added `data/knowledge/` (sanitized KB articles) and the `episodes/ep-07-the-agent/{setup_table.py, upload_knowledge.py}` ingestion path.

## [ep-06] — Roles & Reach (Simple RBAC)

- `scripts/python/setup_simple_rbac.py` — four flat roles authored by the coding agent: **lc Member** (User-level CRU), **lc Owner** (BU-level CRU), **lc Viewer** (BU-level Read), **lc Admin** (team-membership management). One owner-team per role.
- Coverage spans Eps 1–5: `lc_*` tables, the SharePoint + GitHub virtual entities (Ep 4), the `CalculateLaunchReadiness` Custom API + the two BYO MCP connectors (Ep 5).
- Doctrine baked into the docstring: layer on top of OOB `Basic User`; Append on both sides for M:N; root-BU roles propagate to children.
- `scripts/python/rbac_validate.py` — end-to-end primitives probe (test BU, owner team, role clone, role bind, `MSCRMCallerID` impersonation, cleanup).

## [ep-05] — Custom Tools

- `CalculateLaunchReadiness` Custom API + idempotent registration script.
- Two BYO MCP servers registered as Power Platform custom connectors via `paconn`.
- Plugin assembly + types registered; harness with `--plan` / `--run` modes.

## [ep-04] — Connecting the Dots (Virtual Entities + Business Rule)

- Custom **GitHub Issues** virtual entity provider — issues show up in Dataverse as real records, no replication.
- Wired GitHub Issues VE as a lookup target on `lc_task` so a task can point directly at a live issue.
- Companion VE setup guide.
- **Bonus beat:** Claude Code authors a Dataverse business rule on `lc_task` (`workflow` row, `category=9`, XAML body) — when `lc_blockerreason` is set, the rule flips `lc_status` to **Blocked** and shows a notification. Proof that declarative no-code and code-first are the same row, two doors.

## [ep-03] — Promoting the Staging Layer

- `scripts/python/promote.py` — pandas-driven staging → unified promotion (Python SDK).
- Visualization scripts (Sankey, ERD, flow) for the episode video.
- Expanded demo dataset to a 46-row Smart Widget Pro narrative.

## [ep-02] — Your Playbook & Ingestion

- Business Skills authored via MCP.
- Mapping-driven CLI ingestion path so the playbook can absorb new sources without code changes.

## [ep-01] — AI-Powered Data Modeling

- **Unified core** — Launches, Milestones, Tasks, TeamMembers, StatusUpdates tables with relationships.
- **Dataverse skill format for coding agents** — same skill format Dataverse uses for runtime Business Skills is also packaged as Microsoft-shipped plugins: `dataverse@awesome-copilot` for GitHub Copilot / Copilot CLI, and the `dataverse` plugin in Claude's official marketplace for Claude Code. Install either and the coding agent knows how to do Dataverse modeling. `scripts/modeling_skill.py` is the agent's output: it reads `unified_mapping.yaml` and creates 5 staging tables (TrackerA–E) with typed columns, choice fields, and stable option-set integers per `(table, field)`.
- **Provenance from day one** — `lc_ImportRun` + `lc_SourceFile` tables, plus four provenance columns (`lc_SourceSystem`, `lc_SourceFilename`, `lc_SourceRowHash`, `lc_NeedsManualReview`) appended to every staging table.
- **Prompt column** — `Risk Summary` on `lc_Launch` populated by an LLM from row context.
- **Seed data** — sanitized sample CSVs (`datamodel/samples/*.sample.csv`) + generated seed rows.
- Switched auth to `AzureCliCredential`. Initial repo: README, LICENSE, folder structure.
