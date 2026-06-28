# Ep 10 build plan: Dataverse + Web IQ (parallel CLI session)

This plan lets a separate Copilot CLI session build Episode 10 independently of
the Ep 9 (F&O) and Ep 11 (Fabric IQ) sessions. Read it top to bottom, then work
the checklist. The episode narrative and money shot live in `README.md`; this file
is the build runbook.

## One-line goal

A Copilot Studio agent (new unified builder) that composes **two MCP servers**,
the Dataverse MCP (internal launch state) and the Web IQ MCP (live external
signal), and fuses them into one cited "outside-in" risk briefing for a launch.

## Status entering this session

- **DONE (tested live):** the code-first proof. `webiq_client.py`, `preflight.py`,
  and `fuse_external_signal.py` all run against the live Web IQ MCP
  (`https://api.microsoft.ai/v3/mcp`, server v3.0.0). This is the logic the agent
  will use; the UI build is wiring, not logic.
- **TODO:** the Copilot Studio agent itself (browser-gated), its Instructions, and
  a deterministic seed of the Q3 Widget Launch with two blockers.

## Prerequisites / local config

1. Copy `.env.example` to `.env` in this folder (gitignored) and fill in:
   - `DATAVERSE_URL` (the env where the `lc_` launch tables live and where you will
     build the Copilot Studio agent; the reference test agent "DV + Web IQ" was
     built in the main "Product Launch 2.0" env).
   - `WEBIQ_API_KEY` (request from your Microsoft rep; never commit it).
   - `TENANT_ID`.
2. Select this env in any script: PowerShell `$env:LC_ENV = "ep-10-dataverse-webiq"`.
3. Set `$env:PYTHONIOENCODING="utf-8"` before running Python.

## Build checklist

### A. Verify the substrate (scriptable, do this first)
- [ ] `python episodes/ep-10-dataverse-webiq/preflight.py` exits 0 (endpoint
      reachable, key entitled to `web`). If it fails, the key is wrong or not
      entitled; stop and fix before building the agent.
- [ ] Confirm the Dataverse env has the Q3 Widget Launch with **two blockers**
      ("Security review" and "CDN provisioning"). Reuse the existing seed scripts
      (`scripts/seed_q3_widget_launch.py`, `scripts/seed_q3_sample_tasks.py`) or
      verify with `scripts/python/inspect_launches.py`. The internal half must be
      deterministic so the demo is repeatable.
- [ ] `python episodes/ep-10-dataverse-webiq/fuse_external_signal.py --dataverse --max 5`
      produces a cited briefing from live blocked tasks. This is the exact logic
      the agent reproduces.

### B. Build the agent (Copilot Studio new builder, browser)
- [ ] **Create the Business Skill in Dataverse.** Load
      `business-skills/ep10-outside-in-briefing.md` into the agent's Dataverse env
      as a `skill` record (POST to `/api/data/v9.2/skills` with `name`,
      `uniquename` = `lc_ep10outsidein`, `description`, `body` = the markdown,
      `origin` = 0; idempotent-delete any existing row with that uniquename first).
      See `scripts`-style usage in the Ep 9 session, which created
      `lc_ep09erpreadiness` the same way. The agent must follow this skill.
- [ ] Create the agent. Paste the Instructions from `agent-instructions.md` in
      this folder (create it; mirror the Ep 9 `agent-instructions.md` format:
      role, tools, behavior, money-shot script).
- [ ] Add **Tool 1: Microsoft Dataverse MCP Server (Preview)** for internal state.
- [ ] Add **Tool 2: Web IQ MCP Server**. Endpoint `https://api.microsoft.ai/v3/mcp`,
      auth via `x-apikey` header (API key) or Entra ID token. Keep `news`, `web`,
      `browse` in scope; leave `finance`/`sports`/`places` off-narrative.
- [ ] Pick the model in the builder.
- [ ] (Optional) Enable Memory (Preview) for multi-turn "walk me through each
      blocker".
- [ ] Preview with the money-shot prompt, then Publish.

### C. Validate the money shot
- [ ] Prompt: "Give me the external risk picture for the Q3 Widget Launch."
- [ ] The agent returns internal blockers (Dataverse) + live external signal
      (Web IQ `news`/`web`/`browse`) and **cites a source for every external
      claim**. Web results drift, so confirm the live answer the morning of the
      shoot and stage a backup query (see README pre-record checklist).

## Deliverables this session should produce

1. `episodes/ep-10-dataverse-webiq/agent-instructions.md` (paste-ready Instructions,
   same shape as Ep 9's).
2. A short note in `README.md` under a "Build status" line recording that the
   agent is built + the money shot validated (date, model picked).
3. No secrets committed: the Web IQ key stays in the gitignored `.env` only.

## Guardrails

- No em-dashes in committed prose. No real env URLs / tenant IDs / GUIDs / the
  Web IQ key in any committed file (use placeholders; actuals live in `.env`).
- Do not duplicate external content into Dataverse rows; the whole point is that
  live web signal is retrieved fresh, never stored (the README "complement, not
  duplicate" rule).

## Hand-off / coordination with the other sessions

- Ep 10 is the most self-contained of the three: its code is already proven and it
  shares no environment with Ep 9 (F&O) or Ep 11 (Fabric). Safe to run fully in
  parallel.
- The only shared asset is the `lc_` launch model and the Q3 Widget Launch seed.
  If your Dataverse env is the same one another session is seeding, coordinate so
  you do not both reseed; otherwise seed your own env.
