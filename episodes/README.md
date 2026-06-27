# Episodes

The "Launch Control" LinkedIn series: building one project end-to-end, told as a multi-series story. Each folder is self-contained: the episode README is the spec, `preflight.py` is the local test harness, and any episode-specific scripts live alongside. Numbering is flat (`ep-NN`); the **seasons** below are narrative groupings, not separate folders.

> **What is the project?** A launch-management system whose source of truth is **Microsoft Dataverse**, surfaced through agents and native Copilot, and increasingly shown as **better together** with the rest of the Microsoft data and intelligence stack. Built incrementally; every episode adds one capability.

## The arc

### Season 1: Build the Foundation

| # | Episode | Hero capability |
|---|---|---|
| [1](ep-01-data-modeling/) | AI-Powered Data Modeling | Official Dataverse plugins for Copilot & Claude Code → first Dataverse tables |
| [2](ep-02-business-skills/) | Process Modeling | Codifying the playbook as Business Skills with the `@microsoft/dataverse` CLI |
| [3](ep-03-staging-layer/) | Migration & Analysis | Python SDK + pandas; migrate staging → unified and analyze in DataFrames |
| [4](ep-04-extending-and-enforcing/) | Extending & Enforcing the Model | Virtual entities (custom GitHub Issues) **+ a server-side business rule** the coding agent authors; guardrails every future agent must honor |
| [5](ep-05-custom-tools/) | Custom Tools | Custom API + two BYO MCP custom connectors registered with `paconn` |
| [6](ep-06-cowork-plugin/) | Cowork Plugin for Dataverse | Build & publish a Dataverse-aware Cowork (Teams) plugin: Entra registration → Power Platform MCP allowlist → Teams Developer Portal → schema-aware Business Skill |
| [7](ep-07-scout-autopilot/) | Microsoft Scout 🟡 | _(placeholder: blocked on Frontier preview access)_ Hand the Ep-5 substrate to an Autopilot agent and post launch briefings into Teams |
| [8](ep-08-security/) | Roles & Reach | Security for a headless world: row-level roles **and** column-level data masking, authored from any coding agent (now Cursor) |

### Season 2: Dataverse, Better Together

The thesis: Dataverse is not an island. Each episode pairs it with another part of the Microsoft stack: first the operational other half (ERP), then three intelligence layers, and the finale converges them.

| # | Episode | Hero capability |
|---|---|---|
| [9](ep-09-dataverse-fno/) | Dataverse + F&O | CRM and ERP on one platform; the launch record gains budget and supply signal |
| [10](ep-10-dataverse-webiq/) | Dataverse + Web IQ | The outside-in agent (new Copilot Studio builder); internal blockers fused with live web/news/CVE signal |
| [11](ep-11-dataverse-fabriciq/) | Dataverse + Fabric IQ | Autonomous agent reasoning over the semantic baseline; is this launch a statistical outlier? |
| [12](ep-12-dataverse-foundryiq/) | Dataverse + Foundry IQ | Code-first agent grounded in federated, cited knowledge (Foundry IQ over Azure AI Search) |
| [13](ep-13-convergence/) | Convergence | Native M365 Copilot (Dataverse intelligence / Work IQ) **and** the three IQ agents, on one launch |

### Season 3: Operate It

| # | Episode | Hero capability |
|---|---|---|
| [14](ep-14-agentic-admin/) | Agentic Administration | The management plane is agent-driven: capacity, audit, cleanup, blast-radius |
| [15](ep-15-full-orchestra/) | Full Orchestra + Your Turn | Every surface firing on one launch + open-source CTA |

> **Archived Season 1 agent builds.** The original declarative agent, autonomous Sentinel, code-first Python agent, and generative dashboard moved to [`archive/`](archive/). Their capabilities are **absorbed** as the runtimes for Season 2 (Web IQ → new Copilot Studio builder; Fabric IQ → autonomous; Foundry IQ → code-first) and the dashboard folds into the Ep 13 convergence. The code still lives in [`../agents/`](../agents/) and [`../apps/`](../apps/).

## Layout

```
episodes/
  ep-NN-<slug>/
    README.md      ← the episode (script, narrative, file inventory)
    preflight.py   ← local test harness (where applicable)
    *.py           ← episode-specific scripts
  archive/         ← superseded Season 1 agent/dashboard episode docs (absorbed into Season 2)
```

Cross-cutting artifacts live in their canonical homes (not duplicated per-episode):

- `agents/`: coordinator, sentinel, code-first agent, agent-flows (the runtimes Season 2 reuses)
- `business-skills/`: escalation policy, readiness digest, etc.
- `data/knowledge/`: sanitized KB articles for RAG
- `datamodel/`: staging + unified table definitions, mappings, sample data
- `apps/launch-command-center/`: the generative Power Apps page (folds into the Ep 13 convergence)
- `plugins/`: server-side plugins
- `solutions/LaunchControl/`: exported managed solution
- `scripts/auth.py`, `scripts/python/`: shared utilities

## Running a preflight

```bash
# From repo root
python episodes/ep-NN-<slug>/preflight.py
```

Each preflight is read-only by default and exits non-zero if the substrate isn't recording-ready.

## See also

- [`README.md`](../README.md): top-level project README
- [`SECURITY.md`](../SECURITY.md): reporting security issues
- [`CHANGELOG.md`](../CHANGELOG.md): what shipped per episode
- [LinkedIn series](https://www.linkedin.com/in/james-oleinik/): episode posts
