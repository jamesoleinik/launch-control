# 🚀 Launch Control

**A Product Launch Coordinator built with Microsoft Dataverse — from data model to agents to dashboard.**

This repo is the companion to the **Launch Control** LinkedIn series by [James Oleinik](https://www.linkedin.com/in/james-oleinik/), Product Director for Microsoft Dataverse. Over 12 episodes (3/week for 4 weeks), we build a complete product launch coordination system from scratch — and open-source every line of code.

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

| Ep | Title | Key Feature | Week |
|----|-------|-------------|------|
| 1 | AI-Powered Data Modeling 🏗️ | Dataverse MCP Server + Prompt Columns | 1 |
| 2 | Your Playbook & Ingestion 📋 | Business Skills + Dataverse CLI | 1 |
| 3 | Connecting the Dots 🔗 | Virtual Entities (OOB + custom) | 1 |
| 4 | Scripting the Ops 🐍 | Python SDK with pandas | 2 |
| 5 | The Copilot Studio Agent 🤖 | Copilot Studio + MCP | 2 |
| 6 | Agent Flows ⚡ | Agent Flows + MCP steps | 2 |
| 7 | The Native Claude Agent 🧠 | Claude Code + Anthropic business skills | 3 |
| 8 | Custom Tools 🔧 | BYO MCP Server + Custom Plugins | 3 |
| 9 | Copilot Just Knows 💡 | Dataverse Intelligence | 3 |
| 10 | The Dashboard 📊 | Power Apps code-first | 4 |
| 11 | Agentic Administration 🛡️ | CLI + DV Admin Skills | 4 |
| 12 | Full Orchestra + Your Turn 🎼 | Everything together + open source | 4 |

## Quick Start

### Prerequisites
- Python 3.10+ with `pip install PowerPlatform-Dataverse-Client`
- Node.js 18+ with `npm install -g @microsoft/dataverse`
- [PAC CLI](https://learn.microsoft.com/en-us/power-platform/developer/cli/introduction)
- A Microsoft Dataverse environment with System Administrator role

### Setup
```bash
git clone https://github.com/james-oleinik/launch-control.git
cd launch-control
cp .env.example .env
# Edit .env with your Dataverse environment URL and credentials
pip install -r scripts/python/requirements.txt
```

## Repo Structure

```
launch-control/
├── datamodel/              # Table definitions, solution, seed data
├── business-skills/        # Launch readiness, escalation, status rules
├── scripts/
│   ├── python/             # pandas-powered status reports, seed data
│   └── cli/                # Terminal workflow scripts
├── agents/
│   ├── launch-coordinator/ # Copilot Studio agent definition
│   ├── agent-flows/        # Agent Flow configurations
│   └── custom-mcp-server/  # BYO MCP server registration
├── plugins/                # Custom Dataverse plugins & actions
├── app/launch-dashboard/   # Power Apps code-first dashboard
└── docs/                   # Architecture, episodes, security checklist
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

## License

[MIT](LICENSE)

---

Built by [James Oleinik](https://www.linkedin.com/in/james-oleinik/) | Product Director, Microsoft Dataverse
