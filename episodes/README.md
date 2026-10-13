# Episodes

The "Launch Control" LinkedIn series: building one project end-to-end, told as a multi-series story. Each folder is self-contained: the episode README is the spec, with a preflight harness and supporting scripts where applicable. Numbering is flat (`ep-NN`); the **seasons** below are narrative groupings, not separate folders.

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
| [7](ep-07-scout-autopilot/) | Microsoft Scout 🟡 | The Dataverse MCP face-lift (16 tools, semantic `search_data` over records and attached files) driven by an always-on Scout Autopilot agent on a schedule |
| [8](ep-08-security/) | Roles & Reach | Security for a headless world: row-level roles **and** column-level data masking, authored from any coding agent (now Cursor) |

### Season 2: Dataverse, Business Apps, and Work IQ

The thesis: Dataverse is not an island. Episode 12 starts with environment enablement, app selection, and a declarative agent in Microsoft 365 Copilot. Episodes 13-16 explore Cowork, Copilot Studio, Work IQ API and developer tools, and external agents. The Studio build belongs to Episode 14, not a second build inside Episode 12. Episode 17 returns to Dataverse security with filter-based security in Public Preview. The former Web IQ, Foundry IQ, Convergence, Agentic Administration, and Full Orchestra beats are preserved as deferred drafts in their episode folders.

| # | Episode | Hero capability |
|---|---|---|
| [9](ep-09-dataverse-fno/) | Dataverse + F&O | CRM and ERP on one platform; the launch record gains budget and supply signal |
| [10](ep-10-dataverse-fabriciq/) | Dataverse + Fabric IQ | Autonomous agent reasoning over the semantic baseline; is this launch a statistical outlier? |
| [11](ep-11-agent-quality-gate/) | Agent Quality Gate | A local Agent 365 worker with its own governed identity runs the launch approval quality gate |
| [12](ep-12-copilot-chat-agent-builder/) | Business Apps in Work IQ: Enablement + Declarative Agent | Enable the environment, select the app, and extend Microsoft 365 Copilot |
| [13](ep-13-cowork/) | Business Apps in Work IQ: Cowork | Explore business context and approval boundaries in Cowork |
| [14](ep-14-copilot-studio/) | Business Apps in Work IQ: Copilot Studio | Build and verify a governed assistant experience |
| [15](ep-15-workiq-api-devtools/) | Business Apps in Work IQ: Work IQ API + Developer Tools | Verify developer access and evaluate agent behavior |
| [16](ep-16-external-agents/) | Business Apps in Work IQ: External Agents | Evaluate a source-grounded route for external agents |

### Season 3: Dataverse Security

| # | Episode | Hero capability |
|---|---|---|
| [17](ep-17-filter-based-security/) | Filter-based Security in Dataverse (Public Preview) | Evaluate attribute-based row access with a scoped, testable filter |

### Deferred storylines

The earlier Web IQ, Foundry IQ, convergence, administration, and finale storylines are postponed, not removed. Their README drafts and supporting assets remain in the original folders:

- [Web IQ draft](ep-12-copilot-chat-agent-builder/DEFERRED-DRAFT.md), with its existing plan, instructions, client, and demo code.
- [Foundry IQ draft](ep-13-cowork/DEFERRED-DRAFT.md).
- [Convergence draft](ep-14-copilot-studio/DEFERRED-DRAFT.md).
- [Agentic Administration draft](ep-15-workiq-api-devtools/DEFERRED-DRAFT.md), with capacity, audit, cleanup, and blast-radius assets.
- [Full Orchestra + Your Turn draft](ep-16-external-agents/DEFERRED-DRAFT.md), with its preflight and orchestra assets.

> **Archived Season 1 agent builds.** The original declarative agent, autonomous Sentinel, code-first Python agent, and generative dashboard moved to [`archive/`](archive/). Their source code remains in [`../agents/`](../agents/) and [`../apps/`](../apps/). The old Ep 12-16 narrative connections are deferred with their episode drafts and are not asserted as part of the new Work IQ arc.

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
- `apps/launch-command-center/`: the generative Power Apps page (folds into the Ep 14 convergence)
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
