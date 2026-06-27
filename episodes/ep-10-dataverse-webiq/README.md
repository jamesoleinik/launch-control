# Episode 10: Dataverse + Web IQ (the outside-in agent)

**Status:** ✍️ Draft · 🎬 Not yet recorded
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Copilot Studio agent in the new unified builder (model picker, Tools, Knowledge, Memory) · ⭐ Dataverse MCP Server (internal state) · ⭐ Web IQ MCP Server (live external signal) · ⭐ Two MCP servers composed in one agent
**Layer:** 🟣 Layer 3 (the conversational surface), reaching data that does not live in the tenant at all
**Coding agent:** Copilot Studio (new agent builder UI)
**Runtime:** Copilot Studio agent + Dataverse MCP Server (Preview) + Web IQ MCP Server (`https://api.microsoft.ai/v3/mcp`)
**Runtime showcased:** the **new Copilot Studio agent builder** (this episode also supersedes the Season 1 declarative-agent build, archived at `episodes/archive/ep-09-the-agent/`)

---

## The hook

> *"Every pairing so far stayed inside the tenant. This one answers from data we
> would never put in Dataverse: the live web. It connects what is happening inside
> the launch to what is happening outside it, in one breath."*

The F&O episode joined Dataverse to the other half of the business. This episode
joins it to the other half of the **world**. The reason a launch is actually at
risk often lives outside the tenant: a vendor outage, a freshly published CVE, a
competitor shipping first. That signal is real-time, web-scale, and changes
hourly. You would never model it as Dataverse rows, so we do not. We give the
agent a second MCP server that reaches the open web and let it fuse the two.

## Why this is a complement, not a duplicate (the design rule)

The deciding question for any piece of content: *would this naturally be a row I
query, relate, secure, or transact?*

- **Yes, it is a row -> Dataverse.** Launches, milestones, tasks, team, status
  updates, the `lc_launchreadiness` score. Ground on it with the Dataverse MCP
  server.
- **No, it is live external content -> Web IQ.** News, web pages, CVE advisories,
  vendor status, market signal. Retrieved fresh on every ask, never stored.

If a fact is a row, it is Dataverse. If it is the live outside world, it is Web
IQ. Nothing lives in both places, so there is nothing to duplicate. Internal
facts stay governed and permission-trimmed in Dataverse; external facts are
clearly labeled as web sources with citations.

## The agent: an outside-in Launch Coordinator

One job: given a launch, assess the **external** risk the internal data cannot
see, and tie it back to the specific internal blockers it affects.

- **Dataverse MCP (Tools)** answers "what is the state of this launch?": the open
  blockers, their owners, the readiness score.
- **Web IQ MCP (Tools)** answers "what is the world doing about the things that
  block us?": `news` for vendor or market events, `web` and `browse` for
  authoritative sources (for example an NVD CVE page), `videos`/`images` when a
  visual helps.
- The model (your pick in the new builder) synthesizes a recommendation that
  cites both an internal row and an external source.

### The money shot (uses real Web IQ responses captured during research)

> *"Give me the external risk picture for the Q3 Widget Launch."*

1. **Dataverse** returns the internal facts: two blockers, "Security review" and
   "CDN provisioning"; readiness NO-GO (score 38.8); owners and due dates.
2. **Web IQ `news`** surfaces that the CDN vendor had a global outage this week
   (a real result captured in research: a Cloudflare fiber-cut outage disrupting
   X, Reddit, and Zoom, dated June 23, 2026).
3. **Web IQ `web` + `browse`** pulls the authoritative source behind the security
   blocker (a real result captured in research: NVD CVE-2026-33843, an
   authentication-bypass advisory rated CVSS 9.8 Critical).
4. **The agent synthesizes:**
   > "Both of your blockers just got riskier from the outside. Your CDN provider
   > had a global outage on Monday (source: news article), so the CDN
   > provisioning slip is now a vendor-reliability risk, not just a scheduling
   > one. Your security review maps to an actively tracked critical CVE
   > (CVE-2026-33843, CVSS 9.8; source: NVD). Recommend escalating both today."

Neither plane could produce that alone. Dataverse does not know about the outage;
the web does not know your launch has a CDN milestone. The agent is the join.

## Build steps (new Copilot Studio agent builder)

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored),
> fill in your values (including `WEBIQ_API_KEY`), and select it with
> `LC_ENV=ep-10-dataverse-webiq`. Never commit a real Web IQ key.

1. **Create the agent**, give it the outside-in instructions (role: connect
   internal launch blockers to live external signal; always cite the source;
   never invent a row that is not in Dataverse).
2. **Add Tool 1: Dataverse MCP Server (Preview)** for internal state and actions.
3. **Add Tool 2: Web IQ MCP Server** for external signal. Endpoint
   `https://api.microsoft.ai/v3/mcp`, authenticated with an API key (`x-apikey`
   header) or an Entra ID access token. Public docs:
   https://www.microsoft.com/webiq
4. **Pick the model** in the builder.
5. **(Optional) Memory (Preview)** so a multi-turn "walk me through mitigating
   each blocker" holds context across the conversation.
6. **Preview, then Publish.**

### Web IQ MCP at a glance (verified live, server v3.0.0)

- Endpoint: `https://api.microsoft.ai/v3/mcp` (Streamable HTTP, JSON-RPC).
- Auth: API key (`x-apikey`) or Entra ID access token.
- Tools observed live (scoped to the account's allowed service list): `web`,
  `news`, `videos`, `images`, `browse`, `finance`, `places`, `sonic`, `sports`.
  The published quickstart highlights five (`web`, `videos`, `browse`, `news`,
  `images`); the others appear when the key is entitled to them.
- Response shapes: `web` returns `webResults[]`; `news` returns `newsResults[]`,
  each item carrying `title`, `url`, and `content`.

For a Copilot CLI or VS Code client, the MCP config is below. Use a placeholder
for the key and never commit the real value (resolve it from a secret store or
environment at runtime).

```json
{
  "mcpServers": {
    "WebIQ-MCP": {
      "url": "https://api.microsoft.ai/v3/mcp",
      "type": "http",
      "authtype": "api-key",
      "headers": { "x-apikey": "<your-webiq-api-key>" }
    }
  }
}
```

## Pre-record checklist

- [ ] Web IQ API key (or Entra ID token) entitled to at least `web` and `news`.
- [ ] Dataverse MCP server reachable; Q3 Widget Launch seeded with the two
      blockers so the internal half is deterministic.
- [ ] Stage the two external queries that return strong results on the day
      (vendor-outage news; the CVE/NVD source). Web results change; confirm the
      live answer the morning of the shoot and have a backup query ready.
- [ ] Confirm the agent cites sources for every external claim.

## Open questions to resolve before building

- **Auth for the demo.** API key is fastest on camera; Entra ID token is the
  governed story. Pick one as the hero, mention the other.
- **Which extra tools to show.** `finance`/`sports`/`places` are live but off
  narrative; likely keep the demo to `news`, `web`, `browse`.

## Cross-references

- **Ep 5:** `lc_launchreadiness` Custom API (the internal score the external
  signal is weighed against).
- **`episodes/archive/ep-09-the-agent/`:** the Season 1 declarative-agent build
  this episode rebuilds in the new Copilot Studio experience.
- **Ep 13** (convergence): this agent runs alongside the Fabric IQ and Foundry IQ
  agents, with native Copilot, on one launch.
