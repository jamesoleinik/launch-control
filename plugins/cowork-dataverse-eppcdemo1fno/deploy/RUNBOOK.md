# Runbook: Dataverse EPPCDemo1FnO Cowork plugin (preview MCP)

## Provision (scriptable)

```powershell
cd plugins/cowork-dataverse-eppcdemo1fno/deploy
python provision.py
```

`provision.py` creates, for the EPPCDemo1FnO environment (https://eppcdemo1fno.crm.dynamics.com):

- a unique Entra app `Cowork-EPPCDemo1FnO-MCP` with Dynamics CRM
  `user_impersonation` (delegated), the Teams platform redirect URI, and a
  1-year secret;
- a Dataverse application user with System Administrator (demo-grade);
- an `allowedmcpclients` row for the new app;
- a Teams Developer Portal OAuth registration via `atk`, printing the base64
  `referenceId`.

Secrets are written only to `.deploy/cowork-eppcdemo1fno/<timestamp>.json` and
`deploy/env/.env.dev.user`, both gitignored, and never printed.

## Wire + build

Paste the printed `referenceId` into `manifest.json`
(`agentConnectors[0].toolSource.remoteMcpServer.authorization.referenceId`),
then:

```powershell
cd plugins/cowork-dataverse-eppcdemo1fno
.\build.ps1 -OAuthReferenceId "<referenceId>"
```

## Portal-only steps

1. Enable env-level Dataverse MCP for EPPCDemo1FnO in Power Platform admin
   center, then re-run `provision.py` so the built-in `microsoftcowork` row is
   enabled.
2. Grant consent (admin consent for the Entra app, or per-user at Connect).
3. Upload `out/dataverse-eppcdemo1fno-cowork.zip` in M365 Admin Center and publish.
4. Connect the plugin in Cowork and test the schema, data, and policy prompts.
5. Harden: restrict the OAuth registration to this Teams App id; tighten the
   app-user role from System Administrator to least privilege.
