# Launch Control re-record map

**Status: 2:10 highlights edition and production review complete.** The
presenter identified incomplete setup navigation, failing Chat sources,
diagnostic prompts instead of the README conversations, and unrelated
automations. Historical deliverables remain separate from the new live cut.

## Current 2:10 slower narration edition

Latest preview: `ep12-slower-15-panel-voiced.mp4`, with matching
`ep12-slower-15-panel.voiceover.srt` in the ignored media folder.
The script is shortened from 433 to 368 words. Average delivery falls
from about 200 to 170 words per minute, a 15.01 percent reduction.
All thirteen cue windows, chapters, and the 130-second picture are preserved.
The script retains business context, reviewed Dataverse write-back,
the blocked-task transition, scheduled email briefings, and preview wording.

Full media decoding passes. Silence detection at -40 dB measures the
longest pause at 0.325 seconds, below the one-second limit.
Subtitle text matches the complete spoken script. Narration lint and the
regenerated summary table pass. The measured results are saved in
`ep12-slower-15-panel-voiced.validation.json`.

## Earlier 2:10 gap-limited edition

Latest preview: `ep12-gapless-panel-voiced.mp4`, with matching
`ep12-gapless-panel.voiceover.srt` in the ignored media folder.
The narration now contains 433 words, adding relevant business context
to fill the gaps introduced by accelerating the shorter script.
Speech fills all thirteen 10-second windows at about 200 words per minute,
approximately the requested faster delivery, rather than finishing early
and padding each cue with silence. The picture remains unchanged.

Full decoding with silence detection at -40 dB measures the longest
pause at 0.262 seconds, below the requested one-second maximum.
The machine-readable result is
`ep12-gapless-panel-voiced.validation.json`. Narration lint and the
regenerated summary table pass. The runtime remains 130 seconds.

## Earlier 2:10 voice-at-1.5x edition

Latest preview: `ep12-voice-150-panel-voiced.mp4`, with matching
`ep12-voice-150-panel.voiceover.srt` in the ignored media folder.
The voice is 1.5x relative to the continuous edition, as requested.
Pitch, all 13 cue starts, picture, and chapters are preserved.
Full media decoding passes and duration remains exactly 130 seconds.

## Earlier 2:10 moderate-voice edition

Latest preview: `ep12-moderate-voice-panel-voiced.mp4`, with matching
`ep12-moderate-voice-panel.voiceover.srt` in the ignored media folder.
The rejected 2x voice is reduced to 1.25x relative to the continuous
edition, preserving pitch, all cue starts, and the unchanged picture.
Each passage takes eight seconds of its ten-second window. The video
remains exactly 130 seconds and full decoding passes.

## Earlier 2:10 doubled-voice edition

Latest preview: `ep12-double-voice-panel-voiced.mp4`, with matching
`ep12-double-voice-panel.voiceover.srt` in the ignored media folder.
At the presenter's explicit request, only the voice is doubled in speed
using pitch-preserving `atempo=2` on each previously fitted cue.
The 13 cue starts, picture, chapters, and 130-second runtime are unchanged.
Each spoken passage now takes half its prior time, followed by silence
until the next cue. This supersedes continuous delivery for this preview;
no extra words were added. Subtitle times are halved within each cue.
The silent master remains `ep12-continuous-panel.mp4`.
Audio and video durations are verified at 130 seconds; full decoding passes.

## Earlier 2:10 continuous-narration edition

Latest files: `ep12-continuous-panel-voiced.mp4`, silent
`ep12-continuous-panel.mp4`, and
`ep12-continuous-panel.voiceover.srt` in the ignored media folder.

The full narrative is rewritten using the Microsoft blog's themes of
shared business understanding, the business app remaining the system of
record, governed updates, and staying in the flow of work. The sync
wording is removed from narration and the current tracker.
The spoken close now follows all three on-screen takeaways: bring
business context together, save reviewed Dataverse updates and schedule
follow-up, then try the preview rollout in Copilot and Cowork.

At the presenter's request, narration spans the full 130 seconds rather
than leaving deliberate gaps or a silent closing hold. Thirteen contiguous
10-second speech windows cover the four steps and close. The ignored
`continuous_preview.py` synthesizes each cue, trims excess synthetic pauses,
and fits its speech to the window with pitch-preserving audio tempo
adjustment. It does not change video speed. Natural short pauses remain.
`ep12-continuous-timing.json` preserves each window and adjustment.
This intentionally replaces the standard preview's silent-close timing
rule for this edition.

Narration lint and the summary table pass. A full decode with silence
detection reports no pauses of 0.75 seconds or longer at -40 dB.
Sentence subtitles contain the complete script without gaps in their
0-130 second timeline. The final panel sheet confirms connected-context
wording and all three takeaways beside the retained diagram zoom.
No business records, settings, schedules, or messages were changed.

## Earlier 2:10 follow-up transition edition

Latest voiced file: `ep12-followup-panel-voiced.mp4`, with matching
`ep12-followup-panel.voiceover.srt` in the ignored media folder.
The silent master remains `ep12-workflow-panel.mp4`.

Step 3 now closes: "The follow-up is saved. Now I need to monitor this
blocker." Step 4 answers: "So I schedule a Cowork briefing to check
progress and flag what still needs attention." This ties the schedule
to ongoing visibility rather than implying that the saved note resolves
the task. The existing Work IQ context, no separate sync, and email
delivery lines remain.

No new task, schedule, research, or evidence request was executed. The
earlier schedule footage remains a separate example, not a run triggered
by the later write-back. All 15 cues fit, table/subtitle matching passes,
and full media decoding passes. Pictures and the 130-second runtime
are unchanged.

## Earlier 2:10 business-context edition

Latest voiced file: `ep12-business-context-panel-voiced.mp4`, with matching
`ep12-business-context-panel.voiceover.srt` in the ignored media folder.
The silent master remains `ep12-workflow-panel.mp4`.

The incomplete opening outcome is replaced at 0:24 with "Now Copilot can
understand and act on my business data." The preceding access-setting
line is shortened to fit the unchanged 30-second section. This follows
the Learn description of discovering, reading, and acting on business
data alongside productivity information, with source permissions and
governance preserved. All 15 cues fit, table/subtitle matching passes,
and full media decoding passes. The picture and 130-second runtime
are unchanged.

The episode directory is now `episodes/ep-12-business-apps-work-iq`.
Repository links, script paths, and environment defaults use the new slug.
Legacy environment selectors remain accepted by the shared auth helper.

## Earlier 2:10 return-to-Launch-Control edition

Latest voiced file: `ep12-return-panel-voiced.mp4`, with matching
`ep12-return-panel.voiceover.srt` in the ignored media folder. The silent
master remains `ep12-workflow-panel.mp4`; no picture or timing changed.

The opening now welcomes viewers back: "We're finally back to Launch
Control." It introduces the new Business Applications in Work IQ preview
before the app and environment enablement narration. All 15 cues fit and
the subtitle/table matching passes. The four 30-second sections and
10-second close remain unchanged.

## Earlier 2:10 scheduled-workflow edition

Latest files: `ep12-workflow-panel-voiced.mp4`, silent
`ep12-workflow-panel.mp4`, and matching
`ep12-workflow-panel.voiceover.srt` in the ignored media folder.
The existing `ep12-delegate-cut.mp4` remains the clean demo source.

Section 4's narration and tracker now emphasize automating future reviews
through Cowork scheduled tasks, live context through Work IQ and business
apps without a separately maintained sync, and email updates in the flow
of work. The three cues are at 1:30, 1:39, and 1:50. Recorded schedule
creation, Automations, the run result, and received Outlook email are
unchanged. No new schedule or email was created.

The one-time run required attended read approvals. The ongoing automation
value is not evidence of unattended recurring execution. "No separate sync"
means no presenter-maintained export or duplicate pipeline, not a claim
that semantic indexing has zero latency or access is unlimited.

All 15 cues fit, subtitle/table matching passes, and full media decoding
passes. Video and audio both run exactly 130 seconds. The six-frame review
confirms the schedule, run, email, updated tracker, and retained zoomed
three-takeaway close. Section 3 plugin configuration and real reviewed
Dataverse write-back are preserved.

## Earlier 2:10 Cowork delegation edition

Latest files: `ep12-delegate-panel-voiced.mp4`, silent
`ep12-delegate-panel.mp4`, clean `ep12-delegate-cut.mp4`, and matching
`ep12-delegate-panel.voiceover.srt` in the ignored media folder.
The edit map is `ep12-delegate.cuts.json`.

Step 3 now opens with 11 seconds of the previously recorded Cowork Business
apps plugin page. The switch is enabled and the server shows Disconnect,
confirming the connected state. This is the saved configuration, not a
new toggle or sign-in. It is followed by four seconds of the scoped proposal,
four of staged-change review, five of saved-result read-back, and six of
independent native-app verification. Earlier footage and the write-back task
remain separate recordings, not a continuous newly executed session.

The narrative is: "I need the next step analyzed and tracked in Dataverse.
With the Business apps plugin enabled, I delegate that work to Cowork."
It then explains analysis, proposal, personal review, and the next step
recorded in Dataverse. The evidence task explicitly stays blocked.
The tracker is retimed to these screens.

All 15 narration cues fit; the close still ends 8.3 seconds into its
10-second window. The nine-frame review confirms the enabled plugin,
proposal, staged review, saved result, app verification, and retained
three-takeaway zoomed outro. No live settings, records, or schedules were
changed for this edit.

## Earlier 2:10 three-takeaway edition

Latest files: `ep12-three-panel-voiced.mp4`, silent `ep12-three-panel.mp4`,
and matching `ep12-three-panel.voiceover.srt` in the ignored media folder.
The close now says **THREE THINGS TO TAKE AWAY** and reveals these items
at 2:00, 2:04, and 2:08:

1. Bring your business records together with Microsoft 365 context in Copilot.
2. Drive reviewed updates back into Dataverse and receive scheduled briefings.
3. Worldwide preview rollout in Microsoft Copilot and Cowork.

Both requested Learn pages were reread. They support business context and
permission-governed actions; both still label the capability preview. The
previous rollout qualification remains unchanged. The slow diagram zoom,
four demo sections, narration, and exact 130-second duration are preserved.
The four-frame review shows the complete three-item close without clipping.
Narration fit, subtitle matching, and full media decoding pass.

## Earlier 2:10 zoom-and-takeaways edition

Latest files: `ep12-zoom-panel-voiced.mp4`, silent `ep12-zoom-panel.mp4`,
and matching `ep12-zoom-panel.voiceover.srt` in the ignored media folder.
The app-first cut and all four demo sections are preserved.

The outro retains the recorded documentation scroll. After two seconds,
an eight-second editorial zoom moves from 1.0x to 1.7x toward the Work IQ
diagram, without cropping its edges or changing the right pane. The source
is the existing documentation take, seconds 7-17. It is not a new live
product interaction. A held tail frame ensures the video stream itself,
not just the chapter metadata, reaches exactly 130 seconds.

The two takeaways now explicitly cover business context, reviewed updates
back into Dataverse, scheduled briefings, and a worldwide preview rollout
in Microsoft Copilot and Cowork. The close narration is regenerated to
match. It ends 8.3 seconds into the 10-second close. All 14 cues fit.

Availability is deliberately described as rollout, not a claim that every
tenant has it today. The [Microsoft announcement](https://www.microsoft.com/en-us/dynamics-365/blog/it-professional/2026/09/25/work-iq-business-and-workplace-intelligence-in-the-flow-of-work/)
says preview starts September 30 with rollout continuing through October.
The current [Learn overview](https://learn.microsoft.com/power-apps/maker/data-platform/business-applications-work-iq)
and [Cowork documentation](https://learn.microsoft.com/microsoft-365/copilot/cowork/cowork-work-iq)
still call the capability preview and retain access/setup requirements.
Worldwide completion could not be independently verified.

The six-frame review at 2:00, 2:02, 2:04, 2:06, 2:08, and 2:09.5 shows
the scroll, progressive zoom, complete diagram, and both takeaways.

## Earlier 2:10 app-first edition

Latest files: `ep12-app-first-panel-voiced.mp4`, silent
`ep12-app-first-panel.mp4`, and matching
`ep12-app-first-panel.voiceover.srt`. All are in the ignored media folder.
The four 30-second sections and 10-second close are unchanged in length.

Section 1 now starts with the actual populated app, then makes the route to
Copilot explicit:

| Time | Recorded picture |
| --- | --- |
| 0:00-0:04 | Launch Control populated launch list |
| 0:04-0:12 | App designer, Settings, Features, M365 Copilot enabled |
| 0:12-0:20 | Environment Features, Work IQ enabled |
| 0:20-0:26 | Tenant Copilot business-app data access setting |
| 0:26-0:30 | Copilot Chat opening screen |

Narration introduces two business-data settings after the app-designer step.
The tracker says the user can work in Copilot instead of opening the app for
every review, not that the native app can never be needed. Existing recorded
enabled settings were reused without changing live configuration. Catalog
navigation is removed from this short opening; plugin availability remains
documented as a prerequisite. Section 2 starts directly on the successful
saved Chat prompt/answer review, rather than repeating the app introduction.
The Chat opening screen is navigation, not new answer generation.

The 2:00-2:10 outro now opens the Microsoft Learn article and scrolls to the
requested Work IQ productivity-and-business-data diagram. The prior email
still ends Section 4. The new close is real window-only browser footage from
`ep12-docs-outro-take.mp4`, using seconds 7-17 at original speed, fitted into
the left pane. The right-side takeaways and closing narration are retained.
The diagram is explanatory documentation, not a claim that Copilot Studio
or additional systems were demonstrated.

`ep12-app-first.cuts.json` and `ep12-app-first-cut.segments.json` preserve the
new edit map. All 14 narration cues fit with no over-window lines. Narration
lint, summary table, and subtitle matching pass. Final duration is exactly
130.000 seconds, with all five chapter boundaries preserved. Full media
decoding passes. The 16-frame final review sheet was inspected at the app,
designer setting, environment setting, tenant access, Chat opening, preserved
results, and the documentation scroll/diagram.
The latest voiced file was opened in the browser panel and played from the
start with sound enabled. Playback advanced with ready state 4, duration
130 seconds, and no media error.

## Earlier 2:10 write-back edition

The latest video is `ep12-writeback-panel-voiced.mp4`, with silent master
`ep12-writeback-panel.mp4` and matching subtitles
`ep12-writeback-panel.voiceover.srt` in the media folder. It remains exactly
130.000 seconds. Section 1 is titled **Put your business app to work**.
Section 3 now demonstrates **Write back to your business app** rather than
a read-only plan. The short tracker and narration are the current sources.

Cowork independently read Q3 Widget Launch and its blocked partner-evidence
task. It proposed adding a follow-up sentence to `lc_risksummary`, checked
the current value, staged that one field with `prepare_update`, and saved
it with `submit_update` after the separate confirmation. Cowork then read
the record back. The native app form independently showed the saved
follow-up. Status, priority, owner, target date, and task records were not
changed. The task stayed blocked; no evidence request was sent or completed.

The live pickup is `ep12-writeback-take.mp4`, with its event log. The retained
privacy copy is `ep12-writeback-private.mp4`. Incidental owner/account names
are blurred, not replaced with different answer text. Its edit is defined
by `ep12-writeback.cuts.json` and `ep12-writeback-cut.segments.json`.
The new 30-second section has five real-motion segments: proposal at 1:00,
staged review at 1:05, submit approval at 1:10, saved-result comparison at
1:15, and app verification at 1:21. The retained pickup segments run at
approximately 1.2 to 2.6 times original speed, under the presenter's existing
speed-up policy. The other sections use the prior privacy-reviewed footage.

The changed field was backed up in the ignored media folder. A dry-run
checked the exact environment, unique demo record, and expected saved text.
The reset then restored only that field, using its read ETag to prevent
overwriting concurrent edits. Read-back confirmed the original risk summary.
The captured update is real; the live demo data is back at its baseline.

README comparison:

| Section | Current evidence |
| --- | --- |
| 1. Enable business context | Prior verified settings click-throughs, 0:00-0:30 |
| 2. Understand status in context | Prior successful saved Chat answer and loaded Sources, 0:30-1:00 |
| 3. Review and save a scoped update | New Cowork proposal, review, submit, read-back, and native app verification, 1:00-1:30 |
| 4. Receive the briefing | Prior one-time scheduled run and received Outlook email, 1:30-2:00 |
| Close | Received email held beneath the updated takeaways, 2:00-2:10 |

The README now contains the pickup's exact proposal, stage, and save prompts.
The earlier scheduled email predates the new write-back pickup and is not
represented as a response to the changed summary. No new schedule or email
was created. The 2:10 edition is highlights, not a full readable transcript.

All 20 pane states fit. The pane sheet and final footage at the review,
approval, saved result, app verification, all four results, and both closing
reveals were visually reviewed. All 12 narration cues fit, with no over-window
lines; table and subtitle matching pass. Closing speech ends 5.4 seconds into
the 10-second close. Full audio/video decoding passes, with H.264 1920 by
1080 video, AAC audio, and chapters at 0, 30, 60, 90, and 120 seconds.
The new voiced edition was opened at Section 3 in the final-player browser.
Playback advanced with unmuted audio, readyState 4, duration 130 seconds,
and no media error.

## Superseded business-value edition

The latest value-led revision is `ep12-business-value-panel-voiced.mp4`,
with silent master `ep12-business-value-panel.mp4` and matching subtitles
`ep12-business-value-panel.voiceover.srt` in the media folder. It supersedes
the initial `ep12-130-panel-voiced.mp4` below without changing its 130-second
runtime or four 30-second steps. All four panels and the narration now
address someone applying the pattern to their own supported business process:
reuse the existing app, understand status with communications, develop
process-grounded follow-up, and receive the next review in the inbox.

The capabilities and results describe enabled value, not the buttons or
fields passing on screen. The source scope remains model-driven apps, not
every possible business application. Cowork's plan is explicitly a proposal:
no launch, task, or other business record was updated. Only the separate
approved automation and its email were created.

All 20 updated pane states fit and were visually reviewed. Final result and
closing frames were checked in `ep12-business-value-review.jpg`. Narration
lint, summary-table consistency, subtitle matching, and full audio/video
decoding pass. The 12 cues fit their windows; closing speech ends 5.4
seconds into the 10-second outro. Duration remains exactly 130.000 seconds.

The presenter requested a 130-second total, interpreted as four 30-second
steps and a 10-second outro. Opening cards are removed. The existing
privacy-reviewed recordings are edited and accelerated, not replaced with
static screenshots. This short version presents the central points rather
than promising that every field or answer can be read at accelerated speed.

| Section | Final timing |
| --- | --- |
| 1. Set up the business context | 0:00-0:30 |
| 2. Compare the launch with the team's evidence | 0:30-1:00 |
| 3. Review follow-up with Cowork | 1:00-1:30 |
| 4. Receive the scheduled briefing | 1:30-2:00 |
| Outro over the received Outlook message | 2:00-2:10 |

The cut uses 18 accelerated segments, between 2.0 and 11.8 times original
speed. Long navigation is fastest; answer reviews and the final email
receive more time. Speed changes are disclosed here and in the short
tracker's production notes, consistent with the existing no-extra-label
policy. No performance claim is made, no answer is rewritten, and no
schedule or email was created again.

Current files in `.local/recordings/launch-control/`:

- `ep12-130-panel-voiced.mp4`: latest 2:10 voiced edition.
- `ep12-130-panel.mp4`: silent 1080p panel master.
- `ep12-130-panel.voiceover.srt`: matching read-along subtitles.
- `ep12-130-cut.mp4`: clean 120-second accelerated demo.
- `ep12-130.cuts.json` and `ep12-130-cut.segments.json`: exact speed/cut map.
- `ep12-130-final-review.jpg`: inspected transitions, results, and outro.

The short tracker and narration are `short-key-points.md` and
`short-voiceover.md`. The panel builder's required temporary one-second card
is trimmed before final narration, with exact chapter metadata regenerated;
it is not part of the delivered runtime. Probe confirms exactly 130.000
seconds, 1920 by 1080 H.264 and AAC, with chapters at 0, 30, 60, 90, and
120 seconds. All 20 panel states fit and were visually reviewed. All 12
narration cues fit, the 10-second close finishes speaking at 8.6 seconds,
and script/table/subtitle consistency checks pass. Full media decoding
completed without errors. The 10:13 edition below remains the detailed
walkthrough, not the latest requested highlights video.

The latest 2:10 voiced edition was opened in the final-player browser panel.
Playback was verified advancing with unmuted audio, readyState 4, duration
130 seconds, and no media error.

## Earlier focused revision

The presenter requested a successful launch-level story rather than a video
highlighting missing task evidence. The app was inspected and the published
configuration verified: Tasks already belongs to the app with the intended
native evidence form, active view, fields, and table component metadata.
Adding it again was not warranted. No environment-wide semantic model refresh
was performed, and no retrieval fix is claimed.

The README Chat prompt now asks only for saved launch status and risk compared
with relevant communications. A successful fresh rehearsal returned the launch,
Teams conversation, certification brief, handoff draft, and received readiness
briefing. A new live pickup scrolls that saved prompt and complete answer and
opens its loaded Sources. It does not show generation. A separate repeat
returned a less useful answer; that repeat is excluded, not spliced into the
successful answer or represented as the same run. Incidental personal metadata
is blurred and unrelated additional references are covered.

Narration and tracker now emphasize saved launch status, aligned team context,
reviewable follow-up, and a received briefing. Task-retrieval-gap narration and
tracker entries are removed. The technical-gap email scroll is omitted; the
actual answer and received email are not rewritten. Business uncertainty such
as certification being under review remains part of the scenario, not a
retrieval-failure claim.

| README section | Focused panel timeline | Picture |
| --- | --- | --- |
| Setup | 0:20-2:46 | Existing real settings click-throughs |
| App and Chat | 2:46-4:43 | Four launches and record drill-in; focused saved prompt at 3:21; full answer scrolls; loaded Sources from 4:25 |
| Cowork review | 4:43-6:32 | Existing exact-prompt blocker/owner/date review and proposed plan |
| Scheduled briefing | 6:32-9:53 | Existing one-time schedule; attended read approval at 8:37; completed run at 8:49; actual received email at 9:01 |
| Close | 9:53-10:13 | Progressive takeaways over the received briefing |

All current media are in `.local/recordings/launch-control/`:

| Deliverable | Current file |
| --- | --- |
| Latest voiced preview | `ep12-focused-panel-voiced.mp4` |
| Silent panel | `ep12-focused-panel.mp4` |
| Subtitles | `ep12-focused-panel.voiceover.srt` |
| Clean and labelled cut (no additional labels) | `ep12-focused-v2-cut.mp4` |
| Cut list and map | `ep12-focused.cuts.json`, `ep12-focused-v2-cut.segments.json` |
| New window-only pickup | `ep12-focused-chat.mp4` and its event log |

The focused cut is 573 seconds across 22 native-speed segments. With the
20-second opening and 20-second close, the panel is 613 seconds (10:13).
The old 11:52 edition below is superseded, not the current preview.
The new Chat footage includes the previously received briefing as a source;
the later schedule chapter reuses its genuine earlier creation and delivery
capture. This is a multi-take walkthrough, not a new chronological send.
No schedule was rerun and no additional email was sent for this revision.

Final review checked the two opening cards, all four step results, the
new Chat prompt and every answer section, the loaded source panel, the
retained email summary/table, and each progressive closing takeaway.
All 30 tracker states fit. The rebuilt narration and subtitles pass lint,
summary-table matching, and SRT matching; all 31 timed lines fit their windows.
Intro speech ends at 15.0 seconds before the 20-second demo start; closing
speech ends 15.9 seconds into its 20-second hold. Probe confirms 1920 by 1080
H.264, AAC audio, and chapters at 0:00, 0:20, 2:46, 4:43, 6:32, and 9:53.
The complete voiced file decoded without media errors.

The final voice and tracker were checked specifically for the presenter's
request: neither highlights missing task retrieval, missing-evidence lists,
or unavailable source links. The original business content is intact and
technical limitations remain in these production notes, not the spoken story.
The evidence review prompted one further edit: remove the email's dedicated
gap-focused scroll and return to the executive summary after the work table
and recommendations. The last picture remains the real received message.

The latest focused voiced file was opened at its new Chat segment (3:21).
Browser playback was verified advancing with a 613-second duration,
readyState 4, unmuted audio, and no media error. It replaces the old preview
in the final-player panel.

## Replacement acceptance checks

1. Record actual clicks through all four setup surfaces. Show the navigation
   and saved setting, not screenshot holds. Do not broaden permissions.
2. Rehearse the exact README Chat prompt in a clean conversation. Verify the
   business and productivity citations and the Sources side panel. A source
   loading failure is a failed check, not acceptable final evidence.
3. Show the README prompts and complete Chat and Cowork answers. The focused
   revision uses a live review of the successful saved Chat answer rather
   than claiming a new generation capture. Exclude diagnostic/test conversations.
4. Show the populated launch list, open Q3 Widget Launch, and inspect its
   saved evidence and related work. Additional marker-scoped demo launches
   were seeded with read-back; retain neutral role names.
5. If needed, back up and adjust the account's Copilot custom instructions to
   improve source routing and presentation. Do not insert answers or hide
   retrieval failures.
6. Compare the actual narration with the Summit NA 2026 reference: first-person
   launch-lead voice, problem to visible tool to business value, clear section
   bridges, and a concrete outcome. Make edits and record pickups as needed.
7. Create the approved native Cowork scheduled follow-up for this launch,
   verify a run, and end on the resulting email in the current user's Outlook.
   Use a readable subject, executive summary, status/blocker/owner table,
   recommended next steps, and source links. Confirm recipient, timing, and
   send scope before the consequential action. Never substitute a direct
   manual email for a scheduled Cowork result.
8. Review the final video against every README section and exact prompt.
   Record timestamps and any remaining gaps here. Correct mismatches and
   obsolete README status text before handover. Play the final video only
   after these checks pass; do not mark blocked work complete.

## Prior 11:52 edition evidence (superseded)

| Check | Current evidence | Status |
| --- | --- | --- |
| Setup click-through | Final panel 0:20-2:46 retains all four actual navigation paths, with the clean Product > Features > Work IQ pickup. Saved settings are shown without broadening tenant policy. | Reviewed in final picture |
| Chat sources | The exact README prompt in a fresh Chat returned the launch, matching Teams post, certification brief, and handoff draft. References and Personalization loaded. Related task fields were not retrieved. | Verified for those sources, not every related task |
| Full conversations | Final panel 3:21-5:39 and 5:51-7:28 retain the exact README prompts and complete answer scrolls. Cowork uses the intended Business apps plugin and separates proposed work from recorded facts. Internal lookup/approval gaps are omitted, not represented as response performance. | Reviewed in final picture |
| Seed and record tour | Three additional fictional launches, four milestones, and six tasks were applied with per-record read-back. Final panel 2:46-3:21 shows four launches, opens Q3 Widget Launch, and visits its evidence and readiness tabs. Neutral role names are retained. | Reviewed in final picture |
| Instruction quality | Existing Chat source-routing instructions are documented in `chat-custom-instructions.md`. The new exact-prompt rehearsal now retrieves the matching communications and file. No new account-wide customization was made or is claimed necessary. | Existing customization retained |
| Summit style | Compared the final cards, outline, live-demo/tracker layout, and four-part close with the supplied reference frames. Final narration follows the bundled Summit script's first-person problem, tool, and value arc. No full movie-to-movie comparison is claimed. | Reviewed within the available reference scope |
| Scheduled email | Final panel 7:28-11:32 shows the one-time schedule, attended read approval, one completed run, and the actual HTML email in Outlook from 9:57. The schedule is paused. No manual or duplicate send was substituted. | Verified; direct record links unavailable |
| README comparison and playback | All four README sections and both exact review prompts map to the final timeline below. Task retrieval, citation navigation, attended execution, and source-link limitations remain explicit. The latest voiced edition was opened in the browser and verified advancing with unmuted audio, decoded frames, and no media error. | Reviewed and playing |

### Replacement takes

All media below are in the ignored `.local/recordings/launch-control/` folder.
They are window captures, not screenshot montages.

| Take | Length | Review and edit instructions |
| --- | --- | --- |
| `ep12-v2-settings.mp4` | 232.7 s | Keep the actual tenant, tool-catalog, and app-setting navigation. Replace the environment segment with the clean pickup. Remove incidental environment identifiers from the final picture. |
| `ep12-v2-environment.mp4` | 41.3 s | Clean pickup: Product expands, Features opens, then scroll to Work IQ. Contact sheet checked at 0, 8, 16, 24, 32, and 40 seconds. No inventory-tour popup; checkbox read-back is checked. |
| `ep12-v2-app.mp4` | 35.6 s | Four-launch list, click into Q3 Widget Launch, General evidence, Launch Readiness, and Risks. Do not imply Work IQ reads rendered PCF content. |
| `ep12-v2-chat.mp4` | 222.9 s | Keep the exact prompt and complete answer scroll. Loaded Sources are visible around 198-202 seconds. Exclude 204 seconds onward: clicking a business citation opened authentication rather than the record. |
| `ep12-v3-cowork.mp4` | 554.5 s | Enabled Microsoft plugin, exact README prompt, scoped read approvals, complete answer and supplemental task result. Internal lookup failures and approval pauses are edited for time, not represented as response performance. |
| `ep12-v3-schedule.mp4` | 177.4 s | Native one-time schedule creation, sole-recipient permission review, Run once now off, and filtered launch-specific Automations entry. |
| `ep12-v3-delivery.mp4` | 1568.3 s | Actual timed-run approval, received Outlook message with live body scroll, and native Runs (1), Completed, and Paused proof. Retain only the privacy-reviewed portions in the final cut map. |

The event log's `sources_loaded` entry was written late. Use the actual
198-202-second frames, not that log entry, for the Sources scene. The README
Sources image is a genuine frame at 200 seconds, cropped above unrelated
additional references. The answer still reports missing underlying task rows.
Do not describe the draft handoff email as sent, or claim every citation
opens successfully. Bringing the conversation forward after citation
navigation reloaded it and did not retain the native citation controls.

### Summit narrative comparison and chosen edits

The narrative comparison uses the bundled Summit NA written voice-over and
style guide. The visual comparison uses four supplied reference frames:
opening cards and outline, live demo beside the tracker, and closing takeaways.
A finished Summit movie was not available for a new full-length viewing.

| Rejected edition mismatch | Replacement edit | Evidence required in the final picture |
| --- | --- | --- |
| The opening lists checks instead of a launch problem. | Introduce the coordinator's need to reconcile a saved risk with team communications. | Opened launch and matching Chat comparison |
| Setup dominates the story without saying why it matters. | Keep real navigation but explain it as the approved path to business context. | Clicks and saved settings, not held screenshots |
| Chat narration talks mostly about a source error. | Show the complete new answer and its loaded sources, then briefly state the remaining task-level gap. | Exact prompt, answer scroll, loaded References panel |
| Cowork is reduced to a plugin switch. | Bridge from understanding the issue to reviewing follow-up using recorded owners and due dates. | Fresh full Cowork answer using the intended plugin |
| The close lands on unrelated schedules and caveats. | Land on the coordinator receiving a useful, readable launch briefing. | Native schedule, successful run, actual received email |

The final narrative opens with the coordinator's saved risk, moves from
understanding to reviewed follow-up, and ends on the received briefing rather
than an unrelated schedule. The setup explains why the connection matters,
not just which switches exist. The Chat and Cowork bridges state the next
business need. Short caveats accompany the visible evidence rather than
dominating the close. All picture cues were checked against the final cut.

The environment pickup replaces a distracting portal inventory detour.
The final Outlook take replaces the previous screenshot ending. Full answer
scrolls replace diagnostic prompt snippets. Final subtitle review also found
a hyphenated word split across a line; the narration and preview were rebuilt
with the clearer phrase "business data reads." No additional pickup was
needed after the final picture review.

### Prior README coverage and deliverables

Times below refer to the 11:52 panel edition, including its opening cards.

| README section | Final panel | Confirmed result and remaining limits |
| --- | --- | --- |
| 1. Enable Business Applications in Work IQ | 0:20-2:46 | Tenant setting, tool catalog, environment Product > Features > Work IQ, and app Copilot setting are real click-throughs. Existing policy is not broadened. |
| 2. Launch Control and Copilot Chat | 2:46-5:39 | Four-launch list and opened record, exact prompt, full answer, and loaded Sources at 5:31-5:39. Underlying task fields remain missing. The handoff is an unsent draft. A later business-citation click hit authentication and is excluded, not described as successful record navigation. |
| 3. Cowork review | 5:39-7:28 | Intended plugin enabled and connected, exact prompt, recorded blocker, role owner/date, proposed plan, evidence gaps, and additional acceptance-task result. No business writes or sends occur in this review. |
| 4. Scheduled follow-up | 7:28-11:32 | One-time schedule and recipient scope, attended read approval at 9:33, completed-run proof at 9:45, and received Outlook email at 9:57. The body is scrolled through its highlighted work table, proposed steps, gaps, and named sources. Direct record links were unavailable. |
| Closing takeaways | 11:32-11:52 | Four progressive takeaways over the actual received briefing. A deliberate closing hold, not replacement screenshot footage. |

The schedule was triggered once, with Run once now off. Its received message
appeared in Inbox at 8:39 PM during the demonstration. Native Automations
independently shows one completed run and the one-time schedule paused.
It used only the signed-in user's verified mailbox, without CC or BCC.
The audience-facing HTML has an executive summary and highlighted
blocked/overdue work, with role owners, dates, proposed steps, gaps, and
source names. The absence of clickable record links is a disclosed output
limitation, not a claimed success.

All current media below are in `.local/recordings/launch-control/`:

| Deliverable | File |
| --- | --- |
| Latest voiced preview | `ep12-readme-final-panel-voiced.mp4` |
| Silent 1080p panel master | `ep12-readme-final-panel.mp4` |
| Read-along subtitles | `ep12-readme-final-panel.voiceover.srt` |
| Clean and labelled live cut (no labels needed) | `ep12-readme-final-cut.mp4` |
| Multi-take cut list | `ep12-v3.cuts.json` |
| Cut-to-take map | `ep12-readme-final-cut.segments.json` |
| Final picture reviews | `ep12-final-panel-review.jpg`, `ep12-final-evidence-review.jpg`, `ep12-final-clickthrough-review.jpg` |

Production review confirmed 24 native-speed segments, a 672-second cut,
and a 712-second panel edition. The panel chapters start at 0:00, 0:20,
2:46, 5:39, 7:28, and 11:32. The voiced preview is 1920 by 1080 H.264 with
AAC audio. Full audio/video decoding completed without errors. All cards,
step results, close reveals, setup/record navigation, and final email scenes
were viewed in the final contact sheets. All 31 tracker states fit.
Narration lint, summary-table consistency, and subtitle matching passed;
all 32 timed lines fit their windows. The stage ends at 15.0 seconds,
before the demo at 20.0; closing speech ends 15.9 seconds into the 20-second
close. The synthetic voice is a timing preview, not a claimed presenter take.

The enriched fictional data remains available for the demonstration.
The recorded Chat, Cowork review, and scheduled briefing only read business
records; proposed follow-up is not saved work. The intended plugin remains
enabled as approved, and the one-time schedule is paused. The temporary
scoped read-approval helper was stopped; no blanket Do action permission
was enabled. Capture and rendering processes have ended. Current takes,
event logs, and fit reports are retained as production evidence.

The latest voiced preview was opened only after the production and README
reviews. Browser playback confirmed a 712-second duration, readyState 4,
advancing time, unmuted full-volume audio, decoded video frames, and no media
error. It remains playing in the final live-walkthrough browser panel.

### Partial working assembly

`ep12-v2-partial.cuts.json` builds `ep12-v2-partial-cut.mp4`, a 348-second
working assembly of the new setup, app, and Chat takes. It is not the final
episode or a handover preview. It has no Cowork act, scheduled-email ending,
tracker, narration, or subtitles, and has not been played as the final video.

The seven-segment cut check passed. Probe confirmed H.264 at 1200 by 1062
with chapters at 0 and 175 seconds. Transition and answer frames were
inspected at 2, 45, 104, 145, 177, 212, 280, 290, 310, 330, and 346 seconds.
The complete new prompt and AI generation remain at original speed;
repeated idle reading time after the answer was removed. The failed citation
navigation is excluded. Before any audience preview, mask the unrelated
additional references at the bottom of Sources and incidental account
labels. That partial assembly is now superseded by the privacy-reviewed final
deliverables above.

### Approved scope and run behavior

The presenter subsequently approved enabling the README components,
explicitly including the existing Microsoft Business apps (preview) plugin.
The intended Microsoft plugin was enabled and read back as checked. Its
existing connection shows Disconnect and its business-applications skill
is listed. No tenant policy was changed and the duplicate plugins remain
off. The new exact-prompt Cowork capture completed using this plugin.

The native schedule's sole recipient was verified as the signed-in user's
mailbox. The one-time timing and email effect were checked before saving,
with Run once now off. Its timed run started and asked for approval of the
app's read operations. This is an attended scheduled run, not proof of
unattended execution. No manual send or unrelated automation can satisfy
the delivery gate.

## Historical deliverables (rejected edition)

- Silent 1080p panel master:
  `.local/recordings/launch-control/ep12-live-rerecord-panel.mp4`
- Browser-compatible silent AAC copy:
  `.local/recordings/launch-control/ep12-live-rerecord-panel-playable.mp4`
- Timed synthetic voice preview:
  `.local/recordings/launch-control/ep12-live-rerecord-panel-voiced.mp4`
- Read-along subtitles:
  `.local/recordings/launch-control/ep12-live-rerecord-panel.voiceover.srt`
- Clean 115-second demo cut:
  `.local/recordings/launch-control/ep12-live-rerecord-cut.mp4`
- Cut list:
  `.local/recordings/launch-control/ep12-live-rerecord.cuts.json`
- Tracker and narration:
  [readme-rerecord-key-points.md](readme-rerecord-key-points.md) and
  [readme-rerecord-voiceover.md](readme-rerecord-voiceover.md)

The panel edition runs 2:35: 20 seconds of opening cards, a 1:55 demo, and a
20-second close. Its four whole-second chapters start at 0:00, 0:46, 1:30,
and 1:45 on the demo cut.

## What the rejected recording shows

1. **Work IQ setup, 0:00-0:46.** Read-only views of the tenant Copilot
   setting, Business apps availability, environment Work IQ setting, and
   model-driven app Copilot setting. No access or policy was changed.
2. **Copilot Chat, 0:46-1:30.** The existing Launch Control record and Chat
   answer, followed by the Sources pane. It reports a personalization-source
   loading error and generic Dynamics entries. This does not prove complete
   cross-source retrieval or provenance for every citation.
3. **Cowork connection, 1:30-1:45.** The Business apps plugin is enabled and
   connected. The earlier proposal response is not shown because its table
   exposed tenant and record identifiers. This section does not demonstrate
   a saved task, update, or other action.
4. **Automation state, 1:45-1:55.** Active readiness checks for other work.
   The view is reframed to exclude a paused probe and its exact date. No
   Q3 Widget Launch schedule was verified or created.

The title cards, tracker, four-step reveal, and close follow the Summit panel
reference. The cut keeps AI response time intact and uses no screenshot holds.
The automation reframe and the evidence limitations are disclosed in the
production notes and narration.

## Historical verification (not replacement acceptance)

- `multi_cut.py --check` passed: 10 segments, 115 seconds, four chapters on
  whole-second section starts.
- The demo cut was checked at setup transitions, the Chat answer and Sources
  pane, the Cowork connection, and the automation view. The proposal table
  containing identifiers is not retained.
- `build_panel_video.py --panes-only` rendered the cards and all 19 tracker
  states without text-fit errors.
- `check_script.py` passed. The synthetic timing preview reports no lines
  over their windows; all 11 spoken units fit.
- `ffprobe` confirmed the panel copy is 1920x1080 H.264 with AAC audio,
  four section chapters, and a 155-second runtime.
- The AAC copy was opened in the browser preview and verified playing.
