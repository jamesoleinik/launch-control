# Episode 13 — Recording Script

**Working title:** *"Clawpilot, meet your Dataverse."*
**Target length:** 1:20 (80 seconds)
**Voiceover target:** ~165 words
**Hero pattern:** The desktop Clawpilot app shares `~/.copilot/` with the GitHub Copilot CLI, so the Dataverse MCP server registered in earlier episodes just works.
**Hero file in repo:** `episodes/ep-13-clawpilot-dataverse/preflight.py`

---

## What the viewer sees

| Time | Camera / capture | Action |
|---|---|---|
| **0:00–0:08** | Desktop with Clawpilot open beside VS Code | Title card: *"Clawpilot + Dataverse"*. Prompt visible: *"Before my launch review, summarize Q3 Widget Launch."* |
| **0:08–0:18** | VS Code, `README.md` architecture block | Highlight: `Clawpilot.exe → ~/.copilot/mcp-config.json → DataverseMcp<org> → lc_* + readiness Custom API`. Caption: *"Same governed lane. New desktop surface."* |
| **0:18–0:30** | File explorer or `ls ~/.copilot/` | Show the shared substrate: `mcp-config.json`, `installed-plugins/awesome-copilot/dataverse/`, `installed-plugins/launch-control/series-tools/`, `skills/`. Redact OAuth bearer tokens. |
| **0:30–0:42** | Terminal at repo root | Run `python episodes\ep-13-clawpilot-dataverse\preflight.py`. Green checks P1–P6 prove the local substrate is wired to *this* environment. |
| **0:42–1:03** ⭐ | Clawpilot desktop UI | Ask: *"Before my 3pm launch review, summarize Q3 Widget Launch and tell me if we are ready."* The agent calls the Dataverse MCP server. **Hero shot.** |
| **1:03–1:14** | Agent response / trace | Show readiness verdict, score, blockers, and the MCP tool call if visible. Caption: *"The desktop agent didn't get a side door."* |
| **1:14–1:20** | End card | *"Same Dataverse. Every runtime. Episode 13."* + repo link. |

---

## Prompts to type on camera

**Beat A — preflight**

```powershell
python episodes\ep-13-clawpilot-dataverse\preflight.py
```

**Beat B — desktop agent prompt**

> Before my 3pm launch review, summarize Q3 Widget Launch and tell me if we are ready.

**Backup prompt if the first response is too terse**

> What blockers are driving the verdict, and which Dataverse MCP tool did you call?

---

## Captions (SRT)

```srt
1
00:00:00,000 --> 00:00:08,000
We've shown hosted, autonomous, and code-first agents.
Now Launch Control gets a desktop surface: Clawpilot.

2
00:00:08,000 --> 00:00:18,000
Clawpilot wraps the GitHub Copilot CLI, so it reads
the same ~/.copilot tree we've been writing to all series.

3
00:00:18,000 --> 00:00:30,000
One mcp-config.json. One Dataverse plugin folder.
Both the terminal CLI and the desktop app see them.

4
00:00:30,000 --> 00:00:42,000
The preflight checks .env, the MCP URL, the install,
the substrate, the Dataverse plugin, and the live endpoint.

5
00:00:42,000 --> 00:01:03,000
Ask the desktop agent a launch question. It calls Dataverse MCP,
runs the readiness Custom API, and summarizes live launch state.

6
00:01:03,000 --> 00:01:14,000
The agent feels personal because it lives on the desktop.
The control plane is still enterprise-governed Dataverse.

7
00:01:14,000 --> 00:01:20,000
Same Dataverse. Every runtime. Repo's in the description.
```

---

## Voiceover script (4 blocks, ~165 words)

**Block 1 (0:00–0:08, ~27 words)**

> "Launch Control already has declarative, autonomous, and code-first agents.
> Episode 13 adds the surface that lives closest to the user: the desktop."

**Block 2 (0:08–0:30, ~48 words)**

> "Clawpilot is Microsoft's desktop assistant, and the trick is mechanical:
> it wraps the GitHub Copilot CLI, so it reads the exact same `~/.copilot`
> folder. The Dataverse MCP server I registered in Episode 1 is already there.
> No new auth flow, no new skill format."

**Block 3 (0:30–1:03, ~54 words)**

> "The preflight is boring on purpose. Is Dataverse configured, is the MCP URL
> derivable, is Clawpilot installed, does mcp-config.json point at this
> environment, is the Dataverse plugin in place, can the endpoint be reached?
> Then the desktop agent asks the same launch question every other runtime asks:
> is Q3 Widget Launch ready?"

**Block 4 (1:03–1:20, ~36 words)**

> "The response is the familiar one: verdict, score, blockers, next action.
> What changed is the front door. What didn't change is the governance plane.
> Same Dataverse. Every runtime."

---

## Word-count check (~165 words)

27 + 48 + 54 + 36 = **165 words**, on target for an 80-second cut at ~125 WPM.

The narrative beat closes the agent-surfaces loop: Dataverse is not just a
backend for one bot. It is the connective tissue that lets hosted, autonomous,
code-first, and desktop agents act over the same launch system without
inventing new governance for each runtime.

---

## Recording workflow

1. **Off-camera prep**
   - Confirm Clawpilot is installed (`%LOCALAPPDATA%\Programs\clawpilot\Clawpilot.exe`)
     and signed in to the same tenant as the rest of the series.
   - Confirm the GitHub Copilot CLI resolves (`copilot --version`).
   - Confirm `~/.copilot/mcp-config.json` has a `DataverseMcp*` entry pointing
     at the same host as `.env`'s `DATAVERSE_URL` (preflight P5 verifies this).
   - Confirm `awesome-copilot/dataverse` and `launch-control/*` plugins exist
     under `~/.copilot/installed-plugins/`.
   - Confirm no OAuth bearer tokens, tenant IDs, or org IDs are visible in
     terminal output, file explorer, or the Clawpilot UI.
   - Run `python episodes\ep-13-clawpilot-dataverse\preflight.py` until green.
   - Validate Q3 Widget Launch returns a visually interesting verdict
     (CONDITIONAL or NO-GO with blockers).
2. **Camera 1 — VS Code**
   - Open this README and the `~/.copilot/` tree side-by-side.
   - Highlight the shared-substrate language and the MCP URL pattern.
3. **Camera 2 — Terminal**
   - Run preflight from repo root.
   - Keep the terminal width wide enough for pass/fail lines to stay readable.
4. **Camera 3 — Clawpilot**
   - Ask the hero prompt.
   - If the UI exposes tool traces, expand the Dataverse MCP call.
   - If no trace is visible, show the response and cut back to the architecture.
5. **End card**
   - Same visual template as previous episodes.

---

## Pre-publish checklist

- [ ] Preflight passes (6/6 P-checks + S1 green) on the recording machine.
- [ ] Hero prompt returns live Launch Control data, not a mock answer.
- [ ] No OAuth bearer tokens, tenant IDs, or org IDs are visible in footage.
- [ ] `~/.copilot/mcp-config.json` is shown collapsed or redacted on camera —
      it can contain bearer tokens for HTTP MCP servers.
- [ ] Social copy references this as the new Episode 13.

---

## Cross-references

- [Episode 13 spec](README.md)
- [Ep 1 — Data Modeling](../ep-01-data-modeling/README.md) — initial `dv-connect`
  + `awesome-copilot/dataverse` plugin install
- [Ep 5 — Custom Tools](../ep-05-custom-tools/README.md) — readiness Custom API
- [Ep 7 — Cowork Plugin](../ep-07-cowork-plugin/README.md) — the previous "new
  surface, same MCP" episode (Teams)
- [Ep 13 — The Agent](../ep-08-the-agent/README.md) — declarative hosted surface
- [Ep 10 — The Code-First Agent](../ep-10-code-first-agent/README.md) — same
  skills, different runtime framing
