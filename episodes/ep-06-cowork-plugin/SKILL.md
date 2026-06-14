---
name: ep-06-cowork-plugin
description: Follow Episode 6 of the Launch Control series end-to-end — register a Microsoft 365 Cowork custom plugin that talks to the built-in Dataverse MCP server for the Launch Control environment, paired with a schema-aware Business Skill. Use when the user asks to "do Episode 6", "build the Cowork plugin episode", "wire Cowork to Launch Control via MCP", or "set up the Cowork Dataverse plugin end-to-end".
---

# Skill: Episode 6 — Cowork Plugin for Dataverse (Prompt-driven)

This skill encodes Episode 6 of the Launch Control series as a sequence of
GitHub Copilot CLI prompts. **The plugin package, the Business Skill, and
the preflight harness in the repo are the *output* of these prompts, not
the input.** Re-running the prompts against a clean repo should regenerate
equivalent artifacts.

The episode produces three repo-side artifacts plus five tenant-side
configurations (Entra, Power Platform, Teams Developer Portal, M365 Admin
Center, Cowork). The repo artifacts:

| # | Artifact | Type |
|---|---|---|
| Part 6 | `business-skills/cowork-dataverse-mcp.md` | Schema-aware Business Skill |
| Part 4 | `plugins/cowork-dataverse-mcp/{manifest,plugin-action,README}.{json,md}` | Teams plugin package |
| Part 0 | `episodes/ep-06-cowork-plugin/preflight.py` | Read-only recording gate |

Tenant-side steps (Parts 1, 2, 3, 5, 8) are **manual on camera**. The skill
walks the producer through them — it does not script Entra or Teams
Developer Portal because both portals are interactive and policy-sensitive.

---

## Hard rules

1. **Default target is `Product Launch 2.0`** (env id
   `2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07`, URL
   `https://org40ae6a46.crm.dynamics.com`). Verify this against
   `DATAVERSE_URL` in `.env` and proceed silently if they match — do
   **not** stop to ask the user to confirm. Only halt if `.env`
   disagrees, in which case surface the mismatch and wait. Episode 6
   touches Entra, Power Platform, Teams Developer Portal, M365 Admin
   Center, and Cowork — all multi-tenant blast-radius, so a mismatch
   really is a stop-the-line event, but a match is not.
2. **Python only**, per the `dv-overview` skill. The plugin package is
   plain JSON; the preflight is Python. No Node, no PowerShell beyond
   simple file substitution.
3. **One Part at a time.** Run the prompt for Part N, verify, then move to
   N+1. Parts have ordering dependencies (Entra → PPAC → Teams Dev Portal
   → package → deploy → skill → test → harden).
4. **Never invent IDs.** When wiring the plugin package, the two GUIDs the
   user pastes are real values from real portals. Do not auto-generate
   them or guess.
5. **The Entra app MUST have `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect`
   as a Web redirect URI** — Teams Dev Portal OAuth callbacks there.
   Without it Cowork "Connect" fails with the generic *"Authentication is
   still processing"* toast and Entra returns `AADSTS50011`. `deploy.py`
   Phase A sets this via `az ad app update --web-redirect-uris`; never
   skip that step.
6. **After teardown + redeploy, force the Dev Portal OAuth row to resync.**
   `atk oauth/register` dedupes by `name` and silently returns the existing
   row with its old (now-deleted) clientId baked in. Sign-in then fails
   with `AADSTS700016: Application with identifier '<old appId>' was not
   found`. `deploy.py` Phase E handles this when `LC_OAUTH_CONFIG_ID` is
   already in `env/.env.dev`: it rewrites `m365agents.yml` in-memory to
   `oauth/update` with a bumped `name` so atk's diff routine PATCHes the
   row to the current clientId + secret. If you ever run `atk provision`
   outside `deploy.py` after a teardown, mirror the swap manually.

---

## The eight-step recipe (mirrors README §Part 1)

| # | Part | Surface | Output |
|---|---|---|---|
| 1 | Entra app registration | Azure portal | Tenant ID, Client ID, secret, Dynamics CRM permission, admin consent |
| 2 | Power Platform Allowed MCP Client | PPAC env settings | Dataverse MCP enabled; row with Entra Client ID |
| 3 | Teams Developer Portal OAuth registration | dev.teams.microsoft.com | OAuth Registration ID (NOT the Entra Client ID) |
| 4 | Plugin package | Repo: `plugins/cowork-dataverse-mcp-v2/` | manifest.json wired with `/api/mcp_preview` + `OAuthPluginVault` + the OAuth referenceId (base64 `<tenantId>##<oAuthConfigId>`) |
| 5 | Deploy + Connect | M365 Admin Center + Cowork | Plugin uploaded, published to a small audience, Connected in Cowork |
| 6 | Schema-aware Business Skill | Repo: `business-skills/cowork-dataverse-mcp.md` | Tables, lookups, status fields, readiness rule, escalation policy |
| 7 | Real-world test | Cowork chat | The four demo prompts in `recording-script.md#Demo prompts` |
| 8 | Hardening | Teams Developer Portal | Restrict OAuth registration from "Any Teams app" to the deployed Teams App ID |

---

## Prompts (for the coding agent)

### Part 0 — preflight + confirm

> *"Open `episodes/ep-06-cowork-plugin/README.md` and skim the eight-step
> recipe. Show me the `DATAVERSE_URL` from `.env` and ask me to confirm
> we're targeting the correct tenant before we touch any portal."*

### Part 1 — Entra app + app user + MCP allowlist + Dev Portal OAuth (scripted)

> *"Run the headless deploy for Part 1: Entra app**
> *`LaunchControl-Cowork-MCP` with `Dynamics CRM/user_impersonation`*
> *(delegated) and admin consent, a 12-month client secret, a*
> *Dataverse Application User in `Product Launch 2.0`*
> *(env id `2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07`,*
> *URL `https://org40ae6a46.crm.dynamics.com`) with the `System*
> *Administrator` role, the `allowedmcpclients` row enabled for the*
> *new appId via the Dataverse Web API, and the Teams Dev Portal OAuth*
> *registration via `atk provision` against `m365agents.yml`. Persist*
> *the secret to `.deploy/ep-06/<timestamp>.json` and*
> *`env/.env.dev.user` only — never print it. Print the resulting*
> *`referenceId` at the end. Do not ask me to confirm any of these*
> *defaults; they are authoritative for this episode."*

(All five inputs above are episode-level defaults — see
[`README.md` §Defaults](README.md#defaults-the-agent-should-not-ask-for-these).
Override only by editing the prompt explicitly.)

### Part 1 (legacy) — Entra app registration (on-camera, manual)

Kept for the manual recording path only. Skip when running the scripted
Part 1 above.

> *"Walk me through creating an Entra app registration named
> `LaunchControl-Cowork-Dataverse-MCP`. Capture Tenant ID and Client ID
> into a scratch buffer I can paste later. Add a delegated **Dynamics CRM**
> API permission. Generate a client secret with a 12-month expiry. Grant
> admin consent. Do NOT print or store the secret value — just confirm the
> expiry date."*

### Part 2 — Power Platform Allowed MCP Client (manual)

> *"In Power Platform admin center, open the Launch Control environment
> settings → AI hub → Dataverse MCP. Enable client access. Add an Allowed
> MCP Client whose Application ID is the Entra Client ID from Part 1.
> Confirm the exact Dataverse org URL on screen."*

### Part 3 — Teams Developer Portal OAuth registration (manual)

> *"In Teams Developer Portal → OAuth registrations, create a new
> registration named `LaunchControl-Dataverse-MCP`. Set Base URL =
> Dataverse org URL. Auth and token endpoints use the tenant. Scope =
> `{DataverseOrgUrl}/.default offline_access`. Client ID + secret come
> from the Entra app from Part 1. Copy the OAuth Registration ID — this
> is the value the plugin package uses."*

### Part 4 — Plugin package (repo work)

> *"Open `plugins/cowork-dataverse-mcp/`. In `manifest.json`, replace the
> placeholder `id` GUID with a freshly generated one. In
> `plugin-action.json`, substitute `{DATAVERSE_ORG_URL}` with the
> environment URL and `{TEAMS_OAUTH_REGISTRATION_ID}` with the value from
> Part 3. Then run the preflight (`python episodes/ep-06-cowork-plugin/preflight.py --run`)
> and confirm P3 + P4 are green."*

### Part 5 — Deploy + Connect (manual)

> *"Zip `manifest.json`, `plugin-action.json`, and the two icon PNGs into
> `launch-control-cowork-plugin.zip`. Upload it via M365 Admin Center →
> Integrated apps → Upload custom apps. Publish to a small test audience.
> Open Cowork, Add plugin → Launch Control, click Connect, complete the
> OAuth flow."*

### Part 6 — Schema-aware Business Skill (repo work)

> *"Open `business-skills/cowork-dataverse-mcp.md`. Walk through the
> tables, relationships, status fields, readiness rule, and escalation
> rule. This is the document Cowork loads to translate launch questions
> into MCP calls. If Cowork is misbehaving on a lookup, edit this file
> first — don't try to coach the model in the chat."*

### Part 7 — Real-world test (on-camera)

> *"From Cowork, run the four demo prompts in
> `episodes/ep-06-cowork-plugin/recording-script.md` §Demo prompts in
> order: smoke → main → relationship → negative. Validate each response
> against the success criteria in that section. If a response invents a
> column, stop and edit the Business Skill."*

### Part 8 — Hardening (manual)

> *"In Teams Developer Portal, open the OAuth registration from Part 3 →
> App restrictions. Change 'Any Teams app' to the Teams App ID from
> `manifest.json#id`. Save."*

---

## Verification

After Part 4 + Part 6, the preflight must be fully green:

```powershell
python episodes/ep-06-cowork-plugin/preflight.py --run
```

Expected: **6/6 passing** (P1–P4 + T1–T2).

After Part 5 + Part 7, validate in Cowork manually — there is no
programmatic test path because the chat surface is in M365 chat, not
exposed via an API the harness can call.

---

## Cleanup (for re-recording)

Most of Episode 6's footprint is **tenant-side**, not Dataverse-side, but
Phases A/B/D/E now have a scripted reverse. For a clean dry-run or
re-record:

```powershell
python episodes/ep-06-cowork-plugin/teardown.py
```

That script:

1. Deletes the Teams Dev Portal OAuth registration referenced by
   `env/.env.dev` `LC_OAUTH_CONFIG_ID` (Graph
   `DELETE /api/v1.0/oAuthConfigurations/{id}` via `atk` token), then
   clears the key so the next `deploy.py` re-registers fresh.
2. Removes the `LaunchControl-Cowork-MCP` row from
   `allowedmcpclients` (leaves `microsoftcowork` enabled).
3. Removes the Dataverse Application User (systemuser bound to the app).
4. Deletes the Entra app registration (and its service principal).
5. Wipes `env/.env.dev.user` and rotates `.deploy/ep-06/*` into
   `.deploy/ep-06/_archive/`.

Still manual (no public API):

- **Cowork** — Remove plugin from your Cowork chat (per-user).
- **M365 Admin Center → Copilot Agents & Connectors** — Delete the
  uploaded custom agent entry (per-tenant).

No Dataverse data needs to be wiped — Episode 6 is read-mostly on the
`lc_*` substrate and reuses Episode 1–5 artifacts unchanged.

The repo artifacts (`plugins/cowork-dataverse-mcp*/`,
`business-skills/cowork-dataverse-mcp.md`) **stay** between recordings —
they're the source-controlled outputs of the episode.

---

## Common failures (carry-overs from MVP)

- **"Cowork can't find any launches"** — Almost always the `_lc_launchid_value` vs
  `lc_LaunchId` casing mistake in the agent's `$expand`. The skill
  documents both shapes.
- **OAuth succeeds but no data** — Means the signed-in user lacks
  Dataverse access. OAuth is identity, not authorization. Run preflight
  T1 (`WhoAmI`) **as that user** to confirm.
- **Plugin re-upload didn't change behavior** — Cowork caches packages
  aggressively. Bump `manifest.json#version` AND `id` (new GUID) every
  re-upload, and reconnect the plugin in Cowork.
- **"Invalid client" on OAuth** — Mixed up Entra Client ID vs Teams OAuth
  Registration ID. Power Platform Allowed MCP Client = Entra Client ID;
  plugin `reference_id` = Teams OAuth Registration ID.
