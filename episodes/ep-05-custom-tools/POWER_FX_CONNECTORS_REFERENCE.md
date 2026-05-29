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

`scripts/deploy_fx_with_connector.py` provisions the connection + connection reference and PATCHes the Fx body to call MSN Weather. Last invocation (against `Q3 Widget Launch`):

```json
{
  "lc_ReadinessScore": 100,
  "lc_Verdict": "GO",
  "lc_ReadinessSummary": "Q3 Widget Launch: 16 milestone(s); Redmond is 51F (feels 55F)"
}
```

The `Redmond is 51F` portion came from `lc_msnweather.CurrentWeather("Redmond, WA", "Imperial")` — a live HTTPS call out of the Fx runtime through the MSN Weather connector. This **disproves** the common claim that Dataverse server-side logic is sandboxed from outbound HTTPS: when routed through a connector, Power Fx Functions can call any HTTPS API the connector exposes (including custom connectors that wrap arbitrary REST endpoints).

The simpler Dataverse-only variant lives in `scripts/deploy_fx_function.py` — preflight 8/8 verified with both bodies.
