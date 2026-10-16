# Episode 12: Business Applications in Work IQ: Copilot Chat and Cowork

> *My launch data already lives in a business app. Now I can work with it
> directly in Copilot Chat and Copilot Cowork, without building a custom agent.*

**Status:** Recorded 112-second review edition ready. Business Applications in Work IQ is
available in preview; availability is not the same as access in this tenant.
The earlier Cowork screenshot shows Microsoft's **Business apps (preview)**
plugin, its Work IQ connection, and its `business-applications` skill. It also
shows **This plugin is blocked by your organization's policy** and **Request
access**. Authorized policy approval is a setup prerequisite, not evidence
that the product is unavailable.

The app's native evidence and semantic glossary were prepared previously.
The latest signed-in run-through recovered all four tasks in native Chat
after clarifying app context. After enabling the existing Microsoft plugin,
Cowork used the intended Business apps (preview) runtime and returned a
source-matched, review-only proposal. It supplied record IDs rather than
hyperlinks. Both native experiences refused to invent approval for a
nonexistent launch. The two demo persona labels are now neutral roles.
The final edit uses verified app-window takes and readable pickups after the
earlier capture problems. The recorded Chat follow-up returned only one task.
Cowork's draft required an assignee correction, which is visible in the edit.
See the [review deliverables](panel-demo-plan.md#recorded-review-deliverables) and
[run-through results](panel-demo-plan.md#latest-live-run-through).
Earlier Agent Builder and Studio answers remain separate evidence.

**Season:** Business Apps in Work IQ

**Hero surfaces:** Microsoft 365 Copilot Chat and Copilot Cowork, with
Launch Control as the source of truth.

**Result target:** Ask about the launch in Chat, use Cowork's built-in
Business apps (preview) plugin for a bounded follow-up, and compare the
returned evidence with the app.

## Episode boundary

```text
Prepared Launch Control app and business meaning
  -> Confirm environment, app, and user access
  -> Ask Copilot Chat for launch status and blockers
  -> Confirm Cowork's Business apps (preview) plugin is allowed and connected
  -> Ask Cowork for an evidence-based follow-up proposal
  -> Compare with the native records
  -> Episode 13: extend this scenario with declarative and Studio agents
```

Episode 12 does not build a declarative agent, use Agent Builder Preview,
provision a developer package, or build a Studio agent. Those belong to
[Episode 13](../ep-13-cowork/README.md). The legacy folder name is retained
to keep app scripts and existing links stable.

The demonstration is read-only. Cowork may propose follow-up work in its
answer; a proposal is not a saved task, sent message, schedule, or approval.
Record the complete episode, then edit the public panel version to
**90-120 seconds**. Accelerating processing waits is approved. No extra
speed indicators, fictional-data disclaimers, or result headings are wanted.
The production notes disclose that the recording is edited for time.

## 1. Confirm access and enablement

Follow the [pilot quickstart](https://learn.microsoft.com/en-us/power-platform/admin/business-applications-work-iq/quickstart).
Review licensing, Copilot Credits, the pilot audience, and existing permissions.
Use the approved demo environment, not a production environment.

1. In Microsoft 365 administration, confirm the intended pilot audience for
   **Business Applications in Work IQ available to Copilot**. Do not broaden
   access just for filming.
2. In Power Platform admin center, inspect the target environment's
   **Settings > Product > Features > Work IQ** setting.
3. Confirm the app's **Enable M365 Copilot in model-driven apps** setting and
   healthy semantic model. The prepared app was explicitly set to **On**.
   Current documentation permits **Default** or **On**; do not infer that
   every app using Default has the earlier demo's activation problem.
4. Verify the intended user can access the environment, app, and records.
   Settings and a successful administrator read do not grant another user access.
5. In Cowork, inspect the Microsoft-published **Business apps (preview)**
   plugin. If organization policy blocks it, stop the Cowork rehearsal.
   A request is not an approval. Use the authorized administrative process,
   then verify the actual allowed/connected state before claiming access.

Do not click Request access, change policy, activate a plugin, or grant
permissions without separate authorization. Do not substitute the custom
Episode 6 Dataverse plugin, generic Dataverse MCP, or App MCP for this
built-in plugin. Its catalog description is not proof of a successful run.

## 2. Keep the prepared app evidence useful

The app is **Launch Control Demo** and the scenario is **Q3 Widget Launch**,
identified by `EP12-DEMO-01`. Reuse the
[app specification](launch-control-app.json); do not reseed it for filming.

### Native evidence forms and views

| Table | Dedicated form | Dedicated active view | Evidence |
|---|---|---|---|
| Launch | Episode 12 Launch Evidence | Episode 12 Active Launches | Status, business owner, target date, risk summary, saved gate fields |
| Milestone | Episode 12 Milestone Evidence | Episode 12 Active Milestones | Related launch, status, business owner, due date, description |
| Task | Episode 12 Task Evidence | Episode 12 Active Tasks | Related launch/milestone, assignee, status, blocked flag, reason, due date |
| Status update | Episode 12 Status Update Evidence | Episode 12 Active Status Updates | Related records, author, posted time, health, saved summary |

These native forms and views were customized and published before semantic
regeneration. Launch's first tab contains native evidence; the PCF and timeline
remain on the second tab. Original shared forms/views were preserved.
An active-record view is not a count of unfinished work.

The [Work IQ user guide](https://learn.microsoft.com/en-us/power-apps/user/use-business-apps-work-iq)
documents that the selected view determines returned fields and record reads
use fields on the first tab of the selected main form. Custom controls and
subgrids are not supported substitutes. The PCF Activity display shows saved
status updates; the empty standard timeline is not their source.

### Semantic glossary

The last observed completed model had **62 items, four tables, and five
glossary terms**, with sample rows Off. Recheck current state before rehearsal;
do not regenerate a healthy model for a camera shot. Regeneration is
environment-wide, so review its scope before any separately approved request.

| Term | Definition |
|---|---|
| Launch readiness | An assessment of a launch using its recorded status, milestones, blocked tasks, saved updates, and quality-gate results. It is not a separate approval; a missing quality-gate result means no verdict is recorded. |
| Blocker | A launch task explicitly marked blocked. Its recorded blocker reason explains the obstacle; its assignee and due date identify responsibility and timing. A launch risk alone does not establish a blocked task. |
| At risk | The recorded At Risk status of a launch or milestone. It signals a delivery concern, but does not by itself mean a related task is blocked. |
| Business owner | The person named in a launch's or milestone's business-owner field, distinct from the Dataverse record owner and a task's assignee. An empty business-owner field means no business owner is recorded. |
| Latest status update | The saved status-update record with the most recent posted time linked to the launch. It contains the author, reported health, and recorded summary; it is not a generated summary or an ordinary timeline note. |

The [glossary guide](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/manage-semantic-model-glossary)
explains when saved terms take effect. Definitions provide meaning, not
canned answers or permissions. Do not attribute retrieval improvements to
glossary changes alone.

## 3. Ask Copilot Chat directly

Start a fresh conversation in **Copilot Chat**, not a custom agent's Preview.
Use the supported environment/app selection when prompted and confirm
**Launch Control Demo**. Ask:

> Using only Launch Control Demo, what is the current status of Q3 Widget
> Launch, and what is blocking it? Cite the source records and identify any
> evidence you cannot retrieve.

If detail is missing, use this diagnostic follow-up rather than guessing:

> Use the Episode 12 Active Tasks view in Launch Control Demo to list the tasks
> for Q3 Widget Launch. Show each task's status, blocked flag, recorded blocker
> reason, assignee, and due date. Cite the source records and identify any
> fields you cannot retrieve.

Compare actual results with the source. A risk is not automatically a blocked
task. An empty gate field is not approval. Do not infer broad app access or
successful skill execution from an answer without supporting evidence.

## 4. Continue the scenario in Copilot Cowork

Only after the plugin policy/access prerequisite is satisfied, start a new
Cowork task with **Business apps (preview)** enabled and connected. The
supplied listing describes a Work IQ connection and `business-applications`
skill for business-app operations. Discover the approved environment and
app through the supported experience; do not invent endpoint paths.

> Use Business apps (preview) and only Launch Control Demo to review Q3 Widget
> Launch. Identify recorded blocked work and draft a follow-up plan using
> the recorded reasons, assignees, and due dates. Cite source records and
> flag missing evidence. Do not change records, send messages, or schedule work.

The new Cowork task must retrieve its own evidence. Do not paste Chat's answer
as its source or imply shared context between the two sessions. Keep the
follow-up in the response, not an automatically shared document. Inspect
actual returned information and any tool evidence before claiming a skill
or operation ran. Stop on a denied, unknown, or incorrectly scoped operation.

Instructions request read-only behavior; they are not a technical permission
boundary. Writes, messages, schedules, and sharing remain separately gated.

## Rehearse, record, and verify

Use the [demo arc](demo-arc.md), [panel plan](panel-demo-plan.md),
[tracker](panel-demo-key-points.md), and [narration](voiceover-script.md).
Verify Chat and Cowork separately. A blocked Cowork plugin means that segment
is not recording-ready; do not splice agent footage in its place.

Use neutral fictional-role names before the first take, with scoped backup
and approval for any changes. Compare and reset only run-caused changes
after each rehearsal/take, then read back the baseline. Record a verified
no-op reset if read-only data is unchanged. Do not overwrite concurrent edits.

## Existing app setup and historical evidence

The helper [`configure_ep12_app.py`](../../scripts/python/configure_ep12_app.py)
supports `--dry-run`, `--apply`, and `--verify`, using the ignored root `.env`.
It configures the app, not Cowork policy or a custom agent. Any schema, form,
PCF, or solution deployment needs its normal approval and verification.

Historical [declarative-agent experiments](../ep-13-cowork/declarative-rehearsal.md)
and [Studio recordings](../ep-13-cowork/studio-rehearsal.md) now support
Episode 13. They do not establish current direct Chat/Cowork behavior.
The earlier developer-led panel/audio assets are superseded.

- [Episode 11: Agent Quality Gate](../ep-11-agent-quality-gate/README.md)
- [Episode 13: Declarative and Studio agents](../ep-13-cowork/README.md)
- [Deferred Web IQ storyline](DEFERRED-DRAFT.md), not the current episode.
