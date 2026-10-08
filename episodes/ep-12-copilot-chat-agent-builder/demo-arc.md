# Episode 12 demo arc: enable, select the app, ask

**Production status:** Revised shot list, not a completed recording.
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
| Select the app | Published Launch Control app, then its selected Agent Builder knowledge | The intended business app is included explicitly |
| Configure | Agent Builder instructions in Microsoft 365 Copilot | A declarative agent gives a repeatable question a focused purpose |
| Ask | Fresh Try it conversation and one complete response | An actual answer grounded in the selected business data |
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
   administrator's successful read as proof of another user's access.
4. Verify **Dynamics 365 and Power Apps data** is available in Agent Builder
   and select the intended app explicitly. If absent, record the limitation
   privately and stop this portion of the demo.
5. Confirm the available related-record scope. The current app spec contains
   only `lc_launch`; PCF access to tasks and updates does not establish
   knowledge-source access. Do not broaden to every accessible app to get a
   better answer.
6. Apply the [declarative-agent instructions](launch-readiness-agent-instructions.md).
   Exclude unrelated sources and write-capable tools. Keep the agent's
   publication and sharing state explicit.

## Rehearsal

Use a fresh conversation in the actual Microsoft 365 Agent Builder **Try it**
surface. Do not use the existing Studio draft, its transcript, or its timings.

First ask **"What's the current status, and what is blocking it?"** The saved
instructions identify the fictional launch. Measure from Send until the
answer stops changing, then compare the answer with current app evidence.

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
The PCF Activity view, not the empty standard timeline, shows the updates.

### Acceptance criteria

- [ ] Pilot audience and environment setting are verified in the current UI.
- [ ] The selected app appears in Agent Builder knowledge; no all-app default.
- [ ] The tested agent is declarative and uses the Microsoft 365 experience.
- [ ] All required related records are available through that selected route.
- [ ] The answer agrees with current source records and names its evidence.
- [ ] Task counts reconcile; missing fields and stale evidence are explicit.
- [ ] The nonexistent-record check returns an honest limitation.
- [ ] No write, publication, sharing, or background execution is implied.

If any criterion fails, report the exact gap. Do not replace the response
with Studio output, an uploaded answer file, or a narration-only success.

## Recording

Use the supplied `demo-recording-and-narration` skill. Record one visible
application window cropped to the shared browser panel. Rediscover the
window handle and verify a probe frame before capture; old capture coordinates
and handles are not reusable evidence. Exclude account details, environment
identifiers, unrelated tabs, and notifications.

Record the ordered beats above and keep an event log. Settings already enabled
must be described as such. A navigation cut can shorten the setup, but must
not imply a setting changed when it did not.

Keep the prompt, response wait, and final answer contiguous at original
speed. Show the complete answer before returning to the source. Record the
current Activity entries without crediting the declarative agent for creating
them. No business records should change in this take.

### Under-two-minute edition

The [LinkedIn narration](linkedin-voiceover-script.md) targets roughly
110 seconds, but that is a shot budget, not a measured video duration.
Use one question. If the actual wait exceeds the available time, shorten
setup/navigation and spoken copy. If it still cannot fit, label a separate
result excerpt that omits the interaction, rather than accelerating the AI
or presenting an omitted wait as continuous. Keep the full run separately.

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
