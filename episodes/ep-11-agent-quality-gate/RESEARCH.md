# Research: governed agent identity for Dataverse

## Verified product boundaries

The names are similar, but the responsibilities are different:

- The **Microsoft 365 Agents SDK** is a framework for building conversational
  agents and handling channels and conversation state. This episode uses its
  Python `microsoft-agents-hosting-aiohttp` package in `agent/app.py`.
- The **Microsoft Agent 365 SDK and CLI** connect an existing agent to Agent 365
  capabilities such as identity, observability, governed Work IQ tools, and
  notifications. Agent 365 does not build or host the agent.
- **Microsoft Entra Agent ID** represents each agent with a distinct agent
  identity created from a blueprint.
- An **Entra Agentic User** is a specialized user object parented by one Agent
  Identity. Its immutable `identityParentId` establishes that relationship.
- A **Dataverse agent user** associates the Agentic User with a Dataverse
  security principal so an administrator can assign security roles and
  attribute activity.

The Episode 11 runtime is therefore the Microsoft 365 Agents SDK plus the local
worker. Agent 365 is the registration and enterprise integration layer around
that runtime.

Sources:

- [Microsoft 365 Agents SDK](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/)
- [Microsoft 365 Agents SDK Python quickstart](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/quickstart)
- [Microsoft Agent 365 SDK and CLI](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/)
- [Agent 365 SDK overview](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/agent-365-sdk)

## The Dataverse identity chain

The August 6, 2026 Power Platform announcement describes this chain:

1. Microsoft Entra Agent ID gives the agent a distinct enterprise identity.
2. Microsoft Graph creates one Agentic User parented by that Agent Identity.
3. A Power Platform administrator adds the Agentic User to a Dataverse
   environment as a Dataverse agent user.
4. The administrator assigns a purpose-built, least-privilege security role.
5. Dataverse uses the agent user as the in-environment security principal.
6. Dataverse activity can be distinguished from human users and conventional
   application integrations.

Dataverse agent users are a preview feature. The announcement recommends
starting in a non-production environment and validating availability,
licensing, regional support, expected operations, denied operations, and audit
visibility.

Sources:

- [Microsoft Entra Agent ID and Dataverse agent users announcement](https://www.microsoft.com/en-us/power-platform/blog/2026/08/06/microsoft-entra-agent-id-for-dataverse/)
- [Create Entra agent users in Power Platform](https://learn.microsoft.com/en-us/power-platform/admin/agent-users)

## Agent-user provisioning surface

The Entra prerequisite can be created with Microsoft Graph beta:
`POST /beta/users/microsoft.graph.agentUser`. The required properties are
`accountEnabled`, `displayName`, `mailNickname`, `userPrincipalName`, and
`identityParentId`. Each Agent Identity can parent only one Agentic User.

The Power Platform public preview documentation exposes Dataverse agent-user
creation only through the Power Platform admin center. Live metadata shows
writable agent-related fields on `systemuser`, but Microsoft does not publish a
supported `POST /systemusers` payload or a Dataverse action for provisioning
the Agentic User.

Investigation of the current admin-center implementation found that it does not
use the generic BAP `addUser` operation. That operation rejected the parent
Agent Identity because it is a service identity rather than a regular Entra
user. The admin center's Agents picker instead searches for the associated
Agentic User, then calls a tenant-scoped Power Platform user-management preview
API. That API requires internal delegated permissions available to the Power
Platform admin-center client. Azure CLI and Power Platform CLI tokens cannot
request those permissions.

Therefore the supported and repeatable boundary for this preview is:

1. Create or resolve the Agentic User whose `identityParentId` matches the
   tenant-local Agent Identity.
2. Add that Agentic User through
   **Users + permissions > Agents > Add agent**.
3. Use Dataverse APIs after provisioning to resolve the resulting
   `systemuserid`, assign roles, and verify `systemmanagedusertype`.

Do not create a `systemuser` directly or use the legacy `msdyn_AddBotUser`
action. The latter provisions bot application users and does not model an Entra
Agent ID principal.

## Same-tenant constraint

Agent identities are single-tenant and receive tokens only in the tenant where
they are created. The agent identity used by this worker and the target
Dataverse environment must therefore resolve to the same Microsoft Entra
tenant. The preflight compares the token's `tid` claim with `TENANT_ID`, then
uses `WhoAmI` to verify that Dataverse resolves the token to the configured
agent user.

A blueprint can be multitenant. In that case, each customer tenant creates its
own tenant-local agent identity from the blueprint. Do not reuse an identity
from one tenant as a Dataverse principal in another tenant.

Source:
[Agent 365 identity](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/identity)

## Microsoft 365 resources and Teams licensing

An Agentic User does not automatically have a mailbox. The user object is
required for this Dataverse provisioning path, but licensing and Microsoft 365
resources such as a mailbox and OneDrive storage are separate, optional
provisioning steps.

The live Teams proof established that Agent 365 licensing alone is not a Teams
entitlement. Creating a one-to-one chat returned `403 Forbidden` until the
Agentic User also had a Microsoft 365 license containing the `TEAMS1` service
plan. Microsoft lists Microsoft 365 E5 or equivalent and Teams Enterprise as
common requirements for full agent-user functionality. Provisioning typically
takes 10 to 15 minutes and can take up to 24 hours.

Therefore:

- the Dataverse task assignment and worker can operate without a mailbox
- email notification requires a provisioned mailbox
- Teams messaging requires a provisioned Teams service plan
- the demo must not claim either resource until it is provisioned and tested

Sources:

- [Agent 365 identity](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/identity)
- [Connect an existing agent to Agent 365](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/get-started)
- [Agent 365 SDK overview](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/agent-365-sdk)
- [Create agent instances](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/create-instance)
- [Agent 365 validation checklist](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/validation-checklist)

## Authentication decision

Agent authentication uses specialized OAuth token exchanges. Microsoft
recommends its approved SDKs, including the Microsoft Entra ID Auth SDK sidecar,
for production. Microsoft also documents the three token exchanges for
controlled development and testing. The worker supports both paths:

- `A365_TOKEN_BROKER_URL` delegates acquisition to an approved broker or
  sidecar adapter.
- A short-lived `A365_BLUEPRINT_CLIENT_SECRET` enables the documented
  blueprint to Agent Identity to Agent User exchange for a recording test.

`AzureCliCredential` remains a local development fallback, and `preflight.py`
rejects it unless `--allow-dev-identity` is explicitly supplied.

Source:
[Agent User OAuth flow](https://learn.microsoft.com/en-us/entra/agent-id/agent-user-oauth-flow)

## Agentic User access to the Dataverse MCP server

Live validation confirmed that a Dataverse Agentic User can call the native GA
Dataverse MCP endpoint under its own identity.

The required configuration is:

1. Add the delegated Dynamics CRM `mcp.tools` permission to the Agent Identity
   blueprint and grant tenant consent.
2. Add the Agent Identity application ID to the environment's Allowed MCP
   Clients table and enable it.
3. Use the documented Agent User OAuth flow to request the MCP resource scope
   at `<environment-url>/api/mcp/mcp.tools`.
4. Send the resulting bearer token to `<environment-url>/api/mcp`.

The live test verified that:

- the resource token contained the `mcp.tools` scope
- the token object claim matched the configured Agentic User
- MCP `initialize` succeeded
- `tools/list` returned 16 tools, including `read_query`
- an Agentic User-authenticated `read_query` succeeded
- MCP `create_record` created an `lc_qualitygateresult`
- the result's `createdby` was the Agentic User
- the result plug-in projected the score to the Launch
- a passing result advanced the BPF to Launch Approval
- assignment-scoped Launch access was revoked after submission
- all isolated test records were deleted

The MCP lookup value must be a JSON-encoded entity reference containing
`relatedTable` and `recordId`. Web API `@odata.bind` is rejected by
`create_record`.

Dataverse MCP implements `create_record` through its own server plug-in. The
downstream Quality Gate result plug-in therefore runs at execution depth 2.
Its recursion guard allows depths 1 and 2 and rejects deeper calls.

This proves capability, identity compatibility, and the governed BPF action.
It does not yet mean the Episode 11 worker uses MCP. The current worker uses a
direct Dataverse REST client and must be refactored before the runtime
architecture can be described as MCP-based.

Sources:

- [Connect to Dataverse with MCP](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp)
- [Connect non-Microsoft clients to Dataverse MCP](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-other-clients)
- [Agent User OAuth flow](https://learn.microsoft.com/entra/agent-id/agent-user-oauth-flow)

## Agentic User-authored Teams completion

Three Microsoft 365 integration surfaces were evaluated:

- Microsoft 365 Agents SDK proactive messaging is the preferred route when the
  agent application sends through its bot identity and has stored a
  conversation reference.
- Direct delegated Microsoft Graph is the correct route when the message must
  be authored by the Agentic User's ordinary Teams account.
- Agent 365 Notifications is a separate notification capability. It is not a
  general API for arbitrary outbound Teams chat messages.

Episode 11 requires the message sender to be the Agentic User, so the worker
uses delegated Microsoft Graph with `Chat.Create` and `ChatMessage.Send`. It
creates or resolves a one-to-one chat with the configured recipient and posts
an HTML message containing:

- Launch name
- verdict and score
- expected current BPF stage
- a model-driven app entity-record link

The supported record-link shape is:

```text
<environment>/main.aspx?appid=<app-id>&pagetype=entityrecord&etn=lc_launch&id={<launch-id>}
```

The live proof sent a Needs Review result, verified that the returned
`from.user.id` matched the configured Agentic User, and verified that the HTML
contained the expected Launch record link. Both Passed and non-passing body
shapes are covered by unit tests.

Sources:

- [Create chat](https://learn.microsoft.com/en-us/graph/api/chat-post)
- [Send chat message](https://learn.microsoft.com/en-us/graph/api/chatmessage-post)
- [Deep link to a model-driven app](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/open-forms-views-dialogs-reports-url)

## Runtime and process decisions

Dataverse is the durable queue. A synchronous sandbox plug-in creates a task
owned by the Dataverse agent user when the BPF enters Quality Gate. The local
worker polls assigned open tasks, checks for an existing result by assignment
key, marks the task in progress, runs Playwright, creates the result, and
completes the task.

If the Frontier mailbox path is enabled, email is a notification only. The task
remains the source of truth.

The agent writes its result and assigned task. A second plug-in step validates
that the result caller owns the matching assignment, updates the launch fields,
and advances the BPF after a passing result. Keeping stage movement out of the
agent's role narrows its Dataverse permissions without adding a connector or
external automation runtime.

## BPF authoring decision

The first Launch Approval BPF was created in the maker portal and stored in the
LaunchControl solution to establish a known-good platform-generated definition.
The `dataverse-bpf-builder` skill now provides the code-first pattern: validate
a declarative spec, generate matching `clientdata` and XAML, create and activate
the workflow, then add the generated backing table to the solution. The BPF and
flow definitions become ALM artifacts after
solution export. The result table, security role, seed data, local runtime,
Playwright check, and validation harness remain code-first.
