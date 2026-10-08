# Episode 12: Business Apps in Work IQ: Copilot Chat + Agent Builder

> *Can a launch team ask a simple question in Copilot, get an answer grounded
> in its business records, and see the same evidence back in the app?*

**Status:** Build and rehearse in an isolated demo environment. Verify current
product availability and supported connections before recording.
**Season:** Business Apps in Work IQ
**Hero surfaces:** Launch Control, Copilot Chat, and Agent Builder
**Result target:** Build a recording-ready Launch view, verify the agent's
answer against source data, and show any approved follow-up work in the app.

## The build: four sections

Use the existing Launch Readiness PCF and model-driven form as the business
surface. Configure the supported Copilot route only after verifying it in the
target tenant. Keep user prompts natural; put routing and safety requirements
in agent instructions and business skills.

```text
Section 1  Business app  -> Build and verify the Launch view and activity feed
Section 2  Agent          -> Ground a focused Agent Builder experience
Section 3  Rehearsal      -> Ask ordinary questions and verify source evidence
Section 4  Recording      -> Return to the same launch and show the result
```

## Section 1: Build the business app

The Launch main form already places the Launch Readiness PCF beside the
Dataverse timeline. This episode adds an **Activity** view to the PCF for the
latest saved Launch status updates. It displays only persisted update fields;
it does not infer which client or agent authored them.

### Prompt

> I want the Launch page to make the current risks and recent updates easy to
> show in a demo. Please inspect the existing Launch Readiness control, add a
> simple activity view for the latest saved updates, and tell me how to build
> and verify it without changing a live environment.

### Result

- The PCF builds locally and has an Activity view for recent Launch updates.
- The existing model-driven form keeps its readiness control and timeline.
- Live deployment is separately approved and verified in a sandbox.

### Run it

```powershell
npm run build --prefix apps/launch-readiness-control

# Confirm the target in the ignored root .env before provisioning.
python scripts\build_launchcontrol_schema.py --scope unified --with-lookups --dry-run
python scripts\build_launchcontrol_schema.py --scope unified --with-lookups
python scripts\python\seed_ep12_demo.py --dry-run
python scripts\python\seed_ep12_demo.py --apply
python .github\skills\dataverse-model-driven-app-builder\scripts\model_app_builder.py `
  --spec episodes\ep-12-copilot-chat-agent-builder\launch-control-app.json --dry-run
python .github\skills\dataverse-model-driven-app-builder\scripts\model_app_builder.py `
  --spec episodes\ep-12-copilot-chat-agent-builder\launch-control-app.json --apply
```

For sandbox deployment, use the `dataverse-pcf-deployer` skill and the
existing `apps/launch-readiness-control/deploy.py` helper. Its
`--import-control` and `--apply-form` options publish changes to the configured
environment. Confirm the target and review changes before running either.
The form helper adds the standard Dataverse timeline when the Launch main form
does not already contain one. The Episode 12 seed is marker-scoped and
idempotent; do not substitute the older broad seed scripts.

## Section 2: Build the agent experience

Direct Dataverse grounding was removed after fresh previews invoked generic
organization and table-metadata discovery outside the configured demo scope.
A read-only Copilot Studio workflow now has fixed environment/table selections
and filters for the demo launch and related records. The workflow appears in
Copilot Studio as **Respond to the agent and 4 more**. Its four individual
data actions returned the expected launch, milestones, tasks, and status
updates, but the workflow response and agent invocation have not been verified.
The workflow remains an unused draft with no verified end-to-end run.
The Launch Readiness Checker now has **Work IQ (Preview) only** and remains
unpublished. Direct Dataverse MCP was removed; its earlier successful reads
are not evidence for Work IQ.

The workflow workaround is no longer the chosen implementation. The deliverable
is the Launch Readiness Checker agent with a verified business-data connection,
not a workflow. Leave the unused workflow unpublished. Investigate supported
Work IQ business-app grounding, not direct Dataverse MCP. A saved routing
instruction starts discovery with `do_action` on `/businessapps/me`.
A pre-enablement Preview returned HTTP 200 from that discovery call but no matching
Launch Control app in its results. The agent reported that it could not
verify launch facts instead of using unrelated results. This verifies the
discovery invocation and missing-source response, not successful grounding.
The user subsequently approved and enabled **Turn on Business Applications
in Work IQ** in the Launch Control sandbox. A fresh admin-center page confirms
that it, Dataverse intelligence, and supporting search indexing are on.
This feature can incur Copilot Credit usage; Microsoft 365 admin consent may
also be required. Repeat discovery after enablement rather than assuming
this alone resolves app visibility. The first post-enablement Preview now
discovers the app and retrieves the fictional launch, three milestones,
four tasks, two updates, and referenced owners through Work IQ environment
SELECT queries. The answer reports AtRisk and the partner-certification blocker.
This is Work IQ evidence, not the earlier direct Dataverse MCP test.

The app-builder defect is repaired: table components now use the table's own
OData type and resolved primary-key attribute, and verification compares exact
metadata IDs rather than table counts. The erroneous generic `entity` component
was removed from this demo app. App validation, an idempotent rebuild, and the
exported solution all confirm `lc_launch`; existing navigation, form, and view
are preserved. Work IQ now exposes the correct app table. Related records are
still retrieved through Work IQ's matching environment, not another MCP server.

The saved agent instructions require exact-code and related-record filters,
task-count reconciliation, and no inferred review history from empty gate
fields. The three ordinary prompts were rerun in sequence in a fresh draft
Preview after repair. They correctly report AtRisk, the partner-certification
blocker, four unfinished tasks (one Blocked, one InProgress, two NotStarted),
and no recorded gate verdict. Inspected queries use the exact demo code and
returned launch ID. This verifies draft Preview behavior, not publication or
the Microsoft 365 `@` picker.

A real read-only draft run has now been recorded using the supplied
`demo-recording-and-narration` skill. The verified capture is one app window
cropped to this session's shared browser panel, excluding the chat and address
bar. Private session artifacts include the 6:53.733 raw take, 5:08 clean
chaptered cut, and 6:06 backup edition with opening/closing slides, a value
panel, synthetic-voice timing preview, and read-along subtitles.

The recording preserves every AI response wait. Catch-up took about 106 seconds
through four seconds of answer stability, the status follow-up about 12 seconds,
and readiness about 32 seconds. These are observations from one run, not product
performance claims. The status answer explicitly reused the recent read;
readiness refreshed the launch/gate fields and identified the related evidence
as older. Do not present every answer as a fresh retrieval.

Full-file decoding, chapter lengths, slide comparison, panel timing, narration
fit, and subtitle synchronization passed. Contact sheets and selected full-size
frames were inspected. Presenter review of the complete video is still pending.
The agent remains unpublished, no business records were written, and no external
upload or access grant has occurred. Both review previews and the verified
`episode12-private-review.zip` package are delivered locally through this
session's Library. Presenter review is the next human step, not a claim made by
the automated checks. External sharing would require a destination and named
reviewers. See [the timed narration](voiceover-script.md) and
[the recording handoff](demo-arc.md#recording).

The original under-two-minute requirement also has a separate
[LinkedIn voiceover](linkedin-voiceover-script.md) and a **1:37** local video
excerpt, with silent and synthetic-voice editions plus subtitles. The excerpt
clearly discloses that earlier catch-up turns are omitted. It retains the
entire readiness response wait and does not replace the full demo.
Its narration fit, subtitle synchronization, full-file decoding, exact duration,
and source-video fidelity are verified. No LinkedIn post has been made.

### Prompt

> Help me set up a Launch Readiness Checker for the Launch Control demo. First
> confirm which business data source and operations this tenant actually
> supports. Use the readiness guidance in this repository, and tell me what
> still needs configuration before I try it.

### Result

- The agent uses a verified, explicitly scoped business-data connection and
  approved Launch Control data.
- Readiness uses the configured authoritative operation, not a guessed score.
- Optional follow-up work uses the
  [Launch Follow-up Plan](../../business-skills/launch-follow-up-plan.md):
  preview exact changes, wait for approval, and read results back.
- If the target connection or write operation is unavailable, report the
  blocker and keep the demo read-only.

### Run it

Use [`launch-readiness-agent-instructions.md`](launch-readiness-agent-instructions.md)
as starting instructions. Keep Work IQ as the sole MCP server, with only
`do_action`, `get_schema`, `search_paths`, and `fetch` selected for the
business-app test. Disable broad `ask`, agent delegation discovery, and
create/update/delete tools. `do_action` is needed for business-app discovery
but is also capable of writes: this tool selection is not a server-enforced
read-only boundary. Review action targets and allow only discovery or
confirmed read operations. Do not publish the agent. Do not paste environment
URLs, user IDs, or credentials into committed files or recording prompts.

## Section 3: Rehearse the user flow

Start in the model-driven Launch Control app with the fictional **Q3 Widget
Launch** record. Use a fresh Copilot conversation and simple prompts:

1. **"Catch me up on the Q3 Widget Launch."**
2. **"What's the current status, and what is blocking it?"**
3. After the verified data connection is attached, select the readiness agent from
   the `@` picker, then ask:
   **"Is the Q3 Widget Launch ready to launch?"**
4. Open Agent Builder and show the agent's verified business-data connection.
   Return to the conversation and compare its answer with the Launch record
   and readiness evidence.
5. If the separate write path has been confirmed, ask:
   **"Let's address the open blockers."** Review its exact proposed tasks and
   status update. Approve only the reviewed plan with:
   **"Looks good. Go ahead."**

### Pass criteria

- The answer matches current source records and explicitly identifies unknowns.
- The agent's readiness result comes from the configured authoritative source.
- Each write, if enabled, was previewed, explicitly approved, and verified by
  read-back before it is shown as successful.
- Follow-up work does not change the launch's readiness verdict.

### Stop criteria

Stop if the supported route, source, operation, permission, target record, or
write effect is unclear. Never simulate a connection or claim an unverified
write. Use the read-only version if the write path is not supported.

## Section 4: Record the outcome

Return to the same Launch in the app. Refresh the form and open the PCF's
**Activity** view to show the persisted status updates. If follow-up tasks were
created, show those records as well. Run the readiness check again and report
its actual result. The agent must not set the launch to Ready or change its
readiness decision to make the closing shot look better.

Use the ordered setup, rehearsal, recording, and cleanup instructions in
[`demo-arc.md`](demo-arc.md). Keep raw captures and recording tools local;
publish only sanitized, approved materials.

## Pre-record checklist

- [ ] The sandbox, demo account, and fictional Launch record are confirmed.
- [ ] The Launch Readiness PCF builds and the Activity view renders in the app.
- [ ] The agent's business-data connection is scoped, read-only, and tested
      end to end without access outside the approved demo scope.
- [ ] The readiness answer matches source evidence and reports missing
      quality-gate results without inventing a score or verdict.
- [ ] Any write path has separate approval, successful read-back, and cleanup.
- [ ] No credentials, personal information, tenant identifiers, or unrelated
      notifications appear in the recording.

## Supporting material

- [Build, rehearse, and record runbook](demo-arc.md)
- [Agent Builder instructions](launch-readiness-agent-instructions.md)
- [Launch Follow-up Plan business skill](../../business-skills/launch-follow-up-plan.md)
- [LinkedIn video script](voiceover-script.md)
- [Deferred Web IQ storyline](DEFERRED-DRAFT.md), not part of this episode's
  active demo.
- [Episode 11: Agent Quality Gate](../ep-11-agent-quality-gate/README.md)
- [Episode 13: Cowork](../ep-13-cowork/README.md)
