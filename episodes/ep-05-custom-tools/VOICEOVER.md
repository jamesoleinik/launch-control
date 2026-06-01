# Episode 5 · Voiceover script + on-screen text overlays

Read in a calm, confident, mid-tempo cadence. Pauses marked `(beat)` are ~0.5 s; `(——)` is ~1.5 s while you let visuals breathe. Word counts target ~150 wpm so each section's runtime ≈ words ÷ 2.5 seconds.

Overlay convention:
- **TITLE** = full-screen card, ~3 s, animate in/out
- **LOWER-THIRD** = persistent name strip while you talk over a clip
- **CALL-OUT** = small annotation pointing at a specific UI element
- **CODE-CHYRON** = monospace chip in a corner showing the literal artifact name

---

## Cold open · 0:00 – 0:20

**VOICEOVER**

> Every Power Platform agent is only as good as the tools you give it. (beat) In this episode I'm building four custom tools for the same Dataverse environment — a .NET plug-in, a Power Fx twin, a REST connector, and an AI prompt — and wiring all four into one cloud flow you can press *Run* on. (——) All of it driven by GitHub Copilot CLI in the terminal. Zero clicks in the maker portal.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 0:00 | **TITLE** | `LaunchControl · Episode 5`<br>**Custom tools for Power Platform agents** |
| 0:06 | LOWER-THIRD | James Oleinik · Microsoft |
| 0:10 | CALL-OUT (overlaid on a 4-tile mosaic) | `.NET plug-in` · `Power Fx` · `Custom connector` · `AI Prompt` |
| 0:17 | CODE-CHYRON | `gh copilot · LaunchControl env` |

---

## Pre-flight · 0:20 – 0:45

**VOICEOVER**

> Quick frame before we start. (beat) The environment already has the launch-control data model from Episodes 1 through 4 — `lc_launch` and `lc_milestone` tables, the Q3 Widget Launch record, sixteen milestones, the LaunchControl solution. (beat) Copilot in this terminal has my `dv-overview`, `dv-data`, and `dv-solution` skills loaded, which means it already knows the Web API patterns, the solution name, the `lc_` prefix, and that `scripts/auth.py` handles tokens. (beat) Everything you're about to see is one natural-language prompt away.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 0:20 | **TITLE** | `Pre-flight` |
| 0:24 | CALL-OUT on terminal | `pac org who` → `org40ae6a46.crm.dynamics.com` |
| 0:32 | CALL-OUT on skills list | Skills loaded: **dv-overview · dv-data · dv-solution** |
| 0:40 | CODE-CHYRON | `scripts/auth.py` |

---

## Part 1 · .NET Custom API · 0:45 – 2:30

**VOICEOVER**

> Part one. The hard, deterministic, production-grade tool. (beat) I want a custom action called `lc_CalculateLaunchReadiness` that averages every milestone's status into a single score and returns a verdict — GO, CONDITIONAL, or NO-GO. Any blocked milestone forces NO-GO. (beat) Because I want per-milestone reasoning to come back in a tracing-service narrative, this one has to be a .NET sandbox plug-in — Power Fx doesn't have an `ITracingService` equivalent.
>
> (——)
>
> One prompt to Copilot CLI. It writes the C# plug-in, the csproj with the right .NET Framework 4.6.2 targeting pack, the registration script, and a setup guide alongside the code. (beat) I build it, register it, and call it from Python against Q3 Widget Launch.
>
> (——)
>
> Sixteen milestones evaluated. Score 38. Verdict NO-GO. (beat) And right there in `lc_ReadinessSummary` — three Complete, four In-Progress, two At-Risk, five Not-Started, two Blocked, plus the names of the blockers. (beat) That narrative is what makes the tool genuinely useful to an agent. It's not just a number — it's a number plus the reasoning behind it.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 0:45 | **TITLE** | `Part 1 · .NET Custom Action`<br>internal · transactional · server-side |
| 0:55 | CALL-OUT on rubric | `Complete 100 · InProgress 60 · AtRisk 50 · NotStarted 20 · Blocked 0` |
| 1:08 | CALL-OUT on verdict logic | `any Blocked → NO-GO` |
| 1:20 | CODE-CHYRON | `plugins/CalculateLaunchReadiness/` |
| 1:35 | CALL-OUT on csproj | `Microsoft.NETFramework.ReferenceAssemblies.Net462` |
| 1:50 | CALL-OUT on terminal | `dotnet build` → `register_custom_action.py` |
| 2:05 | CALL-OUT on JSON response | `lc_Verdict: "NO-GO"` |
| 2:15 | CALL-OUT on summary field | `ITracingService → lc_ReadinessSummary` |

---

## Part 2 · Power Fx twin + Teams · 2:30 – 4:15

**VOICEOVER**

> Part two. Same contract — different runtime. (beat) Dataverse Functions, formerly known as low-code plug-ins, let me write that same logic in Power Fx with no .NET assembly at all. (beat) And here's the part most pro-devs haven't seen: a Function can invoke any Power Platform connector as a Fx expression. (beat) So I'm going to take the baseline score from the .NET plug-in I just built, and have the Fx twin also post a verdict card to the launch's Teams channel using `MicrosoftTeams.PostMessageToChannelV3` — one line of Power Fx, first-party connector, platform-managed auth.
>
> (——)
>
> One prompt. Copilot writes the Fx body, the `function.json` contract, a deploy script that pre-flights the low-code plug-ins app and the Teams connection reference, and fails gracefully if either is missing instead of bombing out. (beat) I invoke it the same way I invoked the .NET one. Same JSON shape, plus a `lc_NotifiedAt` timestamp — and a card lands in Teams.
>
> (——)
>
> The takeaway: the .NET plug-in is the production path; the Fx twin is the connector-native path. Both ship as `lc_` Custom Actions. Any agent that can call one can call the other.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 2:30 | **TITLE** | `Part 2 · Power Fx Function`<br>low-code · connector-native |
| 2:42 | CALL-OUT | `Functions in Dataverse (preview)` |
| 2:55 | CODE-CHYRON | `MicrosoftTeams.PostMessageToChannelV3(...)` |
| 3:08 | CALL-OUT | preflight: low-code plug-ins app ✓ · `lc_teams` cref ✓ |
| 3:25 | CALL-OUT on JSON | `lc_NotifiedAt: 2026-06-01T06:…Z` |
| 3:40 | SPLIT-SCREEN LABEL | left: terminal · right: Teams channel |
| 3:55 | CALL-OUT on Teams card | `Verdict · NO-GO · sponsor: …` |
| 4:05 | CODE-CHYRON | `functions/CalculateLaunchReadinessFx/` |

---

## Part 3 · Custom connectors — REST + MCP · 4:15 – 6:30

**VOICEOVER**

> Part three. Any HTTPS endpoint becomes a first-class Power Platform tool through the same primitive — the custom connector — and the same primitive covers both REST and MCP servers. (beat) Same governance, same DLP, same Defender for Cloud Apps. The only thing that changes between substrates is one key in the Swagger.
>
> (——)
>
> I'm registering three connectors here. (beat) The GitHub Releases REST API, anonymous. (beat) The Microsoft Learn MCP server, anonymous. (beat) The GitHub MCP server, authenticated with a personal access token. (beat) And critically — I'm doing all three programmatically. No `paconn login`, no maker-portal clicks. One Python script reads any folder under `connectors/`, POSTs straight to the Dataverse Web API with the solution-unique-name header, and the connector shows up in the LaunchControl solution.
>
> (——)
>
> The line that does the work? `x-ms-agentic-protocol: mcp-streamable-1.0`. (beat) That single Swagger key tells the connector framework: this isn't REST, it's an MCP server — do tool discovery and streaming for me. (beat) Three runs of the same script. Three new tools available to every agent in this tenant.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 4:15 | **TITLE** | `Part 3 · Custom connectors`<br>REST + remote MCP · both programmatic |
| 4:25 | CALL-OUT | `no paconn · no portal clicks` |
| 4:40 | THREE-UP TILES | `github-releases-rest` · `learn-mcp` · `github-mcp` |
| 4:55 | CALL-OUT (highlight) | `x-ms-agentic-protocol: mcp-streamable-1.0` |
| 5:15 | CODE-CHYRON | `scripts/register_custom_connector.py` |
| 5:30 | CALL-OUT on terminal | `MSCRM.SolutionUniqueName: LaunchControl` |
| 5:50 | CALL-OUT on Dataverse | `connectors` table · componenttype 372 |
| 6:15 | CALL-OUT | `.connector-id` cache → re-runnable, idempotent |

---

## Part 4 · AI Prompt as a Custom Action · 6:30 – 8:15

**VOICEOVER**

> Part four. (beat) The first three substrates differ in *where the code runs*. This one differs in *how the code reasons*. (beat) When the sponsor asks for a three-sentence briefing in their voice, you don't want a weighted average. You want an LLM with the context.
>
> (——)
>
> Dataverse has had AI Prompts in the AI hub for a while and most pro-devs have never used them. (beat) Author a prompt with typed inputs, point it at a model, and it's automatically exposed as a runnable action — `Predict` on the prompt — governed by the same security and DLP as everything else in the solution.
>
> (——)
>
> One prompt to Copilot. It writes the AI Prompt definition with `LaunchName` and `MilestoneNarrative` as typed inputs, registers it into the LaunchControl solution, and publishes it. (beat) I call it. Three sentences of plain English in the sponsor's voice. Run it twice — the wording changes. (beat) That's the point. (——) Same Custom Action contract as Parts 1 and 2. The agent has no idea this one is an LLM.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 6:30 | **TITLE** | `Part 4 · Custom AI Function`<br>AI Prompt → Custom Action |
| 6:42 | LOWER-THIRD | `non-deterministic logic, same wire contract` |
| 6:55 | CALL-OUT | `AI hub → Prompts → lc_DraftLaunchBriefing` |
| 7:12 | CODE-CHYRON | `prompts/DraftLaunchBriefing/prompt.json` |
| 7:30 | CALL-OUT on inputs | `LaunchName · MilestoneNarrative` |
| 7:45 | CALL-OUT on response | `3 sentences · sponsor voice · paste to Teams` |
| 8:00 | CALL-OUT | run twice → wording changes ✓ |

---

## Part 5 · Test harness flow · 8:15 – 10:30

**VOICEOVER**

> Part five. The proof. (beat) One Power Automate flow. Four actions. One per substrate we just built. Press Run — see the responses side by side.
>
> (——)
>
> Manual trigger, one input — the launch name. (beat) Action one: `Perform an unbound action` on the .NET Custom API. Action two: same operation on the Fx twin. Action three: the GitHub Releases connector, owner and repo. Action four: Run a prompt on the AI Prompt. (beat) The flow itself is deployed programmatically — Copilot writes the workflow definition straight to the Dataverse `workflows` table, into the LaunchControl solution, with connection references for both the Dataverse connector and the GitHub one.
>
> (——)
>
> I open the maker-portal URL, bind the two connection references — one click each — save, and run with Q3 Widget Launch. (beat) In one screen: the .NET score, the Fx score plus the Teams timestamp, the latest GitHub release, and the three-sentence AI briefing. (——) Four substrates, one cloud flow, one uniform tool contract. (beat) That's the whole point of this episode.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 8:15 | **TITLE** | `Part 5 · Test harness flow`<br>one flow · four tools · one Run button |
| 8:25 | CALL-OUT | manual trigger · `LaunchName` |
| 8:40 | FOUR-UP TILES | `.NET CA` · `Fx CA` · `Custom connector` · `AI Prompt` |
| 8:58 | CODE-CHYRON | `scripts/create_test_harness_flow.py` |
| 9:15 | CALL-OUT on Dataverse | `workflows` table → `clientdata` JSON |
| 9:30 | CALL-OUT on portal | bind 2 connection references → Save |
| 9:50 | CALL-OUT on output JSON | `dotnet_readiness · fx_readiness · latest_release · ai_briefing` |
| 10:15 | LOWER-THIRD | four substrates · one contract |

---

## Close · 10:30 – 11:00

**VOICEOVER**

> So there it is. (beat) Four ways to host custom business logic on the Power Platform — .NET, Power Fx, custom connector, AI prompt — all governed identically, all callable identically, all built in one terminal session with one assistant. (beat) The agent layer is the easy part. The interesting work is at the tool layer. (——) Episode 6 next: role-based access control. (beat) Thanks for watching.

**ON-SCREEN OVERLAYS**

| t | Type | Text |
|---|---|---|
| 10:30 | **TITLE** | `Recap · Four substrates · One contract` |
| 10:42 | FOUR-UP TILES (matching cold open) | `.NET` · `Fx` · `Connector` · `AI Prompt` |
| 10:52 | **TITLE** | `Next · Episode 6 · RBAC` |
| 10:58 | END CARD | `github.com/jamesoleinik/launch-control` · subscribe |

---

## Editor's cheat sheet

- **Consistent code chyron position.** Bottom-right corner, monospace, mid-grey panel, ~70% opacity. Same font as the terminal.
- **Title cards** all use the same template — episode number top-left, part title centred, two-line subtitle below.
- **Per-part colour** for the four-up tiles (used in cold open, Part 5, and close):
  - `.NET` — deep teal
  - `Fx` — Power Fx purple
  - `Connector` — Power Platform blue
  - `AI Prompt` — Copilot magenta
- **Audio:** drop background bed by 6 dB under voiceover; come back up during the 1.5 s `(——)` pauses to let the room breathe.
- **B-roll suggestions** during the long voiceover passages:
  - Part 1 — close-up of the C# class scrolling, then the `lc_ReadinessSummary` JSON enlarging
  - Part 2 — split-screen of terminal output left, Teams channel right with the card animating in
  - Part 3 — three swagger files side-by-side, then a highlight zoom on `x-ms-agentic-protocol`
  - Part 4 — the AI hub Prompts page with `lc_DraftLaunchBriefing` highlighted, then the 3-sentence output rendering character-by-character
  - Part 5 — Power Automate run-history with the four actions all going green in sequence
