# Studio rehearsal retained from the earlier Episode 12 build

**Superseded for Episode 12.** That episode now demonstrates direct Copilot
Chat and Cowork use of Business Applications in Work IQ. This earlier
recording demonstrates an unpublished Copilot Studio draft. Keep it as
reference for Episode 13, not as proof that either new episode is complete.

## What actually ran

The Launch Readiness Checker used **Work IQ (Preview)** as its sole MCP
server, with `do_action`, `get_schema`, `search_paths`, and `fetch` selected.
The recorded run used no workflow or direct Dataverse MCP. `do_action` is
write-capable, so this selection was not a server-enforced read-only policy.
Only discovery and reads were observed.

The user enabled Business Applications in Work IQ in the demo environment.
Before enablement, discovery returned HTTP 200 but no matching app. After
enablement, the draft found the app and retrieved the prepared records.
The model-driven app's generic `entity` component was repaired to `lc_launch`;
validation, an idempotent rebuild, and a solution export confirmed the mapping.
Related records were read through Work IQ's matching environment. This is not
proof that an app-scoped declarative knowledge source exposes those tables.

The raw sequence was:

1. Launch Control Overview and custom Activity.
2. "Catch me up on the Q3 Widget Launch."
3. "What's the current status, and what is blocking it?"
4. "Is the Q3 Widget Launch ready to launch?"
5. Studio Build showing Work IQ as the only tool source.
6. The same unchanged source Activity.

Catch-up used an exact-code launch query, related-launch filters, and
referenced-owner name lookups. Inspected reads returned HTTP 200 with one
launch, three milestones, four tasks, and two updates. The answers reported
AtRisk, the partner-certification blocker, four unfinished tasks, and no
recorded gate verdict. The prepared launch name/window mismatch was flagged.

The status answer explicitly reused the earlier retrieval. Readiness refreshed
the launch/gate fields but disclosed that related evidence was older. This
did not strictly meet the instruction to refresh everything before each
answer and must not be described as doing so.

Approximate Send-to-stable times were 106 seconds for catch-up, 12 for status,
and 32 for readiness. These are observations from one run, not guarantees.

An earlier unused workflow remained unpublished and unverified end to end.
Its individual action tests and earlier direct Dataverse MCP tests are not
Work IQ agent evidence. Neither is the chosen implementation.

## Preserved private artifacts

Original filenames retain `ep12` for provenance. They are not the replacement
Episode 12 recording. The original videos, subtitles, and Library ZIP remain
unchanged in private session storage.

| Artifact | File | Observed result |
|---|---|---|
| Raw capture | `ep12-workiq-raw.mp4` | 6:53.733, original waits |
| Event log | `ep12-workiq-events.json` | Send, stable answer, navigation, source comparison |
| Cut list | `ep12-workiq-cuts.json` | Setup/navigation and post-answer automation gaps removed |
| Clean master | `ep12-workiq-cut.mp4` | 5:08, six chapters |
| Full silent edition | `ep12-workiq-backup.mp4` | 6:06, opening/closing slides and value panel |
| Full timing preview | `ep12-workiq-backup-voiced.mp4` | Synthetic voice, not presenter audio |
| Full subtitles | `ep12-workiq-backup.voiceover.srt` | Synchronized with the old script |
| Short silent edition | `ep12-linkedin-backup.mp4` | 1:37 excerpt |
| Short timing preview | `ep12-linkedin-backup-voiced.mp4` | Complete included readiness wait |
| Short subtitles | `ep12-linkedin-backup.voiceover.srt` | Synchronized with the old short script |
| Local handoff | `episode12-private-review.zip` | Ten files verified against the reviewed artifacts |

The short edition omits the earlier catch-up and status turns as whole turns.
The title, footer, and narration disclose that it is not a fresh chat.
No included AI wait was accelerated.

Full-file decoding, chapter timing, slide fidelity, value-panel transitions,
narration fit, and subtitle synchronization passed. Full-edition demo-region
SSIM was 0.998939; short-edition SSIM was 0.998853 outside their closing
transitions. Contact sheets and selected full-size frames were inspected.
These checks do not establish complete presenter review.

Both voiced previews and the ZIP were delivered locally through the session
Library. No external upload or new recipient access was granted. No business
records changed, no reset was needed, and the agent remained unpublished.

## Handoff to Episode 13

- [Original full timed narration](studio-rehearsal-voiceover.md)
- [Original short timed narration](studio-rehearsal-linkedin-voiceover.md)
- [Studio rehearsal instructions](studio-rehearsal-agent-instructions.md)
- [Active Episode 13 specification](README.md)
- [Revised Episode 12 specification](../ep-12-business-apps-work-iq/README.md)

Revalidate the current Studio connection, identity, scope, and answer before
recording Episode 13. These artifacts do not verify Agent Builder, a published
Microsoft 365 agent, autonomous execution, or an approved write operation.
