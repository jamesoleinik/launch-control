# Episode 13 — Recording Script

> 🙈 **Hidden episode.** Not in the public `episodes/README.md` index, no
> social assets in `social/` yet. This script lives in the episode folder.

**Working title:** *"Microsoft 365 Copilot, meet your Dataverse."*
**Target length:** 1:15 (75 seconds)
**Voiceover target:** ~150 words
**Hero pattern:** [MCP Apps in Copilot Chat](https://devblogs.microsoft.com/microsoft365dev/mcp-apps-now-available-in-copilot-chat/)
**Hero file in repo:** `episodes/_ep-14-copilot-mcp-app/declarative-agent/appPackage/actions/dataverse-mcp.action.json`

---

## What the viewer sees

| Time | Camera / capture | Action |
|---|---|---|
| **0:00–0:08** | VS Code, M365 Agents Toolkit sidebar open, project = `declarative-agent` | Quick pan over the project tree: `manifest.json`, `declarativeAgent.json`, `actions/dataverse-mcp.action.json`. Title card: *"Microsoft 365 Copilot, meet your Dataverse."* |
| **0:08–0:18** | VS Code zoomed into `dataverse-mcp.action.json` | Highlight `"type": "ModelContextProtocol"`, the `spec.url` pointing at `https://<org>.crm.dynamics.com/api/mcp`, and the `OAuthPluginVault` auth block. Caption: *"One file. The Dataverse MCP server, as a Copilot action."* |
| **0:18–0:35** ⭐ | Toolkit sidebar → **Lifecycle → Provision** | Provision runs end-to-end: Teams app reg, Entra app reg, OAuth registration, app package zip + validate, upload to Teams catalog. The output panel scrolls. **Hero shot.** |
| **0:35–0:45** | M365 Admin Center tab — Integrated Apps → approve | Single click, agent approved. Cut. |
| **0:45–0:58** | https://m365.cloud.microsoft/chat — Agents rail | Find **Launch Control** in the rail, click. Type: *"What's the readiness for Q3 Widget Launch?"* Submit. |
| **0:58–1:10** | Same chat | Agent calls the Dataverse MCP action. Response renders as a readiness card: verdict pill (NO-GO), score, and the blocking milestones. |
| **1:10–1:15** | End card | *"Same Dataverse. Every Copilot. Episode 13."* + repo link. |

---

## Prompts to type on camera

**Beat A — the hero file** (no typing, just hover)

> `episodes/_ep-14-copilot-mcp-app/declarative-agent/appPackage/actions/dataverse-mcp.action.json`

**Beat B — the toolkit command**

> `Microsoft 365 Agents: Provision`
> (via the command palette, so the keystrokes are visible)

**Beat C — the agent question**

> What's the readiness for Q3 Widget Launch?

(Optional follow-up if there's time in the cut)

> What blockers are driving the verdict, and what does our playbook say about slipping?

---

## Captions (SRT)

```
1
00:00:00,000 --> 00:00:08,000
Twelve episodes of Dataverse, MCP, and agents. Now the front door
everyone in the enterprise actually uses: Microsoft 365 Copilot.

2
00:00:08,000 --> 00:00:18,000
One file. The Dataverse MCP server, registered as a declarative
agent's action. OAuth, scopes, transport — all declarative.

3
00:00:18,000 --> 00:00:35,000
Provision: the Microsoft 365 Agents Toolkit creates the Teams app,
the Entra app registration, the OAuth binding, packages the agent,
and uploads it to the tenant catalog. One command.

4
00:00:35,000 --> 00:00:45,000
Approve in the admin center. Now Launch Control is in the Agents
rail of M365 Copilot for every user in the tenant.

5
00:00:45,000 --> 00:00:58,000
Ask it a launch question. It hits the same Dataverse MCP server we
configured in Episode 1, calls the same readiness skill we built in
Episode 5.

6
00:00:58,000 --> 00:01:10,000
Same Dataverse. Same business skills. New surface — and with MCP Apps
the answer can render as a rich card right inside chat.

7
00:01:10,000 --> 00:01:15,000
Same Dataverse. Every Copilot. Repo's in the description.
```

---

## Voiceover script (4 blocks, ~150 words)

**Block 1 (0:00–0:08, ~22 words)**

> "Twelve episodes building agentic launch management on Dataverse.
> The last surface nobody's seen yet is the one every knowledge worker
> already has open — Microsoft 365 Copilot."

**Block 2 (0:08–0:35, ~50 words)**

> "Thanks to MCP Apps in Copilot Chat, you don't write a plugin.
> You write one action file pointing at your Dataverse MCP endpoint,
> set OAuth, and let the Microsoft 365 Agents Toolkit provision the
> Entra app registration, the OAuth binding, the Teams catalog
> upload — end to end, from VS Code, in one click."

**Block 3 (0:35–0:58, ~38 words)**

> "Approve in the admin center, and Launch Control shows up in
> Microsoft 365 Copilot for the entire tenant. Ask it a launch
> question. It hits the same Dataverse MCP server from Episode 1
> and calls the same readiness Custom API from Episode 5."

**Block 4 (0:58–1:15, ~40 words)**

> "Zero new code. Zero new tools to install for the user. The same
> data model, the same business skills, the same readiness scoring,
> now in the chat surface your CEO already uses. Same Dataverse.
> Every Copilot. Repo's in the description."

---

## Word-count check (~150 words)

22 + 50 + 38 + 40 = **150 words** in the voiceover, on target for a
1:15 cut at ~120 WPM.

The narrative beat closing the series: every preceding episode added
*capability* to Dataverse — tables, virtual entities, custom APIs,
business skills, MCP server. This episode adds *reach*. MCP Apps is
the missing leg of the platform story, taking the same MCP server we
used from the coding agent in Ep 1 and exposing it through the front
door enterprises live in. No new agent code, no new SDK, no Copilot
Studio runtime; just one action file and the Microsoft 365 Agents
Toolkit doing the deployment plumbing.

---

## Recording workflow

1. **Off-camera prep** (follow `declarative-agent/BUILD.md`):
   - Fill `env\.env.dev` with `DATAVERSE_HOST`.
   - Drop icons into `appPackage\`.
   - Run **Provision** once to mint the Entra app reg + OAuth binding.
   - Grant tenant admin consent for the new client ID.
   - Add the new client ID to **PPAC → Features → MCP Server → Allowed
     clients**.
   - Smoke-test in M365 Copilot with the readiness question. Verify the
     MCP tool list, OAuth consent prompt, and a successful answer.
   - Reset the readiness data: ensure Q3 Widget Launch produces a
     visually interesting verdict (CONDITIONAL or NO-GO with at least 2
     blockers, so the answer isn't one boring line).
2. **Camera 1 — VS Code** (screen capture, 1920x1080):
   - Beat A: pan over the project tree.
   - Beat B: open `dataverse-mcp.action.json`, highlight the three key
     fields.
   - Beat C: Cmd-Shift-P → "Microsoft 365 Agents: Provision".
3. **Camera 2 — Microsoft 365 Copilot** (clean browser, no extensions):
   - Agents rail → Launch Control.
   - Type the readiness question. Submit. Capture the answer rendering.
4. **End card**: same template as Ep 1 + Ep 2 (repo URL bottom-right).

---

## Pre-publish checklist before promoting out of `_ep-13-`

- [ ] Recorded video reviewed and approved.
- [ ] `episodes/_ep-14-copilot-mcp-app/` renamed to
      `episodes/ep-13-copilot-mcp-app/`.
- [ ] `episodes/README.md` index updated.
- [ ] `social/linkedin-posts/ep-13-copilot-mcp-app.md` written in the
      Ep 1/Ep 2 format.
- [ ] `social/video-scripts/ep-13-copilot-mcp-app.md` copied from this
      file (with paths fixed to drop the `_` prefix).
- [ ] Series-wide ToC / `README.md` updated.

---

## Cross-references

- [Ep 13 spec](README.md) (this folder)
- [BUILD.md](declarative-agent/BUILD.md) — off-camera plumbing
- [Ep 1 — Data Modeling](../ep-01-data-modeling/README.md) — original MCP setup
- [Ep 7 — The Agent](../ep-07-the-agent/README.md) — the Copilot Studio
  contrast point (same data, different surface)
- [Ep 13 — Full Orchestra](../ep-13-full-orchestra/README.md) — finale that
  this exploration may collapse into

> Reference: [MCP Apps now available in Copilot
> Chat](https://devblogs.microsoft.com/microsoft365dev/mcp-apps-now-available-in-copilot-chat/),
> Microsoft 365 Dev Blog, March 9, 2026.
