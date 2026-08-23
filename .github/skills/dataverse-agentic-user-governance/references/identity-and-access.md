# Identity and access reference

## Identity objects

| Object | Purpose |
|---|---|
| Agent Identity blueprint | Credential and inherited-permission boundary |
| Agent Identity | Tenant-local service identity for one agent instance |
| Agentic User | Optional Entra user account parented by one Agent Identity |
| Dataverse agent user | Dataverse security principal associated with the Agentic User |

An Agent Identity is single-tenant. A multitenant blueprint can create separate
tenant-local identities, but an identity from one tenant cannot be reused as a
Dataverse principal in another.

## Agentic User creation

Microsoft Graph beta creates the Agentic User through:

```text
POST /beta/users/microsoft.graph.agentUser
```

Supply `accountEnabled`, `displayName`, `mailNickname`, `userPrincipalName`,
and `identityParentId`. Query by the parent before creating because one Agent
Identity can parent only one Agentic User.

## Dataverse provisioning boundary

Use Power Platform admin center:

```text
Environment > Settings > Users + permissions > Agents > Add agent
```

Select the Agentic User, not its parent Agent Identity. After provisioning,
use supported Dataverse APIs to resolve the `systemuser`, assign roles, and
verify its type. Do not create `systemuser` directly and do not use legacy bot
user actions as a substitute.

## OAuth verification

Choose the execution mode first:

- S2S: agent acts as its service identity with application permissions.
- OBO: agent acts for a signed-in human with delegated permissions.
- Agentic User: agent acts as its own user account with delegated permissions.

For Agentic User mode, verify sanitized token claims only:

```text
aud  expected downstream resource
tid  target tenant
oid  Agentic User object ID
scp  required delegated scopes
```

Never log or decode a token into committed artifacts.

## Dataverse MCP

For the native endpoint:

1. Add delegated Dynamics CRM `mcp.tools` to the blueprint.
2. Grant tenant consent.
3. Enable the Agent Identity application ID in the environment's Allowed MCP
   Clients table.
4. Request `<environment>/api/mcp/mcp.tools`.
5. Connect to `<environment>/api/mcp`.
6. Verify `initialize`, `tools/list`, one read, and one governed write.

MCP lookup values can differ from Web API `@odata.bind`. Discover and validate
the tool schema instead of assuming Web API payload syntax.

## Microsoft 365 licensing

Agent 365 licensing does not itself provision all Microsoft 365 workloads.
Assign a workload license only when needed:

- Exchange requires a mailbox-capable license and mailbox provisioning.
- Teams requires a Microsoft 365 or Teams entitlement with an enabled Teams
  service plan.
- OneDrive and SharePoint require their applicable service plans.

Allow for asynchronous resource provisioning after assignment. Verify the
resource, not just the license record.

## Teams sender choice

- Use Microsoft 365 Agents SDK proactive messaging when the sender should be
  the bot identity and a conversation reference exists.
- Use delegated Microsoft Graph when the sender must be the Agentic User's
  ordinary Teams account.
- Do not treat Agent 365 Notifications as a general outbound chat API.

For one-to-one Graph chat creation and messaging, grant only the delegated
scopes the operation requires and verify the returned `from.user.id`.

## Safe verification matrix

| Check | Expected proof |
|---|---|
| Parentage | Agentic User `identityParentId` matches Agent Identity |
| Tenant | token `tid` matches configured tenant |
| Caller | Dataverse `WhoAmI` matches configured `systemuserid` |
| Type | `systemmanagedusertype = 3` |
| Roles | only approved baseline and custom roles |
| Allowed read | assigned row is visible |
| Denied read/write | unrelated row or forbidden update fails |
| Attribution | `createdby` or `modifiedby` is Agentic User |
| Cleanup | temporary share is revoked |
