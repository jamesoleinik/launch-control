# Episode 11: Agent Quality Gate

> *What changes when an AI agent gets its own identity and a governed place in
> a business process?*

## The hook

Launch Control now has a **Launch Approval** business process flow. When a
launch enters Quality Gate, Dataverse gives a narrowly scoped Agentic User one
assignment and access to one Launch.

The local agent tests the release with Playwright, writes an attributable
result, and leaves the approval decision with a person. The demo launch starts
Green but finishes **Needs Review, 70** because the real journey exposes a
hidden telemetry failure.

The browser test is the proof mechanism, not the main result. The main result
is a governed nonhuman worker whose identity, permissions, assignment,
evidence, and actions are visible in the same business process.

```text
Process -> Agent -> Identity -> Evidence -> Human decision
```

> **Preview note:** Microsoft Entra Agent ID and Dataverse agent users are
> public-preview capabilities. Validate current availability, licensing, and
> supported provisioning paths before using this pattern outside a demo
> environment.

## The build: four sections

Each section starts with a short GitHub Copilot prompt. Copilot uses the
committed scripts and skills, previews mutations before applying them, keeps
local configuration private, and stops when verification fails.

```text
Section 1  Process and app  -> Dataverse workflow, rules, PCF, and focused app
Section 2  Local agent      -> Agents SDK worker and Playwright evidence
Section 3  Identity         -> Agent 365, Entra Agent ID, and Dataverse access
Section 4  Live proof       -> assignment, check, result, and process outcome
```

## Section 1: Build the process and app

The process contract comes first. Dataverse defines when the work is assigned,
which Launch the agent may access, what result it may submit, and which
outcomes may advance.

```text
Draft -> Quality Gate -> Launch Approval -> Ready to Launch
              |
              +-- create one agent-owned task
              +-- share only the assigned Launch
              +-- accept one result from the assigned agent
              +-- advance only when the result is Passed
```

### Prompt

> *Build a Dataverse business process flow called Launch Approval for the
> Launch table, with Draft, Quality Gate, Launch Approval, and Ready to Launch
> stages. Add the server-side guardrails, a Launch Readiness PCF beside the
> timeline, and a model-driven app that only shows Launches.*

### Result

One prompt produces the business workflow, custom control, focused app, and
server-side business rules in Dataverse:

- **Launch Approval** BPF: Draft, Quality Gate, Launch Approval, Ready to
  Launch.
- One agent-owned assignment when a Launch first enters Quality Gate.
- Assignment-scoped sharing for only that Launch.
- Server-side validation that accepts results only from the assigned Agentic
  User.
- Passed may advance. Failed, Needs Review, and Error stay at Quality Gate.
- Launch Readiness PCF beside the timeline in a 60/40 layout.
- A dedicated model-driven app with only the **Launches** navigation entry.
- BPF, backing table, plug-ins, PCF, form, app, and sitemap in the
  `LaunchControl` solution.

### Run it

> *Deploy Section 1 and verify the active Dataverse BPF, plug-ins, PCF control,
> form layout, and Launches-only model-driven app.*

## Section 2: Build the local agent

The local runtime has two parts: a Microsoft 365 Agents SDK host and a
deterministic assignment worker. The worker combines structured Dataverse
evidence with experiential Playwright evidence from the release candidate.
It does not call an LLM. A model could be added later without changing the
process, assignment, identity, or enforcement boundaries.

### Prompt

> *Build a local Python Quality Gate agent with the Microsoft 365 Agents SDK.
> Have it pick up Dataverse task assignments, test the release with Playwright,
> and write back a Quality Gate result with trace and screenshot evidence.*

### Result

- Microsoft 365 Agents SDK host with status and run handlers.
- Idempotent Dataverse assignment worker.
- Deterministic readiness analysis over Dataverse and browser evidence.
- Playwright journey with trace, console, HTTP, workflow, and screenshot
  evidence.
- Needs Review for a failed business journey rather than a worker crash.
- Remediation task, Yellow status update, and timeline evidence.
- `--wait-once` mode for the recorded demo.

### Run it

> *Start the local demo site and trace viewer, then run the standalone
> Playwright quality check. Do not run the Dataverse worker yet.*

The governed worker waits until Section 3 gives it a verified identity.

## Section 3: Give the agent its identity with Agent 365

The identity chain makes the worker attributable instead of hiding it behind
the developer or a shared application identity. The Agentic User receives
`Basic User`, `lc Quality Gate Agent`, ownership of its assignment, and
temporary access to only the Launch under review. It cannot update the Launch
or manipulate the BPF directly.

### Prompt

> *Use the Agent 365 tooling to register the local Quality Gate agent and
> provision its Entra Agent ID. Create its Agentic User, prepare least-privilege
> Dataverse access, then stop when I need to add the agent user in Power
> Platform admin center.*

### On camera: add the agent user to Dataverse

This is the key identity handoff. Record it as part of Section 3:

1. Open the target environment in **Power Platform admin center**.
2. Open **Settings > Users + permissions > Agent users**.
3. Select **Add agent**.
4. Choose **Launch Control Quality Gate Agent** and add it to the environment.
5. Open the new Dataverse agent user and select **Manage security roles**.
6. Assign exactly **Basic User** and **lc Quality Gate Agent**.
7. Save and hold on the two-role list for the recording.

The Entra Agentic User is now a Dataverse security principal. Dataverse can
control which tables, rows, and operations the agent can access.

### Result

- Agent 365 registration for the existing local agent runtime.
- Agent 365 tooling provisions the blueprint and tenant-local Agent Identity.
- Tenant-local Agent Identity and one parented Entra Agentic User.
- Dataverse agent user added through
  **Users + permissions > Agents > Add agent**.
- Exactly `Basic User` and `lc Quality Gate Agent`.
- Genuine Agent User OAuth verified by Dataverse `WhoAmI`.
- Access denied before assignment, granted for the assigned Launch, and revoked
  after completion.
- Agentic User-authored Teams completion message.
- Separate native Dataverse MCP proof using the same identity and roles.

### Run it

After the on-camera Power Platform admin center handoff:

> *Verify the Entra Agentic User, Dataverse agent user, two security roles, and
> assignment-scoped access. Run the live outcome checks with genuine Agent User
> OAuth.*

Record the provisioning handoff once. Do not remove and recreate the Dataverse
agent user between demo takes. Use the verification output as the repeatable
pickup after the first recording.

## Section 4: Run the demo

The final section runs the complete workflow rather than simulating the
outcome. The launch begins Draft, Green, and Pending. Moving it into Quality
Gate creates the assignment and the scoped access that let the waiting agent
perform its job.

### Prompt

> *Reset Q3 Widget Launch to Draft, open a clean trace viewer, and start the
> genuine Agentic User worker waiting for one Dataverse task. Tell me when to
> advance the Launch Approval BPF to Quality Gate in the model-driven app.*

### Demo flow

1. Show **Draft**, **Green**, and Quality Gate **Pending**.
2. Advance the Launch from **Draft** to **Quality Gate**.
3. Show the new assignment owned by the Agentic User.
4. Watch the waiting worker open Playwright and test the release.
5. Open the failed telemetry check and screenshot in the trace viewer.
6. Refresh the Launch.
7. Show **Needs Review**, score **70**, Yellow health, and the remediation task.
8. Show the same evidence in the Dataverse timeline.
9. Confirm the BPF remains at **Quality Gate**.
10. Open the Agentic User-authored Teams message and follow its Launch link.
11. Explain that the agent did the work, but a person owns the decision.

---

## Appendix

### A. Local setup

Prerequisites:

- Existing Launch Control Dataverse environment and unmanaged
  `LaunchControl` solution.
- Python, Node.js, .NET build tools, Power Platform CLI, and Playwright
  Chromium.
- A gitignored `episodes/ep-11-agent-quality-gate/.env`.

Ask Copilot:

> *Prepare the Episode 11 Python environment, install Playwright Chromium, load
> the local Dataverse configuration, and tell me if setup is ready.*

Required recording configuration:

```text
DATAVERSE_URL
TENANT_ID
A365_AGENT_ID
A365_AGENT_USER_ID
QUALITY_GATE_AGENT_SYSTEMUSER_ID
A365_BLUEPRINT_CLIENT_ID
A365_BLUEPRINT_CLIENT_SECRET
```

An approved `A365_TOKEN_BROKER_URL` can replace the short-lived blueprint
secret. Teams also requires `A365_TEAMS_RECIPIENT` and
`LAUNCH_CONTROL_APP_ID`.

Never commit or display environment URLs, tenant IDs, application IDs, user
IDs, UPNs, tokens, or secrets.

### B. Fresh-session prompts

Build everything:

> *Build and verify the Dataverse process, local agent, and Agentic User from
> Sections 1 through 3. Stop at any required portal handoff.*

Check readiness without changing demo data:

> *Run the Dataverse, BPF, plug-in, PCF, Teams, and Agent User OAuth readiness
> checks without changing demo data. Tell me what is blocking.*

Reset between takes:

> *Reset Q3 Widget Launch to Draft, Green, and Pending, clear the trace viewer,
> and tell me when the next take is ready.*

Final validation:

> *Run the Episode 11 tests and verify the Dataverse BPF, plug-ins, PCF,
> Agentic User OAuth, and Teams setup. Tell me if it is ready to record.*

### C. Recording identity proof

Do not claim a genuine Agent User run unless all of these are true:

1. Graph reports `#microsoft.graph.agentUser`.
2. Its `identityParentId` matches the intended Agent Identity.
3. Dataverse reports `systemmanagedusertype = 3`.
4. The user is enabled and has exactly the two expected roles.
5. Strict preflight reports zero failures.
6. Dataverse `WhoAmI` equals the configured agent `systemuserid`.
7. The worker reports:

```text
Identity mode: Microsoft Entra Agent User OAuth test flow
```

`--allow-dev-identity` and `QUALITY_GATE_IMPERSONATE_AGENT` are development
fallbacks. They are not proof of genuine Agent User OAuth.

### D. Runtime boundaries

- The worker uses direct Dataverse REST today.
- Native Dataverse MCP was proven separately with the same Agentic User.
- The agent creates the result. A trusted plug-in validates it and changes the
  Launch and BPF.
- The agent cannot update the Launch or manipulate the BPF directly.
- Readiness is deterministic and does not call an LLM.
- Teams uses delegated Microsoft Graph as the Agentic User.
- Agent 365 does not provide a Teams workload license. The Agentic User also
  needs a Microsoft 365 license containing Teams.

### E. Recording checklist

- [ ] Launch form hard-refreshed.
- [ ] PCF and timeline render side by side.
- [ ] Launch Control Quality Gate app opens to Launches.
- [ ] Demo site and trace viewer respond.
- [ ] Strict preflight passes with genuine Agent User OAuth.
- [ ] Q3 Widget Launch is Draft, Green, and Pending.
- [ ] No prior assignment, result, remediation, or evidence remains.
- [ ] Entering Quality Gate creates exactly one agent assignment.
- [ ] Needs Review remains at Quality Gate.
- [ ] Result, remediation, and evidence are attributed to the Agentic User.
- [ ] Teams message is authored by the Agentic User.
- [ ] Teams deep link opens the same Launch.

### F. Main artifacts

| Path | Purpose |
|---|---|
| `RESEARCH.md` | Identity, preview, and product-boundary findings |
| `BPF.md` | Process, plug-in, assignment, and security design |
| `SKILL.md` | Detailed implementation and repair runbook |
| `setup_dataverse.py` | Quality Gate schema and least-privilege role |
| `register_plugin.py` | Plug-in build and registration |
| `preflight.py` | Read-only recording checks |
| `reset_demo.py` | Restore the opening state |
| `seed_demo.py` | Headless Quality Gate assignment |
| `test_plugin_live.py` | Four-outcome plug-in matrix |
| `test_mcp_bpf_live.py` | Native MCP and governed BPF proof |
| `test_teams_live.py` | Teams sender and deep-link proof |
| `agent/worker.py` | Assignment and result orchestration |
| `agent/quality_check.py` | Playwright evidence |
| `trace_server.py` | Local trace viewer |
| `../../apps/launch-readiness-control/` | PCF and form deployment |

### G. Verified build

- Fourteen Episode 11 unit tests.
- Active four-stage Launch Approval BPF.
- Registered assignment and result plug-ins.
- Launch Readiness PCF version 1.5.1.
- Governed direct REST and native MCP result paths.
- Agentic User-authored Teams update.

### H. Related material

- [Research and identity findings](RESEARCH.md)
- [BPF and enforcement details](BPF.md)
- [Technical skill and repair guide](SKILL.md)
- [Series index](../README.md)
