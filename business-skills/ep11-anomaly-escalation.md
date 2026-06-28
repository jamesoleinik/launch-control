# Anomaly Escalation (live state versus the semantic baseline)

## Description

The Season 2 / Episode 11 Business Skill for the Dataverse + Fabric IQ autonomous
agent. The agent reasons over two planes: the live per-launch state (Dataverse MCP)
and the semantic baseline of the business (a Fabric IQ ontology over Microsoft
Fabric). This skill defines how it decides what is genuinely abnormal and escalates
only those cases, writing a single grounded `lc_statusupdate`. It runs on a
schedule, not on a human prompt.

## Instructions

### Step 1: Read the live per-launch state (Dataverse)

On each scheduled sweep, using the Dataverse MCP, read for each active launch:

- the blocked task count (`lc_task` where `lc_taskstatus` is Blocked),
- the milestone slip signal (`lc_milestone` AtRisk or Blocked),
- the current readiness trajectory.

### Step 2: Read the semantic baseline (Fabric IQ)

Using the Fabric IQ Ontology MCP, read the modeled norm for this launch's phase:
the expected blocker count, the typical slip rate, the healthy readiness curve. The
baseline is learned across every launch the business has run; it is not a Dataverse
row.

### Step 3: Decide (POLICY)

Escalate only when the live Dataverse state diverges from the Fabric IQ norm beyond
the threshold. A raw count is never the trigger; the trigger is the count relative
to the modeled norm.

- Within the modeled norm: do nothing.
- Beyond the threshold (for example a 95th-percentile anomaly, or a pattern that
  historically preceded a slip): escalate.

### Step 4: Escalate idempotently

For a genuine anomaly, write one `lc_statusupdate` (the same effector as the Season
1 Sentinel) that:

- states the live figure and the modeled norm ("8 blocked vs a modeled 2 to 3"),
- names the pattern it matches if any ("matches launches that later slipped"),
- is written once per anomaly per sweep. Before writing, check for an existing
  update for the same launch and finding in this window and skip if present.

## What this skill is NOT

- It does **not** copy the Fabric IQ baseline, KPI, or trend into a Dataverse row.
  Learned analytics stay in Fabric IQ; only the escalation note is written to
  Dataverse.
- It does **not** escalate on a raw count alone. Without a baseline comparison there
  is no escalation.
- It does **not** double-post. Idempotency across sweeps is mandatory.
- It does **not** wait to be asked. The runtime is autonomous (scheduled or event).
