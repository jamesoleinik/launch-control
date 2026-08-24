---
name: agent-quality-gate
description: Builds, verifies, and repairs Episode 11's governed Dataverse Quality Gate worker. Use when configuring the Microsoft 365 Agents SDK runtime, connecting it to Agent 365 and Microsoft Entra Agent ID, creating the Dataverse agent user and least-privilege role, authoring the Launch Approval BPF and plug-in, validating identity attribution and Playwright evidence, or sending the Agentic User-authored Teams completion update.
---

# Skill: Dataverse Agent Quality Gate

Use this skill to build, run, verify, or repair Episode 11.

## Product boundaries

- Microsoft 365 Agents SDK builds and hosts the conversational runtime.
- Agent 365 extends an existing agent with enterprise integration. It does not
  build or host the agent.
- Microsoft Entra Agent ID supplies the tenant-local agent identity.
- An Entra Agentic User is a specialized user object parented by the Agent
  Identity. Power Platform selects this object when provisioning the Dataverse
  principal.
- The Dataverse agent user is the Dataverse security principal associated with
  that Agentic User. These capabilities are in preview.
- A mailbox and other Microsoft 365 resources are optional. Agent 365
  notifications require those resources and the applicable preview access.
- Direct delegated Graph is used only because the completion message must be
  authored by the Agentic User's Teams account. Prefer Agents SDK proactive
  messaging when the sender should be the bot identity.

Never describe the worker as being built by the Agent 365 SDK. It is built with
the Microsoft 365 Agents SDK and connected to Agent 365.

## Invariants

- Recording-mode Dataverse calls resolve to the dedicated agent user.
- The agent identity and Dataverse environment are in the same Entra tenant.
- The agent has `Basic User` plus `lc Quality Gate Agent`, never System
  Administrator.
- Dataverse tasks are the durable queue. Email is optional notification only.
- The assignment plug-in prevents duplicate tasks for
  `Quality Gate::<launch id>`.
- The worker checks for an existing result before processing an assignment.
- The agent writes the result and assigned task.
- A sandbox plug-in validates the assignment, updates the launch, and advances
  the BPF through the system organization service.
- `Passed` advances. `Failed`, `Needs review`, and `Error` remain at Quality
  Gate.
- Setup and seed commands are idempotent and dry-run first.
- Teams completion requires Agent 365, a Microsoft 365 license with a Teams
  service plan, delegated `Chat.Create` and `ChatMessage.Send`, and a configured
  recipient and model-driven app ID.
- Tenant IDs, application IDs, environment URLs, user IDs, secrets, and mailbox
  addresses come from `.env`.

Do not claim that task claiming is concurrency-safe. The sample marks a task in
progress, but it does not currently use an ETag or transactional lock to exclude
two workers that start at the same instant.

## Build order

1. Run `python setup_dataverse.py --dry-run`.
2. Run `python setup_dataverse.py --apply`.
3. Create the Launch Approval BPF and register the Quality Gate plug-ins using
   [BPF.md](BPF.md).
4. Build and deploy the Launch Readiness PCF from
   `apps/launch-readiness-control`, then verify that the live version exactly
   matches the manifest and that the Launch form contains one binding.
5. Create or update the separate `Launch Control Quality Gate` model-driven
   app with only the Launches table in navigation. Include the app, site map,
   table, form, BPF, and PCF in the `LaunchControl` solution.
6. Register the existing runtime with Agent 365 and provision its Entra agent
   identity.
7. Confirm the identity tenant matches the Dataverse environment tenant.
8. Create one Entra Agentic User parented by the Agent Identity.
9. Add the Agentic User to Dataverse as an agent user.
10. Assign `Basic User` and `lc Quality Gate Agent`.
11. Assign Agent 365 plus the Microsoft 365 and Teams entitlement required by
   the selected collaboration path.
12. Run `python configure_teams_notification.py --dry-run`.
13. Run `python configure_teams_notification.py --apply`.
14. Run `python configure_teams_notification.py --verify`.
15. Run strict `python preflight.py`. Do not use `--allow-dev-identity` for a
    recording proof.
16. Run `python seed_demo.py --dry-run`, then `python seed_demo.py --apply`.
17. Start the demo site and trace viewer.
18. Start `python -m agent.worker --wait-once --wait-timeout-seconds 900` in
    visual mode before advancing the BPF from Draft to Quality Gate.

## Authentication

Use the approved Microsoft Entra Agent ID authentication tooling in production.
For a controlled recording test, the sample can execute Microsoft's documented
three-step Agent User OAuth flow with a short-lived blueprint client secret.
Delete that credential immediately after the run. `A365_TOKEN_BROKER_URL`
remains available for an approved sidecar or broker adapter.

`AzureCliCredential` is a development fallback only. A recording preflight must
use the broker or direct Agent User test flow and verify:

1. the token `tid` matches `TENANT_ID`
2. Dataverse `WhoAmI` matches `QUALITY_GATE_AGENT_SYSTEMUSER_ID`

## BPF ownership

The assignment step creates and assigns work when the BPF enters Quality Gate.
The result step verifies the Agentic User owns that assignment, applies the
result, and advances the process through the system organization service.

The agent role needs only:

- business-unit read on `lc_launch`
- user-level read and write on Activity
- user-level create, read, write, and append on `lc_qualitygateresult`
- business-unit append-to on `lc_launch`

Do not grant the agent launch write permission merely to advance the BPF.

## Verification proof

Show all applicable evidence:

1. Agent 365 inventory shows the registered agent and Entra identity.
2. Dataverse shows the same identity as an agent user.
3. The agent user has only `Basic User` and `lc Quality Gate Agent`.
4. Preflight confirms token tenant and Dataverse `WhoAmI`.
5. The local worker runs Playwright and creates the result.
6. The result's `createdby` is the agent user.
7. The system-owned plug-in operation, not the agent role, advances a passing
   BPF.
8. A failed or review result remains at Quality Gate.
9. A separate denied-operation test confirms the role cannot change unrelated
   business data.
10. The Teams completion message is attributed to the Agentic User and its
    link opens the assigned Launch at its current BPF state.

The current preflight verifies role assignment but does not run the denied
operation. Do not claim that proof unless it has been tested separately.

## Repair order

1. If preflight reports a tenant mismatch, provision a tenant-local agent
   identity in the Dataverse environment's tenant.
2. If `WhoAmI` is wrong, fix the token broker or Dataverse agent-user mapping.
3. If role checks fail, rerun setup and inspect role assignment.
4. If assignments are absent, verify the BPF Update plug-in step.
5. If results exist but the BPF does not move, verify the result Create plug-in
   step and plug-in trace log.
6. If Playwright fails, verify Chromium and `QUALITY_GATE_URL`.
7. If Teams returns a license error, verify both Agent 365 and a Microsoft 365
   license with an enabled Teams service plan, then allow for provisioning.
8. If Teams attribution is wrong, inspect only sanitized token claims and
   confirm the token subject and returned `from.user.id` match the Agentic User.

## Reusable skill boundaries

Keep this episode skill as a composition and repair runbook. Build or extend
focused reusable skills instead of turning it into a generic Dataverse skill.

| Status | Skill | Reusable boundary |
|---|---|---|
| Available | `dataverse-bpf-builder` | Declarative BPF stages, XAML/clientdata generation, activation, backing-table ALM |
| Available | `dataverse-agentic-user-governance` | Blueprint and identity resolution, Agentic User creation, licensing, Dataverse handoff, OAuth, MCP allowlisting, verification |
| Available | `dataverse-plugin-deployer` | Build, register, update, verify, trace, and solution-sync Dataverse plug-ins |
| Available | `dataverse-pcf-deployer` | Build, import, place on forms, publish, and verify PCF controls |
| Available | `dataverse-model-driven-app-builder` | Focused model-driven apps, minimal navigation, publication, verification, and ALM |
| Extend | Dataverse security guidance | Agentic User roles, assignment-scoped sharing, access revocation, denied-operation probes |
| Defer | Generic Playwright, integration-test, and Teams-notification skills | Wait for a second workflow to prove a stable reusable abstraction |
