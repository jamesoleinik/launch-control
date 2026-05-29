# CalculateLaunchReadiness — Setup Guide

The plugin behind the `lc_CalculateLaunchReadiness` Custom API.
Three commands, end-to-end. The Python deployer is fully idempotent — safe
to re-run.

> Episode context: [`episodes/ep-05-custom-tools/README.md`](../../episodes/ep-05-custom-tools/README.md).

## What this ships

| Asset | Where it lives |
|---|---|
| Plugin source | [`CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs`](CalculateLaunchReadiness/CalculateLaunchReadinessPlugin.cs) |
| Project file (.NET Framework 4.6.2, strong-named) | [`CalculateLaunchReadiness/CalculateLaunchReadiness.csproj`](CalculateLaunchReadiness/CalculateLaunchReadiness.csproj) |
| Strong-name key | [`CalculateLaunchReadiness/key.snk`](CalculateLaunchReadiness/CalculateLaunchReadiness/key.snk) |
| Deployer | [`../../scripts/register_custom_action.py`](../../scripts/register_custom_action.py) |
| Solution-membership verifier | [`../../scripts/check_solution_components.py`](../../scripts/check_solution_components.py) |
| Test harness | [`../../episodes/ep-05-custom-tools/preflight.py`](../../episodes/ep-05-custom-tools/preflight.py) |

The Custom API surface (created by the deployer):

- **Message:** `lc_CalculateLaunchReadiness` (Global, Sync, Public)
- **Request parameter (1):** `lc_LaunchName` (String, required)
- **Response properties (3):** `lc_ReadinessScore` (Int), `lc_ReadinessSummary` (String), `lc_Verdict` (String)
- **Plugin type bound:** `CalculateLaunchReadiness.CalculateLaunchReadinessPlugin`
- **Solution:** `LaunchControl` (componenttype 10038 = CustomAPI; `AddRequiredComponents=true` pulls in request/response props + plugin type + assembly)

## Prerequisites

- .NET Framework 4.6.2 developer pack (the plugin assembly must target 4.6.2 for the Sandbox to load it)
- Python 3.11+
- `pip install azure-identity` (transitive via [`scripts/auth.py`](../../scripts/auth.py))
- `az login` against the same tenant as your Dataverse environment
- `.env` at repo root with `DATAVERSE_URL=https://yourorg.crm.dynamics.com`

## Build

```powershell
dotnet build plugins/CalculateLaunchReadiness/CalculateLaunchReadiness --configuration Release
```

Output: `plugins/CalculateLaunchReadiness/CalculateLaunchReadiness/bin/Release/net462/CalculateLaunchReadiness.dll`.

## Register

```powershell
python scripts/register_custom_action.py
```

Idempotent six-step deploy:

1. **Upload assembly** — `pluginassemblies` POST with base64 DLL. If an
   assembly with the same name already exists, `PATCH` the new bytes in.
2. **Register plugin type** — `plugintypes` POST bound to the assembly.
3. **Create Custom API** — `customapis` POST with `bindingtype=0` (Global),
   `isfunction=false`, `allowedcustomprocessingsteptype=0` (sync only),
   `PluginTypeId@odata.bind` pointing at the plugin type. The
   `MSCRM.SolutionName: LaunchControl` request header places it directly in
   the LaunchControl solution on first create.
4. **Request parameter** — one `customapirequestparameters` row for
   `lc_LaunchName` (type 10 = String, required).
5. **Response properties** — three `customapiresponseproperties` rows
   (`lc_ReadinessScore`, `lc_ReadinessSummary`, `lc_Verdict`). These must
   be created _after_ the Custom API exists; declaring them inline on
   create is silently ignored.
6. **Solution membership** — explicit `AddSolutionComponent` for the
   CustomAPI with `AddRequiredComponents=true` so the assembly, plugin
   type, request parameter, and response properties all land in the
   LaunchControl solution. Re-runs are safe — the call no-ops if it's
   already a member.

## Verify

```powershell
# Solution membership only (fast)
python scripts/check_solution_components.py

# Full preflight: registration + solution + smoke + verdict matrix + connectors
python episodes/ep-05-custom-tools/preflight.py --run
```

A successful preflight prints `6/6 passing` and writes a timestamped
`test_results_<ts>.md` next to the harness (gitignored).

## Invoke

```http
POST {DATAVERSE_URL}/api/data/v9.2/lc_CalculateLaunchReadiness
Content-Type: application/json
{ "lc_LaunchName": "Q3 Widget Launch" }
```

```json
{
  "lc_ReadinessScore":   38.8,
  "lc_Verdict":          "NO-GO",
  "lc_ReadinessSummary": "Launch: Q3 Widget Launch\nMilestones evaluated: 16\n…"
}
```

## Pitfalls

- **Custom API request property name vs. plugin input** — the plugin reads
  `context.InputParameters["lc_LaunchName"]` by `UniqueName`. Rename the
  parameter and the plugin gets `null`.
- **Response props need their own POST** — defining them in the `customapis`
  create body silently does nothing. The deployer creates them in step 5.
- **Solution-component IDs are GUIDs** — `AddSolutionComponent` takes the
  CustomAPI GUID, not the unique name.
- **Re-deploys** — re-running `register_custom_action.py` PATCHes the
  assembly bytes onto the existing `pluginassembly` row. Don't manually
  delete the assembly between runs — you'll orphan the plugin type and
  break the binding.
- **Auto-pluralization** — the unbound entity name in the plugin is
  `lc_launch` (logical). When iterating launches over OData (e.g. in the
  preflight verdict matrix), use the entity-set name `lc_launchs`.
