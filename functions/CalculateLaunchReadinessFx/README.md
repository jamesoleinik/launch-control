# CalculateLaunchReadinessFx — the Power Fx twin

This is the **Functions in Dataverse** (Power Fx, preview) implementation of
the readiness score. Same Custom API contract as the .NET plugin in
[`plugins/CalculateLaunchReadiness/`](../../plugins/CalculateLaunchReadiness/),
plus one extra response field (`lc_NotifiedAt`) and one platform capability
the plugin cannot reach: **first-party Power Platform connectors**.

## What it does that the plug-in doesn't

The .NET sandbox plug-in **can** make outbound HTTPS calls (ports 80/443) —
that's been supported for years (see [Access external web
services](https://learn.microsoft.com/power-apps/developer/data-platform/access-web-services)).
What the plug-in **cannot** do is invoke a Power Platform connector:

| | .NET plugin (Part 1) | Power Fx Function (Part 2) |
|---|---|---|
| Custom API name | `lc_CalculateLaunchReadiness` | `lc_CalculateLaunchReadinessFx` |
| Build step | `dotnet build` | None (formula is the source) |
| Outbound HTTPS | ✅ (ports 80/443 only) | ✅ (via connectors) |
| **Power Platform connectors** | ❌ no connection framework | ✅ connection references + DLP |
| Tracing | `ITracingService` | `Trace()` (limited) |
| Production status (May 2026) | GA | Preview |
| Source format | `.cs` + `.csproj` | `formula.fx` + `function.json` |

This Fx body posts an adaptive readiness card to the launch's Teams
channel via the first-party `MicrosoftTeams.PostMessageToChannelV3`
connector action, then returns `lc_NotifiedAt` so the caller can persist
when the notification went out.

## Files

| File | Purpose |
|---|---|
| `function.json` | Custom API contract (1 request param, 4 response props) |
| `formula.fx` | The Power Fx body that executes server-side |
| `README.md` | This file — narrative + the Copilot-for-Power-Fx prompt used to author it |

## The Copilot-for-Power-Fx prompt (verbatim)

> _"Author a Power Fx Function for Dataverse named
> `lc_CalculateLaunchReadinessFx`. Accept a string parameter `LaunchName`.
> Look up the `lc_launch` by name; if none, return Score=0, Verdict='NO-GO',
> Summary='Launch not found', NotifiedAt=Blank. Otherwise, invoke the
> existing Custom API `lc_CalculateLaunchReadiness` for a baseline
> score/verdict/summary. If the launch has both `lc_TeamsTeamId` and
> `lc_TeamsChannelId`, post an HTML message to that Teams channel via the
> first-party MicrosoftTeams connector with the launch name, verdict,
> score, and summary. Return the baseline plus `lc_NotifiedAt = Now()`
> when posted, Blank otherwise."_

Copilot wrote `formula.fx` end-to-end. The only manual edit was extracting
the local-variable `posted` out of the response record so the `Now()`
call wasn't re-evaluated.

## Register in your own environment

```powershell
# 1. One-time per env: opt the env into Functions in Dataverse preview
pac admin update-org-feature --feature LowCodePluginsEnabled --value true

# 2. Make sure a Microsoft Teams connection reference exists (`shared_teams`)
#    in the LaunchControl solution. Standard first-party connector — created
#    in the maker portal under Connections > New > Microsoft Teams.

# 3. Pack and import as part of the LaunchControl solution
pac solution add-component --solution-name LaunchControl `
    --component-type 10038 --component-id lc_CalculateLaunchReadinessFx
pac solution pack --folder solutions/LaunchControl --zipfile LaunchControl.zip
pac solution import --path LaunchControl.zip
```

## Why this exists alongside the .NET plugin

The point of this episode is **two implementations of one contract**.
Whether an agent calls `lc_CalculateLaunchReadiness` or
`lc_CalculateLaunchReadinessFx`, it gets the same readiness fields back.
The Fx twin adds a side-effect (the channel post) that the plug-in
*cannot* do — not because of HTTPS restrictions, but because plug-ins
have no access to the platform's connector framework, DLP enforcement,
or per-environment connection references.

Pick the implementation that fits your team:

- **.NET plugin** — production-supported runtime, no governance side-effects,
  ideal for pure compute the agent calls hundreds of times per minute.
- **Power Fx Function** — preview runtime, one expression to reach any of
  1,000+ first-party connectors, ideal when the readiness calculation should
  trigger downstream notifications, approvals, or workflow.

The agent doesn't care which one runs. That's the whole point.
