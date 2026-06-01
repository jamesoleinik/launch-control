# Episode 5 — Custom Tools

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Custom Plugin → Custom Action · ⭐ Custom Function (Power Fx) → Custom Action · ⭐ Custom Connector (REST + remote MCP, programmatic) · ⭐ Custom AI Function (AI Prompt) → Custom Action · ⭐ Power Automate test-harness flow
**Layer:** 🔵 Layer 2 (intelligence — extending the tool ecosystem)
**Coding agent:** GitHub Copilot CLI (every part — see the prompts below)
**Companion skill:** [`SKILL.md`](SKILL.md) — encodes the prompts below as a single procedure the CLI can follow end-to-end.

> ⚠️ **How to read this episode.** Each Part is a **prompt you type into
> GitHub Copilot CLI**. The scripts, plugin, swagger, prompt definition,
> and flow JSON in this repo are the *output* of those prompts — not the
> demo. Assume nothing in `plugins/`, `functions/`, `connectors/`,
> `prompts/`, or `scripts/` exists at the moment recording starts. The
> point of the episode is that one developer, with one CLI, produces all
> the artifacts in one sitting.

---

## The hook

> _"Before we build agents, we need to give them superpowers. Not by
> writing agent code. By registering tools — once — that every agent we
> ever build can call."_

Episodes 1–4 stood up the data and made it queryable from anywhere.
Episode 5 is about **what agents can do** with that data. Dataverse gives
you **four** places to put custom business logic, and every one of them
ends up as the same primitive: an **agent-callable Custom Action**.

| # | Where the logic lives | Best for | Runtime |
|---|---|---|---|
| 1 | **Custom Plugin** (.NET sandbox) | Deterministic, transactional, observability via `ITracingService` | Dataverse server, in-transaction |
| 2 | **Custom Function** (Power Fx) | Low-code, calls first-party connectors with platform-managed auth | Dataverse server, Fx runtime |
| 3 | **Custom Connector** (REST or remote MCP) | Any HTTPS endpoint you don't own, governed by DLP / connection refs / Defender for Cloud Apps | External, called via Power Platform connector framework |
| 4 | **Custom AI Function** (AI Prompt) | Non-deterministic LLM reasoning — narrative, summarization, classification, judgment | Dataverse AI hub, model-routed |

**All four expose the same shape** — an `lc_*` Custom Action that takes a
launch name in and returns a structured response. Any agent (Copilot
Studio, Agent Builder, M365 Copilot, Claude with the Dataverse plugin,
GitHub Copilot with the companion skill) calls them identically and has
no idea — and no reason to care — which substrate answered.

---

## The narrative beat

The opening shot is a question:

> _"Is the Q3 Widget Launch ready to go?"_

By the end of the episode that question has **four** answers, each
authoritative on its own terms, all reachable from the same agent surface:

```
INVOKE lc_CalculateLaunchReadiness('Q3 Widget Launch')      → .NET     Score=38.8  Verdict=NO-GO
INVOKE lc_CalculateLaunchReadinessFx('Q3 Widget Launch')    → Power Fx Same shape + posts Teams card
INVOKE Launch-Control-GitHub-Releases.GetLatestRelease(...) → REST     Latest shipped artifact
INVOKE lc_DraftLaunchBriefing('Q3 Widget Launch')           → AI       3-sentence exec recommendation, in the sponsor's voice
```

Same agent. Same governance. Four very different runtimes. The agent
doesn't know — or care — which is which.

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

> *Create a Dataverse Custom API called `lc_CalculateLaunchReadiness`*
> *that scores a launch by averaging its milestone statuses and returns*
> *a verdict (GO / CONDITIONAL / NO-GO, with any Blocked milestone*
> *forcing NO-GO). Build it as a .NET sandbox plugin so the per-milestone*
> *reasoning can come back in a tracing-service narrative. Then register*
> *everything programmatically into the LaunchControl solution and smoke*
> *test it against Q3 Widget Launch.*

(Copilot has the `dv-overview`, `dv-data`, and `dv-solution` skills
loaded, so it already knows the Web API patterns, the `LaunchControl`
solution name, the `lc_` prefix, the `lc_launch` / `lc_milestone` table
shape, and that `scripts/auth.py` handles tokens. The only intent that
isn't recoverable from the schema is the scoring rubric — let Copilot
suggest one and confirm it.)

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

> *Build a Power Fx twin of that Custom API — same shape, suffixed `Fx` —*
> *as a Function in Dataverse. After scoring it should also post the*
> *verdict to the launch's Teams channel and return the timestamp it*
> *posted. Register it into the LaunchControl solution. If the low-code*
> *plug-ins app isn't installed in this env, fail gracefully with the*
> *remediation steps — don't error out.*

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

### Part 3a · The prompt — wrap a public REST endpoint

> *Wrap the public GitHub Releases API as a Power Platform custom*
> *connector and register it into the LaunchControl solution*
> *programmatically — no `paconn login`, no maker-portal clicks. I want*
> *the registration script to be re-runnable against any swagger folder*
> *in `connectors/`, since we'll do MCP servers next.*

### Part 3b · The prompt — wrap two remote MCP servers

> *Now do the same for two remote MCP servers: Microsoft Learn MCP*
> *(`learn.microsoft.com/api/mcp`, no auth) and the GitHub MCP server*
> *(`api.githubcopilot.com/mcp/`, GitHub PAT). Re-use the registration*
> *script from 3a — the only thing that should differ between REST and*
> *MCP is the swagger.*

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

## Part 4 · Custom AI Function (AI Prompt → Custom Action)

> Non-deterministic logic — narrative, summarization, judgment — wrapped
> in the **same** Custom Action shape. Authored in the AI hub, callable
> by name from anywhere.

The first three parts produced three deterministic tools — the .NET
plugin returns the same score for the same milestones every time, the Fx
twin does too (plus a Teams post), the REST connector returns whatever
the upstream API returns. Sometimes that's exactly wrong. When the
sponsor asks _"summarise the launch risk in three sentences I can send
to the exec team in their voice"_, you don't want a deterministic
weighted average — you want an LLM with the context.

Dataverse has had that primitive for a while and most pro-devs have
never used it: **AI Prompts in the AI hub**. Author a prompt with
typed inputs, point it at a model, and it's automatically exposed as a
runnable Custom Action (`Predict` on the prompt) governed by the same
security and DLP as everything else. **Same agent-callable contract;
the substrate happens to be an LLM call.**

### The prompt to GitHub Copilot CLI

> *Create a Dataverse AI Prompt called `lc_DraftLaunchBriefing` that*
> *takes a launch name, pulls the milestone narrative for that launch,*
> *and drafts a three-sentence GO / HOLD / NO-GO recommendation in the*
> *voice of the launch sponsor that I can paste straight into Teams.*
> *Wrap it so it's callable as an unbound Custom Action the same way as*
> *the .NET and Fx ones, register it into the LaunchControl solution,*
> *and smoke test it against Q3 Widget Launch.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| AI Prompt definition (inputs, system + user message templates, model binding) | [`prompts/DraftLaunchBriefing/`](../../prompts/DraftLaunchBriefing/) |
| Registration script | `scripts/register_ai_prompt.py` |
| Custom Action wrapper | `lc_DraftLaunchBriefing` in the LaunchControl solution |

### What you run on screen

```powershell
python scripts/register_ai_prompt.py prompts/DraftLaunchBriefing

# Same call shape as Parts 1 and 2 — the agent has no idea this one is an LLM
python -c @"
from auth import get_token
import requests, os, json
t = get_token()
r = requests.post(
    os.environ['DATAVERSE_URL'] + '/api/data/v9.2/lc_DraftLaunchBriefing',
    headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'},
    json={'lc_LaunchName': 'Q3 Widget Launch'})
print(r.status_code, json.dumps(r.json(), indent=2))
"@
```

Expected: three sentences of plain English. Run it twice — the wording
changes. That's the point.

### Why this is its own Part (and not a footnote on Part 1)

The first three substrates differ in **where the code runs**. The AI
Prompt differs in **how the code reasons**. Mashing it into Part 1 ("oh
also you can do this with AI") hides the real beat: _the same Custom
Action contract covers both deterministic and non-deterministic logic_.
That's what makes Dataverse the right place to put agent-callable tools
— the agent picks `lc_CalculateLaunchReadiness` when it wants a number
and `lc_DraftLaunchBriefing` when it wants prose, identical wire
format, identical governance.

---

## Part 5 · The test harness flow (one cloud flow calls all four)

> A single Power Automate flow with four actions — one per substrate we
> built in Parts 1–4. Press Run; see the responses side-by-side. The
> visual confirmation that the tool framework is uniform across all four
> ways of hosting custom business logic.

The first four parts produce four independently-callable tools. The
question every developer asks next is _"how do I prove they all work
without spinning up an agent?"_ Answer: a manual-trigger cloud flow with
four `OpenApiConnection` actions, deployed programmatically via the
Dataverse `workflows` table — same governance, same auth, same surface
every Power Platform developer already knows.

### The prompt

> *Build a Power Automate test-harness flow that exercises all four*
> *tools in one run — the .NET Custom API, the Fx twin, the GitHub*
> *Releases connector, and the AI Prompt — and returns their responses*
> *side-by-side. Manual trigger, takes a `LaunchName` input, deploys*
> *programmatically into the LaunchControl solution. Re-runnable; ping*
> *me with the maker-portal URL when it's deployed so I can bind*
> *connections and test.*

(If Copilot hits an `OpenApiConnection` gotcha — solution-aware flows
needing connection references rather than connection names, unbound
action parameters living at the top level rather than under `item/`,
auto-injected authentication — the companion skill captures those so it
gets them right on the first try. See [`SKILL.md`](SKILL.md) for the
full list.)

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
scored by Power Fx (plus a Teams card posted), the latest release of the
referenced repo, **and** the three-sentence exec briefing drafted by the
AI prompt. **The flow IS the validation surface; no separate Python
preflight needed on-screen.**

> A [`preflight.py`](preflight.py) script still lives in this folder for CI /
> pre-record sanity checks (6 readiness probes: each artifact is in env,
> in the solution, and answers a call). It's not part of the recorded
> narrative — the flow run is.

---

## What's deliberately NOT in this episode

- **A Copilot Studio agent.** That's Episode 8 — _The Agent_. The point of
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
6. **Part 4** — type the Part 4 prompt. Copilot writes the AI Prompt
   definition and `register_ai_prompt.py`. Invoke; show three sentences
   of plain English; invoke again; show different wording. _"Same Custom
   Action shape; non-deterministic substrate."_
7. **Part 5** — type the Part 5 prompt. Copilot writes
   `create_test_harness_flow.py`. Run it, open the URL, bind connection
   references, Test → Run, point at the four green action results
   side-by-side.
8. **The reveal** — _"That dashboard at the top? It's calling the .NET
   Custom API for the verdict. That Teams notification I just got? The
   Fx twin posted it. That latest-release badge? GitHub Releases custom
   connector. That sponsor-voice briefing in my inbox? The AI prompt.
   **Four different runtimes; one agent-callable surface.** Next episode
   we point an agent at it."_

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
prompts/DraftLaunchBriefing/               # Part 4 — AI Prompt definition
  prompt.json                              # Inputs + system/user templates + model
  README.md                                # Iteration notes
scripts/
  register_custom_action.py                # Part 1 — Custom API registration
  register_lowcode_function.py             # Part 2 — Function in Dataverse registration
  register_custom_connector.py             # Part 3 — PAPI-direct connector registration
  register_ai_prompt.py                    # Part 4 — AI Prompt registration
  create_test_harness_flow.py              # Part 5 — flow deployment
  check_solution_components.py             # Cross-cut — verify solution membership
preflight.py                               # CI sanity probes; not recorded on screen
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
