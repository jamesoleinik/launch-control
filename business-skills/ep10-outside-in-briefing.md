# Outside-In Risk Briefing (internal blockers meet live web signal)

## Description

The Season 2 / Episode 10 Business Skill for the Dataverse + Web IQ agent. The
agent composes two MCP servers: the Dataverse MCP for internal launch state and the
Web IQ MCP for live external signal. This skill defines how it fuses them into one
cited "outside-in" risk briefing, surfacing the external risk the internal data
cannot see and tying it back to the specific internal blockers it affects.

## Instructions

### Step 1: Resolve the launch and its blockers (Dataverse)

Resolve the launch (ask if not named). Using the Dataverse MCP, read its open and
blocked work from `lc_task` (blocked = `lc_taskstatus` Blocked; title is
`lc_title`), the milestone health from `lc_milestone`, and the readiness score if
the `lc_launchreadiness` Custom API is present. This is the internal half and it
must be deterministic.

### Step 2: Refresh the external picture (Web IQ)

For each material internal blocker, query the Web IQ MCP for live signal that makes
that blocker more or less risky:

- `news`: vendor outages, competitor moves, market events tied to the blocker.
- `web` and `browse`: the authoritative source behind a blocker (for example an NVD
  CVE page behind a "security review" blocker).
- `videos` / `images`: only when a visual genuinely helps.

Web signal is retrieved fresh on every ask and is **never** stored.

### Step 3: Fuse and cite (POLICY)

For each blocker, state whether the live external signal raises, lowers, or does
not change its risk, and cite the external source by name and URL. The verdict for
the launch is the join: an internal blocker plus a corroborating external event is a
higher-confidence escalation than either alone.

Every external claim must carry a citation. If the web returns nothing relevant for
a blocker, say so rather than inventing a connection.

### Step 4: Report

- Lead with the overall external-risk posture.
- For each blocker: the internal fact (Dataverse row) + the external signal (Web IQ
  source with URL) + the fused recommendation.
- Recommend the next action (escalate, monitor, or clear).

## What this skill is NOT

- It does **not** create a Dataverse row for any web fact. If a fact is the live
  outside world, it stays in Web IQ; if it is a launch row, it stays in Dataverse.
  Nothing lives in both places, so nothing is duplicated.
- It does **not** make an external claim without a citation.
- It does **not** treat a stale cached result as live. Confirm the signal is
  current; web results drift.
