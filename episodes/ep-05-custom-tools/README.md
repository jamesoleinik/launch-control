# Episode 5 — Custom Tools

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Custom Dataverse Plugin → Custom Action · ⭐ Power Fx Function (low-code twin) → Custom Action · ⭐ BYO MCP Server Registration (paconn)
**Layer:** 🔵 Layer 2 (intelligence — extending the tool ecosystem)
**Coding agent:** GitHub Copilot (Part 1 — plugin) · GitHub Copilot for Power Fx (Part 2 — Function) · Terminal + paconn (Part 3)
**Runtime:** .NET Framework 4.6.2 plugin (Sandbox) + Functions in Dataverse (Power Fx, preview) + Power Platform custom connectors

---

## The hook

> _"Before we build agents, we need to give them superpowers. Not by writing
> agent code. By registering tools — once — that every agent we ever build
> can call."_

Episodes 1–4 stood up the data and made it queryable from anywhere. Episode 5
is about **what agents can do** with that data. Three surfaces, one contract:

1. **Custom logic that runs _inside_ Dataverse (.NET path)** — a Custom API
   backed by a plugin. Server-side, transactional, governed by the same
   role-based security as the data it touches.
2. **The same contract, written in Power Fx (low-code path)** — a Function in
   Dataverse that implements `lc_CalculateLaunchReadinessFx` and **calls the
   first-party Microsoft Teams connector** to post a readiness card to the
   launch's Teams channel. Same inputs, same outputs, same agent-callable
   name — different runtime, no build step.
3. **External services exposed _through_ Dataverse's governance plane** —
   Bring-Your-Own MCP servers, registered as custom connectors via `paconn`,
   so DLP, network policies, and Defender for Cloud Apps all apply.

All three end up as tools any agent (Copilot Studio, Agent Builder, M365
Copilot, Claude with the Dataverse plugin, GitHub Copilot with our skill)
can pick up.

---

## The narrative beat

The opening shot is a question:

> _"Is the Q3 Widget Launch ready to go?"_

By the end of the episode, that question has two answers, both correct, both
authoritative — and both reachable from the same agent surface:

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

## Part 1 · Custom Plugin → Custom Action (internal)

> Internal business logic. Server-side. Transactional. Reusable.

`Should this launch go live?` is the kind of question that should not be
re-implemented in every agent prompt. It belongs to the platform, where the
data is, where the security is, where it can be called identically by the
Power Apps form, the Python script, the Copilot Studio agent, and the M365
Copilot natural-language surface.

### Why a .NET plugin _and_ a Power Fx Function?

Dataverse's "Functions" (formerly _instant low-code plug-ins_) let you write
this same logic in Power Fx with no .NET assembly. They're the obvious next
question — so this episode does **both**. We pick .NET first because:

1. **Production status.** Functions in Dataverse are **preview** as of
   May 2026. Sandbox-isolated .NET plug-ins remain the only supported
   production runtime.
2. **Observability.** The `ITracingService` we use to narrate the score
   into `lc_ReadinessSummary` has no Power Fx equivalent — the per-milestone
   reasoning is half the value the Custom API hands back to the agent.

But the contract is what matters, not the implementation. Part 2 of this
episode ships the **exact same Custom API contract** as a Power Fx Function
— and tacks on something the .NET path can't easily do: invoke a
**first-party Power Platform connector** (Microsoft Teams) to post a
readiness card to the launch channel. Two registrations, one agent surface.

### The plugin (GitHub Copilot writes it)

[`plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs`](../../plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs)
is one plugin class registered against a **Custom API** (the modern,
strongly-typed flavour of the Dataverse "custom action" pattern):

```csharp
public class CalculateLaunchReadinessPlugin : IPlugin
{
    public void Execute(IServiceProvider serviceProvider)
    {
        // Input:  lc_LaunchName (string)
        // Output: lc_ReadinessScore   (decimal 0–100)
        //         lc_ReadinessSummary (multi-line narrative)
        //         lc_Verdict          ("GO" | "CONDITIONAL" | "NO-GO")
    }
}
```

The scoring logic is **data-driven**, not hard-coded against gate names:

| Milestone status | Weight |
|---|---:|
| Complete    | 100 |
| InProgress  |  60 |
| AtRisk      |  50 |
| NotStarted  |  20 |
| Blocked     |   0 |

Final score = average across every milestone attached to the launch.

> **A note on the rubric.** This is intentionally the simplest defensible
> scoring — straight average, `Blocked` is a hard veto. If your PMO weights
> _security review_ differently from _order catering_, you change ~15 lines
> of C#. The platform contract — typed Custom API, agent-callable by name,
> server-side and transactional — is what the rest of the series builds on,
> not the formula.

Verdict precedence:

1. Any milestone Blocked → **NO-GO** (regardless of score)
2. Score ≥ 90 _and_ no AtRisk → **GO**
3. Otherwise → **CONDITIONAL**

The tracing service narrates each milestone for the `lc_ReadinessSummary`
output, so the agent has both a number and the reasoning.

### Registration in three steps

The full procedure is in
[`plugins/CalculateLaunchReadiness/SETUP-GUIDE.md`](../../plugins/CalculateLaunchReadiness/SETUP-GUIDE.md).
The short version:

1. **Build** — `dotnet build --configuration Release`, .NET Framework 4.6.2,
   strong-named. (Microsoft has announced .NET 4.8 sandbox support landing
   in Q4 2026; the plugin shape doesn't change — only the `<TargetFramework>`
   bump.)
2. **Register** — [`scripts/register_custom_action.py`](../../scripts/register_custom_action.py)
   uploads the assembly, registers the plugin type, creates the Custom API
   `lc_CalculateLaunchReadiness` with its one request parameter + three
   response properties, and binds the plugin type to the API via
   `PluginTypeId`. Idempotent: if the assembly is already registered, it
   PATCHes the new bytes onto the existing row.
3. **Add to solution** — same script issues one `AddSolutionComponent` call
   for the Custom API with `AddRequiredComponents=true`, which pulls in the
   assembly, plugin type, request parameter, and response properties as
   part of `LaunchControl`. (Verified separately by
   [`scripts/check_solution_components.py`](../../scripts/check_solution_components.py).)

### Invoke it

From anywhere — the SDK, the Web API, MCP, an agent flow:

```http
POST /api/data/v9.2/lc_CalculateLaunchReadiness
Content-Type: application/json
{ "lc_LaunchName": "Q3 Widget Launch" }
```

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

> Same contract. Different runtime. One line of Power Fx to reach a first-party connector.

The .NET plugin is the production path. The **Power Fx Function** is the
low-code twin — same Custom API shape (`lc_CalculateLaunchReadinessFx`),
written in `formula.fx`, registered the same way, callable from the same
agents. The interesting beat for developers: a Function can invoke any
**Power Platform connector** as a Fx expression — `MicrosoftTeams.PostMessageToChannelV3(...)` —
with platform-managed auth, DLP, and audit applied automatically.

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
   first-party Teams connector** — posts an adaptive card with the
   verdict + summary to the launch's Teams channel (looked up from
   `lc_launch.lc_TeamsChannelId`).
3. Returns the unchanged baseline plus a `lc_NotifiedAt` timestamp the
   caller can persist.

Same contract, plus one channel post. The agent calls
`lc_CalculateLaunchReadinessFx` the same way it calls the .NET version;
the connector hop is invisible at the call site.

### The source — three files, all source-controlled

[`functions/CalculateLaunchReadinessFx/`](../../functions/CalculateLaunchReadinessFx/)
holds the Power Fx implementation:

| File | Purpose |
|---|---|
| `formula.fx` | The Power Fx body — what executes server-side |
| `function.json` | Custom API contract (request param + response props, mirrors the plugin and adds a notify timestamp) |
| `README.md` | Build/register notes + Copilot-for-Power-Fx prompt used to write it |

```powerfx
// formula.fx (excerpt)
With(
    {
        launch:   LookUp(lc_launchs, lc_name = LaunchName),
        baseline: Environment.lc_CalculateLaunchReadiness({lc_LaunchName: LaunchName})
    },
    With(
        {
            posted: If(
                !IsBlank(launch.lc_TeamsChannelId),
                MicrosoftTeams.PostMessageToChannelV3(
                    launch.lc_TeamsTeamId,
                    launch.lc_TeamsChannelId,
                    {
                        contentType: "html",
                        content: "<b>" & launch.lc_name & " — " &
                                 baseline.lc_Verdict & "</b><br/>" &
                                 baseline.lc_ReadinessSummary
                    }
                ),
                Blank()
            )
        },
        {
            lc_ReadinessScore:   baseline.lc_ReadinessScore,
            lc_Verdict: baseline.lc_Verdict,
            lc_ReadinessSummary: baseline.lc_ReadinessSummary,
            lc_NotifiedAt:       If(IsBlank(posted), Blank(), Now())
        }
    )
)
```

GitHub Copilot for Power Fx wrote this from one prompt — the
[README in `functions/CalculateLaunchReadinessFx/`](../../functions/CalculateLaunchReadinessFx/README.md)
shows the exact prompt.

### Why connectors from Power Fx (and not from the .NET plugin)?

The .NET sandbox plug-in **can** make outbound HTTPS, but it has no
access to the platform's connection framework — no connection references,
no OAuth tokens managed by the platform, no DLP enforcement, no per-env
credential vault. From a plug-in you'd hand-roll the auth flow, store a
secret somewhere (probably an Azure Key Vault you also stood up), and
opt-out of every governance signal a Power Platform admin relies on.

From Power Fx Functions, you reference a **connection reference**, the
platform handles auth, DLP applies automatically, and the admin's
existing connector policies cover the call. Three words of Power Fx;
zero infrastructure.

This is the part most developers haven't seen yet: **Power Fx Functions
are the low-code path _and_ the connector-native path**. The two paths
together cover every reasonable readiness-calculation shape.

### Registration

> **Env requirement (preview).** Functions in Dataverse is a managed
> feature that ships as the **"Power Platform Low Code Plug-ins"**
> application. Until a tenant admin installs it in the target environment
> the `msdyn_lowcodeplugin` table won't exist and registration will 404.
> The local test harness detects this and **skips** P4 / T4 (rather than
> failing) so the rest of the episode still validates end-to-end. To
> install: Power Platform admin center → Environments → _(your env)_ →
> Resources → Dynamics 365 apps → Install **Power Platform Low Code
> Plug-ins**.

```powershell
# Functions in Dataverse ship in the same solution as the .NET plugin.
pac admin update-org-feature --feature LowCodePluginsEnabled --value true  # one-time per env
pac solution add-component --solution-name LaunchControl `
    --component-type 10038 --component-id lc_CalculateLaunchReadinessFx
pac solution pack --folder solutions/LaunchControl --zipfile LaunchControl.zip
pac solution import --path LaunchControl.zip
```

A **Microsoft Teams connection reference** (`shared_teams`) must exist
in the target environment for the Fx function to resolve
`MicrosoftTeams.PostMessageToChannelV3` at runtime — Teams is a
first-party Microsoft connector, no install needed.

---

## Part 3 · BYO MCP Server (external, via paconn)

> External services. Same governance plane.

Microsoft ships an MCP server at `learn.microsoft.com/api/mcp`. GitHub ships
one at `api.githubcopilot.com/mcp/`. Your team probably has — or will have —
internal MCP servers too. None of these live in Dataverse. **All** of them
should be governable like any other Power Platform connector.

The mechanism is `paconn`, the Power Platform custom connector CLI. The
trick is one Swagger 2.0 extension:

```json
"paths": {
  "/api/mcp": {
    "post": {
      "operationId": "InvokeServer",
      "x-ms-agentic-protocol": "mcp-streamable-1.0",
      "responses": { "200": { "description": "Immediate Response" } }
    }
  }
}
```

`x-ms-agentic-protocol: mcp-streamable-1.0` is the magic bit — it tells the
connector framework "this isn't a REST endpoint, it's an MCP server, do tool
discovery and streaming for me." Everything else (the HTTP path, optional
auth via `connectionParameters`, the icon, the publisher) is identical to
any other custom connector.

### Two real connectors registered

Both live in [`connectors/`](../../connectors/) and were registered with
plain `paconn create`:

| Folder | MCP server | Auth |
|---|---|---|
| [`connectors/learn-mcp/`](../../connectors/learn-mcp/) | `https://learn.microsoft.com/api/mcp` | None (public) |
| [`connectors/github-mcp/`](../../connectors/github-mcp/) | `https://api.githubcopilot.com/mcp/` | GitHub PAT in `Authorization` header |

Each folder has three files:

- `apiDefinition.swagger.json` — the Swagger 2.0 with the `x-ms-agentic-protocol` extension
- `apiProperties.json` — connector capabilities + `connectionParameters` (for auth)
- `settings.example.json` — paconn settings template (real `settings.json` is
  gitignored because it contains an environment-specific GUID)

### Register in your own environment

```powershell
paconn login                          # device-code
pac env list                          # find your environment GUID
cd connectors/learn-mcp
copy settings.example.json settings.json
# edit settings.json — paste your environment GUID
paconn create --settings settings.json
```

Repeat for `github-mcp/`. Two minutes of CLI, no code, two MCP servers now
appear under **Custom connectors** in make.powerautomate.com.

### Why this is the same governance plane

Custom connectors aren't a side door — they're the same primitive that has
governed Excel, SharePoint, ServiceNow, and a thousand others for years.
Once a connector is registered, every Power Platform governance control
(DLP policies, IP firewall, Defender for Cloud Apps, connection references)
applies to it identically. None of that is dev-loop work — it's the admin
plane you already have. We don't cover it on screen here; the point for
this episode is that **the tool exists in the same place every tool exists**.

> _"Same registration pattern, same enforcement surface — whether the logic
> runs in your sandbox or on a server you don't own."_

---

## Part 4 · Local validation (before any agent picks the tools up)

> The episode order is `Custom Tools` (this one) → `The Agent` (Episode 9).
> We want to know the tools _work_ before we point an agent at them.

[`episodes/ep-05-custom-tools/preflight.py`](../../episodes/ep-05-custom-tools/preflight.py) is a
two-mode test harness that exercises the tools without any agent surface:

```powershell
# 1. Generate a reviewable plan (no token prompts)
python episodes/ep-05-custom-tools/preflight.py --plan

# 2. Run the actual tests (acquires token via Azure CLI)
python episodes/ep-05-custom-tools/preflight.py --run
```

`--plan` prints a markdown checklist of what's going to be tested, ideal for
narration prep. `--run` executes 4 pre-flight checks + 4 tests against the
live environment, prints a colorized console report, and writes a timestamped
`test_results_<ts>.md` with raw request/response payloads as evidence.

What's covered:

| # | Check | Validates |
|---|---|---|
| P1 | `lc_CalculateLaunchReadiness` Custom API exists | .NET plugin registration succeeded |
| P2 | Custom API is in `LaunchControl` solution | Solution membership |
| P3 | ≥ 2 BYO MCP custom connectors present | paconn registration succeeded |
| P4 | `lc_CalculateLaunchReadiness**Fx**` Custom API exists | Power Fx Function registration succeeded |
| T1 | Smoke test — invoke `lc_CalculateLaunchReadiness` for "Q3 Widget Launch" | .NET plugin executes, returns expected fields |
| T2 | Verdict matrix — invoke for every launch in env | Score / verdict consistency |
| T3 | Learn MCP server responds to `initialize` + `tools/list` | The MCP endpoint actually speaks the protocol |
| T4 | Invoke `lc_CalculateLaunchReadinessFx` — Fx twin returns same shape, plus `lc_NotifiedAt` when channel set | Power Fx path resolves the Microsoft Teams connector and returns the contract |

Run output (current environment, 2026-05-01):

```
[ OK ] P1: CustomAPI lc_CalculateLaunchReadiness exists           (4431ms)
[ OK ] P2: CustomAPI is in LaunchControl solution                 (2498ms)
[ OK ] P3: BYO MCP custom connectors present (>=2)                (1292ms)
       found 3: cr88d_5Flearn-20mcp, cr88d_5Fmanual-20learn, cr88d_5Flearn-20mcp-202
[ OK ] P4: CustomAPI lc_CalculateLaunchReadinessFx exists         (1102ms)
[ OK ] T1: Smoke test — Score=38.8, Verdict=NO-GO                 (1248ms)
[ OK ] T2: Verdict matrix — 1 launch scored consistently          (2873ms)
[ OK ] T3: Learn MCP server responds to initialize + tools/list   (794ms)
       server=Microsoft Learn MCP Server exposes 3 tool(s)
[ OK ] T4: Fx twin — Score=38.8, Verdict=NO-GO, 2 open blocker(s) (1611ms)

8/8 passing | Results: scripts/test_results_20260501_090533.md
```

The `test_results_*.md` files are gitignored because they contain
environment-specific GUIDs and timestamps; they're per-run evidence, not
source.

---

## What's deliberately NOT in this episode

- **A Copilot Studio agent.** That's Episode 9 — _The Agent_. The point of
  this episode is _the tools exist and are independently verified_. Pointing
  an agent at them is the next episode's payoff.
- **A custom MCP server we host ourselves.** This episode shows BYO MCP via
  registering _someone else's_ public MCP servers (Microsoft Learn, GitHub).
  Hosting your own MCP server (auth, scaling, observability) is a meatier
  topic that resurfaces in later episodes on agent runtimes and admin.
- **Write-through to the external systems.** Both Learn MCP and GitHub MCP
  expose read tools in the configuration we ship. Letting agents create or
  edit through them is a write-path concern with its own auth review; out
  of scope for the "tool registration" beat.

---

## What you see on screen

1. **Hook** — the Q3 Widget Launch dashboard in Power Apps. _"Are we ready?"_
2. **Part 1, GitHub Copilot writing the plugin** — VS Code with the
   `dataverse-skills` plugin loaded. One-line spec: _"Custom action that
   scores a launch by averaging milestone status weights, returns a verdict.
   No hard-coded gate names."_ → Copilot writes `CalculateLaunchReadinessPlugin.cs`.
3. **Build + register** — `dotnet build` then
   `python scripts/register_custom_action.py`. The script's progress lines
   show: assembly uploaded → plugin type → custom API → request/response
   properties → solution component additions → ✅ registered.
4. **First invocation** — terminal `curl` (or MCP query in the IDE):
   ```
   POST .../lc_CalculateLaunchReadiness  { "lc_LaunchName": "Q3 Widget Launch" }
   →  Score=38.8  Verdict=NO-GO  (Blocked: 'Security review', 'CDN provisioning')
   ```
5. **Part 2, paconn** — terminal: `paconn create --settings settings.json`
   for `learn-mcp/`, then for `github-mcp/`. Two custom connectors appear in
   the maker portal under **Custom connectors**.
6. **The Swagger trick** — zoom into `apiDefinition.swagger.json`,
   highlight `"x-ms-agentic-protocol": "mcp-streamable-1.0"`. _"That single
   line is what makes it an MCP connector."_
7. **Test harness** — `python episodes/ep-05-custom-tools/preflight.py --plan` to show
   the checklist, then `--run` to show the 6/6 green output.
8. **The punchline:**
   > _"Custom actions for internal logic. BYO MCP for external systems.
   > Both governed. Both available — by name — to every agent we build
   > next. The agents don't have to be smart about tools. The platform is."_

---

## Files in this episode

| File | Role |
|---|---|
| [`plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs`](../../plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs) | The plugin behind `lc_CalculateLaunchReadiness`. |
| [`plugins/CalculateLaunchReadiness/SETUP-GUIDE.md`](../../plugins/CalculateLaunchReadiness/SETUP-GUIDE.md) | Build / register / verify walkthrough. |
| [`scripts/register_custom_action.py`](../../scripts/register_custom_action.py) | Idempotent Web API deployer — assembly + plugin type + Custom API + properties + step + solution components. |
| [`scripts/check_solution_components.py`](../../scripts/check_solution_components.py) | Verifies all four component types are in the LaunchControl solution. |
| [`connectors/README.md`](../../connectors/README.md) | BYO MCP connector overview + registration steps. |
| [`connectors/learn-mcp/`](../../connectors/learn-mcp/) | paconn definition for Microsoft Learn MCP (no auth). |
| [`connectors/github-mcp/`](../../connectors/github-mcp/) | paconn definition for GitHub MCP (PAT auth). |
| [`episodes/ep-05-custom-tools/preflight.py`](../../episodes/ep-05-custom-tools/preflight.py) | Two-mode test harness — `--plan` emits markdown, `--run` executes 3 pre-flight + 3 tests. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# --- Part 1: Custom Action ---
# 1. Build the plugin (.NET Framework 4.6.2)
dotnet build plugins/CalculateLaunchReadiness/CalculateLaunchReadiness --configuration Release

# 2. Register assembly + plugin type + Custom API + solution components
python scripts/register_custom_action.py

# 3. Smoke test
python episodes/ep-05-custom-tools/preflight.py --run

# --- Part 2: BYO MCP connectors ---
pip install paconn
paconn login                              # device-code

cd connectors/learn-mcp
copy settings.example.json settings.json  # edit: paste your env GUID
paconn create --settings settings.json

cd ../github-mcp
copy settings.example.json settings.json  # edit: paste env GUID + PAT bootstrapping
paconn create --settings settings.json

# Re-run the harness — P3 + T3 should now report >=2 connectors
python episodes/ep-05-custom-tools/preflight.py --run
```

---

## Pitfalls collected during the build

These are the gotchas that ate real time the first time through. The setup
guide and registration script handle them automatically on the second pass,
but they're useful to mention in the recording:

- **`assembly is already registered`** — `register_custom_action.py` is
  idempotent; on re-run it does an `UPDATE` on the existing
  `pluginassembly`, then re-creates the plugin step against the existing
  type. Don't manually delete the assembly between runs.
- **Custom API request property name vs. Input parameter name** — Dataverse
  exposes the property's `UniqueName`, but the plugin reads from
  `context.InputParameters[<UniqueName>]`. Mismatch and the plugin gets
  null. We use `lc_LaunchName` everywhere.
- **Response properties have to be defined as `customapiresponseproperty`
  rows _after_ the Custom API is created.** Defining them in the
  `customapi` create payload silently does nothing. The script creates them
  in a second pass.
- **Solution membership** — registering a plugin and creating a Custom API
  doesn't put either in any solution. You need explicit
  `AddSolutionComponent` calls (componenttype 91 = plugin assembly,
  90 = plugin type, 79 = custom API, 81/80 = response/request property).
- **Plugin field names in the response** — they are
  `lc_ReadinessScore` (decimal), `lc_ReadinessSummary` (multi-line string),
  and `lc_Verdict` (string). _Not_ `lc_Score` or `lc_Summary`. The test
  harness was wrong about this on first write; the env corrected us.
- **paconn settings.json is environment-specific** — it has the
  `environmentGuid` and (for github-mcp) the connector-id assigned by the
  framework on first registration. Both are gitignored.
  `settings.example.json` is the template.
- **paconn-registered connectors carry the publisher prefix `cr88d_`**
  (the Power Platform default for ad-hoc registrations), not your custom
  prefix `lc_`. Names are URL-encoded too (`5F` for `_`, `20` for space).
  When filtering connectors programmatically, search by substring of the
  connector display name (`mcp`, `learn`), not by prefix. _For production,
  register the connector inside a solution context (`paconn create --solution`
  or via the maker portal under your solution) so it picks up the
  `LaunchControl` publisher prefix and exports cleanly._
- **Custom API names in the solution-component API** — use the GUID, not
  the unique name, in the `AddSolutionComponent` call. Easy to mix up.
- **`lc_launches` vs `lc_launchs`** — same auto-pluralization gotcha as
  Episode 4. The plugin uses the entity logical name (`lc_launch`), not the
  set name; the test harness uses the set name (`lc_launchs`) when
  iterating launches via OData.

Each of these turned into a 15–30 minute detour the first time. With the
registration script + test harness, the second time is two commands.
