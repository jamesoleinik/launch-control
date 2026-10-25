# Episode 13: Business Applications in Work IQ: Declarative and Studio agents

> *Historically, we tracked launch status in a weekly review meeting.
> That is no longer enough. My team should be able to ask the launch agent
> directly, without emailing me, and changes in the work should drive
> updates to the records.*

**Status:** Revised story in progress. Builder answers have been demonstrated.
The [separate bounded automation backend](automation/README.md) is published
but disabled. Its first issue-triggered attempt authenticated through federation,
then failed before any business update because the Linux CLI rejected its
request path. A local transport correction is not yet published. Automatic task
completion remains unverified; this is not a Work IQ unattended save.

## The hook

In [Episode 12](../ep-12-business-apps-work-iq/README.md), I brought my
business app into Copilot and delegated a reviewed update to Cowork.
Now the team needs targeted answers between weekly reviews, without making
the launch lead's inbox the way to find out what is happening.

Microsoft 365 Agent Builder gives the review a purpose and one selected
business-app source. People with the appropriate access can ask about status
and blockers whenever they need to. The recorded draft is not yet published
or shared with that audience.

A separate **Launch Readiness Fixer** draft was prepared in Copilot Studio.
Its inspected Work IQ update route requires human confirmation. The selected
automation route is therefore a separate deterministic backend: respond to a
GitHub issue event, finish the explicitly mapped unblocked task, and leave
unresolved launch risks intact. The app remains the system of record. This
does not demonstrate autonomous execution by the Studio agent.

> **Preview note:** Business Applications in Work IQ and Work IQ in Copilot
> Studio are preview capabilities. Work IQ in Studio runs on the GitHub
> Copilot harness and uses Copilot Credits. Verify availability, licensing,
> billing, permissions, and the supported connection before using them.

## The walkthrough: four sections

```text
Section 1  Weekly review  -> Move beyond meeting-based status checks
Section 2  Launch Checker -> Ask targeted questions without emailing the lead
Section 3  Fixer design   -> Respond to a GitHub issue event
Section 4  Fixer rules    -> Reconcile records without hiding blockers
```

Sections 3 and 4 are design intent until the connection, mapping, permissions,
automatic activation, and independent record verification are demonstrated.
The earlier manually confirmed write is not evidence of a triggered run.

## 1. Move beyond the weekly review

Start with the unpublished **Launch Readiness Checker** draft in Agent
Builder and the [natural-language instructions](natural-language-instructions.txt).
Select **Launch Control Demo** under Dynamics 365 and Power Apps knowledge
and leave the other sources off. The
[instruction template](launch-readiness-agent-instructions.md) is reference
material, not the tested text.

The agent should resolve the named launch, separate risk from an explicitly
blocked task, say what evidence is missing, and cite the records. Instructions
are guidance, not permission controls.

## 2. Ask about the launch anytime

Ask in a fresh Builder preview:

> What is the current status of Q3 Widget Launch, and what is blocking it?

Then open the cited records in the app. The demonstrated answer named the
blocked partner security evidence task and the at-risk certification
milestone, and did not treat missing evidence as approval. A second starter
inspects the underlying work:

> Use the Launch Control Active Tasks view in Launch Control Demo to list the
> tasks for Q3 Widget Launch. Show each task's status, blocked flag, recorded
> blocker reason, assignee, and due date. Cite the source records and identify
> any fields you cannot retrieve.

## 3. Respond when the work changes

The prepared backend uses GitHub Actions issue-close events in one repository
and accepts only the configured issue. It independently fetches current
completion evidence. There is no live GitHub virtual-table relationship in
the inspected environment; the task and parent launch are explicitly mapped.
Do not imply that the earlier relationship from
[Episode 4](../ep-04-extending-and-enforcing/README.md) exists here.

Use **Work IQ (preview)** for the business-app experience, not legacy
workload tools. The [Studio build guide](studio-build.md) describes earlier
setup work, not a completed Fixer configuration.

## 4. Reconcile without hiding blockers

The prepared backend's write boundary is only the matched task's status.
Its parent launch's **Recorded launch risks** field is preserved, not rewritten.
Re-read the issue and business
records before acting. An issue closed without completion evidence must not
finish a task. A blocked task stays blocked; do not clear its blocker to force
a successful result. Preserve unrelated launch risks.

Compare desired values before writing so duplicate events can be no-ops.
Respect concurrent edits, surface partial failures, and verify saved values
independently in the app. A successful answer or manual payload test does not
prove automatic activation.

The inspected Studio update schema and current Business Apps user guidance
require explicit human confirmation. The backend does not forge that
confirmation or disable the gate. Keep the Studio draft unpublished and
inactive. The backend needs a separately approved deployment, dedicated
identity, restricted record grants, event test and reset. Its local code and
offline tests are not proof of an activated workflow or saved business update.

## Recording notes

The revised story review opens on the app and reuses existing Builder footage,
then clearly labels the Fixer material as proposed design. It contains no
footage claiming a completed trigger or automatic write. The footage is
edited, not a response-performance test. Record owner names are blurred.
Production scripts, trackers, and narration drafts remain local.

### Rehearse and verify

Verify Builder and Studio separately against native app records, not against
each other's answers. Before the Fixer test, approve the exact event, record
mapping, write rules, connection scope, and reset. Verify wrong-issue rejection,
blocker preservation, duplicate handling, and concurrent-edit behavior.
Trace one real event through run history to independent app readback, then
disable the test trigger and restore only test-caused changes with approval.
Publication, sharing, connections, writes, and recording are separately gated.

The earlier manual-write rehearsal was restored after capture, including the
field and read-only Studio instructions. It remains historical, not the
revised episode's automatic-write proof.

## Existing material

- [Declarative preparation and experiments](declarative-rehearsal.md).
- [Studio rehearsal provenance](studio-rehearsal.md). Historical rehearsals
  are not footage or evidence of this episode.
- [Deferred Foundry IQ storyline](DEFERRED-DRAFT.md), not this build.

The folder keeps its former `ep-13-cowork` name for existing links.

## Cross-references

- [Episode 12: Business Applications in Work IQ](../ep-12-business-apps-work-iq/README.md)
- [Episode 15: Work IQ API and Developer Tools](../ep-15-workiq-api-devtools/README.md)

## Reference documentation

- [Add knowledge to an agent in Agent Builder](https://learn.microsoft.com/microsoft-365/copilot/extensibility/agent-builder-add-knowledge)
- [Work IQ in Copilot Studio (preview)](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/add-work-iq)
- [GitHub connector events and limitations](https://learn.microsoft.com/connectors/github/)
- [Add triggers, GitHub Copilot harness (preview)](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/authoring-add-event-trigger)
- [Business Applications in Work IQ](https://learn.microsoft.com/power-apps/maker/data-platform/business-applications-work-iq)
