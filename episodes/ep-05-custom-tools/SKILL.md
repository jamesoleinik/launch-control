---
name: ep-05-custom-tools
description: Follow Episode 5 of the Launch Control series end-to-end — produce a .NET Custom API plugin, a Power Fx Function twin, a REST custom connector, a remote MCP custom connector, and a Power Automate test-harness flow, all programmatically against a Dataverse environment. Use when the user asks to "do Episode 5", "build the custom tools episode", "make the readiness Custom API and Fx twin", "register a REST/MCP custom connector programmatically", or "deploy the Ep 5 test harness flow".
---

# Skill: Episode 5 — Custom Tools (Prompt-driven)

This skill encodes Episode 5 of the Launch Control series as a sequence of
GitHub Copilot CLI prompts. **The Python scripts and C# plugin in the repo
are the *output* of these prompts, not the input.** Re-running the prompts
against a clean repo should regenerate equivalent artifacts.

The episode produces five artifacts that together demonstrate every way to
extend Dataverse with an agent-callable tool:

| # | Artifact | Surface |
|---|---|---|
| Part 1 | `lc_CalculateLaunchReadiness` Custom API + .NET sandbox plugin | Internal logic, transactional |
| Part 2 | `lc_CalculateLaunchReadinessFx` Power Fx Function (twin contract, posts to Teams) | Low-code + first-party connectors |
| Part 3a | `Launch Control — GitHub Releases` REST custom connector | Wrap any HTTPS REST endpoint |
| Part 3b | `learn-mcp` + `github-mcp` remote MCP custom connectors | Wrap any remote MCP server |
| Part 4 | `LC · Custom Tools Test Harness` Power Automate flow | Single-screen verification |

---

## Hard rules

1. **Confirm the target environment first.** Show the user the Dataverse URL
   from `.env` (`DATAVERSE_URL`) and ask them to confirm. Do not proceed
   until they say yes. This skill makes irreversible changes (registers a
   plugin assembly, creates Custom APIs, registers custom connectors,
   creates a flow in the solution).
2. **Python only**, per the `dv-overview` skill. No Node, no PowerShell
   beyond what `dv-connect` produced.
3. **Solution-first.** Every artifact must land in the `LaunchControl`
   solution with publisher prefix `lc`. Confirm both at the start.
4. **One Part at a time.** Run the prompt for Part N, verify, then move to
   N+1. Don't batch — the agent needs to read each output before the next
   prompt.
5. **Idempotent re-runs.** Every Python script the agent produces should
   check whether the artifact already exists and update in place rather
   than failing.

---

## Pre-flight (before any Part)

Run these checks once at the start of the episode. If any fails, stop and
remediate before running any Part prompt.

```bash
ls .env scripts/auth.py                                  # workspace initialised (else: invoke dv-connect)
pac org who                                              # active PAC profile matches target env
az account show                                          # az logged in (PAPI calls in Part 3)
python -c "import requests, msal, azure.identity"        # script deps available
```

The target env must have:

- The `lc_launch` and `lc_milestone` tables from Episodes 1–4 (containing at
  least one launch named `Q3 Widget Launch` with several milestones).
- For Part 2 only: the "Power Platform Low Code Plug-ins" app installed by
  a tenant admin (creates the `msdyn_lowcodeplugin` table). If absent, Part
  2 will gracefully fail — note it on screen and continue with Parts 3–4.

---

## Part 1 — .NET Custom API + plugin

### Goal

A Custom API named `lc_CalculateLaunchReadiness` backed by a sandboxed .NET
plugin that scores a launch by averaging weighted milestone statuses, with
verdict precedence (any `Blocked` → `NO-GO`).

### Prompt to GitHub Copilot CLI

> *Generate a .NET Framework 4.6.2 Dataverse sandbox plugin called
> `CalculateLaunchReadinessPlugin` in `plugins/CalculateLaunchReadiness/`.
> It should back a Custom API named `lc_CalculateLaunchReadiness` with one
> input parameter `lc_LaunchName` (string) and three output properties:
> `lc_ReadinessScore` (decimal 0–100), `lc_ReadinessSummary` (multi-line
> string narrating each milestone), and `lc_Verdict` (string: GO,
> CONDITIONAL, or NO-GO).*
>
> *Logic: look up the launch by `lc_name`, retrieve every related
> `lc_milestone`, score each by status (Complete=100, InProgress=60,
> AtRisk=50, NotStarted=20, Blocked=0), average them. Verdict rules: any
> Blocked → NO-GO; score ≥ 90 and zero AtRisk → GO; otherwise CONDITIONAL.
> Use `ITracingService` to narrate the per-milestone score into
> `lc_ReadinessSummary`. Sort milestones by `lc_duedate`.*
>
> *Then write `scripts/register_custom_action.py` that uses the Dataverse
> Web API to upload the assembly, register the plugin type, create the
> Custom API + request parameter + response properties, bind PluginTypeId,
> and add the Custom API to the `LaunchControl` solution with
> `AddRequiredComponents=true`. Idempotent (PATCH if it exists). Use
> `scripts/auth.py` for tokens.*

### Verification

```bash
cd plugins/CalculateLaunchReadiness && dotnet build --configuration Release
python scripts/register_custom_action.py
# Then test the action exists:
python -c "
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_CalculateLaunchReadiness',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code, json.dumps(r.json(), indent=2))"
```

Expected: HTTP 200 with `lc_ReadinessScore`, `lc_ReadinessSummary`,
`lc_Verdict` populated.

---

## Part 2 — Power Fx Function twin (posts to Teams)

### Goal

A second Custom API with the same shape (`lc_CalculateLaunchReadinessFx`),
implemented as a Power Fx Function. It calls the Part 1 API for the
baseline, then posts an adaptive card to the launch's Teams channel via
the first-party `MicrosoftTeams` connector.

### Prompt to GitHub Copilot CLI

> *Generate a Power Fx Function under `functions/CalculateLaunchReadinessFx/`
> with three files:*
> - *`function.json` — Custom API contract matching the Part 1 plugin plus
>   an `lc_NotifiedAt` (DateTime) response property.*
> - *`formula.fx` — Power Fx that calls
>   `Environment.lc_CalculateLaunchReadiness({lc_LaunchName: LaunchName})`
>   for the baseline, looks up the launch's Teams team and channel IDs,
>   then invokes `MicrosoftTeams.PostMessageToChannelV3(...)` to post a
>   verdict + summary HTML message. Returns baseline outputs plus
>   `lc_NotifiedAt = Now()` if posted else Blank.*
> - *`README.md` — the exact Copilot for Power Fx prompt used to generate
>   `formula.fx`.*
>
> *Then extend `scripts/register_custom_action.py` (or add a sibling
> script) to register this Function via the `msdyn_lowcodeplugin` table
> and add it to the `LaunchControl` solution. If `msdyn_lowcodeplugin` is
> absent (tenant admin hasn't installed "Power Platform Low Code
> Plug-ins"), print a clear remediation message and skip.*

### Verification

```bash
python scripts/register_lowcode_function.py functions/CalculateLaunchReadinessFx
# Invoke and confirm a Teams message was posted:
python -c "
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_CalculateLaunchReadinessFx',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code, json.dumps(r.json(), indent=2))"
```

Expected: HTTP 200, identical readiness shape, plus `lc_NotifiedAt`
timestamp, plus a card in the launch's Teams channel.

---

## Part 3 — Custom Endpoint Registration (REST + MCP, both programmatic)

### Goal

Two demonstrations of the same primitive:

- **3a** — Wrap the public GitHub Releases API as a REST custom connector.
- **3b** — Wrap a remote MCP server (Microsoft Learn MCP) as an MCP custom
  connector.

Both registered with **one** script, programmatically via the Power Apps
API (PAPI). No `paconn login`, no maker portal clicks.

### Prompt — Part 3a (REST)

> *Generate a Swagger 2.0 connector folder at
> `connectors/github-releases-rest/` for the public GitHub Releases API:*
> - *`apiDefinition.swagger.json` — host `api.github.com`, basePath
>   `/repos`, two operations: `GetLatestRelease` (`GET
>   /{owner}/{repo}/releases/latest`) and `ListReleases` (`GET
>   /{owner}/{repo}/releases`). No security definitions (public API).*
> - *`apiProperties.json` — empty `connectionParameters`, brand colour
>   `#24292F`, capabilities `[]`.*
> - *`settings.example.json` — template for paconn-style settings.*
>
> *Then write `scripts/register_custom_connector.py` that takes a folder
> path on the command line and registers (or updates) a custom connector
> via PAPI directly — no paconn dependency. Use `AzureCliCredential` for
> the bearer token (`https://service.powerapps.com/.default`). POST to
> `/providers/Microsoft.PowerApps/apis?api-version=2016-11-01&$filter=environment eq '<env-id>'`
> for create, PATCH `/providers/Microsoft.PowerApps/apis/<id>?...` for
> update. Body shape: `{"properties": {"openApiDefinition": <swagger>,
> "backendService": {"serviceUrl": "<scheme>://<host><basePath>"},
> "environment": {"name": "<env-id>"}, "description": ..., "displayName":
> ..., "connectionParameters": {}, "capabilities": [],
> "policyTemplateInstances": [], "scriptOperations": []}}`. Cache the
> returned connector id in `<folder>/.connector-id` for re-runs. Add the
> connector to the LaunchControl solution via `pac connector create
> --solution-unique-name LaunchControl` after PAPI registration.*

### Prompt — Part 3b (MCP)

> *Generate two more connector folders using the same script:*
> - *`connectors/learn-mcp/` — wraps `https://learn.microsoft.com/api/mcp`,
>   no auth.*
> - *`connectors/github-mcp/` — wraps `https://api.githubcopilot.com/mcp/`,
>   GitHub PAT via `connectionParameters.api_key` (Authorization header).*
>
> *The Swagger files must include one `POST /api/mcp` (or equivalent) path
> with `operationId: InvokeServer` and the extension
> `"x-ms-agentic-protocol": "mcp-streamable-1.0"` — that's the magic that
> flips the connector framework from REST to MCP.*

### Verification

```bash
python scripts/register_custom_connector.py connectors/github-releases-rest
python scripts/register_custom_connector.py connectors/learn-mcp
python scripts/register_custom_connector.py connectors/github-mcp
# Confirm all three appear in the Dataverse connectors table:
python -c "
from auth import get_token
import requests, os
t = get_token()
r = requests.get(
    os.environ['DATAVERSE_URL'] + \"/api/data/v9.2/connectors?\\$select=name&\\$filter=startswith(name,'Launch Control')\",
    headers={'Authorization': f'Bearer {t}'})
for c in r.json()['value']: print(c['name'])"
```

Expected: three rows (REST + 2x MCP).

---

## Part 4 — Test harness flow (one flow exercises all three)

### Goal

A single Power Automate flow with three `OpenApiConnection` actions — one
per surface from Parts 1, 2, 3a. Manual trigger, returns a Compose of all
three responses. Lives in the `LaunchControl` solution. Deployed
programmatically via the Dataverse `workflows` table (no maker portal).

### Prompt to GitHub Copilot CLI

> *Generate `scripts/create_test_harness_flow.py` that creates a Power
> Automate flow named `LC · Custom Tools Test Harness` via the Dataverse
> `workflows` table (`category=5` modern flow, `type=1` definition). The
> flow should:*
>
> *1. Look up the GitHub Releases custom connector by displayName via PAPI
> (`/providers/Microsoft.PowerApps/apis?$filter=environment eq '...'`).
> If absent, deploy a partial 2-action flow.*
>
> *2. Idempotently ensure two `connectionreference` rows exist in the
> `LaunchControl` solution: `lc_dataverse_harness` (connectorid
> `/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps`)
> and `lc_githubreleases_harness` (pointing at the slug above). Lookup by
> `connectionreferencelogicalname` first; create only if missing.*
>
> *3. Build a logic-apps-style `clientdata` with:*
>    - *`properties.connectionReferences` map — keys are the connection
>      reference logical names; each value is `{"connection":
>      {"connectionReferenceLogicalName": "<name>"}, "api": {"name":
>      "<connector slug>"}, "runtimeSource": "embedded"}`.*
>    - *`properties.definition.triggers.manual` (Request) with a JSON
>      schema input: `LaunchName` (default Q3 Widget Launch), plus
>      `Owner`/`Repo` only if the GH connector is present.*
>    - *`properties.definition.actions` — three `OpenApiConnection`
>      actions: Call_Custom_API_dotnet, Call_Power_Fx_Function (both
>      `PerformUnboundAction` with parameter `actionName` plus the
>      Custom-API input at TOP LEVEL — `lc_LaunchName`, NOT
>      `item/lc_LaunchName`), and Call_GitHub_Releases
>      (`GetLatestRelease`). Each action's `host` block uses
>      `connectionReferenceName: "<map key>"` — not `connectionName`.
>      Do NOT include `"authentication": "@parameters('$authentication')"`
>      anywhere; Power Automate auto-injects this.*
>    - *Compose + Respond actions stitching the three bodies into one
>      JSON.*
>
> *4. POST the flow with header `MSCRM.SolutionUniqueName:
> LaunchControl`. If the flow already exists, DELETE and recreate (PATCH
> cannot change the connection-reference schema in place). Print the
> https://make.powerautomate.com/.../flows/&lt;guid&gt; URL.*

### Verification

```bash
python scripts/create_test_harness_flow.py
# Open the printed URL. Click Edit. There should be a yellow banner
# asking you to bind connections for lc_dataverse_harness and
# lc_githubreleases_harness — pick or create one each. Save. Then
# Test → Manually → Run with LaunchName=Q3 Widget Launch.
```

Expected: the run history shows three green actions, and the Compose
output contains a verdict from the .NET API, a verdict + `lc_NotifiedAt`
from the Fx twin, and a `tag_name` from GitHub Releases.

---

## Order of operations summary

```
[pre-flight checks]
       │
       ▼
[Part 1] dotnet build → register_custom_action.py → smoke-test the Custom API
       │
       ▼
[Part 2] register Fx Function → invoke → confirm Teams card posted
       │
       ▼
[Part 3a] register_custom_connector.py connectors/github-releases-rest
       │
       ▼
[Part 3b] register_custom_connector.py connectors/learn-mcp
          register_custom_connector.py connectors/github-mcp
       │
       ▼
[Part 4] create_test_harness_flow.py → bind connections in portal → Test → Run
```

If a Part fails, stop and remediate before moving on. Each Part's output
is an input to the next (Part 4 needs the GH connector slug from Part 3a;
the .NET API from Part 1 and the Fx twin from Part 2).

---

## Cleanup (optional)

If re-running from scratch:

```bash
# Delete the flow
pac flow delete --flow-id <guid>
# Delete the custom connectors (UI: make.powerapps.com → Custom connectors)
# Delete the Custom APIs (UI: make.powerapps.com → Solutions → LaunchControl)
# Re-run from Part 1
```

---

## Related skills

- `dv-overview` — workspace + auth setup; multi-environment rules.
- `dv-data` — used by the Part 1 verification (record lookup via SDK).
- `dv-metadata` — Custom API definition is metadata; this skill creates it
  via raw Web API because it's a single registration call, but
  `dv-metadata` covers the general pattern.
- `dv-solution` — the `LaunchControl` solution this episode targets; if it
  doesn't exist, create it via that skill first.
