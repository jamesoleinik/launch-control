# Launch Coordinator (Python edition)

A code-first reimplementation of the **Launch Coordinator** agent first built in
Copilot Studio in [Episode 7](../../episodes/ep-07-the-agent/README.md). Same job. Same
skill. Different runtime.

## The point

By Episode 9 we have *three* agents that all do launch readiness:

| Episode | Runtime | Where it lives | LLM brain |
|---|---|---|---|
| 6 | **Copilot Studio Coordinator** | Microsoft Copilot Studio (hosted) | Copilot Studio |
| 7 | **Launch Sentinel** (autonomous) | Microsoft Copilot Studio (hosted) | Copilot Studio |
| **8** | **Launch Coordinator (Python)** | this folder | GitHub Copilot SDK |

All three load the **same** business skill at runtime via the Dataverse MCP
server:

```
                ┌────────────────────────────────────────┐
                │   business-skills/                     │
                │     launch-readiness-checklist.md      │  ◄── single source
                │     escalation-policy.md               │      of truth
                │     status-transition-rules.md         │
                │     launch-readiness-digest.md         │
                └────────────────────────────────────────┘
                                 ▲   uploaded to Dataverse,
                                 │   surfaced via MCP describe()
                                 │
                ┌────────────────┼─────────────────────┐
                │                │                     │
        Ep 7 Coordinator   Ep 8 Sentinel        Ep 9 Coordinator (this)
        (Copilot Studio)   (Copilot Studio)     (Python + GH Copilot SDK)
```

Edit the markdown in Dataverse, save, and **all three agents change behavior on
their next run** — no agent redeploy.

## Architecture

```
your terminal
    └─► python agent.py
          └─► GitHubCopilotAgent           (agent-framework-github-copilot)
                └─► CopilotClient          (github-copilot-sdk, bundled CLI)
                      ├─► GitHub Copilot API   (LLM)
                      └─► npx @microsoft/dataverse mcp <orgUrl>   (subprocess, stdio)
                            └─► Dataverse MCP server
                                  ├─ describe('skills/Launch Readiness Checklist')
                                  ├─ read_query("SELECT ... FROM lc_milestone ...")
                                  ├─ search("ready for launch")
                                  └─ ...
```

## Prerequisites

1. **Python 3.11+**
   ```powershell
   python --version  # must report 3.11.x or higher
   ```

2. **Node.js 18+** with `npx` on PATH (the agent shells out to
   `npx @microsoft/dataverse mcp ...`).

3. **GitHub Copilot subscription** — Free tier is fine for testing, paid for
   sustained use. The SDK bundles its own Copilot CLI, but you must
   authenticate once:
   ```powershell
   copilot auth login
   ```
   Token is cached in Windows Credential Manager under `copilot-cli`.

4. **Dataverse access** — you must have already authenticated the
   `@microsoft/dataverse` CLI against your org (Episode 1):
   ```powershell
   npx -y @microsoft/dataverse auth create
   ```
   And the Dataverse CLI's app ID must be in the env's MCP allowed clients
   list (run once per environment):
   ```powershell
   npx -y @microsoft/dataverse mcp allow 0c412cc3-0dd6-449b-987f-05b053db9457
   ```

5. **Skills uploaded** — the `Launch Readiness Checklist` skill must already
   exist in the env (uploaded in Episode 2).

## Setup

```powershell
cd agents\launch-coordinator-py
pip install -r requirements.txt
copy .env.example .env
# edit .env and set DATAVERSE_URL=https://<yourorg>.crm.dynamics.com
```

## Run

```powershell
python agent.py
# or:
python agent.py --launch "Q3 Widget Launch"
# or override the prompt entirely:
python agent.py --prompt "What blockers exist on the Q3 Widget Launch?"
```

The first invocation in a session may take 30–60s while the SDK boots its CLI
subprocess and `npx` materializes `@microsoft/dataverse`. Subsequent calls are
faster.

## What to look for in the output

The **on-camera moment** for Episode 9: scroll back through the agent's tool
trace. The first MCP call should be:

```
[mcp.dataverse] describe('skills/Launch Readiness Checklist')
```

That single line is the entire "skills as the brain" thesis — the Python
agent's behavior is being driven by markdown stored in Dataverse, not by code
in this repo. Edit the markdown in Dataverse, re-run, and watch the verdict
change.

## Why the stdio transport (not HTTP)

The Dataverse MCP server also exposes a remote HTTP endpoint at
`<orgUrl>/api/mcp`, but as of writing the Python `MCPServerConfig` `http`
shape doesn't expose a `headers` field, so we can't attach the `Authorization:
Bearer ...` token the remote endpoint requires for non-Microsoft clients. The
stdio path uses the existing CLI auth chain instead — simpler, and the same
chain Episodes 1–7 already rely on.

If you've registered your own Entra app and want to use the HTTP path, you'll
need to extend the SDK's transport config (or wait for a release that exposes
a `headers` parameter).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `copilot: command not found` (in trace) | Run `copilot auth login` once |
| Subprocess hangs at startup | Dataverse CLI auth not cached — run `npx -y @microsoft/dataverse auth create` interactively first |
| `Skill not found` from `describe()` | Skill display name is case- and space-sensitive; must be `skills/Launch Readiness Checklist` (spaces, not hyphens) |
| `MCP server timed out` | First-run `npx` install can be slow; rerun once it finishes downloading |
| Empty verdict | The skill couldn't load and the agent has no fallback — check that `Launch Readiness Checklist` exists via `npx -y @microsoft/dataverse skill list` |

## Files

| File | Purpose |
|---|---|
| `agent.py` | The agent (~50 lines of substance). Wires `GitHubCopilotAgent` to the Dataverse MCP server via stdio. |
| `requirements.txt` | `agent-framework-github-copilot` (pinned beta) + `python-dotenv` |
| `.env.example` | Template for the local `.env` |

## See also

- Episode 7 doc — the Copilot Studio Coordinator that authored the same skill
- Episode 8 doc — Launch Sentinel, autonomous, same brain
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [GitHub Copilot SDK](https://github.com/github/copilot-sdk)
- [Dataverse MCP server](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-mcp)
