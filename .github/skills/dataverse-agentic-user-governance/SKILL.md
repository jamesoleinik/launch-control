---
name: dataverse-agentic-user-governance
description: Create and govern a Microsoft Entra Agent ID Agentic User for Dataverse, including blueprint and Agent Identity resolution, Agentic User creation, licensing, Dataverse agent-user provisioning handoff, least-privilege roles, Agent User OAuth, Dataverse MCP allowlisting, and identity verification. Use when an agent needs its own attributable Dataverse or Microsoft 365 user identity.
---

# Dataverse Agentic User Governance

Build the identity chain without substituting an application user or a human
account. Read [references/identity-and-access.md](references/identity-and-access.md)
before changing a tenant or environment.

## Workflow

1. Discover the target Dataverse tenant, environment, unmanaged solution, and
   accountable sponsor.
2. Resolve or create one Agent Identity blueprint per credential boundary.
3. Resolve or create a tenant-local Agent Identity from that blueprint.
4. Resolve or create its single Agentic User. Match on `identityParentId`;
   never create a duplicate.
5. Assign only the Microsoft 365 licenses required by the workloads the
   Agentic User will use.
6. Add the Agentic User through Power Platform admin center:
   **Users + permissions > Agents > Add agent**.
7. Resolve the resulting Dataverse `systemuser`, verify
   `systemmanagedusertype = 3`, and assign `Basic User` plus a purpose-built
   least-privilege role.
8. Configure Agent User OAuth for the exact downstream resource.
9. If Dataverse MCP is required, grant `mcp.tools`, consent it, and enable the
   Agent Identity in Allowed MCP Clients.
10. Run the verification matrix before enabling business writes.

Stop at the documented portal handoff when a preview API is not public. Do not
reverse-engineer an internal admin-center token into automation.

## Required configuration

Read all identifiers from ignored environment configuration:

```text
DATAVERSE_URL
TENANT_ID
A365_BLUEPRINT_CLIENT_ID
A365_BLUEPRINT_CLIENT_SECRET
A365_AGENT_ID
A365_AGENT_USER_ID
QUALITY_GATE_AGENT_SYSTEMUSER_ID
```

Use a certificate, federated credential, or approved token broker in
production. Permit a short-lived blueprint client secret only for a controlled
test, and never print it or persist it in committed files. A strict recording
preflight must fail when genuine Agent User OAuth configuration is absent; a
development Azure CLI or caller-ID fallback is not identity proof.

## Least-privilege rules

- Keep the Agent Identity and Dataverse environment in the same Entra tenant.
- Give the Agentic User only the tables, operations, and row scope required by
  its assignment.
- Prefer assignment-scoped sharing over business-unit-wide access.
- Keep privileged process transitions in a validated server-side plug-in when
  the agent should not receive direct BPF or business-row write permission.
- Revoke temporary row access after result submission.
- Test one expected allowed operation and one denied operation.
- Never grant System Administrator to make a probe pass.

## Verification

Prove all of these independently:

1. Graph returns `#microsoft.graph.agentUser`.
2. `identityParentId` matches the intended Agent Identity.
3. Token `tid` matches the Dataverse tenant.
4. Token subject identifies the intended Agentic User.
5. Dataverse `WhoAmI` equals the configured agent `systemuserid`.
6. Dataverse reports `systemmanagedusertype = 3`.
7. Assigned roles are exactly the approved baseline and custom role.
8. The allowed operation succeeds and records the Agentic User in audit fields.
9. The denied operation fails.
10. Temporary assignment access is revoked after completion.

Report licensing and resource provisioning separately from identity creation.
An Agentic User object alone does not guarantee a mailbox, Teams, or OneDrive.
