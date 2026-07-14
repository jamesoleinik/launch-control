---
name: copilot-studio-agent-authoring
description: Programmatically create and upload a Copilot Studio "cliagent" declarative agent (bot + MCP tool components) into a Dataverse environment via the Web API, minting bot-scoped connection references against the connector's authorized connection so nothing is hardcoded. Use when a Launch Control episode needs to stand up a Copilot Studio agent from code (for example Episode 9 Act 4) instead of clicking through the maker portal, or to re-create/version an agent that has been reverse-engineered from a live bot record.
---

# Copilot Studio agent authoring

Stand up a Copilot Studio declarative agent (the "new agent" `cliagent` experience) in
Dataverse from code, so an episode can create its agent with a single command instead of
hand-building it in the maker portal. This is the model behind the Episode 9 vendor
invoice reconciliation agent.

## What a Copilot Studio agent is, as Dataverse records

A `cliagent` agent is three Dataverse rows:

1. **`bots`** (one row). Template `cliagent-1.0.0`. Its `configuration` column holds a JSON
   document describing the agent: the language model series, the recognizer, and the
   instructions. Shape:

   ```jsonc
   {
     "$kind": "BotConfiguration",
     "channels": [{ "id": "MsTeams", "channelId": "MsTeams" }],
     "recognizer": { "$kind": "CLICopilotRecognizer" },
     "agentSettings": {
       "$kind": "AgentSettings",
       "model": { "$kind": "ModelConfig", "series": "Opus48" },
       "instructions": {
         "$kind": "Instructions",
         "segments": [{ "$kind": "StaticSegment", "value": "<the agent instructions>" }]
       },
       "web": { "$kind": "WebSettings", "enableWebSearch": false }
     },
     "publishOnImport": true
   }
   ```

2. **`botcomponents`** (one row per tool). `componenttype = 9`, linked to the bot with
   `parentbotid@odata.bind`. The `data` column is a small YAML block declaring an
   `McpTool` bound to a connector connection reference. Episode 9 attaches two: the
   Dataverse MCP (`shared_commondataserviceforapps`, operation `InvokeMCPPreview`) and the
   Dynamics 365 ERP MCP (`shared_dynamicsax`, operation `InvokeMCP`).

3. **`connectionreferences`** (bot-scoped, minted per agent). A Copilot Studio cliagent
   will not resolve another bot's connection reference: each MCP tool must point at a
   reference whose logical name is scoped to this bot,
   `<botschema>.cr.<connector>.<connectionid>`. So the script does not reuse an existing
   reference's logical name. It reads the live `connectionid` a connector is already
   authorized against (a clean 32-char hex id, ignoring stale ids), then mints a fresh
   bot-scoped reference bound to that same live connection and points the tool at it.

   **The per-agent tool connection is a one-time manual step, by design.** The actual
   connections live in the Power Platform connections (APIM) plane, not the Dataverse
   `connections` table, and each holds an OAuth token that cannot be minted or re-bound to
   a new agent headlessly. The script therefore creates the bot, both MCP tools, the
   instructions, the model, and a resolvable bot-scoped reference shell, but the binding
   that the runtime and the agent Preview validate is only established when you connect the
   tool interactively. **After `--apply`, open the agent in Copilot Studio Build, open each
   of the two MCP tools, click Connect (choose the existing Dataverse / D365 F&O
   connection), then Publish.** An agent preview that reports "missing connection
   reference(s)" / "InvalidContent" means the two tools have not been connected in the
   canvas yet; connecting them once is the fix (re-running the script does NOT resolve
   this, since the OAuth binding is not a Dataverse row the script can write).

## Prerequisites

- The target environment is a unified/F&O-enabled Dataverse environment with the two MCP
  connectors authorized at least once (so a `connectionreference` with a live
  `connectionid` exists for both `shared_commondataserviceforapps` and `shared_dynamicsax`).
- `scripts/auth.py` resolves the target env from `.env` / a per-episode `.env`
  (`--env ep-09-dataverse-fno`). Never hardcode the environment URL, tenant, or org id.
- Set `$env:PYTHONIOENCODING="utf-8"` before running Python on Windows.
- Instruction text must contain no em-dash (U+2014); the script refuses to author an agent
  whose instructions include one.

## Usage

The instruction shell lives in the episode repo (for Episode 9,
`episodes/ep-09-dataverse-fno/assistive-agent-instructions.md`, section
"Instructions (paste verbatim)"). Dry-run first:

```powershell
$env:PYTHONIOENCODING="utf-8"
python skills/copilot-studio-agent-authoring/create_agent.py `
  --name "Launch Control Reconciliation" `
  --instructions-file episodes/ep-09-dataverse-fno/assistive-agent-instructions.md `
  --env ep-09-dataverse-fno `
  --dry-run
```

The dry-run prints the target environment, the generated schema name, the instruction
length, and the two bot-scoped connection references it will mint. When that looks right,
create the records:

```powershell
python skills/copilot-studio-agent-authoring/create_agent.py `
  --name "Launch Control Reconciliation" `
  --instructions-file episodes/ep-09-dataverse-fno/assistive-agent-instructions.md `
  --env ep-09-dataverse-fno `
  --apply
```

Then open the agent in Copilot Studio and click **Publish** once to make it live. Creating
the records is fully scripted; publish is the single remaining click (there is no stable
headless publish action for a bot over the Web API).

### Options

| Flag | Purpose |
| --- | --- |
| `--name` | Agent display name (required). |
| `--instructions-file` | File with the instruction shell (required). If it has a `## Instructions (paste verbatim)` section, only that section's body is used. |
| `--env` | Episode env selector passed to `scripts/auth` (e.g. `ep-09-dataverse-fno`). |
| `--schemaname` | Full schema name. Default `<prefix>_<slug>_<random5>`. |
| `--prefix` | Publisher customization prefix. Default `PUBLISHER_PREFIX` from `.env`, else `cr555`. |
| `--dataverse-connref` / `--erp-connref` | Pin the underlying connection to bind (a connection id, or the logical name of an existing reference that carries it) instead of auto-picking the live one. The bot-scoped reference is still minted fresh. |
| `--apply` | Actually create the records. Omit (or pass `--dry-run`) to preview only. |

## Files

- `create_agent.py` : the authoring script (dry-run by default).
- `references/agent-configuration.template.json` : the `bots.configuration` template,
  captured from a live `cliagent` bot with the instruction segment left as a placeholder
  the script fills. Update this file if the Copilot Studio configuration schema changes.

## Notes and safety

- Dry-run first; `--apply` is the only thing that writes. Confirm the environment URL in the
  dry-run output before applying.
- The script mints bot-scoped connection references bound to the connector's already
  authorized connection; it does not create connections or store any secret.
- Re-running creates a new bot (a new random schema name) unless you pin `--schemaname`;
  there is no in-place update, so version by creating a fresh agent and publishing it.
