# Episode 6 — Cowork Plugin for Dataverse

**Status:** 🚧 In development · 🎬 Not yet recorded
**Features:** ⭐ Microsoft 365 Cowork custom plugin · ⭐ Dataverse MCP Server · ⭐ Teams Developer Portal OAuth registration · ⭐ Schema-aware Business Skill
**Layer:** 🟣 Layer 3 expands (the conversational surface — Microsoft 365 Cowork / Copilot chat)
**Coding agent:** GitHub Copilot + Teams Developer Portal + M365 Admin Center
**Runtime:** Microsoft 365 Cowork / Copilot chat + Dataverse MCP Server (`/api/mcp_preview`, 3-tool `search`/`describe`/`execute` surface)

> ⚠️ **Preview-only capability:** Invoking Dataverse custom APIs (e.g. our
> `lc_launchreadiness` action) through the MCP `execute` tool is a **Dataverse
> preview MCP** feature available **only on `/api/mcp_preview`**. It is **not
> yet rolled out to the GA `/api/mcp` endpoint**. The plugin and OAuth scope in
> this episode are intentionally pinned to the preview endpoint so the
> readiness-as-custom-API workflow keeps working; expect to repoint
> `mcpServerUrl` (and re-record results) when the capability ships to GA.

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
  → https://<org>.crm.dynamics.com/api/mcp_preview
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

> ⚠️ **How to read this episode.** Each Part below is a **prompt you type
> into GitHub Copilot CLI**. The plugin folders, manifest, skills, and
> deploy scripts in this repo are the *output* of those prompts — not the
> demo. Assume nothing under `plugins/cowork-dataverse-mcp-v2/`,
> `artifacts/dataverse-mcp.cowork-template.zip`, or `plugins/dataverse-launchcontrol.zip`
> exists at the moment recording starts. The point of the episode is that
> a single developer, with one CLI plus three portals, ships a working
> Cowork agent in one sitting.

---

## Part 1 · Create the admin registrations

> Tenant plumbing — now fully scriptable, but still highly privileged.

**🛠 Runs in:** GitHub Copilot CLI (coding agent in your terminal)

> ⚠️ **Heads-up — this Part runs with tenant-admin scope.** It mints an
> Entra app + client secret, grants `Dynamics CRM/user_impersonation`
> with admin consent, creates a Dataverse System Administrator app user,
> toggles the Dataverse MCP Allowed-Client list, and registers a
> Teams Dev Portal OAuth client. Each one is a low-frequency, high-blast-
> radius operation — record it once per environment, keep the output
> `.deploy/ep-06/<timestamp>.json` gitignored, and rotate the secret on
> schedule (see Part 1's `oauth/update` rotation block in `m365agents.yml`).

Most failed Cowork demos are not model failures — they are ID, URL, scope,
or permission failures. Through Episode 5 we treated the Teams Dev Portal
OAuth client registration as a click-through. **That is no longer true.**
The Microsoft 365 Agents Toolkit CLI (`atk`, the renamed Teams Toolkit
CLI) exposes the `oauth/register` driver, which calls the same Dev Portal
Graph endpoint (`POST /api/v1.0/oAuthConfigurations`) the portal UI uses.
A 19-line `m365agents.yml` + `atk provision` replaces the click-through
and returns the `oAuthConfigId` you put into `OAuthPluginVault.referenceId`.

So Part 1 is now: Entra app + redirects (Graph), Dataverse app user +
role (Web API), Power Platform allowed-client toggle (admin API), and
Teams Dev Portal OAuth registration (`atk provision`) — end-to-end
scripted, zero portal clicks.

### Defaults (the agent should NOT ask for these)

Every value Part 1 needs has a known good default — the prompt below
locks them in so the coding agent runs end-to-end without stopping for
confirmations. Override only if you are recording against a different
environment.

| Input | Default | Source |
|---|---|---|
| Power Platform environment | `Product Launch 2.0` (env id `2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07`, URL `https://org40ae6a46.crm.dynamics.com`) | `.env` `DATAVERSE_URL` |
| Entra app display name | `LaunchControl-Cowork-MCP` | [`deploy.py`](deploy.py) `APP_DISPLAY_NAME` |
| Dataverse security role | `System Administrator` (demo-grade; tighten before broad rollout) | [`deploy.py`](deploy.py) `SYSTEM_ADMINISTRATOR_ROLE` |
| Client secret handling | Write to `.deploy/ep-06/<timestamp>.json` (gitignored) and `env/.env.dev.user`; never echo to console | [`deploy.py`](deploy.py) `DEPLOY_DIR` |
| MCP allowlist mechanism | Dataverse Web API `allowedmcpclients` entity (no PPAC env-id needed) | [`deploy.py`](deploy.py) `phase_d_mcp_allowlist` |

### The prompt

> *Wire up the four pieces below so Cowork can call our Dataverse MCP*
> *server in the `Product Launch 2.0` environment*
> *(`https://org40ae6a46.crm.dynamics.com`, env id*
> *`2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07`) — no portal click-throughs.*
>
> - ***Entra app*** *via Graph, display name `LaunchControl-Cowork-MCP`.*
> - ***Dataverse app user*** *via the Web API, assigned `System Administrator`.*
> - ***Dataverse MCP allowlist*** *toggle via the `allowedmcpclients` Web API.*
> - ***Teams Dev Portal OAuth client registration*** *via the `atk` CLI's*
>   *`oauth/register` driver.*

(Copilot has `dv-overview`, `dv-data`, and `dv-security` loaded, so it
already knows the `LaunchControl` solution, `scripts/auth.py`, and the
App User creation + role assignment flow. All five defaults above are
authoritative — the agent should run straight through without asking
to confirm them.)

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Entra app + secret + Dataverse app user + role + allowedmcpclients + OAuth registration | [`episodes/ep-06-cowork-plugin/deploy.py`](deploy.py) |
| Dev Portal OAuth registration driver | [`episodes/ep-06-cowork-plugin/m365agents.yml`](m365agents.yml) (invoked by `deploy.py` Phase E via `atk provision`) |
| Standalone allowedmcpclients toggle (re-runnable) | [`episodes/ep-06-cowork-plugin/configure_mcp_allowlist.py`](configure_mcp_allowlist.py) |
| Teardown (reverse Phases A/B/D/E) | [`episodes/ep-06-cowork-plugin/teardown.py`](teardown.py) |
| Secret + IDs (gitignored) | `.deploy/ep-06/<timestamp>.json`, `env/.env.dev.user` |

### Reference example — the OAuth registration step

The new piece — Copilot writes a minimal `m365agents.yml`, drops the
clientSecret into `env/.env.dev.user`, and runs `atk provision`:

```yaml
# m365agents.yml
version: v1.11
environmentFolderPath: ./env
provision:
  - uses: oauth/register
    with:
      name: LaunchControl-Cowork-OAuth
      flow: authorizationCode
      appId: ${{TEAMS_APP_ID}}             # the Cowork plugin's teamsApp id
      clientId: ${{AAD_APP_CLIENT_ID}}     # LaunchControl-Cowork-MCP Entra app
      clientSecret: ${{SECRET_AAD_APP_CLIENT_SECRET}}  # REQUIRED; see gotcha below
      baseUrl: https://org40ae6a46.crm.dynamics.com
      authorizationUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/authorize
      tokenUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token
      refreshUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token
      scope: 'https://org40ae6a46.crm.dynamics.com/.default'
      identityProvider: Custom
      applicableToApps: AnyApp
      targetAudience: HomeTenant
    writeToEnvironmentFile:
      configurationId: LC_OAUTH_CONFIG_ID
```

`atk provision --env dev -i false` writes `LC_OAUTH_CONFIG_ID` to
`env/.env.dev` as a base64 blob that decodes to `<tenant>##<oAuthConfigId>`
(two hashes, not three). The base64 form is what goes directly into
`OAuthPluginVault.referenceId` in `plugins/cowork-dataverse-mcp-v2/manifest.json`;
the inner `<oAuthConfigId>` (a bare GUID) is what older
`plugins/cowork-dataverse-mcp/plugin-action.json` packages expect. End-to-end
console output (truncated):

```text
✓ Entra app 'LaunchControl-Cowork-MCP' created  (clientId=<new-appId>)
✓ Client secret minted, valid 1y  →  env/.env.dev.user
✓ Dynamics CRM/user_impersonation granted + admin consent
✓ Web redirect URI set: https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect
✓ Dataverse app user created, System Administrator assigned
✓ Allowed MCP Client row: LaunchControl-Cowork-MCP  →  enabled
✓ atk provision: OAuth registration created
→ referenceId (base64) = YWRmYTQ1NDIt…ODQzNA==
→ decoded              = adfa4542-…##b2cb2ac2-539f-43a7-bc70-bbbbfea88434
```

### Gotchas baked into the script (learned the hard way)

1. **Always set `clientSecret` on first register.** The `oauth/register`
   driver accepts an empty secret, the API returns 201, and the row is
   created — but the Dev Portal **list page** validates with a Zod schema
   that requires `clientSecret: string`. A missing secret crashes the
   entire `/tools/oauth-configuration` page with a `[ [ { "code":
   "invalid_type", "expected": "string", "received": "undefined", "path":
   [ N, "clientSecret" ], "message": "Required" } ] ]` toast.
2. **`oauth/update` won't patch clientSecret alone.** The driver's diff
   routine deliberately ignores `clientSecret`. To rotate the secret you
   must change another field (e.g., bump `name`) in the same `oauth/update`
   call — the PATCH payload then carries both.
3. **Use schema `version: v1.11` in `m365agents.yml`.** CLI `1.1.10`
   accepts up to v1.11; `v1.12` errors with `version v1.12 is not
   supported`.
4. **`identityProvider` is valid on `oauth/register` but not on
   `oauth/update`.** The bundled JSON schema is strict — leave it out of
   update payloads.
5. **Idempotency hinges on `LC_OAUTH_CONFIG_ID` in `env/.env.dev`.**
   `deploy.py` Phase E *preserves* this key on re-runs so `atk` no-ops
   into "reused" instead of minting a duplicate registration. To force a
   fresh registration (after a teardown, or to rotate), delete the key
   from `env/.env.dev` first. [`teardown.py`](teardown.py) does this for
   you.
6. **Admin consent is silently flaky.** `az ad app permission
   admin-consent` returns non-zero on a transient Graph 500 even when
   you have GA. Re-run; if the second attempt also fails, verify with
   `az ad app permission list-grants --id <appId> --show-resource-name`.
7. **Set the Teams platform redirect URI on the Entra app — the OAuth
   handshake won't complete without it.** The Teams Dev Portal OAuth
   connection (the one Cowork consumes via `OAuthPluginVault`) callbacks
   to `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect`, and
   Entra rejects the auth code exchange with `AADSTS50011` if that exact
   URI isn't on the app's `web.redirectUris`. `deploy.py` Phase A now
   adds it via `az ad app update --web-redirect-uris ...` right after
   creating the app.
8. **After teardown + redeploy, the Dev Portal OAuth row keeps the
   *deleted* clientId.** `atk oauth/register` dedupes by `name`. If
   `LaunchControl-Cowork-OAuth` already exists, atk returns its id and
   leaves `clientId` / `clientSecret` pointing at the old (now-deleted)
   Entra app. Sign-in then fails with `AADSTS700016: Application with
   identifier '<old appId>' was not found in the directory`. `deploy.py`
   Phase E detects this case (`prior_config` is set in `.env.dev`) and
   rewrites `m365agents.yml` to use `oauth/update` with a bumped `name`
   so atk's diff routine fires the PATCH and resyncs the row to the
   current `AAD_APP_CLIENT_ID` + `SECRET_AAD_APP_CLIENT_SECRET`. The
   committed yml stays in `oauth/register` shape for first-time runs;
   the rewrite is in-memory + restored in a `finally`.

### 📚 References

- [Microsoft 365 Agents Toolkit CLI overview](https://learn.microsoft.com/microsoftteams/platform/toolkit/microsoft-365-agents-toolkit-cli) — `atk` command surface
- [`oauth/register` action reference](https://aka.ms/teamsfx-actions/oauth-register) — required args, write-back env keys
- [Dataverse MCP server overview](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp) — GA `/api/mcp` and preview `/api/mcp_preview`, allowed clients, scopes
- [Teams Dev Portal OAuth client registrations](https://learn.microsoft.com/microsoftteams/platform/messaging-extensions/api-based-oauth) — the source of the `referenceId`
- Repo: [`deploy.py`](deploy.py), [`teardown.py`](teardown.py), [`configure_mcp_allowlist.py`](configure_mcp_allowlist.py), [`m365agents.yml`](m365agents.yml), [`setup_demo.py`](setup_demo.py) (Dataverse-side demo seed)

---

## Part 2 · Build the package (manifest + three skills + zip)

> One Copilot turn turns the template into a wired plugin with everything Cowork needs.

**🛠 Runs in:** GitHub Copilot CLI (coding agent in your terminal)

A Cowork agent package is a devPreview Teams manifest with
`agentConnectors[]` (where the MCP server lives) plus `agentSkills[]`
(SKILL.md files that teach the agent what to do with it). A plugin
without skills is just a connection string. So Part 2 is one Copilot turn
that bootstraps the manifest *and* drops in all three skills LaunchControl
needs before producing the upload zip:

1. **MCP workflow skill** — how to authenticate, what `search` /
   `describe` / `execute` look like on `/api/mcp_preview`, and the
   hard rules (always `describe` before `execute` for case-sensitive
   parameter names; never invent column names; reason readiness from
   the `lc_risksummary` prompt column on `lc_launch` plus the blocked
   `lc_task` rows — do not hand-tally milestone statuses).
2. **Schema skill** — the `lc_*` logical names, the case-sensitive
   `$expand` navigation properties (most common failure mode), status
   choice values, and lookup foreign-key columns.
3. **Business-skills loader** — the key Episode 6 unlock. Instead of
   shipping copies of LaunchControl policy inside the plugin, the loader
   tells Cowork to read its policies from the Dataverse `skill` table
   (entity set `skills`; columns `uniquename`, `description`, `body`) at
   session start. Edit a `body` row in Dataverse → every agent inherits
   the change. Same rows Scout and the code-first agent read.

### The prompt

> *Bootstrap the Cowork plugin from `artifacts/dataverse-mcp.cowork-template.zip`*
> *(devPreview manifest with `agentConnectors[]` + `agentSkills[]`, the only*
> *shape Cowork accepts) wired to our Dataverse preview MCP endpoint*
> *(`/api/mcp_preview`) with the OAuth referenceId from Part 1. Then add*
> *three skills inside the plugin:*
>
> - ***MCP workflow skill*** *— three tools (`search`, `describe`, `execute`)*
>   *with the limited SQL subset and the hard rule that readiness is sourced*
>   *from the `lc_risksummary` AI prompt column on `lc_launch` plus the*
>   *blocked `lc_task` rows (never hand-tally).*
> - ***Schema skill*** *— one entry per `lc_*` table with case-sensitive*
>   *`$expand` nav properties.*
> - ***Business-skills loader*** *— reads policy from the Dataverse `skill`*
>   *table at session start.*
>
> *Bump the manifest version and produce `plugins/dataverse-launchcontrol.zip`.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Plugin folder + manifest | [`plugins/cowork-dataverse-mcp-v2/`](../../plugins/cowork-dataverse-mcp-v2/) |
| MCP workflow skill | [`plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-mcp/SKILL.md`](../../plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-mcp/SKILL.md) |
| Schema skill | [`plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-schema/SKILL.md`](../../plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-schema/SKILL.md) |
| Business-skills loader | [`plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-business-skills/SKILL.md`](../../plugins/cowork-dataverse-mcp-v2/skills/dataverse-launchcontrol-business-skills/SKILL.md) |
| Values JSON (env-specific, gitignored secrets) | [`artifacts/launchcontrol-cowork-values.json`](../../artifacts/launchcontrol-cowork-values.json) |
| Upload artifact | `plugins/dataverse-launchcontrol.zip` (~42 KB, manifest + 3 skills) |

### Reference example — manifest excerpt + the three skill bodies

```jsonc
// plugins/cowork-dataverse-mcp-v2/manifest.json (excerpt)
{
  "manifestVersion": "devPreview",
  "version": "1.0.0",
  "id": "<bumped GUID per release>",
  "name": { "short": "Dataverse - LaunchControl" },
  "agentConnectors": [{
    "id": "dataverse-launchcontrol",
    "toolSource": {
      "remoteMcpServer": {
        "mcpServerUrl": "https://org40ae6a46.crm.dynamics.com/api/mcp_preview",
        "authorization": {
          "type": "OAuthPluginVault",
          "referenceId": "<oAuthConfigId from Part 1>"
        }
      }
    }
  }],
  "agentSkills": [
    { "folder": "./skills/dataverse-launchcontrol-mcp" },
    { "folder": "./skills/dataverse-launchcontrol-schema" },
    { "folder": "./skills/dataverse-launchcontrol-business-skills" }
  ]
}
```

```markdown
# MCP workflow skill — Hard rules (skills/dataverse-launchcontrol-mcp/SKILL.md)
1. Readiness questions are answered by invoking the `lc_launchreadiness`
   Dataverse **custom API** via `execute(operation='execute', …)` — this is
   a **preview-only** MCP capability (`/api/mcp_preview`); it is NOT
   available on the GA `/api/mcp` endpoint. The custom API internally
   re-reads the `lc_risksummary` AI prompt column on `lc_launch` and the
   open/blocked `lc_task` rows. Never hand-tally milestone statuses.
2. Stay within the LaunchControl environment; do not call other orgs.
3. Three tools only: `search` (discovery), `describe` (schema / API
   signature), `execute` (operation = read | create | update | delete |
   execute). Always `describe` before `execute` for case-sensitive
   parameter names — especially for custom API actions where bound
   entity / parameter names must match exactly.
```

```markdown
# Schema skill — one row per table (skills/dataverse-launchcontrol-schema/SKILL.md)
## lc_milestone
| Aspect | Value |
|---|---|
| Logical name        | lc_milestone |
| Entity set          | lc_milestones |
| Status column       | lc_milestonestatus (1=NotStarted, 2=InProgress, 3=AtRisk, 4=Blocked, 5=Complete) |
| Parent lookup       | lc_Launch  ← case-sensitive nav prop, _lc_launch_value as FK |
| Inverse to launch   | lc_launch.lc_milestone_Launch |

GET /lc_launches?$select=lc_name
  &$expand=lc_milestone_Launch($select=lc_name,lc_milestonestatus)
```

```markdown
# Business-skills loader — session-start procedure
1. execute(operation='read', query='SELECT TOP 200 skillid, uniquename,
   name, description FROM skill'). Cache the rows for the session.
2. On every user turn, match intent against `description`. If a row
   matches, `describe("skills/<uniquename>")` to load its `body` and
   FOLLOW that body verbatim. Do not improvise.
3. Policy questions defer here — the MCP skill's Step 3 cross-references
   this skill so readiness, status-transition, escalation, and briefing
   questions all run through cached rows.
```

> _"The plugin is the pipe. The three skills are the operator's manual,*
> the schema cheat sheet, and the playbook table — and the playbook lives*
> in Dataverse so it never drifts."_

### 📚 References

- [Cowork plugin manifest schema (devPreview)](https://learn.microsoft.com/microsoft-365/copilot/extensibility/) — `agentConnectors` + `agentSkills`
- [`scripts/cli/upload-skills.mjs`](../../scripts/cli/upload-skills.mjs) — confirms the `skill` table contract (entity set `skills`, `uniquename` / `description` / `body`)
- [`agents/launch-coordinator-py/sync_skills.py`](../../agents/launch-coordinator-py/sync_skills.py) — same read pattern Scout uses
- Repo: [`artifacts/dataverse-mcp.cowork-template.zip`](../../artifacts/dataverse-mcp.cowork-template.zip)

---

## Part 3 · Install the plugin in Cowork

> One upload via M365 Admin Center. The Graph publish path does not work.

**🛠 Runs in:** [M365 Admin Center → Copilot → Agents](https://admin.microsoft.com/#/copilot/agents) (manual upload — click-through, no API)

### Click-path

```text
plugins/dataverse-launchcontrol.zip   ← 42KB, manifest + 3 skills

M365 Admin Center
  └─ Copilot
       └─ Agents
            └─ All Agents
                 └─ Add agent
                      └─ Upload custom agent  ← drop the zip here
```

---

## Part 4 · Show the plugin in use

> Cowork pulls Dataverse launch risks from the outside world and writes the response back as tasks.

**🛠 Runs in:** Cowork (chat window inside M365 Copilot)

This is the demo beat — and it's the one where the plugin earns its keep.
The scenario: you're 8 weeks out from launching a Dataverse-backed
LaunchControl app. New Power Platform release notes just dropped, and
the Power Platform Community forums are lit up with people hitting fresh
issues. You don't want to read all of that yourself, and you definitely
don't want to leave the findings as a chat reply that vanishes. You want
Cowork to do the analysis, then **write tasks back into your launch** so
the risks live in Dataverse alongside everything else.

The mechanic for Part 4 is the **Business Skill** pattern: instead of
typing the whole workflow as a one-off prompt, the logic lives as a
versioned skill (`Launch Risk Scout`) inside Dataverse. Cowork pulls
the skill via the plugin's `search` tool, installs it as a local skill
for this chat, then runs it. The same skill can be re-run from any
client, in any chat, by name.

### Cowork prompt 1 — discover the skill

> *In the LaunchControl Dataverse plugin, search the Business Skills*
> *catalog for a skill called "Launch Risk Scout" and show me what it*
> *does, what inputs it needs, and which other Dataverse objects it*
> *touches before I run it.*

What Cowork does: business-skills loader fires the plugin's `search`
tool, which routes via the preview MCP to `tables/skill` + `skills/`
paths, finds `Launch Risk Scout`
(skillId `520194bd-f660-f111-a826-000d3a5a5cf3`,
uniquename `lc_launchriskscout`), and `describe`s it. Cowork echoes
back the skill's purpose, the `LaunchName` input, the tables it reads
(`lc_launch`, `lc_milestone`), and the table it writes (`lc_task`).

### Cowork prompt 2 — install the skill into this chat

> *Install Launch Risk Scout as a local skill for this conversation so*
> *I can re-run it later by name.*

What Cowork does: persists the skill body into the chat's skill scope.
On every subsequent turn, Cowork has the full `Launch Risk Scout`
instructions in context — including its guardrails (5-task cap,
mandatory milestone binding, `GeneratedByAutomation: true` footer) — and
will follow them faithfully when invoked.

### Cowork prompt 3 — run it

> *Run Launch Risk Scout against the Q3 Widget Launch.*

What Cowork does: executes the seven-step skill body — resolves the
launch, reads its milestones, fetches release notes + the community
forum, identifies up to 5 risks, writes each as an `lc_task` row bound
to the right `lc_milestoneid`, re-reads the `lc_risksummary` AI prompt
column on `lc_launch` (server-side re-evaluates as soon as the new
tasks land), and replies with the templated summary table showing the
refreshed readiness `Score` and `Decision`. Every write carries the
`GeneratedByAutomation: true` provenance marker.

### What the audience sees

1. **Skill-as-data** — the workflow lives in Dataverse, not in a prompt.
   Anyone with the plugin can run the same scan, the same way, every
   time. New version of the skill ships? Next chat picks it up.
2. **Outside-in awareness** — Cowork knows about Power Platform release
   notes and forum activity without you opening a browser tab.
3. **Authoritative scoring** — the readiness number comes from the
   same `lc_risksummary` AI prompt column on `lc_launch` that the Power
   App reads; it can't drift, because both clients hit the same
   server-side prompt evaluation.
4. **Mutation, not just chat** — the tasks are real Dataverse rows the
   moment Cowork answers. Refresh the LaunchControl Power App, they're
   there. That's the "plugin > chatbot" moment.

### 📚 References

- [Power Platform Community — Dataverse forum](https://community.powerplatform.com/t5/Microsoft-Dataverse/bd-p/PowerApps1) — the source for prompt 1
- [Power Platform release notes](https://learn.microsoft.com/power-platform/release-plan/) — second source for prompt 1
- [`tmp/cowork-template-extracted/`](../../tmp/cowork-template-extracted/) — bundled `render.py` (bootstrap only)
- [`SKILL.md`](SKILL.md) — recording-time playbook, hard rules, eight-step recipe

---

## Appendix · Governance and hardening

> Custom plugins need the same governance story as pre-built plugins.

Rafsan Huseynov's feedback is the guardrail beat: pre-built plugins are easy
to manage and remove; custom plugins can accumulate versions, stale packages,
and unclear ownership if teams do not govern them.

So the hardening checklist is part of the episode, not an afterthought:

- Restrict the Teams OAuth registration scope (`applicableToApps`) — start with
  `AnyApp` for validation, tighten to `SpecificApp` once the plugin's Teams App
  ID is stable in `m365agents.yml`.
- Increment plugin version on every re-upload; do not rely on Cowork picking
  up stale packages.
- Publish first to a small audience, then widen.
- Track which users, domains, prompts, and outputs use the plugin.
- Keep domain-specific packages separate: HR, finance, healthcare, and Launch
  Control should not share one opaque plugin.
- Respect Dataverse permissions and add Purview / sensitivity guardrails for
  highly confidential data.
- Rotate the OAuth client secret on schedule — use the `oauth/update` block
  in `m365agents.yml` (remember to change another field to force the PATCH;
  see Part 1 gotcha #2).

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
| P4 | Plugin action points at `/api/mcp_preview` and uses `OAuthPluginVault` | The package is wired to the preview Dataverse MCP (3-tool surface) |
| T1 | `WhoAmI` via `scripts/auth.py` | Dataverse connectivity works |
| T2 | Core `lc_*` table metadata exists | Cowork has real Launch Control schema to query |

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
4. **Plugin package** — VS Code: highlight `/api/mcp_preview`, `OAuthPluginVault`, and
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
| [`SKILL.md`](SKILL.md) | Recording-time playbook \u2014 hard rules, eight-step recipe table, prompts to give the coding agent. |
| [`preflight.py`](preflight.py) | Read-only local harness for repo files + Dataverse connectivity. |
| [`setup_demo.py`](setup_demo.py) | Idempotent Dataverse-side demo prep: WhoAmI, table check, seed `Q3 Widget Launch`, full preflight. |

## Related repo artifacts

| File/folder | Role |
|---|---|
| [`business-skills/`](../../business-skills/) | Existing schema/rule skills; Step 6 adds the Cowork-specific schema-aware skill here. |
| [`business-skills/cowork-dataverse-mcp.md`](../../business-skills/cowork-dataverse-mcp.md) | The schema-aware Business Skill for this episode \u2014 tables, lookup nav-property casing, readiness rule, escalation tiers. |
| [`plugins/cowork-dataverse-mcp/`](../../plugins/cowork-dataverse-mcp/) | **Deprecated** v1 Teams-app archetype (wrong manifest shape — silently fails Cowork upload). Kept only for git history. |
| [`plugins/cowork-dataverse-mcp-v2/`](../../plugins/cowork-dataverse-mcp-v2/) | **Live** Cowork plugin package — devPreview manifest + three agentSkills (`dataverse-launchcontrol-mcp`, `-schema`, `-business-skills`). Source of truth for `plugins/dataverse-launchcontrol.zip`. |
| [`artifacts/dataverse-mcp.cowork-template.zip`](../../artifacts/dataverse-mcp.cowork-template.zip) | Authoritative Cowork template (bundled `render.py` + manifest + skill templates). Bootstraps v2; not used for incremental edits. |
| [`artifacts/launchcontrol-cowork-values.json`](../../artifacts/launchcontrol-cowork-values.json) | Env-specific values consumed by the template's `render.py` (org URL, OAuth registration ID, app GUID). |
| [`scripts/seed_q3_widget_launch.py`](../../scripts/seed_q3_widget_launch.py) | Idempotent seed for the deterministic demo data the recording prompts depend on. |
| [`business-skills/launch-readiness-checklist.md`](../../business-skills/launch-readiness-checklist.md) | Readiness rule: source the Score from the `lc_risksummary` AI prompt column on `lc_launch`, never hand-tally. |
| [`business-skills/status-transition-rules.md`](../../business-skills/status-transition-rules.md) | Canonical status columns and allowed transitions. |
| [`business-skills/escalation-policy.md`](../../business-skills/escalation-policy.md) | Escalation routing for blocked launches and tasks. |
| [`connectors/`](../../connectors/) | Episode 5 BYO MCP connector pattern; useful contrast for the Cowork plugin package. |
| [`scripts/auth.py`](../../scripts/auth.py) | Shared Dataverse auth used by the preflight harness. |

---

## Run it yourself (one-shot, no narration)

The Parts above are the recording flow. If you just want to reproduce
everything end-to-end without the prompts, this is the condensed sequence:

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 0. Auth (one-time per session; interactive if MFA needed)
az login --tenant <your-tenant-id> --scope https://<your-org>.crm.dynamics.com/.default

# 1. Tenant plumbing (Part 1) — Entra app + Dataverse app user + MCP allowlist
python episodes/ep-06-cowork-plugin/setup_demo.py
python episodes/ep-06-cowork-plugin/configure_mcp_allowlist.py
# Then in Teams Dev Portal -> Tools -> OAuth client registrations -> New:
#   Base URL  = https://<your-org>.crm.dynamics.com
#   Scope     = https://<your-org>.crm.dynamics.com/.default offline_access
#   Auth URL  = https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize
#   Token URL = https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token
# Copy the OAuth Registration ID into artifacts/launchcontrol-cowork-values.json.

# 2. Bootstrap the plugin scaffold (Part 2)
Expand-Archive artifacts/dataverse-mcp.cowork-template.zip tmp/cowork-template-extracted -Force
python tmp/cowork-template-extracted/render.py `
  --template tmp/cowork-template-extracted `
  --values artifacts/launchcontrol-cowork-values.json `
  --out plugins/cowork-dataverse-mcp-v2 `
  --zip

# 3. Skills are already authored under plugins/cowork-dataverse-mcp-v2/skills/
#    (Parts 3-5). After any hand-edit, re-zip:
Compress-Archive -Path plugins/cowork-dataverse-mcp-v2/* `
                 -DestinationPath plugins/dataverse-launchcontrol.zip -Force

# 4. Deploy (Part 6) — M365 Admin Center upload only. Graph publish silently
#    falls back to the prior version.
#    Upload plugins/dataverse-launchcontrol.zip via:
#      M365 Admin Center -> Copilot -> Agents -> All Agents -> Add agent
#    (NOT "Integrated apps -> Upload custom apps" — that's Teams-app-only.)

# 5. Test (Part 7) — in Cowork: "What is blocking Q3 Widget Launch, and should we slip?"
#    NOTE: as of 2026-06 the OAuthPluginVault handshake does not complete in
#    M365 Copilot Frontier (postMessage to Teams JS SDK fails). See Part 7.
```

### Critical gotcha (came out of MVP testing)

The Entra app registration MUST have **`https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect`**
listed as a Web redirect URI. The Teams Dev Portal OAuth connection (which
Cowork consumes via `OAuthPluginVault`) callbacks to that URI; without it
Entra rejects the auth-code exchange with `AADSTS50011` and Cowork surfaces
only the generic *"Authentication is still processing. Please try again."*
toast. `deploy.py` Phase A sets this automatically — if you provisioned the
app any other way, add it manually:

```powershell
az ad app update --id <appId> --web-redirect-uris "https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect"
```

A second, equally silent failure: after teardown + redeploy, the Dev Portal
OAuth row keeps the *deleted* clientId baked in (atk's `oauth/register`
dedupes by `name`), and sign-in fails with `AADSTS700016: Application with
identifier '<deleted appId>' was not found`. `deploy.py` Phase E detects
this via the surviving `LC_OAUTH_CONFIG_ID` in `env/.env.dev` and rewrites
the yml to `oauth/update` for that run so the row resyncs to the current
Entra app. If you're operating outside `deploy.py`, mirror the workaround:
swap the `provision` block to `oauth/update`, bump `name`, then re-run
`atk provision --env dev -i false`.

---

## Pitfalls collected from the MVP findings

- **Client ID vs OAuth Registration ID** — Power Platform uses the Entra
  Client ID in the Allowed MCP Client row. The plugin `referenceId` uses the
  Teams Developer Portal OAuth Registration ID. Mixing them breaks auth.
- **Wrong MCP URL** — the endpoint is the Dataverse org URL plus `/api/mcp_preview`
  (the preview surface — `search`/`describe`/`execute`).
  GA `/api/mcp` is the older 11-tool CRUD shape with a narrower tool set
  and **does not yet support invoking Dataverse custom APIs** (e.g.
  `lc_launchreadiness`) — that capability is preview-only today.
  Note the underscore in `mcp_preview`: `/api/mcp/preview` (slash) does not exist.
- **Wrong scope** — use `{DataverseOrgUrl}/.default offline_access`, not a
  generic Graph scope.
- **Permission mismatch** — a successful OAuth prompt does not grant data the
  user cannot read in Dataverse. Test with a real launch user.
- **Stale deployment/session** — re-uploading the same version or testing in
  an old Cowork session can hide changes. Increment version, re-add, reconnect.
- **`@odata.bind` rejected by preview MCP** — when invoking
  `execute(operation='create'|'update')` for rows with lookups, set the
  lookup attribute directly to the GUID (`"lc_launchid": "<guid>"`), not the
  OData `@odata.bind` syntax. The preview MCP rejects `@odata.bind`.
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
in Copilot Studio — same `lc_*` model, same `lc_risksummary` prompt column,
hosted conversation surface.

## Live deployment state

The live IDs (Entra appId, systemuser GUID, allowlist row GUID, OAuth
oAuthConfigId, manifest version) churn every time `deploy.py` runs.
Rather than baking a stale table into this README, the source of truth
is `.deploy/ep-06/<timestamp>.json` — the most recent run's full
artifact dump (gitignored). Read it like:

```powershell
Get-ChildItem .deploy/ep-06/*.json | Sort-Object LastWriteTime |
  Select-Object -Last 1 | Get-Content | ConvertFrom-Json
```

Everything in this section used to be a hand-maintained checklist of
manual portal steps (Teams Dev Portal OAuth, plugin packaging, Cowork
"Add plugin"). `deploy.py` Phase E + the v2 plugin zip + the M365
Admin Center upload now cover all of it; the only step left for a
human is the literal **Add plugin → Connect** click inside Cowork.
