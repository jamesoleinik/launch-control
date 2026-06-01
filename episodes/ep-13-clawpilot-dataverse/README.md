# Episode 13 — Clawpilot + Dataverse

**Status:** 🟢 Ready to record · 🎬 Not yet recorded
**Features:** ⭐ Clawpilot desktop app · ⭐ GitHub Copilot CLI substrate (`~/.copilot/`) · ⭐ Shared `mcp-config.json` · ⭐ Dataverse MCP server · ⭐ Plugin + skill reuse
**Layer:** 🖥️ Local desktop agent surface — same Dataverse, new always-on front door
**Coding agent:** GitHub Copilot CLI drafts the substrate + preflight
**Runtime:** Clawpilot.exe on the user's machine, sharing the same `~/.copilot/` config tree as the `copilot` CLI, calling the Dataverse MCP server

---

## The hook

> _"Every previous episode lived in a terminal, a Studio canvas, or a server-side
> runtime. Episode 13 puts the agent on the desktop — and it doesn't need a new
> configuration. Clawpilot already shares the GitHub Copilot CLI's `~/.copilot/`
> tree, so the same plugin, the same skills, and the same MCP server entries we
> registered in Episodes 1–7 light up automatically in the desktop app."_

Launch Control's thesis is **one governed data plane, many agent surfaces.**
Episode 13 adds the local desktop surface — Microsoft's Clawpilot — without
introducing a new auth flow, a new skill format, or a new MCP registration. The
config tree is shared by construction.

Same data. Same permissions. Same plugin. New front door.

---

## The narrative beat

Episodes 8–10 stood up the **hosted, autonomous, and code-first** agents.
Episode 11 added the **generative Power Apps page**. Episode 12 showed Microsoft
365 Copilot answering questions over Launch Control natively — *no* agent, *no*
MCP, just Dataverse Intelligence. Episode 13 closes the surface loop with the
runtime that lives closest to the user: a desktop assistant that can watch
context, remember work, and act without making the user switch apps.

The key insight is mechanical, not philosophical: Clawpilot is an Electron
desktop app that **wraps the GitHub Copilot CLI** (`@github/copilot`) and reads
the same `~/.copilot/` folder. That means:

```text
~/.copilot/
├── mcp-config.json              ← Dataverse MCP server registered here
├── installed-plugins/
│   ├── awesome-copilot/dataverse/   ← dv-connect, dv-data, dv-query, ...
│   └── launch-control/series-tools/ ← episode authoring skills
├── skills/                      ← user-authored SKILL.md skills
└── m-settings.json, config.json, m-mcp-servers.json, ...
```

The desktop pipeline becomes:

```text
User desktop
  → Clawpilot.exe (Electron + GitHub Copilot CLI)
      → reads ~/.copilot/mcp-config.json
          → DataverseMcp<org> → https://<org>.crm.dynamics.com/api/mcp_preview
              → lc_launch / lc_milestone / lc_task / lc_statusupdate
              → lc_CalculateLaunchReadiness
              → Dataverse Business Skills
```

The money shot: the desktop agent answers a launch-readiness question, and the
**only** thing different from Episode 5 or 6 is the chrome around the chat.

```text
User → "Before my 3pm launch review, summarize Q3 Widget Launch."

Clawpilot → invokes Dataverse MCP read_query over lc_launch / lc_milestone / lc_task
Clawpilot → invokes lc_CalculateLaunchReadiness
Clawpilot ← "NO-GO: score 38.8. Security review and CDN provisioning blocked..."
```

---

## Part 1 · Why Clawpilot belongs in the arc

> Local, persistent, personal — but governed by the same Dataverse RBAC.

Clawpilot is Microsoft's internal agentic desktop assistant — an Electron app
distributed via the Inner Ring (`aka.ms/clawpilot`). It surfaces M365 (Outlook,
Teams, OneDrive, Calendar, SharePoint), browser automation, shell + code
execution, and proactive automations (`Heartbeat`, `Co-create`, `Second Brain`).

Crucially for this series, the underlying runtime **is** the GitHub Copilot CLI:

- `copilot` CLI lives at `~\AppData\Roaming\Code\User\globalStorage\github.copilot-chat\copilotCli\copilot.ps1`
  (or wherever `npm install -g @github/copilot` puts it).
- Clawpilot.exe lives at `%LOCALAPPDATA%\Programs\clawpilot\Clawpilot.exe`,
  with state under `%APPDATA%\ClawPilot\`.
- Both read **the same** `~/.copilot/` config tree.

That collapses what would otherwise be a complicated integration story into a
one-liner: if Episodes 1–7 already wrote a `dataverse-*` entry into
`~/.copilot/mcp-config.json` and installed `awesome-copilot/dataverse` as a
plugin, **Clawpilot inherits all of it on first launch**. There is no separate
"Launch Control skill for Clawpilot" to ship.

Launch Control's integration surface stays unchanged:

| Requirement | Launch Control answer |
|---|---|
| Live launch state | `lc_*` Dataverse tables |
| Business process | Business Skills + plugin SKILL.md files |
| Deterministic readiness math | `lc_CalculateLaunchReadiness` Custom API |
| Cross-runtime tool surface | Dataverse MCP server (`/api/mcp_preview`) |
| Permission boundary | Dataverse RBAC + per-server `oauthClientId` |
| Desktop client | Reuses the GitHub Copilot CLI `~/.copilot/` substrate |

Clawpilot does not get a side door. It gets the same `mcp-config.json` entry.

---

## Part 2 · The shared substrate (`~/.copilot/`)

Everything Clawpilot needs is already on disk after the standard setup:

| Path | What it is | Who put it there |
|---|---|---|
| `~/.copilot/mcp-config.json` | MCP server registry (Dataverse, M365 WorkIQ, Azure) | `dv-connect` (Ep 1) + any per-environment registrations |
| `~/.copilot/installed-plugins/awesome-copilot/dataverse/` | The Dataverse plugin (`dv-connect`, `dv-data`, `dv-metadata`, `dv-query`, `dv-admin`, `dv-security`, `dv-solution`, `dv-overview`) | `copilot plugin install` (Ep 1) |
| `~/.copilot/installed-plugins/launch-control/series-tools/` | Series authoring skills (e.g. `episode-video-script`) | Installed from this repo |
| `~/.copilot/skills/<name>/SKILL.md` | User-authored ad-hoc skills | User, via `copilot` CLI or Clawpilot Settings |
| `~/AppData/Roaming/ClawPilot/` | Clawpilot UI state (Electron cache, preferences) | Clawpilot installer |

The Clawpilot Windows setup guide (Inner Ring distribution) installs
`@github/copilot` first, then plugins go in via:

```text
Install the launch-control plugin from:
  github.com/jamesoleinik/launch-control
Confirm path: ~/.copilot/installed-plugins/launch-control
```

…and MCP servers get added by pasting a prompt into Clawpilot that writes
`~/.copilot/mcp-config.json`. After that, both the terminal `copilot` and
desktop `Clawpilot.exe` see the same world.

> Skill format: this series uses Anthropic-style Markdown skills (a `SKILL.md`
> with YAML front-matter under a skill folder). That is the same format the
> bundled Clawpilot skills use (`/pptx`, `/docx`, `/xlsx`, `/loop`,
> `/web-artifacts-builder`, `/excalidraw`, `/expense-report`), so nothing about
> Launch Control's process documentation needs a new wrapper.

---

## Part 3 · Wire the local surface to Dataverse MCP

For new machines, the steps are:

1. **Install the GitHub Copilot CLI** (Clawpilot bundles it, but explicit is
   fine):
   ```powershell
   npm install -g @github/copilot
   copilot --version
   ```
2. **Install the Launch Control plugin** (from a fresh Clawpilot chat or
   `copilot` terminal):
   ```text
   Install the launch-control plugin from:
     github.com/jamesoleinik/launch-control
   Confirm path: ~/.copilot/installed-plugins/launch-control
   ```
3. **Register the Dataverse MCP server** for the Launch Control environment.
   `dv-connect` does this automatically — or paste:
   ```text
   Add MCP server "DataverseMcp<orgId>":
     type: http
     url: https://<org>.crm.dynamics.com/api/mcp_preview
     oauthClientId: aebc6443-996d-45c2-90f0-388ff96faa56
     oauthPublicClient: true
   Then restart the MCP connection.
   ```
4. **Open Clawpilot.** Sign in with the same `@microsoft.com` (or tenant)
   identity used for the Dataverse environment.
5. **Ask the launch-readiness prompt** and verify the trace shows the Dataverse
   MCP server being called, not a mock.

---

## Part 4 · Local validation

[`preflight.py`](preflight.py) is read-only. It checks whether the recording
machine looks ready before opening the desktop app:

```powershell
# from launch-control/
python episodes/ep-13-clawpilot-dataverse/preflight.py

# quick local-only check, no network call to Dataverse
python episodes/ep-13-clawpilot-dataverse/preflight.py --offline
```

### What the harness checks

| # | Pre-flight | Validates |
|---|---|---|
| P1 | `.env` + `scripts/auth.py` exist and expose `DATAVERSE_URL` | Repo is initialized for Dataverse |
| P2 | Dataverse MCP URL is derivable from `DATAVERSE_URL` | The target `/api/mcp[_preview]` endpoint is known |
| P3 | Clawpilot.exe and/or the `copilot` CLI are installed | Desktop + CLI runtimes are present |
| P4 | `~/.copilot/` substrate exists with `mcp-config.json`, `installed-plugins/`, and `skills/` | Clawpilot has a world to read |
| P5 | `~/.copilot/mcp-config.json` contains a Dataverse MCP entry whose URL matches `DATAVERSE_URL` | The desktop client is wired to *this* Launch Control environment |
| P6 | The `awesome-copilot/dataverse` plugin is installed and its `SKILL.md` files mention `mcp`/Dataverse | The Dataverse plugin is in place |
| S1 | `scripts/auth.py` can obtain a token and reach the Dataverse MCP endpoint | The MCP endpoint is reachable for recording |

---

## What's deliberately NOT in this episode

- **Not a second Dataverse integration.** No direct Web API bypass for the
  desktop agent. The point is shared MCP reuse via `~/.copilot/mcp-config.json`.
- **Not a Clawpilot install tutorial.** Inner Ring distribution and access
  approval (`aka.ms/clawpilot-request`) are out of scope. The episode assumes
  Clawpilot is already installed and the user is signed in.
- **Not a new skill format.** Clawpilot's bundled skills and the Launch Control
  plugin skills both use the Anthropic-style `SKILL.md` convention. We reuse it,
  we do not invent.
- **Not a renumbering cleanup.** The shifted folders (`ep-08-the-agent`,
  `ep-09-autonomous-agents`, …) carry the previously-published episodes at their
  new positions. This folder is the new Episode 13 only.

---

## What you see on screen

1. **Hook** — desktop assistant prompt: _"Before my launch review, summarize Q3
   Widget Launch and tell me if we're ready."_
2. **Architecture pan** — VS Code split with `~/.copilot/` tree on one side
   (mcp-config.json + installed-plugins/ + skills/) and Clawpilot.exe on the
   other. Caption: *one config tree, two surfaces.*
3. **Config peek** — show the `DataverseMcp<org>` entry in
   `~/.copilot/mcp-config.json` and the `awesome-copilot/dataverse` plugin
   folder. Do not show OAuth bearer tokens on screen.
4. **Preflight** — run `python episodes/ep-13-clawpilot-dataverse/preflight.py`
   and show green checks (P1–P6 + S1).
5. **Desktop agent** — ask the readiness prompt in Clawpilot.
6. **Trace / response** — show the Dataverse MCP call and the readiness verdict.
7. **Punchline:**
   > _"The surface changed. The governance didn't. That's why one Dataverse
   > config tree under `~/.copilot/` is enough."_

---

## Files in this episode

| File | Role |
|---|---|
| [`README.md`](README.md) | Episode spec, narrative, file inventory, sources, caveats |
| [`recording-script.md`](recording-script.md) | Concrete shot list, captions, voiceover, and recording workflow |
| [`preflight.py`](preflight.py) | Read-only local readiness harness for ClawPilot + Dataverse MCP |
| [`business-skills/launch-readiness-checklist.md`](../../business-skills/launch-readiness-checklist.md) | Canonical readiness skill reused by the desktop agent |
| [`business-skills/escalation-policy.md`](../../business-skills/escalation-policy.md) | Canonical escalation behavior |
| [`business-skills/status-transition-rules.md`](../../business-skills/status-transition-rules.md) | Canonical state-change behavior |
| [`scripts/auth.py`](../../scripts/auth.py) | Shared Dataverse auth helper used by the preflight |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Confirm the local substrate
python episodes/ep-13-clawpilot-dataverse/preflight.py

# 2. Open ClawPilot / OpenClaw
# 3. Ask:
#    Before my 3pm launch review, summarize Q3 Widget Launch and tell me if we are ready.
# 4. Verify the answer cites live Launch Control state and calls the readiness tool.
```

---

## Sources & caveats

Setup references used for this draft (verified locally against this machine):

- **Clawpilot Windows Setup Skill — First-Time User Guide** (Inner Ring docx).
  Names `~/.copilot/installed-plugins/` as the plugin root, the
  `npm install -g @github/copilot` bootstrap, and the
  `Add MCP server "<name>": ...` chat prompt that writes
  `~/.copilot/mcp-config.json`.
- **Clawpilot Overview** (Inner Ring pptx). Documents Clawpilot as a desktop
  assistant with bundled skills (`/pptx`, `/docx`, `/xlsx`, `/loop`,
  `/web-artifacts-builder`, `/excalidraw`, `/expense-report`), Heartbeat,
  Co-create, and Second Brain, with access gated through
  `aka.ms/clawpilot-request`.
- **Local install verified on the recording machine:**
  - `copilot` CLI present (resolved via VS Code globalStorage).
  - `%LOCALAPPDATA%\Programs\clawpilot\Clawpilot.exe` exists.
  - `~/.copilot/mcp-config.json` contains `DataverseMcp*` entries pointing at
    `/api/mcp_preview`.
  - `~/.copilot/installed-plugins/awesome-copilot/dataverse/` contains the
    `dv-*` skills and `scripts/auth.py`.
  - `~/.copilot/installed-plugins/launch-control/series-tools/` contains the
    `episode-video-script` skill.
- **Microsoft Learn:** Dataverse MCP server overview. The GA URL pattern is
  `/api/mcp`; current preview deployments use `/api/mcp_preview`. The preflight
  accepts either.

**Caveat for recording:** do not display OAuth bearer tokens, tenant IDs, or
org IDs from `~/.copilot/mcp-config.json` on camera. The preflight is
deliberately read-only and prints derived URLs only.

---

## Next up

**Episode 14 — Agentic Administration.** Episode 13 wired the desktop agent into
the same governed data plane. Episode 14 turns that lens on the **management
plane**: the Copilot CLI + `awesome-copilot/dataverse` plugin become the audit
log, the capacity report, and the agent-blast-radius probe.
