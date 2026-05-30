# Episode 5 — Custom Tools

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Custom Dataverse Plugin → Custom Action · ⭐ Power Fx Function (low-code twin) → Custom Action · ⭐ Custom Endpoint Registration (REST + remote MCP, programmatic) · ⭐ Power Automate test-harness flow
**Layer:** 🔵 Layer 2 (intelligence — extending the tool ecosystem)
**Coding agent:** GitHub Copilot CLI (every part — see the prompts below)
**Companion skill:** [`SKILL.md`](SKILL.md) — encodes the prompts below as a single procedure the CLI can follow end-to-end.

> ⚠️ **How to read this episode.** Each Part is a **prompt you type into
> GitHub Copilot CLI**. The scripts, plugin, swagger, and flow JSON in this
> repo are the *output* of those prompts — not the demo. Assume nothing in
> `plugins/`, `functions/`, `connectors/`, or `scripts/` exists at the
> moment recording starts. The point of the episode is that one developer,
> with one CLI, produces all five artifacts in one sitting.

---

## The hook

> _"Before we build agents, we need to give them superpowers. Not by writing
> agent code. By registering tools — once — that every agent we ever build
> can call."_

Episodes 1–4 stood up the data and made it queryable from anywhere. Episode
5 is about **what agents can do** with that data. Three surfaces, one
contract:

1. **Custom logic that runs _inside_ Dataverse (.NET path)** — a Custom API
   backed by a sandbox plugin. Server-side, transactional, governed by the
   same role-based security as the data it touches.
2. **The same contract, written in Power Fx (low-code path)** — a Function
   in Dataverse that implements `lc_CalculateLaunchReadinessFx` and **calls
   the first-party Microsoft Teams connector** to post a readiness card to
   the launch's Teams channel. Same inputs, same outputs, same
   agent-callable name — different runtime, no build step.
3. **External services exposed _through_ Dataverse's governance plane** —
   REST endpoints and remote MCP servers, registered as custom connectors
   programmatically, so DLP, network policies, and Defender for Cloud Apps
   all apply.

All three end up as tools any agent (Copilot Studio, Agent Builder, M365
Copilot, Claude with the Dataverse plugin, GitHub Copilot with the
companion skill) can pick up.

---

## The narrative beat

The opening shot is a question:

> _"Is the Q3 Widget Launch ready to go?"_

By the end of the episode, that question has two answers, both correct,
both authoritative — and both reachable from the same agent surface:

```
INVOKE lc_CalculateLaunchReadiness('Q3 Widget Launch')
→ Score=38.8  Verdict=NO-GO  (because 2 milestones are Blocked)
```

```
INVOKE Learn-MCP.search('virtual entity setup gotchas')
→ Live Microsoft Learn results, governed exactly like any Dataverse query
```

Same agent. Same governance. One tool runs server-side in Dataverse, the
other on a remote server you don't own. The agent doesn't know — or care —
which is which.

---

## Pre-flight (before you type the first prompt)

A clean machine, the repo cloned, and:

```powershell
# 1. dv-connect skill ran (creates .env, scripts/auth.py, installs deps)
ls .env scripts/auth.py

# 2. PAC + Azure CLI logged in to the target tenant
pac auth create --environment <env-id>
az login

# 3. Target env confirmed
pac org who
# → URL: https://org40ae6a46.crm.dynamics.com
# (LaunchControl solution + lc_launch / lc_milestone tables from Eps 1–4)
```

**Env requirement for Part 2 only:** a tenant admin must have installed
the **Power Platform Low Code Plug-ins** application in the target
environment (Power Platform admin center → Environments → _(your env)_ →
Resources → Dynamics 365 apps). Until that's done the
`msdyn_lowcodeplugin` table doesn't exist and the Part 2 prompt's
registration step will gracefully skip with a remediation note — the rest
of the episode still ships end-to-end.

---

## Part 1 · Custom Plugin → Custom Action (internal)

> Internal business logic. Server-side. Transactional. Reusable.

`Should this launch go live?` is the kind of question that should not be
re-implemented in every agent prompt. It belongs to the platform — where
the data is, where the security is, where it can be called identically by
the Power Apps form, the Python script, the Copilot Studio agent, and the
M365 Copilot natural-language surface.

### Why .NET and not Power Fx for this one?

Dataverse's Functions (formerly _instant low-code plug-ins_) let you write
this same logic in Power Fx with no .NET assembly. Part 2 ships exactly
that twin. We do .NET first because:

1. **Production status.** Functions in Dataverse are **preview** as of May
   2026. Sandbox-isolated .NET plug-ins remain the only supported
   production runtime.
2. **Observability.** The `ITracingService` we use to narrate the score
   into `lc_ReadinessSummary` has no Power Fx equivalent — the
   per-milestone reasoning is half the value the Custom API hands back to
   the agent.

### The prompt

Type this into GitHub Copilot CLI:

> *Generate a .NET Framework 4.6.2 Dataverse sandbox plugin called*
> *`CalculateLaunchReadinessPlugin` in `plugins/CalculateLaunchReadiness/`.*
> *It should back a Custom API named `lc_CalculateLaunchReadiness` with*
> *one input parameter `lc_LaunchName` (string) and three output*
> *properties: `lc_ReadinessScore` (decimal 0–100), `lc_ReadinessSummary`*
> *(multi-line string narrating each milestone), and `lc_Verdict`*
> *(string: GO, CONDITIONAL, or NO-GO).*
>
> *Logic: look up the launch by `lc_name`, retrieve every related*
> *`lc_milestone`, score each by status (Complete=100, InProgress=60,*
> *AtRisk=50, NotStarted=20, Blocked=0), average them. Verdict rules: any*
> *Blocked → NO-GO; score ≥ 90 and zero AtRisk → GO; otherwise*
> *CONDITIONAL. Use `ITracingService` to narrate the per-milestone score*
> *into `lc_ReadinessSummary`. Sort milestones by `lc_duedate`.*
>
> *Then write `scripts/register_custom_action.py` that uploads the*
> *assembly, registers the plugin type, creates the Custom API + request*
> *parameter + response properties via the Dataverse Web API, binds*
> *PluginTypeId, and adds the Custom API to the `LaunchControl` solution*
> *with `AddRequiredComponents=true`. Idempotent. Use `scripts/auth.py`*
> *for tokens.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| C# plugin class | [`plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs`](../../plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs) |
| csproj (with the `Microsoft.NETFramework.ReferenceAssemblies.Net462` NuGet pkg — needed because the SDK no longer ships .NET 4.6.2 targeting packs by default) | `plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadiness.csproj` |
| Registration script | [`scripts/register_custom_action.py`](../../scripts/register_custom_action.py) |
| Setup notes (Copilot writes these alongside the code) | [`plugins/CalculateLaunchReadiness/SETUP-GUIDE.md`](../../plugins/CalculateLaunchReadiness/SETUP-GUIDE.md) |

### What you run on screen

```powershell
cd plugins/CalculateLaunchReadiness
dotnet build --configuration Release
cd ../..
python scripts/register_custom_action.py
```

Then prove it's live:

```powershell
python -c @"
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_CalculateLaunchReadiness',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code, json.dumps(r.json(), indent=2))
"@
```

Expected output:

```json
{
  "lc_ReadinessScore":   38.8,
  "lc_Verdict":          "NO-GO",
  "lc_ReadinessSummary": "16 milestones evaluated\n  Complete:    3\n  InProgress:  4\n  AtRisk:      2\n  NotStarted:  5\n  Blocked:     2\nBlockers: …"
}
```

> _"This is business logic that runs **in** Dataverse. Any agent, any app
> can call it the same way."_

---

## Part 2 · The Power Fx twin (low-code, connector-native)

> Same contract. Different runtime. One line of Power Fx to reach a
> first-party connector.

The .NET plugin is the production path. The **Power Fx Function** is the
low-code twin — same Custom API shape (`lc_CalculateLaunchReadinessFx`),
written in `formula.fx`, registered the same way, callable from the same
agents. The interesting beat for developers: a Function can invoke any
**Power Platform connector** as a Fx expression —
`MicrosoftTeams.PostMessageToChannelV3(...)` — with platform-managed auth,
DLP, and audit applied automatically.

> **Side-note on HTTPS from plug-ins.** The .NET sandbox plug-in *can*
> make outbound HTTPS calls (ports 80/443 only) — that's been supported
> for years per [Access external web services](https://learn.microsoft.com/power-apps/developer/data-platform/access-web-services).
> What the sandbox **can't** do is reach a connector. Connections,
> connection references, DLP, the user-consent OAuth grant, the per-env
> credential vault — none of that exists from inside a plug-in. That's
> the real distinction, and it's the whole reason Functions in Dataverse
> exist.

### What we add: notify the launch channel with a readiness card

Every launch lives in a Microsoft Teams channel. The Fx function:

1. Calls the .NET Custom API for the baseline score / verdict / summary.
2. **Calls `MicrosoftTeams.PostMessageToChannelV3(...)` via the
   first-party Teams connector** — posts a card with the verdict +
   summary to the launch's Teams channel (looked up from
   `lc_launch.lc_TeamsChannelId`).
3. Returns the unchanged baseline plus a `lc_NotifiedAt` timestamp the
   caller can persist.

### The prompt

> *Generate a Power Fx Function under*
> *`functions/CalculateLaunchReadinessFx/` with three files:*
>
> - *`function.json` — Custom API contract matching the Part 1 plugin*
>   *plus an `lc_NotifiedAt` (DateTime) response property.*
> - *`formula.fx` — Power Fx that calls*
>   *`Environment.lc_CalculateLaunchReadiness({lc_LaunchName:*
>   *LaunchName})` for the baseline, looks up the launch's Teams team and*
>   *channel IDs from `lc_launch`, then invokes*
>   *`MicrosoftTeams.PostMessageToChannelV3(...)` to post a verdict +*
>   *summary HTML message. Returns baseline outputs plus `lc_NotifiedAt =*
>   *Now()` if posted else Blank.*
> - *`README.md` — record the exact Copilot for Power Fx prompt used to*
>   *generate `formula.fx` so the next dev can regenerate it.*
>
> *Then write `scripts/register_lowcode_function.py` that registers the*
> *Function via the `msdyn_lowcodeplugin` table and adds it to the*
> *`LaunchControl` solution. If `msdyn_lowcodeplugin` is absent (tenant*
> *admin hasn't installed "Power Platform Low Code Plug-ins"), print a*
> *clear remediation message and exit 0 (not failure).*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Power Fx body | [`functions/CalculateLaunchReadinessFx/formula.fx`](../../functions/CalculateLaunchReadinessFx/formula.fx) |
| Custom API contract | [`functions/CalculateLaunchReadinessFx/function.json`](../../functions/CalculateLaunchReadinessFx/function.json) |
| Prompt log | [`functions/CalculateLaunchReadinessFx/README.md`](../../functions/CalculateLaunchReadinessFx/README.md) |
| Registration script | `scripts/register_lowcode_function.py` |

### What you run on screen

```powershell
python scripts/register_lowcode_function.py functions/CalculateLaunchReadinessFx

# Invoke the twin. Same shape, plus lc_NotifiedAt, plus a Teams card lands.
python -c @"
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_CalculateLaunchReadinessFx',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code, json.dumps(r.json(), indent=2))
"@
```

A **Microsoft Teams connection reference** (`shared_teams`) must already
exist in the target environment — Teams is a first-party Microsoft
connector, no install needed; you'll just be prompted to consent the
first time.

This is the part most developers haven't seen yet: **Power Fx Functions
are the low-code path _and_ the connector-native path**. Three words of
Power Fx; zero infrastructure.

---

## Part 3 · Custom Endpoint Registration (REST + remote MCP, both programmatic)

> Any HTTPS endpoint — REST or MCP — becomes a first-class Power Platform
> tool through the same `custom connector` primitive. Same governance,
> same DLP, same Defender for Cloud Apps. The only thing that changes per
> endpoint is a small Swagger 2.0 document.

Custom connectors aren't a side door — they're the same primitive that
has governed Excel, SharePoint, ServiceNow, and a thousand others for
years. Once a connector is registered, every Power Platform governance
control (DLP policies, IP firewall, Defender for Cloud Apps, connection
references) applies to it identically.

This part does **both** flavors and registers each one
**programmatically** — no `paconn login`, no hand-clicks in the maker
portal. **One script** drives PAPI directly, reads any `connectors/<name>/`
folder, and creates or updates the connector idempotently.

### Part 3a · The prompt — wrap a public REST endpoint (GitHub Releases)

> *Generate a Swagger 2.0 connector folder at*
> *`connectors/github-releases-rest/` for the public GitHub Releases API:*
>
> - *`apiDefinition.swagger.json` — host `api.github.com`, basePath*
>   *`/repos`, two operations: `GetLatestRelease` (GET*
>   *`/{owner}/{repo}/releases/latest`) and `ListReleases` (GET*
>   *`/{owner}/{repo}/releases`). No security definitions (public API).*
> - *`apiProperties.json` — empty `connectionParameters`, brand colour*
>   *`#24292F`, capabilities `[]`.*
> - *`settings.example.json` — paconn-style settings template.*
>
> *Then write `scripts/register_custom_connector.py` that takes a folder*
> *path on the command line and registers (or updates) a custom connector*
> *via PAPI directly — no paconn dependency. Use `AzureCliCredential`*
> *for the bearer token against*
> *`https://service.powerapps.com/.default`. POST to*
> *`/providers/Microsoft.PowerApps/apis?api-version=2016-11-01&$filter=environment eq '<env-id>'`*
> *for create, PATCH `/providers/Microsoft.PowerApps/apis/<id>?...` for*
> *update. Body shape: `{"properties": {"openApiDefinition": <swagger*
> *contents>, "backendService": {"serviceUrl":*
> *"<scheme>://<host><basePath>"}, "environment": {"name": "<env-id>"},*
> *"description": ..., "displayName": ..., "connectionParameters": {},*
> *"capabilities": [], "policyTemplateInstances": [],*
> *"scriptOperations": []}}`. Cache the returned connector id in*
> *`<folder>/.connector-id` for re-runs. After PAPI registration, also*
> *add the connector to the LaunchControl solution via*
> *`pac connector create --solution-unique-name LaunchControl`.*

### Part 3b · The prompt — wrap two remote MCP servers

> *Generate two more connector folders using the same script:*
>
> - *`connectors/learn-mcp/` — wraps*
>   *`https://learn.microsoft.com/api/mcp`, no auth.*
> - *`connectors/github-mcp/` — wraps*
>   *`https://api.githubcopilot.com/mcp/`, GitHub PAT via*
>   *`connectionParameters.api_key` (Authorization header).*
>
> *The swagger files must include one `POST /api/mcp` (or equivalent)*
> *path with `operationId: InvokeServer` and the extension*
> *`"x-ms-agentic-protocol": "mcp-streamable-1.0"` — that's the bit that*
> *flips the connector framework from "REST" to "MCP".*

### The magic line

`x-ms-agentic-protocol: mcp-streamable-1.0` is what tells the connector
framework "this isn't a REST endpoint, it's an MCP server, do tool
discovery and streaming for me." Everything else (the HTTP path, optional
auth via `connectionParameters`, the icon, the publisher) is identical to
the REST connector in Part 3a. **One swagger key, two different
substrates governed identically.**

### What Copilot produces

| Folder | Surface | Auth |
|---|---|---|
| [`connectors/github-releases-rest/`](../../connectors/github-releases-rest/) | REST | None |
| [`connectors/learn-mcp/`](../../connectors/learn-mcp/) | MCP (`mcp-streamable-1.0`) | None |
| [`connectors/github-mcp/`](../../connectors/github-mcp/) | MCP (`mcp-streamable-1.0`) | GitHub PAT |
| [`scripts/register_custom_connector.py`](../../scripts/register_custom_connector.py) | The PAPI-direct registration script that drives all three | — |

### What you run on screen

```powershell
python scripts/register_custom_connector.py connectors/github-releases-rest
python scripts/register_custom_connector.py connectors/learn-mcp
python scripts/register_custom_connector.py connectors/github-mcp
```

Each run prints the resulting connector id and caches it in
`<folder>/.connector-id` so subsequent runs update in place. Re-runnable,
diff-able, CI-friendly.

> _"REST endpoint or MCP server, the registration story is identical:
> describe it in Swagger, run one script, the tool shows up in every
> agent surface in your tenant."_

---

## Part 4 · The test harness flow (one cloud flow calls all three)

> A single Power Automate flow with three actions — one per surface we
> built in Parts 1, 2, and 3a. Press Run; see the responses side-by-side.
> The visual confirmation that the tool framework is uniform.

The first three parts produce three independently-callable tools. The
question every developer asks next is _"how do I prove they all work
without spinning up an agent?"_ Answer: a manual-trigger cloud flow with
three `OpenApiConnection` actions, deployed programmatically via the
Dataverse `workflows` table — same governance, same auth, same surface
every Power Platform developer already knows.

### The prompt

> *Generate `scripts/create_test_harness_flow.py` that creates a Power*
> *Automate flow named `LC · Custom Tools Test Harness` via the Dataverse*
> *`workflows` table (`category=5` modern flow, `type=1` definition). The*
> *flow should:*
>
> *1. Look up the GitHub Releases custom connector by displayName via*
>    *PAPI (`/providers/Microsoft.PowerApps/apis?$filter=environment eq*
>    *'...'`). If absent, deploy a partial 2-action flow.*
>
> *2. Idempotently ensure two `connectionreference` rows exist in the*
>    *`LaunchControl` solution: `lc_dataverse_harness` (connectorid*
>    *`/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps`)*
>    *and `lc_githubreleases_harness` (pointing at the GH slug from step 1).*
>    *Lookup by `connectionreferencelogicalname` first; create only if*
>    *missing.*
>
> *3. Build a logic-apps-style `clientdata` with:*
>    *- `properties.connectionReferences` map — keys are the connection*
>      *reference logical names; each value is `{"connection":*
>      *{"connectionReferenceLogicalName": "<name>"}, "api": {"name":*
>      *"<connector slug>"}, "runtimeSource": "embedded"}`.*
>    *- A manual trigger with `LaunchName` (default Q3 Widget Launch),*
>      *and `Owner`/`Repo` inputs only if the GH connector is present.*
>    *- Three `OpenApiConnection` actions: `Call_Custom_API_dotnet`,*
>      *`Call_Power_Fx_Function` (both `PerformUnboundAction` with*
>      *parameter `actionName` plus the Custom-API input at TOP LEVEL —*
>      *`lc_LaunchName`, NOT `item/lc_LaunchName`), and*
>      *`Call_GitHub_Releases` (`GetLatestRelease`). Each action's `host`*
>      *block uses `connectionReferenceName: "<map key>"`, NOT*
>      *`connectionName`. Do NOT include*
>      *`"authentication": "@parameters('$authentication')"` anywhere;*
>      *Power Automate auto-injects it and rejects the flow if present.*
>    *- Compose + Respond actions stitching the three bodies into one*
>      *JSON.*
>
> *4. POST the flow with header `MSCRM.SolutionUniqueName: LaunchControl`.*
>    *If the flow already exists, DELETE and recreate (PATCH cannot*
>    *change the connection-reference schema in place). Print the*
>    *https://make.powerautomate.com/.../flows/&lt;guid&gt; URL.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Deployment script | [`scripts/create_test_harness_flow.py`](../../scripts/create_test_harness_flow.py) |
| The flow itself | `LC · Custom Tools Test Harness` in the LaunchControl solution |
| Connection references | `lc_dataverse_harness`, `lc_githubreleases_harness` (Dataverse `connectionreference` table) |

### What you run on screen

```powershell
python scripts/create_test_harness_flow.py
# → OK - Flow deployed.
#   Open: https://make.powerautomate.com/.../flows/<guid>
```

Open the URL. Click **Edit** — Power Automate prompts you to bind the two
connection references to actual connections (one Dataverse, one GitHub
Releases — the custom connector requires no auth). Save. Then **Test →
Manually → Run** with `LaunchName = Q3 Widget Launch`.

In one screen you see the same launch scored by .NET, the same launch
scored by Power Fx (plus a Teams card posted), and the latest release of
the referenced repo. **The flow IS the validation surface; no separate
Python preflight needed on-screen.**

> A [`preflight.py`](preflight.py) script still lives in this folder for CI /
> pre-record sanity checks (6 readiness probes: each artifact is in env,
> in the solution, and answers a call). It's not part of the recorded
> narrative — the flow run is.

---

## What's deliberately NOT in this episode

- **A Copilot Studio agent.** That's Episode 9 — _The Agent_. The point of
  this episode is _the tools exist and are independently verified_.
  Pointing an agent at them is the next episode's payoff.
- **A custom MCP server we host ourselves.** This episode shows BYO MCP via
  registering _someone else's_ public MCP servers (Microsoft Learn,
  GitHub). Hosting your own MCP server (auth, scaling, observability) is
  a meatier topic that resurfaces in later episodes on agent runtimes and
  admin.
- **Write-through to the external systems.** Both Learn MCP and GitHub MCP
  expose read tools in the configuration we ship. Letting agents create
  or edit through them is a write-path concern with its own auth review;
  out of scope for the "tool registration" beat.

---

## What you see on screen (timing-wise)

1. **Hook** — the Q3 Widget Launch dashboard in Power Apps. _"Are we
   ready?"_
2. **Part 1** — type the Part 1 prompt into Copilot CLI. Copilot writes
   `CalculateLaunchReadinessPlugin.cs` and `register_custom_action.py`.
   `dotnet build`, run the script, smoke-test the Custom API. _"This is
   business logic that runs in Dataverse."_
3. **Part 2** — type the Part 2 prompt. Copilot writes `formula.fx`,
   `function.json`, and `register_lowcode_function.py`. Register, invoke,
   show the Teams card landing in the launch channel. _"Same contract,
   plus a Teams post — three words of Power Fx."_
4. **Part 3a** — type the Part 3a prompt. Copilot writes the GitHub
   Releases swagger and `register_custom_connector.py`. Register, show
   the connector in make.powerapps.com.
5. **Part 3b** — type the Part 3b prompt. Copilot writes two more swagger
   folders. Re-run the same registration script twice. _"One script,
   three connectors, two of them MCP — one swagger key apart."_
6. **Part 4** — type the Part 4 prompt. Copilot writes
   `create_test_harness_flow.py`. Run it, open the URL, bind the two
   connection references, Test → Run, point at the three green action
   results side-by-side.
7. **The reveal** — _"That dashboard at the top? It's calling the .NET
   Custom API for the verdict. That Teams notification I just got? The Fx
   twin posted it. That latest-release badge? GitHub Releases custom
   connector. **Three different runtimes; one agent-callable surface.**
   Next episode we point an agent at it."_

---

## Repo inventory (output of the prompts, in dependency order)

```
plugins/CalculateLaunchReadiness/
  CalculateLaunchReadiness/
    CalculateLaunchReadinessPlugin.cs      # Part 1 — plugin class
    CalculateLaunchReadiness.csproj        # Part 1 — .NET 4.6.2 csproj
  SETUP-GUIDE.md                           # Part 1 — registration walk-through
functions/CalculateLaunchReadinessFx/
  formula.fx                               # Part 2 — Power Fx body
  function.json                            # Part 2 — Custom API contract
  README.md                                # Part 2 — Copilot for Power Fx prompt
connectors/
  github-releases-rest/                    # Part 3a — REST connector
    apiDefinition.swagger.json
    apiProperties.json
    settings.example.json
  learn-mcp/                               # Part 3b — MCP connector (Learn)
    apiDefinition.swagger.json
    apiProperties.json
  github-mcp/                              # Part 3b — MCP connector (GitHub)
    apiDefinition.swagger.json
    apiProperties.json
scripts/
  register_custom_action.py                # Parts 1 + 2 — Custom API registration
  register_lowcode_function.py             # Part 2 — Function in Dataverse registration
  register_custom_connector.py             # Part 3 — PAPI-direct connector registration
  create_test_harness_flow.py              # Part 4 — flow deployment
  check_solution_components.py             # Cross-cut — verify solution membership
preflight.py                               # CI sanity (6 probes); not recorded on screen
```

---

## Companion skill

The [`SKILL.md`](SKILL.md) in this folder encodes the prompts above as a
single procedure GitHub Copilot CLI can follow end-to-end. With the skill
installed (copy or symlink it under your Copilot CLI plugin path), the
recording session becomes:

```
User: do Episode 5
CLI:  [pre-flight checks, target env confirmation]
      [runs Part 1 prompt → builds plugin → registers → smoke-tests]
      [runs Part 2 prompt → registers Fx twin → posts Teams card]
      [runs Part 3a + 3b prompts → registers 3 connectors]
      [runs Part 4 prompt → deploys flow → returns URL for the user to test]
```

That's the recorded path. The README above is the human-readable version
of the same procedure.
