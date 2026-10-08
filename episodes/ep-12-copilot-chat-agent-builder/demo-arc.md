# Episode 12 demo arc: build, rehearse, record

This runbook turns the Episode 12 README into a repeatable demo using the
Launch Control app and a fictional launch. It adapts the multi-surface pattern
of opening in the business app, asking an everyday question in Copilot, showing
the agent's grounding, and returning to the same record. It does not reuse
private data, names, branding, recordings, or environment details from another
demo.

## Scope and proof

The central proof is that an answer in Copilot is grounded in the same governed
Dataverse record shown in the Launch Control app. If the tenant supports a
separately authorized write action, the optional follow-up beat previews the
exact tasks, waits for approval, reads them back, and shows the resulting
status update in the app. It never changes the launch's readiness verdict.

Do not imply that Agent Builder's Knowledge source alone enables writes. If a
confirmed write operation is unavailable, keep the recording read-only and
show the route limitation honestly.

## Before the build

1. Use an isolated demo environment with the Launch Control solution and
   sanitized sample records. Confirm that the sample launch and its linked
   blockers exist. Do not claim a Quality Gate verdict unless that operation
   has been configured and verified in the target environment.
   Preview `scripts/python/seed_ep12_demo.py --dry-run` and apply only its
   `[EP12-DEMO]`-scoped fictional records with `--apply`. The seed is
   idempotent and reads every saved row back. Do not run a broad seed script
   that deletes existing rows in the target environment.
2. Confirm that the account used in the app and Copilot has only the intended
   demo access. Do not use a System Administrator session to prove user-level
   restrictions.
3. Read the repository guidance, this episode README, the readiness skill, and
   [Launch Follow-up Plan](../../business-skills/launch-follow-up-plan.md).
4. Keep `.env`, tokens, environment URLs, tenant identifiers, and live record
   identifiers out of screenshots, video, and committed files.

## Build the app surface

The existing Launch main form places the Launch Readiness PCF beside the
Dataverse timeline. This branch adds an **Activity** view to the PCF, backed by
the five latest `lc_statusupdate` records for the selected Launch. It displays
the saved title, summary, health, and timestamp. It does not infer or display
which client created an update.

Build the PCF locally:

```powershell
npm run build --prefix apps/launch-readiness-control
```

For an authorized sandbox deployment, first build the unmanaged solution
package using the repository's Dataverse PCF deployment guidance. Then follow
the `dataverse-pcf-deployer` skill to import and bind it. The existing helper's
`--import-control` and `--apply-form` options publish changes to the configured
environment; inspect the target and obtain approval before running either.
If the form has no timeline yet, the helper adds the standard timeline beside
the readiness control.
Verify the form, PCF version, timeline placement, and Activity view in the
target app before recording.

## Build the agent experience

1. Keep the `Launch Readiness Checker` unpublished with Work IQ (Preview) as
   its sole MCP server. Direct Dataverse connectors and direct Dataverse MCP
   are not part of this Work IQ test. Results obtained through those routes
   must not be presented as Work IQ evidence.
2. A read-only Copilot Studio workflow is saved as a draft and currently
   appears as `Respond to the agent and 4 more`. It uses a fixed Launch Control
   environment, fixed table selections, and fixed filters for the fictional
   launch and related rows. Its four Dataverse actions were tested individually
   and returned 1 launch, 3 milestones, 4 tasks, and 2 status updates.
   Unnecessary personal columns were omitted. These action tests do not verify
   the workflow response step or agent invocation.
3. Copilot Studio marks the workflow `Not published` and disables it in the
   agent tool picker. The overall workflow Run view has no runs. Do not treat
   this as an end-to-end verified grounding route.
4. The workflow workaround is superseded by the user-directed agent-first
   approach. Leave it unpublished. The agent now uses the documented Work IQ
   business-app discovery route, `do_action` on `/businessapps/me`, with a
   Launch Control-specific query. The pre-enablement Preview call returned HTTP 200
   but no matching Launch Control app in its results. The agent reported
   missing access and did not use unrelated results as launch evidence.
   Resolve this visibility gap before attempting the recording. Do not assume
   that selecting Launch Control in Copilot Studio proves Work IQ can see it.
   The user approved and enabled **Turn on Business Applications in Work IQ**.
   A fresh admin-center page confirms it, Dataverse intelligence, and supporting
   search indexing are on. Review Copilot Credit costs and Microsoft 365 consent
   requirements. The post-enablement catch-up now retrieves the expected launch,
   three milestones, four tasks, two updates, and referenced owners through
   Work IQ environment SELECT queries. The app's generic `entity` mapping was
   repaired to `lc_launch`, validated, published, and verified in an idempotent
   rebuild and solution export. This publishes the model-driven app only;
   the agent remains a draft.
   The first launch query was unfiltered; saved instructions now require the
   exact demo code and returned launch ID for scoped reads. Repeat the ordinary
   prompts and inspect the actual queries before accepting the rehearsal.
   A subsequent readiness trace verified those filters, but its answer
   miscounted unfinished tasks. The final instruction revision adds task-status
   reconciliation; a fresh status/blocker run then correctly reported all four
   tasks unfinished (one Blocked, one InProgress, two NotStarted). Its filtered
   Work IQ reads and record counts were verified. After app repair, all three
   ordinary prompts were rerun in sequence in a fresh draft Preview on the
   final instructions, with correct counts and no invented gate verdict.
   This is not a published Microsoft 365 `@` picker rehearsal.
5. Configure only an approved, scoped, read-only connection. Use fresh Preview
   conversations to test the three ordinary prompts below and compare each
   answer with the source. Keep the agent unpublished and write operations
   disabled. If no safe connection can be verified, report that blocker and
   do not record the Copilot grounding portion.

The draft's Work IQ tool selection is limited to `do_action`, `get_schema`,
`search_paths`, and `fetch`. Broad `ask`, `list_agents`, binary retrieval, and
create/update/delete tools are disabled. `do_action` also supports mutations,
so this is not proof of a server-enforced read-only policy. Approve only the
specific discovery or read calls needed for the test.

## Rehearse with ordinary prompts

Use a fresh Copilot conversation and the same demo user for each take:

1. In the Launch Control app, open **Q3 Widget Launch** and show its readiness
   overview and current Activity entries.
2. In the unpublished Launch Readiness Checker's Copilot Studio draft Preview,
   enter: **"Catch me up on the Q3 Widget Launch."**
3. Then ask: **"What's the current status, and what is blocking it?"**
4. In the same draft conversation, ask:
   **"Is the Q3 Widget Launch ready to launch?"**
   The published Microsoft 365 `@` picker route is a separate future rehearsal,
   not a capability demonstrated by this recording.
5. After the agent's business-data connection has been verified, open the
   agent in Agent Builder and show that connection. Hide tenant and identity
   information. Return to the conversation and compare its answer against
   the app.
6. If the approved write path has passed its separate rehearsal, ask:
   **"Let's address the open blockers."** Review the exact task and status
   update proposal. New demo tasks and the status update must use the
   `[EP12-DEMO]` marker. Approve only if it matches the demo plan by entering:
   **"Looks good. Go ahead."**
7. Read each saved task and status update back from the source. Return to the
   same Launch in the app, refresh it, and show the Activity view. State that
   follow-up work was created, not that readiness changed. Run the readiness
   check again and show the actual result.
8. If the write route is unavailable, omit steps 6-7's writes. Show the
   read-only evidence and clearly label the action as unsupported in this
   tenant.

Time each response during rehearsal. Do not edit the user prompts to hide
latency or improve tool selection. Improve the agent instructions or business
skill, then repeat the complete rehearsal. Do not proceed to recording until
the agent's data retrieval, source comparison, and app evidence all pass.

## Recording

The supplied `demo-recording-and-narration` skill resolved the capture setup.
A fresh one-window probe verified this Episode 12 session and its shared
browser panel. Earlier probes of unrelated content were rejected and deleted.
The new recording and its derived editions remain in private session storage,
not the repository. No upload or sharing permission has been granted.

| Artifact | File | Result |
|---|---|---|
| Raw recording | `ep12-workiq-raw.mp4` | 6:53.733, original response waits |
| Event log | `ep12-workiq-events.json` | Send, answer stability, navigation, source comparison |
| Cut list | `ep12-workiq-cuts.json` | Only setup/navigation and post-answer automation gaps removed |
| Clean cut | `ep12-workiq-cut.mp4` | 5:08, six chapters, no overlays |
| Silent backup | `ep12-workiq-backup.mp4` | 6:06, title slides and value panel |
| Timing preview | `ep12-workiq-backup-voiced.mp4` | Built-in synthetic voice, not presenter narration |
| Read-along subtitles | `ep12-workiq-backup.voiceover.srt` | Matches the timed voiceover |
| Short silent excerpt | `ep12-linkedin-backup.mp4` | 1:37, below the original two-minute target |
| Short timing preview | `ep12-linkedin-backup-voiced.mp4` | Synthetic voice, full included readiness wait |
| Short subtitles | `ep12-linkedin-backup.voiceover.srt` | Matches the short voiceover |
| Review evidence | `raw-contact-sheet.png`, `edition-contact-sheet.png`, `edition-verification.json` | Private visual samples and automated checks |

The backup labels the run as recorded draft Preview with simulated data.
The agent stays unpublished. This run uses no workflow or direct Dataverse MCP.
Catch-up queries were inspected off-camera: exact demo-code launch filter,
related launch-ID filters, and referenced-name-only lookup, all returning
HTTP 200 and the expected record counts. Readiness re-read the launch/gate
fields. The status follow-up reused recent records and explicitly said so.
This differs from the instruction to refresh before every answer; it is
documented rather than concealed in editing.

The approximate Send-to-stable observations are 106 seconds for catch-up,
12 seconds for status, and 32 seconds for readiness. The first includes
discovery. These are one-run measurements, not latency guarantees.

The raw and voiced files decode completely. The cut contains 9,240 frames,
and the backup has eight chapters including the opening and close. Slide
mean absolute error is below 1.4 on a 0-255 scale. Demo-region SSIM is 0.998939
outside the closing transition, all twenty panel transitions match their
scheduled frames, and no narration line exceeds its time window.
Contact sheets and selected full-size frames have been inspected. Full
presenter playback/review remains pending, as do an approved private destination
and named reviewers. Automated decoding and sampled inspection are not a
claim that every frame has received human review.

The [short LinkedIn narration](linkedin-voiceover-script.md) accompanies a
separate excerpt, not an accelerated version of the full chat. It omits the
earlier catch-up and status turns as whole turns, with that omission disclosed
in the title, footer and narration. The readiness prompt and its complete wait
remain contiguous at original speed. The resulting video is exactly 97 seconds
with six chapters; full decoding and narration/SRT checks passed. Demo-region
SSIM is 0.998853 outside the closing transition. The full demo is unchanged.
Publication to LinkedIn is not part of this local artifact creation.

- Capture a single, visible application window rather than the full desktop.
  Keep the same window visible throughout. Do not minimize it or switch the
  active capture target mid-take.
- Close unrelated chats, notifications, and windows. Use sanitized demo data
  and hide account, tenant, and environment identifiers.
- Record the full sequence, including real response time. If editing pauses,
  preserve enough context that the recorded order and actual result remain
  clear. Do not fabricate a response or imply a write succeeded before read-back.
- Review the entire capture and inspect a contact sheet before sharing. Check
  every frame for private data and stale identifiers.
- Keep the recording, raw screenshots, and local capture scripts outside the
  public repository. Publish only sanitized episode materials and approved
  output.

For a Windows capture workstation with FFmpeg 9 and its `gfxcapture` input,
record only the selected app window. Replace the window handle and crop values
after inspecting a test frame. Save the master outside the repository:

```powershell
ffmpeg -f lavfi -i "gfxcapture=hwnd=<HWND>:capture_cursor=0:max_framerate=30" `
  -vf "hwdownload,format=bgra,crop=<WIDTH>:<HEIGHT>:<LEFT>:<TOP>" `
  -c:v libx264 -crf 20 "$env:USERPROFILE\Videos\episode12-master.mkv"
```

Review the full capture before editing. A contact sheet can help spot
unexpected windows or identifiers:

```powershell
ffmpeg -i "$env:USERPROFILE\Videos\episode12-master.mkv" `
  -vf "fps=1/20,scale=320:-1,tile=4x4" `
  "$env:USERPROFILE\Videos\episode12-contact-sheet.jpg"
```

Keep every AI response wait intact at original speed. Remove only automation
gaps between steps or excess post-answer holds. Never splice in a generated
answer or imply a write completed before its read-back. Record the presenter's
voice separately against the reviewed silent edition, and confirm each line
finishes before its visual cue changes.

## Reset and verify

This recorded run was read-only. Its final source read shows the same open
blocker, Yellow health, and prepared Activity entries. No reset or reseed is
needed, and source records must not be deleted to reset a read-only take.

For a separately approved future write rehearsal, use an approved cleanup
method to identify `[EP12-DEMO]`
tasks and status updates for the exact demo Launch. Review the matching rows
before deleting anything, then read back the launch, task, and update baseline.
Do not delete source blockers or unrelated demo data. If the marker or target
is ambiguous, or cleanup cannot be verified, stop and leave the environment
unchanged for its owner to resolve.
