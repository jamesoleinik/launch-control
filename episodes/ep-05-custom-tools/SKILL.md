---
name: ep-05-custom-tools
description: Follow Episode 5 of the Launch Control series end-to-end — produce a .NET Custom API plugin, a Power Fx Function twin, a REST custom connector, a remote MCP custom connector, and a Power Automate test-harness flow, all programmatically against a Dataverse environment. Use when the user asks to "do Episode 5", "build the custom tools episode", "make the readiness Custom API and Fx twin", "register a REST/MCP custom connector programmatically", or "deploy the Ep 5 test harness flow".
---

# Skill: Episode 5 — Custom Tools (Prompt-driven)

This skill encodes Episode 5 of the Launch Control series as a sequence of
GitHub Copilot CLI prompts. **The Python scripts and C# plugin in the repo
are the *output* of these prompts, not the input.** Re-running the prompts
against a clean repo should regenerate equivalent artifacts.

The episode produces six artifacts that together demonstrate every way to
extend Dataverse with an agent-callable tool — across all **four** ways
to host custom business logic:

| # | Artifact | Hosting model |
|---|---|---|
| Part 1 | `lc_CalculateLaunchReadiness` Custom API + .NET sandbox plugin | **Custom plugin** — .NET in the sandbox |
| Part 2 | `lc_CalculateLaunchReadinessFx` Power Fx Function (twin contract, posts to Teams) | **Custom function** — low-code + first-party connectors |
| Part 3a | `Launch Control — GitHub Releases` REST custom connector | **Custom connector** — wrap any HTTPS REST endpoint |
| Part 3b | `learn-mcp` + `github-mcp` remote MCP custom connectors | **Custom connector** — wrap any remote MCP server |
| Part 4 | `lc_DraftLaunchBriefing` AI Prompt (Custom Action) | **Custom AI function** — non-deterministic LLM call |
| Part 5 | `LC · Custom Tools Test Harness` Power Automate flow | Single-screen verification (all four substrates) |

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

> *Create a Dataverse Custom API called `lc_CalculateLaunchReadiness`*
> *that scores a launch by averaging its milestone statuses and returns*
> *a verdict (GO / CONDITIONAL / NO-GO, with any Blocked milestone*
> *forcing NO-GO). Build it as a .NET sandbox plugin so the per-milestone*
> *reasoning can come back in a tracing-service narrative. Then register*
> *everything programmatically into the LaunchControl solution and smoke*
> *test it against Q3 Widget Launch.*

### Implementation notes (don't put these in the prompt — but the agent needs to honour them)

- **.NET Framework 4.6.2** is the supported sandbox runtime as of May 2026
  (4.8 lands Q4 2026). The csproj needs
  `Microsoft.NETFramework.ReferenceAssemblies.Net462` because the SDK no
  longer ships the targeting pack by default.
- Strong-name the assembly before registration.
- Default rubric (confirm with user before locking in): Complete=100,
  InProgress=60, AtRisk=50, NotStarted=20, Blocked=0. Verdict precedence:
  any Blocked → NO-GO; score ≥ 90 AND zero AtRisk → GO; else CONDITIONAL.
- Custom API shape: input `lc_LaunchName` (string); outputs
  `lc_ReadinessScore` (decimal 0–100), `lc_ReadinessSummary` (multi-line
  string), `lc_Verdict` (string).
- Registration script must be idempotent: PATCH the assembly bytes if the
  row exists; one `AddSolutionComponent` call with
  `AddRequiredComponents=true` pulls the assembly, plugin type, request
  parameter, and response properties into the LaunchControl solution
  together. Use `scripts/auth.py` for tokens.

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

> *Build a Power Fx twin of that Custom API — same shape, suffixed `Fx` —*
> *as a Function in Dataverse. After scoring it should also post the*
> *verdict to the launch's Teams channel and return the timestamp it*
> *posted. Register it into the LaunchControl solution. If the low-code*
> *plug-ins app isn't installed in this env, fail gracefully with the*
> *remediation steps — don't error out.*

### Implementation notes

- Folder layout: `functions/CalculateLaunchReadinessFx/{formula.fx,
  function.json, README.md}`. The README captures the exact Copilot for
  Power Fx prompt used to write `formula.fx` so the next dev can
  regenerate it.
- Contract mirrors Part 1 plus one extra response prop: `lc_NotifiedAt`
  (DateTime).
- `formula.fx` calls `Environment.lc_CalculateLaunchReadiness(...)` for
  the baseline, looks up `lc_TeamsTeamId` + `lc_TeamsChannelId` from the
  launch row, then calls `MicrosoftTeams.PostMessageToChannelV3(...)`.
  Returns baseline + `lc_NotifiedAt = If(posted, Now(), Blank())`.
- Registration uses the `msdyn_lowcodeplugin` table. If that table is
  absent the registration script should print the install path (Power
  Platform admin center → Environments → _(env)_ → Resources → Dynamics
  365 apps → "Power Platform Low Code Plug-ins") and exit 0, not
  failure.
- A `shared_teams` connection reference must already exist in the env.

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

> *Wrap the public GitHub Releases API as a Power Platform custom*
> *connector and register it into the LaunchControl solution*
> *programmatically — no `paconn login`, no maker-portal clicks. I want*
> *the registration script to be re-runnable against any swagger folder*
> *in `connectors/`, since we'll do MCP servers next.*

### Prompt — Part 3b (MCP)

> *Now do the same for two remote MCP servers: Microsoft Learn MCP*
> *(`learn.microsoft.com/api/mcp`, no auth) and the GitHub MCP server*
> *(`api.githubcopilot.com/mcp/`, GitHub PAT). Re-use the registration*
> *script from 3a — the only thing that should differ between REST and*
> *MCP is the swagger.*

### Implementation notes (REST + MCP)

- Folder layout per connector: `connectors/<name>/{apiDefinition.swagger.json,
  apiProperties.json, settings.example.json}`. `.connector-id` is
  gitignored — the registration script writes the returned slug there for
  re-runs.
- **The registration script talks PAPI directly — no paconn dependency.**
  Use `AzureCliCredential` against `https://service.powerapps.com/.default`.
  - **Create:** `POST /providers/Microsoft.PowerApps/apis?api-version=2016-11-01&$filter=environment eq '<env-id>'`
  - **Update:** `PATCH /providers/Microsoft.PowerApps/apis/<id>?api-version=2016-11-01&$filter=environment eq '<env-id>'`
  - Body: `{"properties": {"openApiDefinition": <swagger>, "backendService":
    {"serviceUrl": "<scheme>://<host><basePath>"}, "environment": {"name":
    "<env-id>"}, "description": ..., "displayName": ...,
    "connectionParameters": {}, "capabilities": [],
    "policyTemplateInstances": [], "scriptOperations": []}}`
  - **Gotcha 1:** property name is `openApiDefinition`, NOT `swagger`.
    Wrong key → `ApiDefinitionUrlInvalid` 400.
  - **Gotcha 2:** create is POST (not PUT). PUT → 405.
  - Header `x-ms-origin: paconn-cli` is what paconn sets — include it.
- After PAPI registration, add the connector to the LaunchControl
  solution via `pac connector create --solution-unique-name LaunchControl`
  (or the `connector` Dataverse table directly).
- **The "MCP magic":** the swagger has one `POST /api/mcp` path with
  `operationId: InvokeServer` and the extension
  `"x-ms-agentic-protocol": "mcp-streamable-1.0"`. That single key flips
  the connector framework from REST to MCP. Everything else is identical.
- GitHub MCP auth: declare `connectionParameters.api_key` (header type,
  `Authorization` header, prefix `Bearer ` if you want raw PATs — the
  GitHub MCP server also accepts `token <PAT>`).

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

## Part 4 — Custom AI Function (AI Prompt → Custom Action)

### Goal

A Dataverse **AI Prompt** named `lc_DraftLaunchBriefing` that takes a
launch name, pulls its milestone narrative, and returns a 3-sentence
GO / HOLD / NO-GO recommendation written in the sponsor's voice. Once
registered, AI Prompts in Dataverse are automatically invocable as
unbound Custom Actions — so the agent calls it the same shape as the
.NET and Fx ones. **Non-deterministic substrate, identical contract.**

### Prompt to GitHub Copilot CLI

> *Create a Dataverse AI Prompt called `lc_DraftLaunchBriefing` that*
> *takes a launch name, pulls the milestone narrative for that launch,*
> *and drafts a three-sentence GO / HOLD / NO-GO recommendation in the*
> *voice of the launch sponsor. Wrap it as an unbound Custom Action,*
> *register it into the LaunchControl solution, and smoke test it*
> *against Q3 Widget Launch.*

### Implementation notes (easy-to-miss bits)

- AI Prompts are records in the AI hub. The primary table is
  `msdyn_aiprompt`; the runnable Custom Action surface that wraps it
  is what the agent calls. Look it up rather than hard-coding the table
  schema — Microsoft has been iterating on the column names.
- Source-control the prompt definition under `prompts/DraftLaunchBriefing/`:
  - `prompt.json` — inputs, system + user message templates, target
    model, expected output shape
  - `README.md` — iteration notes and example outputs
- `scripts/register_ai_prompt.py` should be idempotent: look up the
  prompt by `name`, update if it exists, else create. Set
  `MSCRM.SolutionUniqueName: LaunchControl` so it lands in the solution.
- The action name exposed to agents and flows is `lc_DraftLaunchBriefing`
  (or the action name the prompt registration produces — verify and
  document in the script's output). Smoke-test by POSTing to
  `/api/data/v9.2/<actionname>` with `{"lc_LaunchName": "Q3 Widget Launch"}`.
- Calling it twice in a row will return **different** wording — that's
  expected; that's the whole point of this Part. The episode contrasts
  this with the deterministic Parts 1–3.
- Bind a model in the environment that the calling identity is licensed
  for. If the call returns "no AI Builder capacity" or similar, fall
  back to a different model in the prompt definition.

### Verification

```bash
python scripts/register_ai_prompt.py prompts/DraftLaunchBriefing

# Same call shape as the .NET and Fx APIs — agent doesn't know it's an LLM
python -c "
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_DraftLaunchBriefing',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code); print(json.dumps(r.json(), indent=2))
"
```

Expected: HTTP 200 and three sentences of plain English. Run it twice —
the wording changes. That contrast is the recorded beat.

---

## Part 5 — Test harness flow (one flow exercises all four)

### Goal

A single Power Automate flow with four `OpenApiConnection` actions — one
per substrate from Parts 1, 2, 3a, and 4. Manual trigger, returns a
Compose of all four responses. Lives in the `LaunchControl` solution.
Deployed programmatically via the Dataverse `workflows` table (no maker
portal).

### Prompt to GitHub Copilot CLI

> *Build a Power Automate test-harness flow that exercises all four*
> *tools in one run — the .NET Custom API, the Fx twin, the GitHub*
> *Releases connector, and the AI Prompt — and returns their responses*
> *side-by-side. Manual trigger, takes a `LaunchName` input, deploys*
> *programmatically into the LaunchControl solution. Re-runnable; ping*
> *me with the maker-portal URL when it's deployed so I can bind*
> *connections and test.*

### Implementation notes (these are the easy-to-miss bits — get them right on the first try)

- Flow name `LC · Custom Tools Test Harness`. Lives in the Dataverse
  `workflows` table: `category=5` (modern flow), `type=1` (definition),
  `statecode=0` (draft).
- POST with header `MSCRM.SolutionUniqueName: LaunchControl` to land it
  in the solution.
- **Solution-aware flows need connection references, not connection
  names.** Idempotently ensure two `connectionreference` rows exist:
  `lc_dataverse_harness` (`connectorid =
  /providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps`)
  and `lc_githubreleases_harness` (pointing at the GH connector slug
  from Part 3a). Look up by `connectionreferencelogicalname` first;
  create only if missing.
- `clientdata.properties.connectionReferences` is a map whose **keys are
  the connection-reference logical names**. Each value:
  `{"connection": {"connectionReferenceLogicalName": "<name>"}, "api":
  {"name": "<connector slug>"}, "runtimeSource": "embedded"}`.
- Each action's `host` block uses `connectionReferenceName: "<map key>"`
  — NOT `connectionName`.
- **For unbound Custom API calls (`PerformUnboundAction`), input params
  go at the TOP LEVEL of `parameters` — NOT under `item/`.** Using
  `item/lc_LaunchName` is the bound-action shape; the unbound action
  rejects it as "no longer present in the operation schema".
- **Do NOT include `"authentication": "@parameters('$authentication')"`**
  on `OpenApiConnection` actions. Power Automate auto-injects this and
  rejects the flow if present (`should not have the property
  'authentication'`).
- PATCH can't change `clientdata`'s connection-reference schema in
  place. If a flow with the same name exists, **DELETE and recreate**.
- Discover the GH connector slug at runtime by querying PAPI by
  displayName (`/providers/Microsoft.PowerApps/apis?$filter=environment eq
  '<env>'`, filter client-side for `displayName == "Launch Control —
  GitHub Releases"`). If missing, deploy a partial 2-action flow and
  warn rather than failing.
- Print the maker-portal URL on success:
  `https://make.powerautomate.com/environments/<env>/flows/<workflow-id>`.

### Verification

```bash
python scripts/create_test_harness_flow.py
# Open the printed URL. Click Edit. There should be a yellow banner
# asking you to bind connections for lc_dataverse_harness and
# lc_githubreleases_harness — pick or create one each. Save. Then
# Test → Manually → Run with LaunchName=Q3 Widget Launch.
```

Expected: the run history shows four green actions, and the Compose
output contains a verdict from the .NET API, a verdict + `lc_NotifiedAt`
from the Fx twin, a `tag_name` from GitHub Releases, and three sentences
of exec briefing from the AI prompt.

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
[Part 4] register_ai_prompt.py prompts/DraftLaunchBriefing → smoke-test twice
       │
       ▼
[Part 5] create_test_harness_flow.py → bind connections in portal → Test → Run
```

If a Part fails, stop and remediate before moving on. Each Part's output
is an input to the next (Part 5 needs the GH connector slug from Part 3a,
the .NET API from Part 1, the Fx twin from Part 2, and the AI prompt
action name from Part 4).

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
