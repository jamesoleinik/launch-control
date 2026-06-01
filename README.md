# 🚀 Launch Control

**A Product Launch Coordinator built with Microsoft Dataverse — from data model to agents to dashboard.**

This repo is the companion to the **Launch Control** LinkedIn series by [James Oleinik](https://www.linkedin.com/in/james-oleinik/), Product Director for Microsoft Dataverse. Over 15 episodes (3/week for ~5 weeks), we build a complete product launch coordination system from scratch — and open-source every line of code.

## The Problem

Engineering teams are automating code reviews, DRIs, and incident response. But up the stack? Executives still want status. Cross-team projects still mean passing spreadsheets around. **What if we applied the same agentic thinking to project coordination?**

## The Solution: Three Layers

```
┌──────────────────────────────────────────────────────┐
│  LAYER 3: MANAGEMENT & OPERATIONS                    │
│  Power App Dashboard  │  Python SDK/pandas  │  CLI   │
│  Admin Skills (agentic administration at scale)      │
├──────────────────────────────────────────────────────┤
│  LAYER 2: INTELLIGENCE                               │
│  Business Skills  │  Agents (Copilot Studio, Claude) │
│  Agent Flows  │  Custom Actions  │  BYO MCP Servers  │
│  MCP Server (universal) │ CLI │ SDK (coding agents)  │
├──────────────────────────────────────────────────────┤
│  LAYER 1: BUSINESS SYSTEM OF RECORD                  │
│  Dataverse Tables & Relationships │ Prompt Columns   │
│  Virtual Entities (real-time, no data replication)   │
│  Dataverse Intelligence (native M365 Copilot)        │
└──────────────────────────────────────────────────────┘
```

## Episode Guide

Full series index with links to each episode's README, preflight, and scripts: **[`episodes/README.md`](episodes/README.md)**.

| # | Episode | Hero capability |
|---|---------|------------------|
| [1](episodes/ep-01-data-modeling/)        | AI-Powered Data Modeling      | Official Dataverse plugins for Copilot & Claude Code → first Dataverse tables |
| [2](episodes/ep-02-business-skills/)      | Your Playbook & Ingestion     | Business skills + mapping-driven CLI ingestion |
| [3](episodes/ep-03-staging-layer/)        | Promoting the Staging Layer   | Python + pandas; staging → unified |
| [4](episodes/ep-04-extending-and-enforcing/) | Extending & Enforcing the Model | Virtual entities (custom GitHub Issues) **+ a server-side business rule** the coding agent authors — guardrails every future agent must honor |
| [5](episodes/ep-05-custom-tools/)         | Custom Tools                  | Custom API + two BYO MCP custom connectors registered with `paconn` |
| [6](episodes/ep-06-rbac/)                 | Roles & Reach                 | Four flat roles (Member / Owner / Viewer / Admin) over Eps 1–5 data + tools — same query, four lenses |
| [7](episodes/ep-08-the-agent/)            | The Agent                     | Declarative Launch Coordinator + knowledge substrate |
| [8](episodes/ep-09-autonomous-agents/)    | Autonomous Agents             | Launch Sentinel — event-triggered autonomous agent |
| [9](episodes/ep-10-code-first-agent/)     | The Code-First Agent          | Same skills, different runtime — Python agent that pulls skills from Dataverse |
| [10](episodes/ep-11-the-dashboard/)        | The Dashboard                 | Generative Power Apps page deployed via `pac model genpage upload` |
| [11](episodes/ep-12-copilot-just-knows/)  | Copilot Just Knows            | Native Copilot intelligence over Dataverse — no agent needed |
| [12](episodes/ep-14-agentic-admin/)       | Agentic Administration        | The management plane is agent-driven — capacity, audit, cleanup, blast-radius |
| [13](episodes/ep-15-full-orchestra/)      | Full Orchestra + Your Turn    | Six surfaces in 60 seconds + open-source CTA |

Each episode is also tagged in git: `git checkout ep-09` to see the repo as it was at that episode's ship.

## Quick Start

### Prerequisites
- Python 3.10+ with `pip install PowerPlatform-Dataverse-Client`
- Node.js 18+ with `npm install -g @microsoft/dataverse`
- [PAC CLI](https://learn.microsoft.com/en-us/power-platform/developer/cli/introduction)
- A Microsoft Dataverse environment with System Administrator role

### Setup
```bash
git clone https://github.com/jamesoleinik/launch-control.git
cd launch-control
cp .env.example .env
# Edit .env with your Dataverse environment URL and credentials
pip install -r scripts/python/requirements.txt
```

To verify any episode is set up correctly, run its preflight:

```bash
python episodes/ep-11-the-dashboard/preflight.py
```

## Repo Structure

```
launch-control/
├── episodes/                  # 13 per-episode folders (READMEs + preflights + scripts)
├── datamodel/                 # Table definitions, mappings, sample data
├── solutions/LaunchControl/   # Exported managed solution
├── business-skills/           # Launch readiness, escalation, status rules
├── data/knowledge/            # Sanitized KB articles for RAG
├── agents/
│   ├── launch-coordinator/    # Declarative Copilot Studio agent (Ep 8)
│   ├── launch-sentinel/       # Autonomous agent (Ep 9)
│   ├── launch-coordinator-py/ # Code-first agent (Ep 10)
│   └── agent-flows/           # Agent flow configurations
├── apps/launch-command-center/# Generative Power Apps page (Ep 11)
├── plugins/                   # Custom Dataverse plugins & actions
└── scripts/                   # auth.py + shared Python utilities
```

## Key Themes

### Skills All the Way Down
- **Build skills** — AI creates your data model, plugins, and agents
- **Process skills** — Business knowledge agents follow at runtime (portable across agent platforms)
- **Operate skills** — Scripted automation and agentic administration at scale

### Master the Process in Dataverse
The launch spans GitHub, SharePoint, email — but mastering the business process state in Dataverse (think dynamic programming) means every agent, app, and Copilot reads the same truth.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to fork and adapt this for your own scenario — customer onboarding, release management, incident response, or anything else.

## See also

- [`CHANGELOG.md`](CHANGELOG.md) — what shipped in each episode (with git tags)
- [`SECURITY.md`](SECURITY.md) — how to report a security issue
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Microsoft Open Source Code of Conduct

## License

[MIT](LICENSE)

---

Built by [James Oleinik](https://www.linkedin.com/in/james-oleinik/) | Product Director, Microsoft Dataverse
