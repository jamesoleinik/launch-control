# Episode 11: Agent Quality Gate

---

## The hook

> *"The launch team says Green. Before we ship, can an AI agent independently
> validate that claim, show its evidence, and still stay inside a governed
> business process?"*

Launch Control now has a **Launch Approval** business process flow (BPF). When
a launch enters Quality Gate, Dataverse assigns a narrowly scoped Agentic User
to review it. A local worker reads the assigned launch, runs a critical user
journey with Playwright, captures visual evidence, and writes its verdict back
as that agent.

The launch starts **On Track and Green**. There are no visible blockers, no
overdue work, and no Quality Gate score. The reveal comes from the independent
validation: the browser journey exposes a broken telemetry-consent route. The
agent attaches the screenshot, creates a blocked remediation task, posts a
Yellow status update, and returns **Needs Review, 70**. The BPF remains at
Quality Gate for a human decision.

The browser test is not the main result. The main result is a governed
nonhuman worker whose identity, permissions, assignment, evidence, and actions
are all visible in the same business process.

> **Preview note:** Dataverse agent users and Entra Agentic Users are preview
> capabilities. Validate current availability, licensing, and supported
> provisioning paths before using this pattern outside a demo environment.

## The build: four sections

The build follows the same developer-with-a-coding-agent pattern as the other
Launch Control episodes. In each section, the developer gives the coding agent
one outcome-oriented prompt, reviews what it creates, and runs the visible
proof. When a preview capability still requires a portal action, the coding
agent discovers the correct boundary, prepares everything it can, and gives
the developer the exact supported step.

```text
Section 1  Process     -> coding agent builds the BPF, assignment, and plug-in guardrails
Section 2  Agent       -> coding agent builds the worker and Playwright evidence path
Section 3  Identity    -> coding agent provisions the principal and least-privilege access
Section 4  Experience  -> coding agent builds the PCF, timeline, and recording state
```

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored),
> fill in the environment-specific values, set
> `LC_ENV=ep-11-agent-quality-gate`, and set
> `PYTHONIOENCODING=utf-8`. Never commit tenant IDs, application IDs,
> environment URLs, user IDs, UPNs, or credentials.

## Setup (before Section 1)

This episode requires the Launch Control Dataverse environment and unmanaged
`LaunchControl` solution from the earlier episodes. It also requires Node.js,
Python, the Power Platform CLI, .NET build tools for the plug-in, and
Playwright Chromium.

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:LC_ENV="ep-11-agent-quality-gate"

pip install -r episodes\ep-11-agent-quality-gate\requirements.txt
playwright install chromium
```

## Section 1 · Build the governed Quality Gate process

The developer starts by asking the coding agent to define the process contract:
the data the worker will read and write, the stage where work is assigned, and
the server-side rules that decide whether the launch can advance.

```text
Draft -> Quality Gate -> Launch Approval -> Ready to Launch
              |
              +-- create one agent-owned task
              +-- share only the assigned Launch
              +-- accept one result from the assigned agent
              +-- advance only when the result is Passed
```

### The prompt

> *Create a Launch Approval business process flow over lc_launch with Draft,
> Quality Gate, Launch Approval, and Ready to Launch stages. When the process
> enters Quality Gate, assign one durable task to the Dataverse agent user and
> grant access only to that Launch. Accept a Quality Gate Result only from the
> assigned Agentic User. Passed may advance; Failed, Needs Review, and Error
> must remain at Quality Gate.*

### What the coding agent produces

- The active **Launch Approval** BPF with each Quality Gate field included
  exactly once.
- The generated BPF backing table included in the `LaunchControl` solution.
- A synchronous assignment plug-in that creates one agent-owned task and
  grants scoped access to the related Launch.
- A synchronous result plug-in that validates identity, assignment, and
  idempotency before applying the outcome.
- Cleanup that revokes assignment-scoped shares without trying to revoke
  records owned by the Agentic User.

The agent role does not have Launch write permission and the BPF is not
available to the agent. The plug-in uses the system organization service for
the governed process transition.

### What you run on screen

```powershell
Set-Location episodes\ep-11-agent-quality-gate

python setup_dataverse.py --dry-run
python setup_dataverse.py --apply
python register_plugin.py --dry-run
python register_plugin.py --apply
python register_plugin.py --verify
```

At this point the process, schema, role definition, and plug-in steps exist.
The live identity and four-outcome matrix are connected in Section 3.

For the complete stage definition, registration model, security boundary, and
programmatic BPF builder, see [BPF.md](BPF.md).

## Section 2 · Build the local Quality Gate agent runtime

The coding agent builds the runtime in two layers:

1. A **Microsoft 365 Agents SDK host** exposes an authenticated agent endpoint
   and handles `status` and `run quality gate` messages.
2. A **deterministic background worker** polls Dataverse assignments, gathers
   evidence, runs the browser journey, calculates the readiness result, and
   publishes the governed outcome.

The worker uses two evidence planes:

- **Structured evidence** from Dataverse: Launch, milestones, tasks, status
  updates, and prior Quality Gate state.
- **Experiential evidence** from Playwright: whether a critical user journey
  actually works in the release candidate.

The committed demo target deliberately fails its telemetry-consent request.
That defect is hidden from the initial Green Dataverse state and is discovered
only when the agent exercises the browser workflow.

### The prompt

> *Build a local Python Quality Gate agent using the Microsoft 365 Agents SDK.
> Give it an authenticated message endpoint with status and run commands, plus
> a background worker that polls open Dataverse assignments. For each assigned
> Launch, gather the related milestones, tasks, and status updates; run a
> Playwright critical user journey; capture HTTP, title, required-content,
> workflow-state, console, and screenshot evidence; calculate a deterministic
> readiness result; and publish the attributable verdict and remediation
> artifacts. Treat a failed business journey as Needs Review, not as a worker
> crash.*

### What the coding agent produces

- A Microsoft 365 Agents SDK `AgentApplication` hosted through `aiohttp`.
- Authenticated `status` and `run quality gate` message handlers.
- A local Python worker that can run once or poll on a configured interval.
- Idempotent assignment processing and an existing-result check.
- Deterministic readiness analysis over Dataverse and browser evidence.
- A Playwright validator that clicks **Validate release telemetry**.
- Evidence for response status, title, required content, workflow result,
  browser console, and a full-page PNG.
- A local trace event stream with screenshot attachment metadata.
- A secure local evidence endpoint and trace-viewer thumbnail.
- A blocked remediation task, Yellow status update, and PNG note attached to
  the Launch timeline.

Microsoft Agent 365 connects the agent to enterprise identity, observability,
governed tools, and notifications. It does not build or host the worker. The
runtime in this episode is the Microsoft 365 Agents SDK.

This implementation does not call an LLM. It is an autonomous, identity-bearing
quality worker with deterministic decision logic. The governance pattern does
not depend on probabilistic reasoning, and a model could be added later without
changing the BPF, assignment, identity, or plug-in boundaries.

The committed worker currently uses direct Dataverse REST calls. A separate
live proof shows that the same Agentic User can read Dataverse and submit the
governed result through the native Dataverse MCP server. Do not describe the
worker itself as MCP-based until its runtime client is replaced.

### What you run on screen

Start the release candidate:

```powershell
python -m http.server 8000 --bind 127.0.0.1 `
  --directory episodes\ep-11-agent-quality-gate\demo-site
```

Start the trace viewer:

```powershell
python episodes\ep-11-agent-quality-gate\trace_server.py
```

Run the visual browser validation:

```powershell
Set-Location episodes\ep-11-agent-quality-gate
$env:QUALITY_GATE_DEMO_MODE="true"
$env:QUALITY_GATE_DEMO_STEP_SECONDS="1.2"
$env:QUALITY_GATE_DEMO_HOLD_SECONDS="8"

python -m agent.quality_check --launch-name "Episode 11 Release"
```

Open `http://127.0.0.1:8765` to see the ordered trace and screenshot evidence.

## Section 3 · Give the agent its governed identity and access

Only after the process and worker contracts exist does the developer ask the
coding agent to establish the identity chain. This makes every Dataverse action
attributable to the agent instead of the developer or a shared service account.

The agent does not receive access to manipulate the BPF. Human Launch Control
roles can use the process. The Agentic User receives `Basic User`,
`lc Quality Gate Agent`, ownership of its assignment task, and temporary access
to only the Launch it has been assigned to review.

### The prompt

> *Set up a governed identity for the Quality Gate worker in the same tenant as
> my Launch Control Dataverse environment. Use Agent 365 and Microsoft Entra
> Agent ID, create or reuse the required Agentic User, add it to Dataverse as an
> agent user, and assign only the roles required by the worker we just built.
> Verify that it can research an assigned Launch and create the expected result
> and remediation records, but cannot update the Launch or move the BPF
> directly. Build a preflight that proves the directory identity, token caller,
> Dataverse principal, and roles all match. Use supported APIs where available
> and stop with an exact portal handoff where the preview does not expose a
> supported automation path.*

### What the coding agent produces

- An Agent 365 blueprint and tenant-local Agent Identity.
- One Entra Agentic User whose `identityParentId` points to that identity.
- An idempotent Graph check that reuses the Agentic User rather than creating a
  duplicate.
- The exact supported PPAC handoff:
  **Users + permissions > Agents > Add agent**.
- One enabled Dataverse agent user selected from that Agentic User.
- Exactly two assigned roles: `Basic User` and `lc Quality Gate Agent`.
- Assignment-scoped sharing that exposes only the Launch under review.
- A read-only preflight that verifies tenant, caller, principal type, role
  assignment, and required runtime configuration.
- Local ignored configuration for every environment-specific identifier.
- Delegated Graph `Chat.Create` and `ChatMessage.Send` consent for the
  Agentic User-authored completion message.
- Agent 365 plus a Microsoft 365 license that includes the Teams service plan.

The Agent Identity and Dataverse environment must be in the same Entra tenant.
A multitenant blueprint can create a tenant-local identity elsewhere, but an
identity from one tenant cannot be reused as the Dataverse principal in
another.

The Agentic User is distinct from its parent Agent Identity. The Power Platform
Agents picker selects the Agentic User. Do not substitute an application user
or create a `systemuser` directly through OData.

Agent 365 licensing alone does not provision Teams. The live notification proof
also required a Microsoft 365 license containing the `TEAMS1` service plan.
Microsoft documents Microsoft 365 E5 or equivalent plus Teams Enterprise as the
common prerequisite. Resource provisioning can take 10 to 15 minutes and, in
some tenants, up to 24 hours.

### What you run on screen

Complete the one preview boundary the coding agent cannot perform through a
supported public API:

1. Open the target environment in Power Platform admin center.
2. Select **Users + permissions > Agents > Add agent**.
3. Select the Agentic User prepared by the coding agent.
4. Assign `Basic User` and `lc Quality Gate Agent`.
5. Return to the terminal and run:

```powershell
Set-Location episodes\ep-11-agent-quality-gate
python preflight.py
python test_plugin_live.py --apply
python probe_agent_access.py --launch-name "Q3 Widget Launch" --expect denied
python configure_teams_notification.py --verify
```

The live matrix exercises Passed, Failed, Needs Review, and Error. It verifies
that only Passed advances and that duplicate or unauthorized results are
rejected.

After the BPF creates an assignment, the same probe should return granted.
After result processing revokes the share, it should return denied again.

The identity proof is:

- Microsoft Graph reports `#microsoft.graph.agentUser`.
- `identityParentId` matches the Agent Identity.
- Dataverse reports `systemmanagedusertype = 3`.
- The principal is enabled.
- The assigned roles are exactly `Basic User` and
  `lc Quality Gate Agent`.
- The agent can see an assigned Launch but cannot manipulate the BPF directly.

### Agentic User MCP proof

The Agentic User was also validated directly against the native Dataverse MCP
endpoint:

1. The blueprint was granted the delegated Dataverse `mcp.tools` permission
   alongside `user_impersonation`.
2. The Agent Identity client was enabled in the environment's Allowed MCP
   Clients table.
3. The documented blueprint to Agent Identity to Agentic User OAuth exchange
   produced a resource token for the GA `/api/mcp` endpoint.
4. The token contained `mcp.tools`, and its object claim matched the configured
   Agentic User.
5. MCP `initialize` succeeded and returned 16 tools.
6. `tools/list` included `read_query`.
7. An Agentic User-authenticated `read_query` completed successfully.
8. The Agentic User created a passing Quality Gate Result through MCP.
9. The result was attributed to the Agentic User.
10. The server-side plug-in projected the score to the Launch, advanced the
    BPF to Launch Approval, and revoked assignment-scoped Launch access.
11. All isolated test records were removed.

This proves the Agentic User can use the Dataverse MCP server under its own
identity and Dataverse roles, including the governed result-write path. The
agent does not update the BPF directly. It creates the result through MCP, and
the trusted plug-in validates the caller and assignment before changing the
Launch and BPF. The current worker source still uses its direct REST client, so
Section 2 must replace that runtime path with MCP before the episode describes
the worker itself as MCP-based.

The full preview provisioning findings and supported boundary are documented
in [RESEARCH.md](RESEARCH.md).

## Section 4 · Turn the finding into a governed launch outcome

Finally, the developer asks the coding agent to bring the result back to the
business surface. The worker does not just print a test report. It changes the
operational picture in ways that are visible, attributable, and constrained.

### The prompt

> *Present the Quality Gate result beside the launch timeline. Before review,
> distinguish owner-reported Green health from an official agent verdict and
> withhold the score. After review, show Needs Review, score 70, feedback,
> evidence, a blocked remediation task, and Yellow health. Keep the BPF at
> Quality Gate and leave the decision to return to Draft to a human.*

### What the coding agent produces

- The compact `lc_LaunchControl.LaunchReadiness` PCF.
- A 60/40 horizontal form layout with PCF and timeline side by side.
- Pending and reviewed states that do not confuse reported health with
  independently validated readiness.
- Three focused views: Overview, Risks, and Quality.
- A standard timeline note containing the Playwright PNG.
- Agent-attributed remediation and health records.
- A BPF that remains at Quality Gate after Needs Review.
- An Agentic User-authored Teams completion message with verdict, score,
  expected BPF state, and a clickable Launch record link.

### What you run on screen

Build and deploy the form control:

```powershell
Set-Location apps\launch-readiness-control
npm run build
Set-Location ..\..

python apps\launch-readiness-control\deploy.py `
  --import-control --apply-form --verify
```

The live control is version 1.5.0. The form tab must use
`verticallayout="false"` for the two columns to render side by side. Publish all
customizations after importing a newer PCF version so Dataverse serves the
updated control.

Reset the recording launch:

```powershell
Set-Location episodes\ep-11-agent-quality-gate
python reset_demo.py --apply --launch-name "Q3 Widget Launch"
```

Then:

1. Open the Launch and show On Track, Green, and Quality Gate Pending.
2. Advance the BPF from Draft to Quality Gate.
3. Show the new agent-owned assignment in the timeline.
4. Run the worker once with visual demo mode enabled.
5. Watch Playwright expose the telemetry-consent failure.
6. Open the trace screenshot.
7. Refresh the Launch form.
8. Show Needs Review, score 70, Yellow health, the blocked remediation task,
   and the same screenshot in the Dataverse timeline.
9. Show that the BPF remains at Quality Gate.
10. Open Teams and show the completion message authored by the Agentic User.
11. Click **Open Launch in Launch Control**.
12. Show that the link opens the same Launch at its current BPF state.
13. Explain that a human now decides whether to return the launch to Draft.

The Teams path is direct delegated Microsoft Graph because the requirement is
to author the message as the Agentic User's ordinary Teams account. The
Microsoft 365 Agents SDK proactive-message path is the preferred transport for
an agent application replying through its bot identity. Agent 365
Notifications is a separate notification capability and is not the arbitrary
outbound Teams message API used here.

Validate the message body without sending:

```powershell
python configure_teams_notification.py --verify
python test_teams_live.py --dry-run `
  --launch-id <launch-id> `
  --launch-name "Q3 Widget Launch" `
  --outcome NEEDS_REVIEW `
  --score 70
```

Use `--apply` only for the controlled recording proof. The live run verifies
that Graph returns the configured Agentic User as the sender and that the
message contains the model-driven app record link.

## Identity proof for the recording

The preferred proof is a genuine Agent User OAuth token whose Dataverse
`WhoAmI` result equals the configured Dataverse agent user.

The current repeatable recording path can use:

```powershell
$env:QUALITY_GATE_IMPERSONATE_AGENT="true"
python -m agent.worker --once
```

This development fallback uses an Azure CLI token with Dataverse
`MSCRMCallerID`. Dataverse still enforces the Agentic User's roles and records
the Agentic User in `createdby`, but this is **not** proof of an Agent User OAuth
exchange. State that distinction explicitly if the fallback is used.

Do not claim a genuine Agent User token run unless the blueprint client,
credential or approved token broker, Agent Identity, and Agentic User settings
are present and `preflight.py` verifies the caller.

## Pre-record checklist

- [ ] Hard-refresh the model-driven Launch form.
- [ ] Confirm the header-free PCF and timeline render side by side.
- [ ] Confirm the demo target responds at `http://127.0.0.1:8000`.
- [ ] Confirm the trace viewer responds at `http://127.0.0.1:8765`.
- [ ] Run `python preflight.py`.
- [ ] Reset Q3 Widget Launch to Green, Pending, and Draft.
- [ ] Confirm there are no visible blocked or overdue work items before review.
- [ ] Confirm entering Quality Gate creates exactly one agent assignment.
- [ ] Confirm the screenshot appears in both the trace and Dataverse timeline.
- [ ] Confirm the remediation task and Yellow update are attributed to the
      Agentic User.
- [ ] Confirm Needs Review remains at Quality Gate.
- [ ] Confirm the Agentic User has Agent 365 and a Microsoft 365 license with
      a Teams service plan.
- [ ] Confirm the Teams message is authored by the Agentic User.
- [ ] Click the message link and confirm it opens the expected Launch and BPF.
- [ ] State whether the run uses genuine Agent User OAuth or the explicit
      recording fallback.

## Code artifacts

| Path | Purpose |
|---|---|
| `RESEARCH.md` | Preview identity, tenant, provisioning, and SDK findings |
| `BPF.md` | BPF, plug-in, assignment, and security design |
| `SKILL.md` | Detailed technical build, verification, and repair model |
| `setup_dataverse.py` | Quality Gate schema and least-privilege role |
| `register_plugin.py` | Idempotent plug-in build and registration |
| `configure_teams_notification.py` | Graph permissions and consent verification |
| `seed_demo.py` | Enter Quality Gate and create the durable assignment |
| `reset_demo.py` | Restore a coherent Green/Pending recording state |
| `probe_agent_access.py` | Verify assignment-scoped Launch visibility |
| `test_plugin_live.py` | Isolated four-outcome plug-in matrix |
| `test_mcp_bpf_live.py` | Isolated MCP result and governed BPF transition |
| `test_worker_live.py` | Isolated worker and attribution test |
| `test_teams_live.py` | Agentic User sender and Launch-link proof |
| `demo-site/index.html` | Release candidate with the hidden telemetry defect |
| `trace_server.py` | Local trace and evidence server |
| `preflight.py` | Read-only recording readiness checks |
| `agent/worker.py` | Assignment research, validation, remediation, and result |
| `agent/quality_check.py` | Playwright critical-path check and screenshot |
| `agent/teams.py` | Delegated Graph completion-message client |
| `agent/app.py` | Microsoft 365 Agents SDK message endpoint |
| `../../apps/launch-readiness-control/` | Compact PCF and form deployment |

## Test and validate the solution

```powershell
$env:PYTHONIOENCODING="utf-8"

python -m unittest discover `
  -s episodes\ep-11-agent-quality-gate\tests `
  -p "test_*.py"

python episodes\ep-11-agent-quality-gate\preflight.py
python episodes\ep-11-agent-quality-gate\register_plugin.py --verify
python episodes\ep-11-agent-quality-gate\configure_teams_notification.py --verify
python apps\launch-readiness-control\deploy.py --verify
```

The completed build has fourteen passing Episode 11 unit tests, a verified
eighteen-privilege agent role, registered plug-in steps, an active four-stage
BPF, a governed direct-REST and MCP result path, an Agentic User-authored Teams
update, and the Launch Readiness PCF live beside the timeline.

## Cross-references

- **Episode 8:** row-level and column-level Dataverse security conventions.
- **Episode 10:** the analytical plane that judges a launch against portfolio
  history.
- **Episode 12:** the outside-in agent that combines launch blockers with live
  web signal.
- [`RESEARCH.md`](RESEARCH.md): official preview and identity findings.
- [`BPF.md`](BPF.md): process and enforcement details.
- [`SKILL.md`](SKILL.md): implementation and repair runbook.
