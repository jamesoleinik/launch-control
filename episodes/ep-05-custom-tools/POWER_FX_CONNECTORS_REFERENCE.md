# Power Fx Functions in Dataverse — Connector Reference

Captured from:
- https://learn.microsoft.com/en-us/power-apps/maker/data-platform/low-code-plug-ins?tabs=instant#using-connector-actions-in-low-code-plug-ins
- https://learn.microsoft.com/en-us/power-apps/maker/data-platform/lowcode-plug-ins-examples#sample-instant-plug-in-with-msn-weather-connector

> **Note**: Microsoft has renamed "low-code plug-ins" → **Functions in Dataverse**. The connector usage docs still live under the legacy low-code-plug-ins URL but the syntax applies unchanged.

## TL;DR

A Dataverse Function **can** call Power Platform connector actions from Power Fx — including custom connectors that wrap arbitrary HTTPS APIs. This means the often-repeated "Dataverse plugins can't make HTTP calls" rule **does not apply** to Fx Functions when routed through a connector.

## Syntax

```
new_<ConnectorRef>.<ActionName>(arg1, arg2, ...)
```

- `new_<ConnectorRef>` is the **connection reference internal logical name** (prefix + name), NOT the display name.
- Use `With()` to capture the entire response and pluck nested properties:

```powerfx
With({ c: new_MsnWeather.CurrentWeather(Location, "Imperial").responses.weather.current },
    { Out: "Current temp: " & c.temp & " degrees. Feels like " & c.feels & " degrees." })
```

## Prerequisites (per-environment)

1. The connector must be **allowed** by DLP in the environment.
2. A **connection** to the connector must exist.
3. A **connection reference** wrapping that connection must exist in the environment.

## Wiring at the fxexpression level

In the `fxexpression.context` JSON, the `ConnectionReferences` array must include the connection-reference logical name(s):

```json
{
  "Tables": ["lc_launch"],
  "CustomApis": [],
  "ConnectionReferences": ["new_MsnWeather"],
  "TabularConnectionReferences": [],
  "ActionConnectorConnectionReferences": []
}
```

Without declaring the ref in `ConnectionReferences`, the Fx body will not compile.

## What is NOT supported

- **Dataverse connector** must not be used. Use native `Filter/LookUp/Patch/Collect/Set` against table logical names (declared in `context.Tables`).
- "Not all connector actions are supported at this time" — per Microsoft. Test individual actions.

## Permissions

Connector access inside a function can be restricted with security roles (create/read/update/delete privileges on the connection reference).

## Tested in this repo — VERIFIED ✅

Two production scripts, both end-to-end idempotent:

### MSN Weather (no-auth connector)

`scripts/deploy_fx_with_connector.py` — proves outbound HTTPS works:

```json
{
  "lc_ReadinessScore": 100,
  "lc_Verdict": "GO",
  "lc_ReadinessSummary": "Q3 Widget Launch: 16 milestone(s); Redmond is 51F (feels 55F)"
}
```

### Microsoft Teams (OAuth connector, real side effect)

`scripts/deploy_fx_with_teams.py` — proves first-party OAuth connectors work and a real Teams message lands every invoke:

```json
{
  "lc_ReadinessScore": 100,
  "lc_Verdict": "GO",
  "lc_ReadinessSummary": "Q3 Widget Launch: 16 milestone(s); posted to Teams id=1780081213991"
}
```

Verified call shape (PostMessageToChannelV3):

```powerfx
lc_teams.PostMessageToChannelV3(
    groupId,                                  // Team groupId (GUID)
    channelId,                                // "19:...@thread.tacv2"
    { content: "<message html>", contentType: "html" }   // FLAT record, not nested
)
```

> **Gotcha — flat records only.** The connector swagger nests `body.content` and `body.contentType` under a `body` object, but Power Fx low-code-plugin binding **does not support nested records**. Passing `{ body: { content, contentType } }` returns `"Missing property content, object is too complex or not supported"`. Pass the leaves directly.

> **Gotcha — positional args ≠ Power Apps canvas.** In Power Apps canvas, this action is called as `MicrosoftTeams.PostMessageToChannelV3("Flow bot", "Channel", ...)` with synthesized "post-as" / "post-in" dropdown args. **Inside Fx Functions, those synthetic args do not exist** — args bind to swagger path parameters in order: `(groupId, channelId, body-record)`. Compile will accept anything string-typed for the first two positions, but at runtime they go on the wire as groupId/channelId and the post will 404 if you pass the wrong thing.

Both Dataverse-only and Teams-connector bodies are interchangeable on the `lc_calculatelaunchreadinessfx` Fx Function — preflight 8/8 with either deployed.

