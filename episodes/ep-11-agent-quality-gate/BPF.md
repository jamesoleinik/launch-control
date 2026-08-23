# Launch Approval business process flow

Create this BPF and the Quality Gate plug-in in the **LaunchControl** unmanaged
solution.
Dataverse agent users are in preview, so use a non-production environment.

## Primary table

`lc_launch`

## Launch columns

`setup_dataverse.py --apply` creates these columns in the `LaunchControl`
solution. It also verifies their logical names and types.

| Column | Suggested type | Purpose |
|---|---|---|
| `lc_qualitygatestatus` | Choice | Pending, Passed, Failed, Needs review, Error |
| `lc_qualitygatescore` | Whole number | Latest score from 0 to 100 |
| `lc_qualitygatefeedback` | Multiline text | Latest worker feedback |
| `lc_qualitygatecheckedon` | Date and time | Latest completed check |
| `lc_qualitygateevidence` | URL | Evidence location |
| `lc_approvaldecision` | Choice | Pending, Approved, Rejected |

## Stages

| Stage | Required data | Exit rule |
|---|---|---|
| Draft | Name, owner, target date | Launch record is ready for review |
| Quality Gate | Quality gate status | Only `Passed` advances |
| Launch Approval | `ownerid` and `lc_approvaldecision` | Approved advances |
| Ready to Launch | Launch status | Process complete |

Add the five Quality Gate columns to the **Quality Gate** stage.

## Programmatic authoring

The reusable `dataverse-bpf-builder` skill can create and verify this process
from a declarative JSON specification. It validates live table metadata,
generates matching workflow `clientdata` and XAML, activates the BPF, and adds
both the workflow and its generated backing table to the solution.

The generated backing table must be included with the workflow. Otherwise,
solution export fails even when the BPF is active.

## Current preview provisioning boundary

The supported product experience currently requires two visual admin steps:

1. Create one Entra Agentic User whose `identityParentId` is the Agent
   Identity's object ID. Each Agent Identity can parent only one Agentic User.
2. In the Power Platform admin center, open the environment, then
   **Settings > Users + permissions > Agents > Add agent**. Select the
   `Launch Control Quality Gate Agent`, assign `Basic User` and
   `lc Quality Gate Agent`, and save.
3. In the Power Apps maker portal, open the `LaunchControl` solution and select
   **New > Automation > Process > Business process flow**. Name it
   `Launch Approval`, select the `Launch` table, create the stages below, and
   activate it. The current maker experience does not expose or require a
   separate table-level enablement checkbox.

Do not substitute a Dataverse application user. The demo depends on the preview
agent-user type so Dataverse attribution identifies the Entra Agentic User. The
admin-center picker searches for the Agentic User, not its parent Agent
Identity. The generic Power Platform `addUser` API does not accept the parent
Agent Identity, and the preview user-management API used by the admin center
requires internal delegated permissions that are unavailable to Azure CLI and
Power Platform CLI. Direct `systemuser` creation is not a supported
replacement.

## Plug-in step 1: create the assignment

`QualityGateAutomation.CreateQualityGateAssignmentPlugin` runs synchronously
after `activestageid` changes on the generated Launch Approval BPF table.

1. Return unless the new active stage is **Quality Gate**.
2. Query tasks with subject `Quality Gate::<launch id>`.
3. If none exists, create a task with that subject.
4. Put JSON containing `launch_id` and `launch_name` in `description`.
5. Resolve the single enabled Agentic User with `lc Quality Gate Agent`.
6. Assign the task to that user.
7. Do not advance the BPF from this step.

The Dataverse task is the durable assignment. Mail notification remains an
optional worker-side integration.

## Plug-in step 2: apply the result

`QualityGateAutomation.ApplyQualityGateResultPlugin` runs synchronously after
an `lc_qualitygateresult` row is created.

Direct Web API creates invoke it at execution depth 1. Dataverse MCP
`create_record` performs its create from the MCP server plug-in, so this
handler runs at depth 2. The handler accepts both expected depths and rejects
deeper calls.

1. Require an assignment key matching `Quality Gate::<related launch id>`.
2. Require exactly one matching task.
3. Require the caller to be the enabled Agentic User that owns that task and
   has `lc Quality Gate Agent`.
4. Reject duplicate results for the same assignment.
5. Copy outcome, score, feedback, checked-on time, and evidence to the matching
   `lc_launch` columns.
6. If the outcome is `Passed`, set `lc_qualitygatestatus` to Passed and move the
   active BPF instance to **Launch Approval**.
7. If the outcome is `Failed`, `Needs review`, or `Error`, set the matching
   status and leave the active stage at **Quality Gate**.

The plug-in resolves the active process and stage IDs at runtime. It updates
the generated BPF instance's `activestageid` and `traversedpath`.

## Programmatic registration

```powershell
python register_plugin.py --dry-run
python register_plugin.py --apply
python register_plugin.py --verify
python test_plugin_live.py --dry-run
python test_plugin_live.py --apply
python test_mcp_bpf_live.py --dry-run
```

The registrar builds the signed sandbox assembly, upserts both plug-in types,
and registers both synchronous post-operation steps through the Dataverse Web
API. The live test creates isolated temporary records for Passed, Failed,
Needs review, and Error, verifies authorization and idempotency, and removes
them afterward. `test_mcp_bpf_live.py --apply` additionally requires the
Agentic User OAuth environment variables and an admin token in
`DV_ADMIN_TOKEN`. It creates the result through Dataverse MCP and verifies
Agentic User attribution, Launch projection, BPF advancement, and access
revocation before removing its isolated records.

## Security boundary

The agent writes only its assigned task and Quality Gate Result. The sandbox
plug-in uses the system organization service to create the assignment, copy
result data to the launch, and move the BPF. It accepts a result only from the
Agentic User that owns the matching assignment.

## Verification

1. Enter Quality Gate and confirm exactly one open assignment task.
2. Confirm the task owner is the Dataverse agent user.
3. Confirm the task's Regarding record is the Launch so it appears in the
   model-driven app timeline.
4. Run the worker and confirm the result's `createdby` is that agent user.
5. Confirm `Passed` advances through the plug-in, not through the agent role.
6. Confirm `Failed`, `Needs review`, and `Error` remain at Quality Gate.
7. Re-enter or retrigger the stage and confirm the plug-in does not create a
   duplicate open task.
