# Episode 6 — Cowork Plugin for Dataverse: Recording Script

**Target length:** 4–6 minutes
**Format:** LinkedIn short-form technical demo
**Audience:** Dataverse / Power Platform builders, M365 admins, technical PMs
**Core promise:** Cowork can converse with Launch Control data through the Dataverse MCP server when the plugin package, OAuth registration, and schema skill are all aligned.

---

## Cold open

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 0:00 | Cowork chat | Show prompt already typed: `What is blocking Q3 Widget Launch, and should we slip?` | "We have Launch Control in Dataverse. Now we want the launch team to ask about it where they already work — Microsoft 365 Cowork and Copilot chat." |
| 0:08 | Architecture card | Show `Cowork → Teams custom plugin → OAuthPluginVault → Dataverse MCP → lc_* tables` | "The chat is simple. The plumbing is not. A custom plugin has to authenticate, reach the Dataverse MCP endpoint, and understand the Launch Control schema." |
| 0:18 | Title card | `Episode 6 — Cowork Plugin for Dataverse` | "This episode is the Cowork front door." |

---

## Shot list

### 1. Establish the substrate

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 0:25 | VS Code | Open `episodes/ep-06-cowork-plugin/README.md`, scroll to the eight-step recipe. | "The MVP findings came down to a repeatable eight-step setup. Most failures are not AI failures. They are ID, URL, scope, permission, or stale package failures." |
| 0:38 | Terminal | Run `python episodes/ep-06-cowork-plugin/preflight.py --plan`. | "Before recording, I run a read-only preflight. It checks that the repo and Dataverse substrate are ready before I touch Cowork on camera." |

### 2. Entra app registration

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 0:50 | Azure portal | Show app registration overview. Blur secrets. Highlight Tenant ID and Application / Client ID. | "Step one is the Entra app registration. Capture the tenant and client ID, add Dynamics CRM permissions, create a client secret, and grant admin consent." |
| 1:05 | Azure portal | Show API permissions: Dynamics CRM delegated permission. | "This is the identity Cowork will use to request a Dataverse token through the Teams OAuth registration." |

### 3. Power Platform MCP client allowlist

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 1:15 | Power Platform admin center | Open environment settings for the Launch Control Dataverse environment. | "Step two is the Power Platform side. Enable Dataverse MCP client access for the environment." |
| 1:25 | PPAC settings | Show Allowed MCP Client row. Highlight Application ID. | "The Allowed MCP Client row uses the Entra Application ID. This is one of the easy mix-ups: this is not the Teams OAuth registration ID." |
| 1:37 | Browser address bar / settings | Highlight org URL: `https://<org>.crm.dynamics.com`. | "Also copy the exact Dataverse org URL. The plugin endpoint will be this URL plus `/api/mcp_preview`." |

### 4. Teams Developer Portal OAuth registration

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 1:48 | Teams Developer Portal | Open OAuth registrations. | "Step three is the Teams Developer Portal OAuth registration." |
| 1:55 | OAuth detail | Highlight Base URL = Dataverse org URL. | "The base URL is the Dataverse org URL, not Graph and not a placeholder." |
| 2:05 | OAuth detail | Highlight auth endpoint, token endpoint, client ID, secret. | "The auth and token endpoints use the tenant. The client ID and secret come from Entra." |
| 2:16 | OAuth detail | Highlight scope: `{DataverseOrgUrl}/.default offline_access`. | "The scope is Dataverse dot-default plus offline_access. A generic Graph scope will authenticate the wrong resource." |
| 2:27 | OAuth detail | Highlight OAuth Registration ID. | "Copy this OAuth Registration ID. The plugin action references this value — not the Entra client ID." |

### 5. Plugin package wiring

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 2:38 | VS Code | Open plugin package files under the local Cowork package folder. | "Step four is the custom plugin package." |
| 2:44 | VS Code | Highlight `mcpServerUrl` or URL value ending in `/api/mcp_preview`. | "The MCP server URL must end in `/api/mcp_preview` (note the underscore). Missing that suffix or using the GA `/api/mcp` shape is a common failure." |
| 2:52 | VS Code | Highlight auth block: `OAuthPluginVault`. | "The auth type uses OAuthPluginVault so Cowork can bind to the Teams OAuth registration." |
| 3:00 | VS Code | Highlight `referenceId`. | "The reference ID is the Teams Developer Portal OAuth Registration ID. That is the second big ID mix-up." |

### 6. Deploy and connect

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 3:12 | M365 Admin Center | Upload the custom app package. | "Step five is deployment. Upload the package in M365 Admin Center and publish it to a small test audience first." |
| 3:24 | Cowork / Copilot chat | Add plugin, click Connect, complete OAuth consent. | "In Cowork, add the plugin and connect. A successful OAuth flow does not bypass Dataverse security — it signs in the user." |
| 3:37 | Cowork plugin list | Show plugin connected. | "Now Cowork can call the Dataverse MCP server as that user." |

### 7. Schema-aware Business Skill

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 3:45 | VS Code | Open `business-skills/` and the Cowork schema skill. | "Step six is the quality unlock: a schema-aware Business Skill." |
| 3:52 | VS Code | Highlight `lc_launch`, `lc_milestone`, `lc_task`, lookups, status fields. | "Cowork should not ask the user for logical names. The skill teaches tables, relationships, lookup fields, status values, and where readiness comes from." |
| 4:05 | VS Code | Highlight references to readiness and status rules. | "For Launch Control, readiness is sourced from the `lc_risksummary` AI prompt column on `lc_launch` — status changes follow the business skill rules. The model should not hand-tally gates." |

### 8. Real-world test

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 4:18 | Cowork chat | Ask: `What is blocking Q3 Widget Launch, and should we slip?` | "Now the real test: ask a launch question, not a table question." |
| 4:30 | Cowork answer | Show answer referencing blocked tasks, readiness, and escalation. | "The answer should combine live Dataverse status with the Launch Control rules. If the user cannot read the rows, Cowork should not invent them." |
| 4:45 | Cowork chat | Ask follow-up: `Which milestone owns the blocker?` | "Follow-up questions prove the plugin can traverse relationships, not just retrieve one row." |

### 9. Hardening close

| Time | Shot | On-screen action | Narration |
|---:|---|---|---|
| 4:58 | Teams Developer Portal | Show OAuth registration app restrictions. | "After validation, harden the OAuth registration. Restrict it from 'any Teams app' to the deployed plugin's Teams App ID." |
| 5:08 | README pitfalls | Show pitfalls list. | "The checklist is the governance story: correct IDs, correct URL, correct scope, correct permissions, fresh deployment, and a schema skill." |
| 5:20 | Terminal | Run `python episodes/ep-06-cowork-plugin/preflight.py --run`. | "The preflight stays read-only. It proves the repo, package, skill, auth, and tables are ready for the next take." |
| 5:35 | Closing card | Show architecture again. | "The user sees a chat. The admin sees OAuth, app IDs, scopes, and governance. The agent sees Dataverse MCP plus a schema skill. All three have to be right." |

---

## Narration beats to keep

- "The chat is simple. The plumbing is not."
- "Most failed demos are ID, URL, scope, permission, or stale deployment failures."
- "Power Platform gets the Entra Client ID. The plugin action gets the Teams OAuth Registration ID. Do not mix them."
- "The endpoint is the Dataverse org URL plus `/api/mcp_preview`."
- "A successful OAuth prompt does not grant data the user cannot read in Dataverse."
- "The plugin connects the pipe. The Business Skill makes the answer correct."
- "Do not make users speak logical names. Put the schema in the skill."
- "After validation, restrict the OAuth registration to the deployed plugin's Teams App ID."

---

## Demo prompts

Use known seeded Launch Control records so the output is deterministic.

### Smoke prompt

```text
What launch records can you see?
```

Expected:

- Cowork calls Dataverse MCP.
- Response names real `lc_launch` rows.
- No made-up launch names.

### Main prompt

```text
What is blocking Q3 Widget Launch, and should we slip?
```

Expected:

- Cowork queries `lc_launch`, related `lc_task` / `lc_milestone`, and readiness.
- Answer identifies blocked work, owner or milestone, and current launch posture.
- Answer cites or applies escalation guidance rather than improvising policy.

### Relationship prompt

```text
Which milestone owns the blocker, and who should follow up?
```

Expected:

- Cowork follows lookup relationships.
- Answer uses Launch Control team member or owner data if available.
- If owner data is missing, answer says so.

### Negative prompt

```text
What is the launch budget?
```

Expected:

- Cowork says the Launch Control schema does not expose budget information.
- No invented dollars, no invented spreadsheet.

---

## B-roll checklist

- `episodes/ep-06-cowork-plugin/README.md`
- `episodes/ep-06-cowork-plugin/preflight.py --plan`
- Power Platform environment Dataverse MCP client settings
- Allowed MCP Client row with Entra Application ID
- Teams Developer Portal OAuth registration
- Plugin package file showing `/api/mcp_preview`
- M365 Admin Center custom app upload
- Cowork plugin Connect flow
- Cowork answer over Launch Control records
- `business-skills/` schema-aware skill
- Hardening: restrict OAuth registration to Teams App ID

---

## Lower-third captions

| Moment | Caption |
|---|---|
| Cold open | `Cowork → custom plugin → Dataverse MCP → Launch Control` |
| PPAC allowlist | `Allowed MCP Client = Entra Application ID` |
| Teams OAuth | `Plugin referenceId = Teams OAuth Registration ID` |
| Package wiring | `MCP URL = Dataverse org URL + /api/mcp_preview` |
| Skill | `Schema-aware Business Skill = better lookup handling` |
| Test | `Same Dataverse permissions. New conversational front door.` |
| Hardening | `After validation: restrict OAuth to the deployed Teams App ID` |

---

## Recording workflow

1. Run local preflight before opening portals:

   ```powershell
   python episodes/ep-06-cowork-plugin/preflight.py --run
   ```

2. Reset browser state:
   - Entra app open.
   - Power Platform environment settings open.
   - Teams Developer Portal OAuth registration open.
   - M365 Admin Center custom app upload page open.
   - Cowork chat open with plugin not yet connected, if possible.

3. Blur or avoid:
   - Client secret value.
   - Tenant details not needed for the demo.
   - User list / audit log personal data.
   - Any real customer launch data.

4. Keep the pointer on the three critical values:
   - Entra Client ID.
   - Dataverse org URL + `/api/mcp_preview`.
   - Teams OAuth Registration ID.

5. Reconnect Cowork after every package version change.

---

## Troubleshooting table for filming

| Symptom | Likely cause | Fix before next take |
|---|---|---|
| OAuth opens but token exchange fails | Wrong scope or wrong token endpoint | Use `{DataverseOrgUrl}/.default offline_access`; verify tenant endpoints |
| Plugin says MCP server unavailable | URL missing `/api/mcp_preview` or stale package | Fix package, increment version, re-upload, reconnect |
| Consent succeeds but no data returns | User lacks Dataverse permissions | Test as a user with Launch Control read access |
| Action never appears in Cowork | M365 Admin Center deployment not published to user | Publish to test audience, wait, re-add plugin |
| Cowork asks for table names | Missing or weak Business Skill | Add schema-aware skill with logical names and relationships |
| Answers use old package config | Stale deployment/session | Increment manifest version, upload again, remove/re-add plugin |
| Post-validation still allows any app | OAuth registration not hardened | Restrict registration to the deployed Teams App ID |

---

## End-card copy

```text
Episode 6: Cowork Plugin for Dataverse

A Teams custom plugin connects Microsoft 365 Cowork to the Dataverse MCP server.
The Business Skill makes the answers Launch Control-aware.
```

---

## TODO \u2014 LinkedIn post credits

When writing the LinkedIn post for this episode, **call out**:

- **Robert H. (Robert Hogner)** \u2014 his recent post tested the same custom Cowork \u2194 Dataverse MCP plugin against a destructive operation and showed the plugin strictly respects the signed-in user's Dataverse security roles (delete-on-PROD refused, no privilege escalation, no custom API layer needed). Mirrors our Part 4 governance beat and the "same Dataverse permissions, new conversational front door" punchline \u2014 worth quoting / linking.
- **Josh Cook** \u2014 author of the setup guide that made the eight-step recipe in Part 1 straightforward; the lookup-handling finding that shapes Part 3 (schema-aware Business Skill) is his. Robert's post already shouts him out; mirror it.

Suggested line: *"Credit to Josh Cook for the setup guide that turned all this plumbing into a repeatable recipe, and to Robert Hogner for stress-testing the security model on the same pattern."*
