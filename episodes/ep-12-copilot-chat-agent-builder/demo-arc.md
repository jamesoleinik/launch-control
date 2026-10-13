# Episode 12 demo arc: enable, explain the app, ask, verify

**Production status:** Revised shot list, not a completed recording.
The updated draft is saved and the glossary-inclusive regeneration is complete.
Window capture is blocked until a probe matches the intended browser canvas.
The earlier Studio videos are superseded for this episode. See the
[Studio rehearsal record](../ep-14-copilot-studio/studio-rehearsal.md).

The presenter is a launch coordinator who wants business-record answers
inside Microsoft 365 Copilot. The audience sees the setup that makes this
possible, then a focused declarative agent. Episode 14 covers the Studio
build; only a short comparison belongs here.

## What each shot proves

| Beat | Screen | Value and required evidence |
|---|---|---|
| Open | Title and prepared launch | The question matters because status and blockers live in the app |
| Enable | Microsoft 365 pilot setting, then environment Features | The intended audience and environment are enabled, not merely an MCP tool attached |
| Enable and select the app | App Settings > Features, published Launch Control app, then selected Agent Builder knowledge | App indexing is enabled and the intended business app is included explicitly |
| Explain the app | Four-table native evidence views/forms, semantic Overview and Glossary | Forms and views expose the evidence; five glossary terms clarify business meaning without embedding answers |
| Configure | Agent Builder instructions in Microsoft 365 Copilot | A declarative agent gives a repeatable question a focused purpose |
| Ask and follow up | Fresh Preview conversation, status question, then dedicated Tasks-view follow-up | Two actual source-cited responses; do not imply reliable one-shot task retrieval |
| Compare and close | Source record, then declarative/Studio comparison | The facts match; Episode 14 adds the Studio-specific build |

Do not show an App MCP package download as if it configured Agent Builder's
Work IQ knowledge. The [README](README.md#not-the-same-as-app-mcp) explains
that separate integration route.

## Before rehearsal

1. Confirm the approved sandbox and pilot account privately. Use the existing
   fictional launch `EP12-DEMO-01`. Do not reseed an unchanged read-only demo.
2. Follow the [enablement and app setup](README.md#1-enable-business-applications-in-work-iq).
   Save only approved changes. An already-enabled setting is a valid shot;
   say it is already enabled instead of staging a toggle.
3. Verify the pilot can open the intended app and records. Do not use an
   administrator's successful read as proof of another user's access. Inspect
   **Enable M365 Copilot in model-driven apps** in the app's Features settings.
   Save/publish an approved change to On if needed, then verify persistence.
   This app-level indexing prerequisite is separate from App MCP. If discovery
   fails, inspect the associated semantic model's generation state using the
   README's troubleshooting steps. A running regeneration is not a successful
   knowledge-source test.
4. Verify **Dynamics 365 and Power Apps data** is available in Agent Builder
   and select the intended app explicitly. If absent, record the limitation
   privately and stop this portion of the demo.
5. Confirm the four-table scope: `lc_launch`, `lc_milestone`, `lc_task`, and
   `lc_statusupdate`. Use the dedicated Episode 12 native forms and active
   views. PCF access alone does not establish knowledge-source access.
   Customize and publish before regenerating. The latest observed completed
   model has 62 items, four tables, and five glossary terms. Sample rows are Off.
   Do not regenerate again merely for filming or broaden to every accessible app.
6. Use the saved [natural-language instructions](natural-language-instructions.txt).
   Exclude unrelated sources and write-capable tools. Keep the agent's
   publication and sharing state explicit. The existing draft is named
   Launch Readiness Checker; the experimental business-skill paragraph is removed.
7. Show the five glossary definitions from the README. Explain the distinction
   between a recorded risk and an explicitly blocked task, and between business
   owner, record owner, and assignee. Do not credit glossary terms alone for
   retrieval improvements.

## Rehearsal

Use a fresh conversation in the actual Microsoft 365 Agent Builder **Preview**
surface. Do not use the existing Studio draft, its transcript, or its timings.

First ask **"What is the current status of Q3 Widget Launch, and what is
blocking it?"** Then ask:

> Use the Episode 12 Active Tasks view in Launch Control Demo to list the tasks
> for Q3 Widget Launch. Show each task's status, blocked flag, recorded blocker
> reason, assignee, and due date. Cite the source records and identify any fields
> you cannot retrieve.

Measure each turn from Send until the answer stops changing for four seconds.
Compare both responses with current app evidence. A starter button fills the
composer; explicitly click Send. Do not reopen the canvas URL mid-response,
because doing so resets this preview.

Off camera, also ask **"Catch me up on the Q3 Widget Launch."** and
**"Is the Q3 Widget Launch ready to launch?"** Test a deliberately nonexistent
launch code and expect an explicit missing-record response, not an invented
record or a fallback to the prepared launch. Repeat the visible sequence in
a fresh conversation after any instruction changes.

### Prepared data is a comparison baseline, not a canned answer

The previous source read showed the following. Re-read before the new take;
do not insert these facts into the agent's knowledge or instructions.

| Source | Previously observed baseline |
|---|---|
| Launch | AtRisk, Medium priority |
| Blocker | Confirm partner security evidence; Dana Flores |
| Milestones | Engineering Sign-off Done; Partner Certification AtRisk; Customer Readiness InProgress |
| Tasks | Four unfinished: one Blocked, one InProgress, two NotStarted |
| Updates | Latest Yellow, earlier Green |
| Quality gate | No recorded verdict; launch owner also empty |

The launch name says Q3 while the prepared release window says Q4 2026 with
a December target. Do not silently correct the record or conceal the
inconsistency. Empty gate fields do not establish whether a review ever ran.
The dedicated Status Updates view and form expose the saved updates. The PCF
Activity view also displays them; the empty standard timeline is not their source.

### Acceptance criteria

- [x] Pilot audience and environment setting are verified in the current UI.
- [x] App-level M365 Copilot indexing is enabled and published.
- [x] The selected app appears in Agent Builder knowledge; no all-app default.
- [x] The tested agent is declarative and uses the Microsoft 365 experience.
- [x] Four-table semantics regenerated after the five glossary terms were saved.
- [x] The two-turn rehearsal returns the launch and all four task records.
- [x] Explicit blocker fields match the native source form.
- [x] Task counts reconcile and missing blocker reasons are reported explicitly.
- [x] The nonexistent-record/source-override check returns an honest limitation.
- [x] No write, publication, sharing, or background execution is implied.
- [ ] A new capture probe visibly matches the Episode 12 browser panel.
- [ ] The actual recorded take passes source comparison and media review.

The latest first turn also retrieved the explicit blocked task, unlike the
earlier trial. Do not promise repeatable one-shot retrieval. Preserve the
two-turn demo and disclose the citation/owner-label limitations in the README.

If any criterion fails, report the exact gap. Do not replace the response
with Studio output, an uploaded answer file, or a narration-only success.

## Recording

Use the supplied `demo-recording-and-narration` recording scripts. Record one visible
application window cropped to the shared browser panel. Rediscover the
window handle and verify a probe frame before capture; old capture coordinates
and handles are not reusable evidence. Exclude account details, environment
identifiers, unrelated tabs, and notifications.

Record the ordered beats above and keep an event log. Settings already enabled
must be described as such. A navigation cut can shorten the setup, but must
not imply a setting changed when it did not.

Keep each prompt, response wait, and final answer contiguous at original
speed. Show both complete answers before returning to the source. Record the
current saved updates without crediting the declarative agent for creating
them. No business records should change in this take.

### Under-two-minute edition

The [LinkedIn narration](linkedin-voiceover-script.md) targets roughly
110 seconds, but that is a shot budget, not a measured video duration.
Plan a clearly labelled **result excerpt from a two-turn Preview conversation**.
Show completed responses rather than implying both full interactions fit.
The opening, value panel, and narration must identify the excerpt. Keep the
full run separately at original speed; never accelerate either response wait
or present an omitted wait as continuous.

The [main narration](voiceover-script.md) provides the same story with room
for the complete setup and response. It has no final timestamps until the
new master cut exists. Do not lay it over the old Studio recording.

## Review and handoff

Inspect the raw capture, contact sheet, and full playback. Build the cut and
value panel only from observed events. Generate measured narration cues,
subtitles, and a synthetic-voice timing preview from the new cut. Shorten
lines that overrun; do not speed up voice or video.

Before handoff, confirm source records remain unchanged and document the
agent's actual save/sharing state. No reset is needed for an unchanged
read-only take. Keep raw footage and identifiers private; publication or
external delivery needs separate approval.

Preserve the old Studio videos and Library ZIP as historical artifacts.
Use clearly different filenames for the replacement declarative-agent
recording so neither the captions nor the provenance can be confused.
