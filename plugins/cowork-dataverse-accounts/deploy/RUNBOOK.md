# Runbook: Dataverse Accounts Cowork plugin (portal-only steps)

The scriptable Part 1 (`deploy/deploy.py`) is done. This runbook covers the
steps that have no public API and must be done in a portal, plus the
hardening pass. Work top to bottom.

## Provisioned artifacts (this environment)

| Item | Value |
|---|---|
| Tenant ID | `01eed126-9f96-4d2d-a127-dc2e786a898b` |
| Dataverse URL | `https://org77c9659c.crm.dynamics.com` |
| Environment ID | `5af9d25e-9d3c-ea33-83a7-e8001dfa6508` |
| Entra app (client) ID | `d037e0d1-c923-4bcb-9b66-547423399d76` |
| Service principal ID | `6b81a17b-8c69-4e9d-a57b-dd829962aec6` |
| Dataverse app user (systemuserid) | `bf39fde0-ec6c-f111-ab0d-00224805aa76` |
| Allowed MCP client row | `new_coworkaccountsmcp` (id `8297b1fb-ec6c-f111-ab0d-70a8a5b1e115`) |
| Teams Dev Portal OAuth config ID | `8d95fc56-8524-4f41-9dde-cece82045517` |
| OAuth referenceId (in manifest) | `<oauth-reference-id>` |
| Teams App ID (manifest `id`) | `d8fb9683-1383-4f69-8c27-f56094fe41d5` |
| Package zip | `plugins/cowork-dataverse-accounts/out/dataverse-accounts-cowork.zip` |

The signed-in identity used for the deploy was
`jamesol@agent365003.onmicrosoft.com` (tenant `01eed126...`). The Cowork
sign-in at Step 3 can be any user who has a Dataverse security role with read
on the `account` table in this environment.

---

## Step 0 (prerequisite): enable Dataverse MCP at the environment level

The deploy reported the built-in `microsoftcowork` allowed-MCP-client row was
**not found**. That usually means the environment-level Dataverse MCP (preview)
feature is not enabled yet, and Cowork cannot call `/api/mcp` until it is.

1. Open Power Platform admin center: https://admin.powerplatform.microsoft.com
2. Environments -> select the environment with URL
   `https://org77c9659c.crm.dynamics.com` (Environment ID
   `5af9d25e-9d3c-ea33-83a7-e8001dfa6508`).
3. Settings -> Product -> Features (or the Copilot / AI hub area, depending on
   the current portal layout) -> turn on **Dataverse MCP** / **Model Context
   Protocol** client access.
4. Re-run the allowlist toggle so both the built-in Cowork row and the custom
   client row are enabled:

   ```powershell
   cd plugins/cowork-dataverse-accounts/deploy
   python deploy.py
   ```

   The script is idempotent; it will reuse the existing Entra app, app user,
   and OAuth registration and only flip the allowlist rows.

If the portal already shows Dataverse MCP enabled, the custom client row
(`new_coworkaccountsmcp`) created by the deploy is sufficient and you can move
on.

---

## Step 1: grant API consent

> DONE (2026-06-20): admin consent was granted for app
> `d037e0d1-c923-4bcb-9b66-547423399d76`. The Dataverse `user_impersonation`
> delegated permission is consented tenant-wide (`consentType=AllPrincipals`).
> No action needed unless the app's permissions change.

Admin consent during the deploy **failed** because the signed-in account is not
a Privileged Role Admin / Global Admin. Pick one path:

- **Admin consent (preferred):** have a tenant admin run

  ```powershell
  az ad app permission admin-consent --id d037e0d1-c923-4bcb-9b66-547423399d76
  ```

  or, in Entra admin center, open app `Cowork-Accounts-MCP` -> API permissions
  -> "Grant admin consent for <tenant>".

- **Per-user consent:** if the tenant allows user consent for the Dynamics CRM
  API, the user can simply consent during the Cowork Connect prompt at Step 3.
  If Connect fails with a consent error, fall back to admin consent above.

---

## Step 2: upload and publish the package

1. Open M365 admin center: https://admin.microsoft.com
2. Copilot -> Agents & connectors (the new Copilot agents hub). If you only see
   Settings -> Integrated apps -> Upload custom apps, that path also works for
   custom agent packages.
3. Upload `plugins/cowork-dataverse-accounts/out/dataverse-accounts-cowork.zip`.
4. Publish to a **small test audience first** (for example, just yourself).
   Deployment can take a few minutes to propagate.

---

## Step 3: connect in Cowork

1. Open Microsoft 365 Copilot Cowork chat.
2. Add the plugin **Dataverse Accounts**.
3. Click **Connect** and complete the OAuth sign-in as a user who has Dataverse
   read access to `account` in this environment.
4. A successful sign-in does not bypass Dataverse security. It signs the user
   in; their security role still decides which account rows return.

---

## Step 4: test "list my accounts"

Run these in Cowork:

```text
List my accounts
```
```text
How many accounts do I own?
```
```text
Find accounts in Seattle
```
```text
Show the 10 most recently created accounts
```

Expected: the plugin calls the Dataverse MCP server, returns a compact table of
real `account` rows the user can see, and never invents accounts. If the user
owns no accounts, it should say so rather than returning everyone's.

> Note: at provisioning time this environment had **0 account rows**. If "list
> my accounts" returns nothing, seed a few accounts first (Step 5).

---

## Step 5 (optional): seed sample accounts for the demo

If the environment is empty, create a handful of accounts owned by the demo
user so the prompts return data. Minimal Web API example (run as a user who can
create accounts):

```powershell
$tok = az account get-access-token --resource https://org77c9659c.crm.dynamics.com --query accessToken -o tsv
$h = @{ Authorization = "Bearer $tok"; "Content-Type" = "application/json" }
"Contoso Ltd|Seattle","Fabrikam Inc|Redmond","Adventure Works|Bellevue" | ForEach-Object {
  $n,$c = $_.Split("|")
  $body = @{ name = $n; address1_city = $c } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "https://org77c9659c.crm.dynamics.com/api/data/v9.2/accounts" -Headers $h -Body $body | Out-Null
}
```

Accounts created this way are owned by the calling user. To have them owned by a
specific demo user for "list **my** accounts", sign in as that user when
creating them, or reassign ownership in the app.

---

## Step 6: harden

1. **Restrict the OAuth registration.** Teams Developer Portal
   (https://dev.teams.microsoft.com) -> Tools -> OAuth client registration ->
   open `Cowork-Accounts-OAuth` (config id `8d95fc56-8524-4f41-9dde-cece82045517`)
   -> change applicability from "Any Teams app" to the specific Teams App ID
   `d8fb9683-1383-4f69-8c27-f56094fe41d5`. (The deploy re-run path also does
   this automatically via `oauth/update` with `applicableToApps: SpecificApp`.)
2. **Tighten the Dataverse app user role.** The app user was assigned
   `System Administrator` for a friction-free first run. For anything beyond a
   demo, replace it with a custom security role that grants only read on
   `account` (and any related tables you expose).

---

## Re-uploads and re-runs

- Cowork caches packages. After any manifest change, bump `version` in
  `manifest.json` (and the `id` GUID if behavior still does not change), rebuild
  with `build.ps1 -OAuthReferenceId <ref>`, re-upload, and remove + re-add the
  plugin in Cowork.
- `deploy/deploy.py` is idempotent and re-runnable. On a re-run it reuses the
  existing Entra app and OAuth config and resyncs the registration via
  `oauth/update`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Connect fails with a consent error | Delegated permission not consented | Run admin consent (Step 1) |
| "MCP server unavailable" | Env-level Dataverse MCP off, or app not in allowlist | Step 0; confirm `new_coworkaccountsmcp` row is enabled |
| Connect succeeds but no data | User lacks Dataverse read on `account` | Grant a role with read on `account` |
| AADSTS50011 redirect error | Missing Teams platform Web redirect URI | The deploy set it; confirm on the Entra app if it was changed |
| Behavior unchanged after re-upload | Cached package | Bump `version` (and `id`), re-upload, re-add in Cowork |
