# Launch Control panel-demo plan: Copilot Chat and Cowork

**Status: recorded 112-second review edition complete; not externally published.**
Episode 12 is about Business Applications in Work IQ directly in Copilot
Chat and Copilot Cowork. Cowork uses the Microsoft-published
**Business apps (preview)** plugin. Custom-agent authoring has moved to
[Episode 13](../ep-13-cowork/README.md), covering declarative and Studio agents.
The prior developer-led Episode 12 plan, panes, and audio are superseded.

The presenter later requested a broader story: a launch 360 view in Chat that
combines productivity context with live business status, followed by Cowork
coordinating tasks and scheduled monitoring. That is now documented as
[Revision B](revision-b-demo-arc.md), with a
[draft tracker](revision-b-key-points.md) and
[draft voice-over](revision-b-voiceover.md). These are editorial drafts only.
The existing Edition A evidence does not prove retrieval of email, Teams
conversations, or files, nor does it prove task creation or scheduled
monitoring. No such operation was attempted. The new story requires read-only
verification, presenter review, and separate explicit approval before any
live write, schedule, reset, or recording.

### Revision B offline review

The draft tracker rendered successfully with two opening cards, eight steps,
28 panel states, and a 195-second proposed demo timeline. The contact sheet
is in the gitignored local folder
`artifacts\ep12-panel-demo\chat-cowork\revision-b-panes\contact-sheet.jpg`.
Its draft-result labels and provisional timings are not observed evidence.
The Revision B voice-over table was generated and its table/lint check passed
with the house comma limit configured to two. No footage exists for this
revision, so read-aloud review, synthetic-voice fit, live source verification,
and final timing remain outstanding. The generated pane images are local
review artifacts and are not committed.

## Recorded review deliverables

The recordings were made on October 14, 2026. The completed private package
is under `artifacts\ep12-panel-demo\chat-cowork\`:

| File | Purpose |
|---|---|
| `final\ep12-chat-cowork-panel.mp4` | Silent 112-second panel master for presenter narration |
| `final\ep12-chat-cowork-panel-voiced.mp4` | Synthetic voiced preview with an optional English subtitle track |
| `final\ep12-chat-cowork-panel.voiceover.srt` | Separate read-along subtitles |
| `final\ep12-chat-cowork-review-sheet.jpg` | Cards, all steps, correction, and close for visual review |
| `final\validation.json` | Media, chapter, subtitle, and narration-fit results |
| `edit\ep12-chat-cowork-cut.mp4` | Clean 88-second demo cut; no extra label edition is needed |
| `edit\ep12-chat-cowork.cuts.json` | Source ranges, held waits, and chapter definitions |
| `recordings\` | Private original takes, event logs, and framing pickups |

Both panel files are 1920x1080 at 30 fps, with ten chapters: opening,
eight steps, and close. The SRT has fourteen cues. The default-rate synthetic
narration fits every window; opening speech ends at 9.6 seconds and closing
speech at approximately 110.1 seconds. The final preview decodes successfully.
The cards, step states, source comparisons, retry, correction, and held close
were inspected in extracted frames.

The short cut retains the failed-read/retry state and the actual assignee
correction. The Chat task follow-up returned one task, not a complete inventory.
Cowork's references were record names and IDs, not direct hyperlinks. Record
identifiers are blurred in the Chat excerpts; real account-owner fields are
cropped out. Pickups improve framing without rewriting responses. Full waits
and the unmodified original takes remain private. Publication requires review
and separate authorization.

## Confirmed brief

| Item | Decision |
|---|---|
| Audience | Public Launch Control episode for Power Platform makers and developers |
| Scenario | The existing Launch Control Demo app and Q3 Widget Launch |
| Role and acts | Launch coordinator: ask in Chat, then follow up in Cowork |
| Capture | Record the complete episode in the GitHub Copilot app window only |
| Public edit | 90-120 seconds, accelerating processing waits where needed |
| Labels | No extra speed indicators, fictional-data disclaimers, result heading, or footage labels |
| Visual structure | Opening cards beside an outline, demo beside an evidence-timed tracker, takeaways over the held last frame, chapters |
| Narration | First person; presenter records the master, synthetic voice is a timing aid |
| Editions | Short silent panel master, voiced preview, SRT, clean cut, private complete raw capture; no extra act/subset editions requested |
| Clearance | Public product names and preview wording; no real names or environment identifiers on screen |
| Privacy and reset | Approved neutral-role preparation; baseline comparison and reset/readback after every rehearsal and take |

This is a recording edited for time, not a real-time latency demonstration.
The user explicitly approved processing acceleration without additional
on-screen labels. Preserve readable questions, results, errors, and source
checks. Keep the source raw capture unchanged.

## Setup prerequisite: Cowork plugin access

The supplied screenshot shows **Business apps (preview)** by Microsoft,
with a Work IQ connection and a `business-applications` skill. It also shows
**This plugin is blocked by your organization's policy** and **Request access**.

That screenshot was the earlier state. The Microsoft plugin was subsequently
enabled after the presenter directed continuation of the listed preparation.
The toggle persisted after reload. The later run used the actual
`business-applications` skill and Business apps (preview) read operations.
No organization policy or new connection was created or changed.

The Episode 12 canvases are signed in to Chat, Cowork, and the native Launch
Control app. The semantic-model page is also accessible and still shows
62 items, four tables, five glossary terms, and sample rows Off.
Old Builder and Studio transcripts are not replacements for native evidence.

## Latest live run-through

The presenter requested rehearsal and recording after signing in. Initial
window-visibility and crop failures were discarded. Subsequent native,
glossary, Chat, plugin, and Cowork recordings were checked, with readable
pickups used where the long take's window geometry changed.

| Check | Observed result |
|---|---|
| Source baseline | One launch, three milestones, four tasks, two saved updates, and two linked demo personas read privately. One task is explicitly blocked; the launch remains AtRisk with empty gate fields. |
| Native Chat, exact prompt | Both an ordinary chat and a temporary-chat retry confused the app name with an environment name and qualified app provenance. The ordinary chat's Sources panel also included a past chat. Neither is a clean first-turn success. |
| Native Chat, diagnostic | After clarifying app versus environment with the runtime-resolved app URL, the planned task-view question returned four task citations. Titles, statuses, blocked flags, assignees, due dates, and the recorded blocker reason matched the live source. Missing fields and lack of saved-view metadata were qualified. |
| Native Chat, recorded take | After role/app-context preparation, the question retrieved the explicit blocker. Its task-view follow-up returned one task. The edit preserves that result rather than presenting the earlier four-task rehearsal as this take. |
| Cowork, initial disabled-plugin attempt | Requested a generic Dataverse connection. That substitute was canceled without approval. |
| Cowork, enabled-plugin run | Used Business apps (preview), selected the environment containing the requested app, and read the launch, four tasks, three milestones, and two updates. The blocked task, reason, neutral assignee, due date, risk, update health, and empty gate fields matched live Dataverse. A failed read URL was followed by successful supported reads. Only scoped read requests were approved. |
| Cowork proposal and references | Produced a review-only follow-up plan and identified missing evidence and source inconsistencies. Returned record names and IDs, not direct hyperlinks; a follow-up explicitly reported that limitation. Do not portray these references as clickable source links. |
| Cowork, recorded verification | The initial draft incorrectly called a secondary task unassigned. A follow-up requested saved assignee reads without supplying the answer. Cowork corrected itself and displayed all four saved assignees. That corrective response is retained in the panel edit. |
| Missing-record and source-substitution checks | Both native experiences reported no matching launch for the test code and refused to fabricate an Approved verdict from unrelated sources or general knowledge. These are response-grounding checks, not row-level permission tests. |
| Neutral preparation | Only the two seeded demo-owned persona display labels changed to Launch Coordinator and Partner Review Lead. The original values were backed up; changes were read back. Real user accounts and launch/task facts were not changed. |
| Reset/readback | Rehearsal and capture-attempt readbacks matched the neutral recording baseline, including modification metadata. Resets were verified no-ops. The two preparation writes are distinct from run-caused changes. |
| Capture | Correct Episode 12 window probes were obtained, but the shared physical window subsequently displayed other sessions and changed size. Unrelated probes and the unusable take were deleted. A live-pixel wait timed out; Windows refused a foreground activation, so no physical navigation click was sent. |

Before the next take, the actual Windows capture machine must keep GitHub
Copilot on Episode 12 with its browser panel visible and the screen unlocked.
An app-side navigation result or accessibility-tree match is not enough:
verify actual window pixels, measure immediately before capture, and check the
encoded dimensions. Stop if another session appears.

Resolve app versus environment context before the stage question without
supplying expected answers. Establish the presenter role as Launch Coordinator
before recording; the first Cowork response otherwise used the account name.
Crop the glossary Owner column and native record-owner/account chrome rather
than renaming real users or rewriting rendered responses.

Private snapshots and observations are under
`artifacts\ep12-panel-demo\chat-cowork\live\`. Keep app locators, IDs, persona
backups, and raw transcripts out of committed prose and public footage.

## Recorded story

Opening cards introduce the coordinator's business question and the two
experiences. The [tracker](panel-demo-key-points.md) matches the measured
112-second edit, including its bookends.

| Step | Problem | Surface | Visible evidence and value |
|---|---|---|---|
| 1. Start with the launch | Status alone does not explain the work | Native Launch Control app | The prepared record is the comparison baseline |
| 2. Make app meaning useful | Business terms need context | Saved glossary | Definitions were prepared earlier |
| 3. Ask Chat directly | The coordinator needs status and blocker evidence | Copilot Chat, not Agent Builder Preview | Fresh scoped question and actual answer |
| 4. Check Chat's evidence | A generated answer needs verification | Returned sources and native task | Compare retrieved fields and missing evidence |
| 5. Check the Cowork connection | Plugin availability is not permission | Business apps (preview) listing/connection | Verify policy approval and selected app before using it |
| 6. Give Cowork bounded work | The coordinator needs a follow-up proposal | Copilot Cowork with the built-in plugin | Fresh business-app retrieval, no custom agent |
| 7. Review the proposal | Proposed work needs verification | Cowork corrective response | Saved assignees correct the draft; no saved changes |
| 8. Return to the source | Neither answer is launch approval | Native task and launch | Evidence supports a human decision; bridge to Episode 13 |

Use the exact stage prompts and rehearsal criteria in [demo-arc.md](demo-arc.md).
The short cut prioritizes the two native experiences; the full run includes
enablement checks and complete waits. Do not regenerate the semantic model
or toggle an already-enabled setting for a shot.

## Live preparation and reset

1. Read the scoped launch, linked milestones, tasks, saved updates, and
   displayed persona labels. Privately back up the exact fields before
   proposing any changes.
2. Inventory all intended shots for real names, account chrome, identifiers,
   and notifications. Use neutral labels only for approved demo-owned
   records, such as Launch Coordinator and Partner Review Lead.
3. Never rename real Entra users or unrelated records. Crop account details
   or use an approved demo identity; do not rewrite rendered page text.
4. Apply only the separately approved mapping and read it back. Retain the
   pre-change backup separately from the neutral recording baseline.
5. Before and after every rehearsal/take, compare statuses, blocked fields,
   relationships, assignees, dates, updates, and saved gate fields.
6. Preview and reset only run-caused differences, then read back every write.
   Record a verified no-op reset for an unchanged read-only run.
7. Stop on concurrent edits or an uncertain target. Do not run broad seed,
   security teardown, or cleanup scripts. Start fresh conversations for the
   next run without altering the app, glossary, or permissions.

The existing app configuration helper is not a reset helper. The scenario
remains At Risk; do not manufacture a green outcome.

## Production phases and gates

| Phase | Work | Gate |
|---|---|---|
| Editorial revision | Update Episode 12, Episode 13, series links, and offline assets | Approved for this revision; no live operations |
| Story | Render cards and tracker with `--panes-only` | Presenter reviews the new wording/panes before recording |
| Access | Authenticate and verify Chat plus the allowed Cowork plugin | Authorized policy approval and correct source access |
| Rehearsal | Fresh scoped prompts, actual sources, proposal only | Separate Chat/Cowork evidence and baseline reset/readback |
| Capture | Discover the current GitHub Copilot window and crop; check liveness; log events | Explicit recording go-ahead, visible/unlocked correct window |
| Cut and panel | Observed events, accelerated processing, whole-second chapters, held-frame close | Final 90-120-second video and readable evidence |
| Narration | Retiming, style check, local synthetic voice, subtitles | No overruns and alignment to real footage |
| Review and handover | Inspect the cut and rebuild dependent outputs after feedback | Playback, final source baseline, actual state documented |

No external publication or agent deployment occurred. The existing Microsoft
plugin was enabled and the two demo-only persona labels were prepared before
recording. Rehearsals and takes caused no source-record changes; readbacks
matched the neutral baseline. Episode 13's developer knowledge-binding
question is not an Episode 12 prerequisite.

## Files and offline outputs

- [README](README.md): active scope, access prerequisites, native evidence,
  glossary, and direct-use prompts.
- [Demo arc](demo-arc.md): shot procedure, exact prompts, acceptance, reset.
- [Tracker](panel-demo-key-points.md): cards, steps, takeaways.
- [Narration](voiceover-script.md): canonical short-edit script and reading table.
- [Short-edition note](linkedin-voiceover-script.md): same canonical edit.

Use the personally installed panel-demo kit. New private outputs go under
`artifacts\ep12-panel-demo\chat-cowork\`, separate from the superseded
developer-led assets:

- `panes\contact-sheet.jpg`: proposed visual review.
- `narration-audio\ep12-chat-cowork-rehearsal.wav`: audio-only timing aid.
- `narration-audio\ep12-chat-cowork-rehearsal.srt`: draft read-along cues.
- `narration-audio\timing-report.json`: measured speech fit.

Offline renders and audio checks do not prove live retrieval, video duration,
or final subtitle synchronization. No new demo footage is produced by them.

### Superseded offline rehearsal

The revised renderer produced two opening cards, eight steps, and 24 panel
states. The contact sheet was inspected: the outline, titles, evidence boxes,
and close fit without the unwanted footer or result heading.

The 112-second audio-only rehearsal contains 14 cues. The script's style,
reading table, and exact subtitle text checks pass. The default-rate synthetic
speech fits every proposed window: opening speech ends at 9.552 seconds and
closing speech at 110.082 seconds. There are no cue overruns. These are audio
timings only; final video fit still depends on actual footage.
