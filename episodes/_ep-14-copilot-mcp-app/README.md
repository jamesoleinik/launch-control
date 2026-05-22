# Episode 13 — Copilot MCP App (HIDDEN / EXPLORATION)

> **Status:** 🔬 Exploration · 🙈 Hidden from the public episode index (`_` prefix).
> Not listed in `episodes/README.md`. Promote to `ep-13-...` if/when it ships.

**Working title:** *"A Microsoft Copilot app over the Dataverse MCP server."*
**Hero capability:** A **declarative agent for Microsoft 365 Copilot** that consumes the
Dataverse MCP server as an **MCP App** — built with the **Microsoft 365 Agents Toolkit**
for VS Code, rendered as an interactive UI inside Copilot chat.
**Coding agent (off-camera):** GitHub Copilot CLI with the `dataverse@awesome-copilot` plugin.
**Runtime agent (on-camera):** A declarative agent the viewer talks to inside Microsoft 365 Copilot chat.

> 🆕 **March 9, 2026 announcement (Microsoft 365 Dev Blog):**
> [MCP Apps now available in Copilot Chat](https://devblogs.microsoft.com/microsoft365dev/mcp-apps-now-available-in-copilot-chat/).
> Agents in Microsoft 365 Copilot can now consume MCP servers natively via **MCP Apps**
> or the **OpenAI Apps SDK**, rendering rich HTML UI in a sandboxed iFrame in chat.
> This re-frames Ep 13 around the **Microsoft 365 Agents Toolkit** path rather than
> Copilot Studio. Power Apps agents are already shipping the same pattern in public preview.

---

## Why this episode (and why it's hidden for now)

Episode 1 wired the **coding agent** (GitHub Copilot) to the Dataverse MCP server.
Episodes 6–8 built **runtime agents** (declarative, autonomous, code-first).
This bonus episode closes the loop for the surface most enterprises actually live in:
**Microsoft 365 Copilot**, via a Copilot Studio agent that consumes the same Dataverse
MCP server we've been using all series.

It's hidden because (a) it's exploration — we want to validate the demo arc before
promoting; (b) the auth setup is finicky on camera; (c) we may decide it belongs as
Episode 13.5 or as an addendum to Episode 13.

---

## The hook

> _"Twelve episodes of building agentic launch management on Dataverse. The last surface
> nobody's seen yet is the one everyone in the enterprise actually uses — Microsoft 365
> Copilot. Same MCP server, new front door."_

The narrative: same Dataverse MCP server we connected from the coding agent in Ep 1.
This time we hand the keys to **Copilot Studio**, point it at the same `/api/mcp`
endpoint, and publish the result to Microsoft 365 Copilot so business users can ask
launch questions in the chat they already have open all day.

---

## State of the art (May 2026)

| Surface | Native MCP support | Notes |
|---|---|---|
| **M365 Copilot declarative agents (MCP Apps / Apps SDK)** | ✅ **GA path via M365 Agents Toolkit** (announced March 9, 2026) | ⭐ what we use here — inline UI in Copilot chat |
| **Copilot Studio** | ✅ GA (Aug 2025) — MCP onboarding wizard accepts Streamable HTTP | Alternative path; publish-to-M365-Copilot channel |
| **GitHub Copilot CLI** | ✅ via `~/.copilot/mcp-config.json` | Already wired in Ep 1 |

**Why MCP Apps over Copilot Studio for this episode:**

1. **It's the native M365 Copilot extensibility model** — same Agent Store, same
   `@mention` UX users already know. Copilot Studio is one degree removed.
2. **Rich UI in chat.** MCP Apps render HTML widgets (tables, forms, dashboards,
   maps) in a sandboxed iFrame via the MCP `meta` property. Copilot Studio's MCP
   tool returns are mostly text.
3. **Existing Dataverse MCP server works as-is.** The blog explicitly calls out that
   "your current functionality, authentication, and integrations stay intact. UI
   components are layered through the meta property, ensuring they're additive and
   backward compatible." Our `/api/mcp` endpoint already speaks Streamable HTTP.
4. **Microsoft is leading with this pattern.** Power Apps agents, Adobe Express,
   Figma, Coursera, monday.com all shipped on the same SDK on launch day. This is
   where the platform is going.

---

## Prerequisites (off-camera, do once)

These are the same tenant/environment prerequisites as the Ep 1 MCP setup. If you
already did them for the GitHub Copilot client ID, you'll do them again for the
declarative agent's MCP client (or reuse one).

1. **Entra app registration** for the declarative agent's MCP client. Note its
   **Client ID** and create a **Client Secret**.
2. **Tenant-level admin consent** at
   `https://login.microsoftonline.com/{tenantId}/adminconsent?client_id={CLIENT_ID}`
3. **Environment allowlist** in PPAC →
   *Environments → your environment → Settings → Product → Features → MCP Server*
   → On → add the Client ID to the allowed list.
4. **Microsoft 365 Agents Toolkit** for VS Code installed.
5. **Auth profile in the Dataverse CLI** for off-camera verification —
   `dataverse auth create --environment https://{org}.crm.dynamics.com/`.

> The setup is identical to the `dataverse-mcp-configure` skill flow we used in Ep 1.
> The only difference is *which* client ID gets consented + allow-listed.

---

## The on-camera flow (60–75s demo arc)

| Time | What's on screen | What's happening |
|---|---|---|
| **0:00–0:10** | VS Code with the Microsoft 365 Agents Toolkit panel open. Empty declarative agent project for "Launch Control." | "Let's give Microsoft 365 Copilot a Dataverse brain." |
| **0:10–0:30** ⭐ | In the Agents Toolkit: **Add an Action → Start with an MCP Server** → paste `https://{org}.crm.dynamics.com/api/mcp` → OAuth → the toolkit generates the action manifest entries. | The toolkit hits the MCP server, discovers tools, scaffolds the declarative agent action. **Hero shot.** |
| **0:30–0:45** | Hit F5 / *Provision & Publish*. Toolkit packages the declarative agent and side-loads it into M365 Copilot. | One command — the agent is live in the tenant. |
| **0:45–1:05** | Switch to **Microsoft 365 Copilot chat**. `@`-mention the new Launch Control agent. Ask: *"What's the readiness for Q3 Widget Launch?"* The agent calls the Dataverse MCP tool that wraps `lc_CalculateLaunchReadiness`. The verdict + per-milestone breakdown renders as an **inline MCP App UI widget** (table + status pills) inside chat. | Same Dataverse, same skills as Ep 7. **Native M365 Copilot front door, with rich UI.** |
| **1:05–1:15** | End card: *"Same Dataverse. Every Copilot."* Repo link. | Wrap. |

---

## The exact prompts / inputs to use on camera

**1. Microsoft 365 Agents Toolkit — Add an Action**

| Field | Value |
|---|---|
| Action source | `Start with an MCP Server` |
| Server URL | `https://<your-org>.crm.dynamics.com/api/mcp` |
| Transport | `Streamable HTTP` |
| Authentication | `OAuth 2.0` |
| Client ID | *(Entra app reg client ID, allow-listed in PPAC)* |
| Client Secret | *(from Entra app reg)* |
| Authorization URL | `https://login.microsoftonline.com/<tenantId>/oauth2/v2.0/authorize` |
| Token URL | `https://login.microsoftonline.com/<tenantId>/oauth2/v2.0/token` |
| Scopes | `https://<your-org>.crm.dynamics.com/.default` |

The toolkit will scaffold the action declaration in the declarative agent manifest
and wire up the auth config. Per the March 2026 blog: *"In VS Code, select 'Add an
Action,' choose 'Start with an MCP Server,' and then provide the URL for your MCP
server."*

**2. The user question on camera (M365 Copilot chat)**

> @LaunchControl What's the readiness for Q3 Widget Launch?

The agent should call the MCP tool that wraps `lc_CalculateLaunchReadiness`. With
MCP Apps UI metadata enabled on the tool response, the result renders as an
inline widget (verdict pill, readiness score, milestone table) instead of plain text.

---

## What this episode is *not*

- **Not a Copilot Studio episode.** Copilot Studio can also consume MCP servers
  (GA Aug 2025) and remains a valid alt path — but the March 2026 announcement
  made the Agents Toolkit + declarative agent + MCP Apps route the canonical
  Microsoft 365 Copilot story for MCP-server-backed agents. We use it.
- **Not a Power Apps agent episode.** Power Apps is the *other* launch partner
  Microsoft promotes in the same dev blog — see the next section. Different
  surface, different tradeoff; we acknowledge it but don't build it here.
- **Not a custom UI build.** Rich-card rendering in chat comes from the agent
  producing **GitHub-flavored Markdown** (header + status emojis + tables +
  block-quotes — see `declarative-agent/appPackage/instruction.txt`). The
  Dataverse MCP server returns `TextContent` today; Markdown is the
  mitigation. No HTML, no Adaptive Cards, no proxy server.
- **Not a replacement for Ep 7's Copilot Studio agent.** Ep 7 stays in Copilot
  Studio's native runtime. This episode is the M365 Copilot front door.

---

## The Power Apps companion path (acknowledged but not built here)

The same March 2026 dev blog calls out a *second* GA path for getting rich,
Dataverse-backed UI into M365 Copilot chat — **Power Apps agents** (public
preview as of the announcement):

> *"Power Apps agents bring all these capabilities to chat with compelling
> visualizations."* — [MCP Apps now available in Copilot Chat](https://devblogs.microsoft.com/microsoft365dev/mcp-apps-now-available-in-copilot-chat/)

The heatmap GIF in that post is literally a canvas app rendering inline in
Copilot chat.

**Architecture** (alternative to this episode's MCP path):

```
M365 Copilot chat
       │
       ▼
 Power Apps agent (canvas/model-driven app published as an in-chat agent)
       │
       ▼  Dataverse connector (user identity, no MCP server in the loop)
 Dataverse  ─ lc_launch / lc_milestone / lc_task / lc_CalculateLaunchReadiness
```

| | This episode (declarative + MCP) | Power Apps companion path |
|---|---|---|
| Surface in M365 Copilot | Agents rail, conversational | Agents rail, conversational + **inline canvas screens** |
| Auth to Dataverse | OAuth via Entra app reg → MCP endpoint | Power Platform Dataverse connector (user identity) |
| UI fidelity in chat | Markdown card (header + emoji + table) | Real canvas controls — charts, heatmaps, forms |
| Net-new code | ✅ none beyond manifest/action JSON | ⚠️ a canvas app (1-2 screens) |
| Reuses Business Skills | ✅ inherited through MCP server | ❌ Power App calls Dataverse directly; skills bypassed |
| Story alignment with Eps 1-12 | ✅ "MCP everywhere, one server" | ⚠️ "Power Apps everywhere" — pivots the thread |
| Public preview vs. GA | Both surfaces are preview at time of writing | Both surfaces are preview at time of writing |

**Why this episode picks the MCP path:**
1. **Narrative thread.** Eps 1-12 sell "Dataverse MCP server as the single point
   of integration for every agent." Power Apps agents bypass MCP entirely. The
   declarative-agent build closes the MCP arc cleanly.
2. **Business Skills payoff.** The Ep 2 Business Skills only show up at runtime
   through MCP. A Power App reading Dataverse directly doesn't invoke them.
3. **No new app to build.** The Power Apps path requires ~1-2 hours of canvas
   app work for one or two screens; the declarative-agent path is pure config.

**When the Power Apps path wins:**
- You want **richer in-chat visuals** (heatmaps, charts, write-back forms) than
  Markdown can produce.
- The MCP server's tool catalog isn't expressive enough for the workflow you
  want to demo.
- The audience is Power Platform builders rather than agent/SDK developers.

**If we ever ship the Power Apps variant**, it'd live as a sibling folder
`power-apps-agent/` under this episode (or get spun out as Ep 13.5
*"Same Dataverse, native canvas in chat"*). Out of scope for the current
recording.

> 📖 **Build steps for the Power Apps companion path are now in
> [`power-apps-agent/BUILD.md`](power-apps-agent/BUILD.md)** if you want
> to construct it in parallel.

---

## Open questions for the exploration

- [x] **Does the Dataverse MCP server (`/api/mcp`) emit MCP Apps `meta`-tagged UI
      payloads, or just text?** Confirmed **text only** as of May 2026 — the
      preview server returns `TextContent`. Mitigation: the agent's
      `instruction.txt` includes a Markdown-formatting block so MCP tool
      responses render as styled cards (header + status emoji + table +
      block-quote) inside M365 Copilot chat without any server changes.
      Track Microsoft adding `_meta` UI shaping for a future episode upgrade.
- [ ] Does the **Microsoft 365 Agents Toolkit** "Start with an MCP Server" flow
      work with the Dataverse MCP's OAuth dance, or does it require static
      credentials / a different auth flavor?
- [ ] Should we use a **new** Entra app reg for the declarative agent's MCP
      client, or reuse the Copilot CLI client ID
      (`aebc6443-996d-45c2-90f0-388ff96faa56`)?
- [ ] Side-loading vs. Agent Store distribution — side-load is fine for the demo
      but the blog teases Agent Store availability "by mid-April." Worth checking
      whether we can submit ours.
- [ ] Latency budget — MCP Apps render in chat with strict latency expectations.
      Does `lc_CalculateLaunchReadiness` stay under the limit?
- [ ] Power Apps agents are already shipping this pattern in public preview —
      should we contrast with their preview as a callout in the script?
- [ ] **Optional Ep 13.5 — proxy MCP server.** If we want guaranteed framed
      cards / `EmbeddedResource text/html` rendering, scaffold a ~150-line
      Node/Python MCP server that wraps `/api/mcp` and decorates hero tool
      responses with `_meta` UI hints. Net-new code, but the only way to get
      the rich-card moment until Microsoft ships UI shaping in the Dataverse
      MCP server itself.

---

## Files in this episode (planned)

| Path | Role |
|---|---|
| `episodes/_ep-14-copilot-mcp-app/README.md` | This file |
| `episodes/_ep-14-copilot-mcp-app/notes/` | Recording prep notes, screenshots of the wizard, agent transcripts |
| `episodes/_ep-14-copilot-mcp-app/agents/` | Exported Copilot Studio agent zip (if we go that far) |

---

## Why this is hidden

- The repo's `episodes/README.md` index does **not** list this folder.
- The folder name is prefixed with `_` to keep it out of the top of `episodes/`
  alphabetically.
- The Ep 13 "Full Orchestra" episode already promises six surfaces in 60 seconds
  — if this one earns its place, we promote it (rename to `ep-13-copilot-mcp-app/`,
  add a row to the index, write the social assets).
- For now this is just the spec we use to scope the recording. No social assets,
  no preflight, no scripts.

---

## See also

- [`episodes/ep-01-data-modeling/`](../ep-01-data-modeling/) — original Dataverse MCP
  configuration for GitHub Copilot CLI
- [`episodes/ep-02-business-skills/`](../ep-02-business-skills/) — the Business Skills
  this Copilot Studio agent will call through MCP
- [`episodes/ep-07-the-agent/`](../ep-07-the-agent/) — declarative Launch Coordinator
  built natively in Copilot Studio (this episode's contrast point)
- [`episodes/ep-13-full-orchestra/`](../ep-13-full-orchestra/) — the "six surfaces"
  finale; this exploration may end up as part of that montage

---

## Microsoft docs referenced

- 🆕 **MCP Apps now available in Copilot Chat** (March 9, 2026 announcement):
  https://devblogs.microsoft.com/microsoft365dev/mcp-apps-now-available-in-copilot-chat/
- **Microsoft 365 Agents Toolkit — Declarative agent UI widgets** (the "Add an
  Action → Start with an MCP Server" flow):
  https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/declarative-agent-ui-widgets
- **MCP Apps overview** (Model Context Protocol spec extension):
  https://modelcontextprotocol.io/extensions/apps/overview
- **OpenAI Apps SDK** (alternative to MCP Apps; same outcome):
  https://developers.openai.com/apps-sdk
- **Work IQ overview** (the org-context layer that pairs with MCP Apps):
  https://techcommunity.microsoft.com/blog/microsoft365copilotblog/a-closer-look-at-work-iq/4499789
- **Original Microsoft 365 Copilot announcement** (March 9, 2026):
  https://techcommunity.microsoft.com/blog/microsoft365copilotblog/enable-agents-to-bring-apps-into-the-flow-of-work%E2%80%94while-keeping-it-in-control/4499464
- **Power Apps agents in public preview** (Dataverse-backed reference):
  https://www.microsoft.com/en-us/power-platform/blog/power-apps/public-preview-your-business-apps-now-part-of-every-conversation/
- Copilot Studio MCP onboarding (alternative path, GA Aug 2025):
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent
- Dataverse Business Skills overview:
  https://learn.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-business-skill-overview
- Dataverse MCP plugin source (the official MS sample for GitHub Copilot):
  https://github.com/microsoft/Dataverse-skills
