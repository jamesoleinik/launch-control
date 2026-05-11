# Changelog

All notable changes to **Launch Control** are documented here, organized by episode. Each entry corresponds to a git tag (`ep-01` through `ep-12`) — `git checkout ep-NN` to see the repo as it was at the end of that episode.

Episode docs live in [`episodes/ep-NN-<slug>/README.md`](episodes/README.md).

## [ep-12] — Full Orchestra + Your Turn

- Added `episodes/ep-12-full-orchestra/orchestra/` — six-surface demo runner that exercises MCP, SDK, CLI, declarative agent, autonomous agent, and code-first agent in a single timed sequence.
- Added `episodes/ep-12-full-orchestra/preflight.py` to validate every surface is recording-ready.
- Open-source CTA: SECURITY.md, CODE_OF_CONDUCT.md, issue templates, sensitive-data sweep, per-episode folder restructure, episode tags `ep-01..ep-12`.

## [ep-11] — Agentic Administration

- New theme: the **management plane** is agent-driven, not just the data plane.
- Added `episodes/ep-11-agentic-admin/agent_blast_radius.py` — enumerates every Dataverse object an agent identity can read/write in an environment.
- Added `episodes/ep-11-agentic-admin/capacity_report.py` — pulls capacity + storage telemetry programmatically (no portal scraping).
- Locked runtime: Copilot CLI + `dataverse@awesome-copilot v1.0.0` plugin as the canonical admin surface.
- Backdated seed data so the audit/cleanup beats have something real to chew on.

## [ep-10] — Copilot Just Knows (Dataverse Intelligence)

- Episode doc + `prompt-data` preflight covering the three demo prompts + one backup.
- Showcase: native M365 Copilot answers about Launches/Milestones/Tasks with **no agent in the middle** — Dataverse Intelligence is the wiring.

## [ep-09] — The Dashboard

- Shipped `apps/launch-command-center/` — a generative Power Apps page deployed via `pac model genpage upload` (programmatic, no maker-portal click-ops).
- Discovered + documented the `pac model genpage` path; set the page as the default landing for the model-driven app.
- `episodes/ep-09-the-dashboard/{set_genpage_default.py, inspect_sitemap.py, preflight.py}`.

## [ep-08] — The Code-First Agent

- `agents/launch-coordinator-py/` — a Python agent that pulls the **same business skills** the declarative agent uses, proving the skills are runtime-portable.
- Demonstrates: Dataverse as the skill registry; any runtime (Copilot Studio, Claude, custom Python) can consume.

## [ep-07] — Autonomous Agents

- `agents/launch-sentinel/` — event-triggered autonomous agent with an explicit escalation policy.
- Refined the escalation rules in `business-skills/` so both the declarative coordinator and the autonomous sentinel route the same way.

## [ep-06] — The Agent

- `agents/launch-coordinator/` — declarative Copilot Studio agent grounded on Dataverse + the knowledge substrate.
- Added `data/knowledge/` (sanitized KB articles) and the `episodes/ep-06-the-agent/{setup_table.py, upload_knowledge.py}` ingestion path.

## [ep-05] — Custom Tools

- `CalculateLaunchReadiness` Custom API + idempotent registration script.
- Two BYO MCP servers registered as Power Platform custom connectors via `paconn`.
- Plugin assembly + types registered; harness with `--plan` / `--run` modes.

## [ep-04] — Connecting the Dots (Virtual Entities)

- Custom **GitHub Issues** virtual entity provider — issues show up in Dataverse as real records, no replication.
- Wired GitHub Issues VE as a lookup target on `lc_task` so a task can point directly at a live issue.
- Companion VE setup guide.

## [ep-03] — Promoting the Staging Layer

- `scripts/python/promote.py` — pandas-driven staging → unified promotion (Python SDK).
- Visualization scripts (Sankey, ERD, flow) for the episode video.
- Expanded demo dataset to a 46-row Smart Widget Pro narrative.

## [ep-02] — Your Playbook & Ingestion

- Business Skills authored via MCP.
- Mapping-driven CLI ingestion path so the playbook can absorb new sources without code changes.

## [ep-01] — AI-Powered Data Modeling

- **Unified core** — Launches, Milestones, Tasks, TeamMembers, StatusUpdates tables with relationships.
- **Modeling Skill** — `scripts/modeling_skill.py` reads `unified_mapping.yaml` and creates 5 staging tables (TrackerA–E) with typed columns, choice fields, and unique option-set integers per `(table, field)`.
- **Provenance from day one** — `lc_ImportRun` + `lc_SourceFile` tables, plus four provenance columns (`lc_SourceSystem`, `lc_SourceFilename`, `lc_SourceRowHash`, `lc_NeedsManualReview`) appended to every staging table.
- **Prompt column** — `Risk Summary` on `lc_Launch` populated by an LLM from row context.
- **Seed data** — sanitized sample CSVs (`datamodel/samples/*.sample.csv`) + generated seed rows.
- Switched auth to `AzureCliCredential`. Initial repo: README, LICENSE, folder structure.
