# Building Episode 13 — Step-by-Step

This is the off-camera build guide for the **Launch Control MCP** declarative
agent. Run through it once before you record. The on-camera narrative is in
[`../recording-script.md`](../recording-script.md); this file is the boring
plumbing.

> **Outcome:** A declarative agent published to your tenant's Microsoft 365
> Copilot, talking to the live Dataverse MCP server (Ep 1) over OAuth, calling
> `lc_CalculateLaunchReadiness` (Ep 5) and reading the same `lc_*` tables we
> built in Ep 1, with the agent surfacing answers — and ideally inline UI —
> inside Copilot chat.

---

## 0. Prerequisites

- Microsoft 365 tenant with a Dataverse environment from earlier episodes
  (`org<id>.crm.dynamics.com`).
- **Microsoft 365 Agents Toolkit** extension installed in VS Code.
  https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.ms-teams-vscode-extension
- Node.js LTS (the toolkit uses it for packaging).
- Azure CLI authenticated to the same tenant (`az login`) — used by the
  toolkit's `aadApp/*` actions.
- Dataverse CLI authenticated (`dataverse auth create --environment
  https://<org>.crm.dynamics.com/`) — used for the off-camera verification
  in step 6.
- Tenant role: ability to side-load custom apps (App Studio role or
  equivalent) and ability to grant tenant admin consent on the new Entra
  app reg (or a global admin who can do it for you).

## 1. Open the project

```powershell
cd episodes\_ep-13-copilot-mcp-app\declarative-agent
code .
```

VS Code → **Microsoft 365 Agents Toolkit** sidebar should detect the
project from `m365agents.yml`.

## 2. Fill in `env\.env.dev`

Open `env\.env.dev` and set:

```env
DATAVERSE_HOST=<your-org>.crm.dynamics.com
```

Leave everything else blank — the toolkit fills it during `provision`.

## 3. Drop in icons

The toolkit will fail to package without them. Replace the two README
placeholders:

```
appPackage\color.png       (192x192 PNG)
appPackage\outline.png     (32x32 transparent PNG, white line art)
```

If you want to skip making icons, copy the ones from
`..\..\..\agents\launch-coordinator\` if they exist, or any 192x192 /
32x32 PNGs you have around.

## 4. Provision

In the toolkit sidebar: **Lifecycle → Provision**. This:

1. Creates a Teams app registration → writes `TEAMS_APP_ID`.
2. Creates an Entra app registration (`LaunchControlMcp-dev`) → writes
   `AAD_APP_CLIENT_ID` + writes the client secret to `env\.env.dev.user`.
3. Adds the Copilot OAuth redirect URIs (`teams.microsoft.com`,
   `copilot.microsoft.com`, `m365.cloud.microsoft`) from
   `aad.manifest.json`.
4. Registers an OAuth authorization for the MCP plugin →
   `OAUTH_REGISTRATION_ID` (this is what the action's `reference_id`
   binds to at runtime).
5. Zips the app package, validates it, and uploads to your tenant's
   Teams App Catalog.

## 5. Grant tenant admin consent (one-time)

The new Entra app reg needs tenant-level admin consent before Copilot can
call the MCP server through it. Open this URL in a browser as a tenant
admin (replace tenant id and client id from `env\.env.dev`):

```
https://login.microsoftonline.com/<AAD_APP_TENANT_ID>/adminconsent?client_id=<AAD_APP_CLIENT_ID>
```

Click **Accept**.

## 6. Add the client ID to the environment's MCP allowed list (one-time)

Power Platform Admin Center → **Environments** → your environment →
**Settings** → **Product** → **Features** → scroll to **MCP Server**:

1. Toggle **Enable MCP Server** to **On** (if it isn't already from Ep 1).
2. Under **Allowed clients**, click **Add client**.
3. Paste the `AAD_APP_CLIENT_ID` from `env\.env.dev`.
4. Save.

Verify the MCP server is reachable as that client:

```powershell
# From the repo root, with a dataverse auth profile active:
dataverse mcp list-tools --environment https://<your-org>.crm.dynamics.com/
```

You should see the Dataverse MCP tool list (records, business skills,
`lc_CalculateLaunchReadiness`). If you get a 403, the allowlist hasn't
propagated yet — wait 2-3 minutes and retry.

## 7. Publish to Microsoft 365 Copilot

Toolkit sidebar: **Lifecycle → Publish**. The agent goes through the org
app-catalog publish flow. As a tenant admin, approve the submission in
**Microsoft 365 Admin Center → Integrated apps → Manage apps**.

(For the on-camera demo you can skip the full publish and use
**Preview & Customize → Preview in Copilot** instead — it side-loads the
agent for the current user only, no admin approval needed.)

## 8. Verify in Microsoft 365 Copilot

Open https://m365.cloud.microsoft/chat. The **Agents** rail should now
show **Launch Control**. Click it. Try a conversation starter:

> What's the readiness for Q3 Widget Launch?

The agent should:

1. Authenticate to Dataverse over OAuth (a one-time consent prompt for the
   first user — they grant access to *the agent's* Entra app reg, not their
   user identity).
2. Discover the MCP tool list.
3. Call the `lc_CalculateLaunchReadiness` tool.
4. Render the verdict. If the MCP server returns `meta`-tagged UI payloads,
   the verdict shows as an inline card with the score and per-milestone
   breakdown. Otherwise it shows as text.

## 9. (Recording day) Side-load the agent for clean demos

To avoid org-catalog approval lag on recording day:

```powershell
# Re-zip after any tweak:
.\scripts\package-agent.ps1
```

…then in M365 Copilot → **More agents** → **Build an agent** →
**Upload custom agent** → choose `appPackage\build\appPackage.dev.zip`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `AADSTS65001 consent required` when invoking a tool | Re-run step 5 (tenant admin consent) — the user-level consent dialog does not cover the MCP scope. |
| `403 ServerRejectedClient` from `/api/mcp` | Step 6 didn't take — verify the client ID is in **Allowed clients** and the **MCP Server** toggle is on. |
| Tool list comes back empty | Check the OAuth registration scope is `https://<your-org>.crm.dynamics.com/.default`. The Dataverse-specific `user_impersonation` scope alone won't expose MCP tools. |
| Agent answers from "training data" instead of calling the action | Re-validate the action's `description_for_model` field — make sure it explicitly says "all record reads/writes go through this server." Also confirm `run_for_functions: ["*"]` is present. |
| Icons fail validation | The two icons MUST be exactly 192x192 and 32x32. The toolkit's validator is strict. |
| `m365agents.yml` schema errors | Re-open with toolkit, choose **Run wizard** to regenerate — the toolkit owns this file. |

## Files this agent depends on (cross-episode)

| Dep | Episode | Notes |
|---|---|---|
| Dataverse MCP server (`/api/mcp`) | Ep 1 | The endpoint this whole episode hangs on. |
| `lc_launch` / `lc_milestone` / `lc_task` / `lc_teammember` / `lc_statusupdate` / `lc_githubissue` | Ep 1, Ep 4 | Tables the agent reads. |
| `lc_CalculateLaunchReadiness` Custom API | Ep 5 | The hero tool. |
| `lc_knowledgearticle` + Business Skills | Ep 2 | Reached as MCP knowledge tool. |
| GitHub virtual entity | Ep 4 | Used by the Escalation Policy skill. |
| Tenant admin consent for the new Entra app reg | this episode | One-time per tenant. |
| PPAC MCP Server allowed clients entry | this episode | One-time per environment. |
