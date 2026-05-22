# Episodes

The "Launch Control" LinkedIn series — thirteen short episodes building one project end-to-end. Each folder is self-contained: the episode README is the spec, `preflight.py` is the local test harness, and any episode-specific scripts live alongside.

> **What is the project?** A launch-management system whose source of truth is **Microsoft Dataverse**, with multiple agents (declarative + autonomous + code-first) coordinating around it, surfaced through a generative Power Apps page. Built incrementally — every episode adds one capability.

## The arc

| # | Episode | Hero capability |
|---|---|---|
| [1](ep-01-data-modeling/) | AI-Powered Data Modeling | Official Dataverse plugins for Copilot & Claude Code → first Dataverse tables |
| [2](ep-02-business-skills/) | Process Modeling | Codifying the playbook as Business Skills with the `@microsoft/dataverse` CLI |
| [3](ep-03-staging-layer/) | Migration & Analysis | Python SDK + pandas — migrate staging → unified and analyze in DataFrames |
| [4](ep-04-connecting-the-dots/) | Connecting the Dots | Virtual entities (SharePoint OOB + custom GitHub Issues) **+ a business rule** the coding agent authors over the unified model |
| [5](ep-05-custom-tools/) | Custom Tools | Custom API + two BYO MCP custom connectors registered with `paconn` |
| [6](ep-06-rbac/) | Roles & Reach | Four flat roles (Member / Owner / Viewer / Admin) over Eps 1–5 data + tools — same query, four lenses |
| [7](ep-07-the-agent/) | The Agent | Declarative Launch Coordinator + knowledge substrate |
| [8](ep-08-autonomous-agents/) | Autonomous Agents | Launch Sentinel — event-triggered autonomous agent |
| [9](ep-09-code-first-agent/) | The Code-First Agent | Same skills, different runtime — Python agent that pulls skills from Dataverse |
| [10](ep-10-the-dashboard/) | The Dashboard | Generative Power Apps page deployed via `pac model genpage upload` |
| [11](ep-11-copilot-just-knows/) | Copilot Just Knows | Native Copilot intelligence over Dataverse — no agent needed |
| [12](ep-12-agentic-admin/) | Agentic Administration | The management plane is agent-driven — capacity, audit, cleanup, blast-radius |
| [13](ep-13-full-orchestra/) | Full Orchestra + Your Turn | Six surfaces in 60 seconds + open-source CTA |

## Layout

```
episodes/
  ep-NN-<slug>/
    README.md      ← the episode (script, narrative, file inventory)
    preflight.py   ← local test harness (where applicable)
    *.py           ← episode-specific scripts
```

Cross-cutting artifacts live in their canonical homes (not duplicated per-episode):

- `agents/` — declarative coordinator, sentinel, code-first agent, agent-flows
- `business-skills/` — escalation policy, readiness digest, etc.
- `data/knowledge/` — sanitized KB articles for RAG
- `datamodel/` — staging + unified table definitions, mappings, sample data
- `apps/launch-command-center/` — the Ep 10 generative page
- `plugins/` — server-side plugins
- `solutions/LaunchControl/` — exported managed solution
- `scripts/auth.py`, `scripts/python/` — shared utilities

## Running a preflight

```bash
# From repo root
python episodes/ep-NN-<slug>/preflight.py
```

Each preflight is read-only by default and exits non-zero if the substrate isn't recording-ready.

## See also

- [`README.md`](../README.md) — top-level project README
- [`SECURITY.md`](../SECURITY.md) — reporting security issues
- [`CHANGELOG.md`](../CHANGELOG.md) — what shipped per episode
- [LinkedIn series](https://www.linkedin.com/in/james-oleinik/) — episode posts
