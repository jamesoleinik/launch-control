# Cowork \u2194 Dataverse MCP \u2014 plugin package

> ## \u26a0\ufe0f DEPRECATED \u2014 wrong manifest archetype
>
> This hand-rolled package used `copilotAgents.plugins[]` (and later
> `copilotAgents.declarativeAgents[]`) under the Teams **v1.19** schema.
> Neither shape is accepted by the **Copilot Agents & Connectors** deploy
> surface as of 2026-06. Uploads either fail validation outright (v0.1.x)
> or validate but leave **Next** greyed because the wizard recognizes the
> package as a Teams app, not a Copilot agent (v0.2.x).
>
> **Use the authoritative template instead:**
>
> ```powershell
> Expand-Archive ..\..\artifacts\dataverse-mcp.cowork-template.zip ..\..\tmp\cowork-template-extracted -Force
> python ..\..\tmp\cowork-template-extracted\render.py `
>   --template ..\..\tmp\cowork-template-extracted `
>   --values ..\..\artifacts\launchcontrol-cowork-values.json `
>   --out ..\cowork-dataverse-mcp-v2 `
>   --zip
> # produces ..\dataverse-launchcontrol.zip \u2014 upload that.
> ```
>
> The template uses the `vDevPreview` schema with `agentConnectors[]` +
> `agentSkills[]`, which is what Cowork's plugin picker actually surfaces.
>
> This folder is kept only for historical reference and the rendered
> `out/` artifacts from earlier attempts. Do not deploy from it.

---

Custom Microsoft 365 Cowork plugin that talks to the **Dataverse MCP server**
of the Launch Control environment. This is the artifact deployed in
**Episode 6 \u2014 Cowork Plugin for Dataverse**.

## What this package is

A Teams app package + a Copilot plugin descriptor:

| File | Role |
|---|---|
| `manifest.json` | Teams app manifest (Microsoft Teams v1.19). References `plugin-action.json` under `copilotAgents.plugins[]`. |
| `plugin-action.json` | Copilot plugin descriptor (v2.4 schema). Declares an `McpServer` runtime pointing at `{DATAVERSE_ORG_URL}/api/mcp` with `OAuthPluginVault` auth bound to `{TEAMS_OAUTH_REGISTRATION_ID}`. |
| `color.png`, `outline.png` | Required by the Teams manifest validator. Placeholder LC marks \u2014 swap for real brand icons before broad rollout. |
| `build.ps1` | One-command builder: substitutes placeholders, generates a fresh Teams App GUID, and zips everything into `out/launch-control-cowork-plugin.zip`. |

The package is intentionally tiny because the **server side** (Dataverse
MCP server) already exposes every table, lookup, and Custom API. The
package's job is just to (1) make the endpoint reachable from Cowork and
(2) bind the right OAuth registration.

## Three values you must substitute

Before zipping and uploading, replace the placeholders:

| Placeholder | Where it comes from |
|---|---|
| `{DATAVERSE_ORG_URL}` | The exact org URL of the Launch Control Dataverse environment, e.g. `https://org40ae6a46.crm.dynamics.com`. The MCP endpoint is this URL + `/api/mcp`. |
| `{TEAMS_OAUTH_REGISTRATION_ID}` | The **OAuth Registration ID** copied from **Teams Developer Portal \u2192 OAuth registrations** (NOT the Entra Client ID). |
| `manifest.json#id` | A fresh GUID per package version \u2014 generate with `python -c "import uuid; print(uuid.uuid4())"`. Re-using a GUID across versions makes Cowork serve stale packages. |

> The two IDs **most commonly mixed up** are the Entra Application (Client)
> ID and the Teams Developer Portal OAuth Registration ID. Power Platform's
> *Allowed MCP Client* row takes the **Entra Client ID**. This package's
> `referenceId` takes the **Teams OAuth Registration ID**. They are
> different IDs from different portals \u2014 see Episode 6 README \u00a7Pitfalls.

## Build + upload

One command does all the substitution + zipping. Sources stay templated;
output lands in `out/` (gitignored):

```powershell
cd plugins/cowork-dataverse-mcp
./build.ps1 `
    -DataverseUrl "https://<your-org>.crm.dynamics.com" `
    -OAuthRegistrationId "<Teams Dev Portal OAuth Registration ID>"
# Optional: -AppId <existing guid>   (default: fresh guid each build)
# Optional: -Version "0.1.1"         (default: 0.1.0)
```

That writes `out/launch-control-cowork-plugin.zip` containing the
substituted `manifest.json`, `plugin-action.json`, `declarative-agent.json`,
and both icons.

Then in **Microsoft 365 Admin Center → Copilot → Agents → All Agents → Add agent**,
upload `launch-control-cowork-plugin.zip`. Publish to a small test audience
first. Open Cowork, **Add plugin → Launch Control**, click **Connect**,
complete the OAuth flow. The plugin should now appear in the connected
list.

> **Don't use** *Integrated apps → Upload custom apps* — that surface is
> Teams-app-only as of 2026-06. Declarative-agent-bearing packages are
> funnelled through the new Copilot Agents & Connectors hub. The wizard
> silently greys out **Next** if you pick the wrong path.

## Verify

Run the episode's preflight from the repo root:

```powershell
python episodes/ep-06-cowork-plugin/preflight.py --run
```

Checks P3 + P4 inspect this directory for `manifest.json`, an action JSON,
and the three required markers (`/api/mcp`, `OAuthPluginVault`,
`referenceId`).

## Hardening (post-validation)

In **Teams Developer Portal \u2192 OAuth registrations \u2192 \u003cyour registration\u003e \u2192
App restrictions**, change *Any Teams app* to **the specific Teams App ID**
from `manifest.json#id`. That restricts which custom plugin packages can
use this OAuth registration; it's the difference between "anyone in tenant
can build a plugin reusing this OAuth" and "only the published Launch
Control package can".

## Iconography

`color.png` (192x192) and `outline.png` (32x32) ship as placeholder LC
marks so the Teams validator accepts the package out of the box. Replace
both before promoting beyond a test audience.
