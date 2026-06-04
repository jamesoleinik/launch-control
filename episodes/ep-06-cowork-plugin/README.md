# Episode 6 — Cowork Plugin for Dataverse

**Status:** 🚧 In development · 🎬 Not yet recorded
**Features:** ⭐ Microsoft 365 Cowork custom plugin · ⭐ Dataverse MCP Server · ⭐ Teams Developer Portal OAuth registration · ⭐ Schema-aware Business Skill
**Layer:** 🟣 Layer 3 expands (the conversational surface — Microsoft 365 Cowork / Copilot chat)
**Coding agent:** GitHub Copilot + Teams Developer Portal + M365 Admin Center
**Runtime:** Microsoft 365 Cowork / Copilot chat + Dataverse MCP Server (`/api/mcp`)

---

## The hook

> _"We already taught agents how to talk to Launch Control. Now we put that
> conversation where the launch team already works — inside Microsoft 365
> Cowork and Copilot chat."_

Episodes 1–5 built the substrate: the unified `lc_*` model, staging
promotion, virtual entities, server-side guardrails, custom actions, and
MCP connectors. Episode 6 is the reach layer: a **Teams
custom plugin** that lets Cowork connect directly to the Dataverse MCP server
for the Launch Control environment. (Role boundaries follow in Episode 8.)

The important part is not another chat UI. It is this:

```text
Cowork / Copilot chat
  → custom Teams plugin package
  → OAuthPluginVault
  → https://<org>.crm.dynamics.com/api/mcp
  → Launch Control Dataverse data, governed by the signed-in user
```

Same data. Same security. Same business skills. New front door.

---

## The narrative beat

The opening question is deliberately plain:

```text
User → "What is blocking Q3 Widget Launch, and should we slip?"
```

Without schema guidance, Cowork can get lost: lookup columns, logical names,
choice values, and relationship names are not intuitive to a human and they
are not always obvious to the model. The two MVP findings that shape this
episode are blunt:

- Authentication and packaging take too much effort to get right the first
  time.
- Lookup handling is fragile unless the plugin is paired with a full
  schema-aware skill.

So the episode has two payoffs:

1. **The plugin connects.** Cowork can discover and call the Dataverse MCP
   server from inside Microsoft 365.
2. **The answers are Launch Control answers.** A Business Skill tells the
   model which tables, columns, lookups, status fields, and rules matter.

```text
Cowork → Dataverse MCP → lc_launch / lc_milestone / lc_task
       → Business Skill: status columns, lookups, readiness rules
       ← "NO-GO. Security review and CDN provisioning are blocked.
          Per the escalation policy, a one-week slip requires Director approval."
```

---

## Part 1 · The eight-step setup recipe

> This is the part that needs to be boring, repeatable, and recorded clearly.

The canonical setup sequence from the Cowork + Dataverse MCP findings:

| # | Step | Recording beat |
|---|---|---|
| 1 | **Create Entra app registration** | Capture Tenant ID, Client ID, Client Secret expiry, Dynamics CRM permission, admin consent. |
| 2 | **Configure Power Platform environment** | Enable Dataverse MCP client access and add an Allowed MCP Client where Application ID = Entra Client ID. Capture the Dataverse org URL. |
| 3 | **Create OAuth registration in Teams Developer Portal** | Base URL = Dataverse org URL. Auth/token endpoints use the tenant. Scope = `{DataverseOrgUrl}/.default offline_access`. Copy the OAuth Registration ID. |
| 4 | **Build the plugin package** | Set MCP server URL to `{DataverseOrgUrl}/api/mcp`, auth vault to `OAuthPluginVault`, and `referenceId` to the OAuth Registration ID. |
| 5 | **Deploy plugin** | Upload the custom app package in M365 Admin Center, publish to a small test audience, add it in Cowork, click **Connect**. |
| 6 | **Create schema-aware Business Skill** | Teach Cowork the `lc_*` logical names, key columns, lookups, status fields, and rules. This is the quality unlock. |
| 7 | **Run real-world test** | Ask about known records, related tables, lookup relationships, status reports, and readiness. Validate with a user who has real Dataverse permissions. |
| 8 | **Post-validation hardening** | Restrict the Teams Developer OAuth registration from **Any Teams app** to the deployed plugin's Teams App ID. |

The episode is intentionally honest about the plumbing: most failed demos are
not model failures. They are ID, URL, scope, permission, or stale deployment
failures.

---

## Part 2 · The plugin package

> One package, one MCP endpoint, one OAuth binding.

The Cowork plugin package is the Teams/M365 wrapper around the Dataverse MCP
endpoint. The three values that matter on camera:

```text
mcpServerUrl = https://<org>.crm.dynamics.com/api/mcp
auth vault   = OAuthPluginVault
referenceId  = <Teams Developer Portal OAuth Registration ID>
```

The `referenceId` is the easiest thing to get wrong. It is **not** the Entra
Client ID. The Entra Client ID goes into the Power Platform Allowed MCP Client
record. The plugin action uses the **OAuth Registration ID** from Teams
Developer Portal.

This mirrors the Episode 5 connector story, but with a different surface:

- Episode 5 registered remote MCP servers as Power Platform custom connectors
  in [`connectors/`](../../connectors/).
- Episode 6 registers the Dataverse MCP server as a Cowork custom plugin so
  users can talk to Launch Control inside Microsoft 365 chat.

---

## Part 3 · The schema-aware Business Skill

> The plugin connects the pipe. The skill makes the answer correct.

The skill should live with the rest of the runtime instructions in
[`business-skills/`](../../business-skills/). It needs the same shape as the
existing skills, but optimized for Cowork + Dataverse MCP:

- Tables: `lc_launch`, `lc_milestone`, `lc_task`, `lc_teammember`,
  `lc_statusupdate`, plus `lc_githubissue` from Episode 4 where relevant.
- Key display columns: `lc_name` for launches/milestones, `lc_title` for
  tasks.
- Lookup columns: launch → milestones → tasks, task → GitHub issue, status
  updates → launch/task.
- Status fields: `lc_launchstatus`, `lc_milestonestatus`, `lc_taskstatus`,
  `lc_isblocked`, `lc_blockerreason`.
- Rules: readiness comes from `lc_CalculateLaunchReadiness`; status changes
  follow [`status-transition-rules.md`](../../business-skills/status-transition-rules.md);
  escalation follows [`escalation-policy.md`](../../business-skills/escalation-policy.md).

This is where Josh Cook's lookup finding becomes actionable: do not make the
user say logical names. Put the schema in the skill so Cowork can translate
normal launch questions into the right MCP calls.

---

## Part 4 · Governance and hardening

> Custom plugins need the same governance story as pre-built plugins.

Rafsan Huseynov's feedback is the guardrail beat: pre-built plugins are easy
to manage and remove; custom plugins can accumulate versions, stale packages,
and unclear ownership if teams do not govern them.

So the hardening checklist is part of the episode, not an appendix:

- Restrict the Teams OAuth registration to the deployed plugin's Teams App ID
  after validation.
- Increment plugin version on every re-upload; do not rely on Cowork picking
  up stale packages.
- Publish first to a small audience, then widen.
- Track which users, domains, prompts, and outputs use the plugin.
- Keep domain-specific packages separate: HR, finance, healthcare, and Launch
  Control should not share one opaque plugin.
- Respect Dataverse permissions and add Purview / sensitivity guardrails for
  highly confidential data.

---

## Local validation

[`preflight.py`](preflight.py) is the read-only recording gate:

```powershell
# from launch-control/
python episodes/ep-06-cowork-plugin/preflight.py --plan
python episodes/ep-06-cowork-plugin/preflight.py --run
```

What it checks:

| # | Check | Validates |
|---|---|---|
| P1 | `.env` + `DATAVERSE_URL` + `scripts/auth.py` | Local repo can authenticate the same way every episode does |
| P2 | Cowork schema-aware Business Skill in `business-skills/` | Step 6 exists before filming |
| P3 | Cowork plugin package files are present | Manifest/action/package scaffold exists, even if still stubbed |
| P4 | Plugin action points at `/api/mcp` and uses `OAuthPluginVault` | The package is wired to the Dataverse MCP pattern |
| T1 | `WhoAmI` via `scripts/auth.py` | Dataverse connectivity works |
| T2 | Core `lc_*` table metadata exists | Cowork has real Launch Control schema to query |
| T3 | `lc_CalculateLaunchReadiness` exists | The readiness tool from Episode 5 is available |

The harness does not deploy, mutate Dataverse, upload packages, or call Cowork
itself. It proves the substrate is recording-ready, then the in-product chat
is validated manually.

---

## What you see on screen

1. **Hook** — Cowork chat in Teams: _"What is blocking Q3 Widget Launch, and
   should we slip?"_
2. **MCP endpoint** — Power Platform environment settings: Dataverse MCP
   client access enabled; Allowed MCP Client row shows the Entra Client ID.
3. **OAuth registration** — Teams Developer Portal: Dataverse base URL,
   tenant auth/token endpoints, scope = `/.default offline_access`, copy the
   OAuth Registration ID.
4. **Plugin package** — VS Code: highlight `/api/mcp`, `OAuthPluginVault`, and
   `referenceId`.
5. **Deploy** — M365 Admin Center: upload custom app, publish to yourself,
   open Cowork, add plugin, Connect.
6. **Business Skill** — VS Code: schema-aware skill in `business-skills/`,
   highlighting logical names, lookups, and status fields.
7. **Real test** — Cowork answers a readiness/status question over known
   records and related tables.
8. **Preflight** — `python episodes/ep-06-cowork-plugin/preflight.py --run`
   shows the repo and Dataverse substrate are ready.
9. **The punchline:**
   > _"The user sees a chat. The admin sees OAuth, app IDs, scopes, and
   > governance. The agent sees Dataverse MCP plus a schema skill. All three
   > have to be right."_

---

## Files in this episode

| File | Role |
|---|---|
| [`README.md`](README.md) | Episode spec, narrative, setup recipe, pitfalls, and file inventory. |
| [`recording-script.md`](recording-script.md) | Concrete shot list, voiceover, captions, and recording workflow. |
| [`preflight.py`](preflight.py) | Read-only local harness for repo files + Dataverse connectivity. |

## Related repo artifacts

| File/folder | Role |
|---|---|
| [`business-skills/`](../../business-skills/) | Existing schema/rule skills; Step 6 adds the Cowork-specific schema-aware skill here. |
| [`business-skills/launch-readiness-checklist.md`](../../business-skills/launch-readiness-checklist.md) | Readiness rule: always invoke `lc_CalculateLaunchReadiness`, never hand-tally. |
| [`business-skills/status-transition-rules.md`](../../business-skills/status-transition-rules.md) | Canonical status columns and allowed transitions. |
| [`business-skills/escalation-policy.md`](../../business-skills/escalation-policy.md) | Escalation routing for blocked launches and tasks. |
| [`connectors/`](../../connectors/) | Episode 5 BYO MCP connector pattern; useful contrast for the Cowork plugin package. |
| [`plugins/CalculateLaunchReadiness/`](../../plugins/CalculateLaunchReadiness/) | Custom API backend Cowork should use for readiness answers. |
| [`scripts/auth.py`](../../scripts/auth.py) | Shared Dataverse auth used by the preflight harness. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Confirm local substrate
python episodes/ep-06-cowork-plugin/preflight.py --plan
python episodes/ep-06-cowork-plugin/preflight.py --run

# 2. Complete tenant-side setup manually
# - Entra app registration
# - Power Platform Allowed MCP Client
# - Teams Developer Portal OAuth registration
# - Cowork plugin package build
# - M365 Admin Center upload + limited publish
# - Cowork Connect

# 3. Manual Cowork prompt
# What is blocking Q3 Widget Launch, and should we slip?
```

---

## Pitfalls collected from the MVP findings

- **Client ID vs OAuth Registration ID** — Power Platform uses the Entra
  Client ID in the Allowed MCP Client row. The plugin `referenceId` uses the
  Teams Developer Portal OAuth Registration ID. Mixing them breaks auth.
- **Wrong MCP URL** — the endpoint is the Dataverse org URL plus `/api/mcp`.
  Missing the suffix means no MCP server.
- **Wrong scope** — use `{DataverseOrgUrl}/.default offline_access`, not a
  generic Graph scope.
- **Permission mismatch** — a successful OAuth prompt does not grant data the
  user cannot read in Dataverse. Test with a real launch user.
- **Stale deployment/session** — re-uploading the same version or testing in
  an old Cowork session can hide changes. Increment version, re-add, reconnect.
- **Lookup ambiguity** — Cowork needs schema help for lookup columns and
  relationship names. Put logical names and relationships in the Business
  Skill, not in the user's prompt.
- **Custom plugin sprawl** — old package versions accumulate. Keep ownership,
  domain, audience, and retirement documented before broad rollout.

---

## What this unlocks for the rest of the series

- The will-be-renumbered **Agent** episode can contrast Copilot Studio and
  Cowork: same Dataverse MCP server, different orchestration surface.
- The code-first agent can reuse the same schema-aware skill: the runtime
  changes, the business instructions do not.
- The finale gets one more surface in the orchestra: Launch Control from
  Microsoft 365 chat, governed by Dataverse and tenant admin controls.

---

## Next up

**Episode 9 — The Agent.** Cowork was the enterprise chat front door. Episode 9
moves the same Dataverse substrate into the **declarative** Launch Coordinator
in Copilot Studio — same `lc_*` model, same readiness Custom API, hosted
conversation surface.
