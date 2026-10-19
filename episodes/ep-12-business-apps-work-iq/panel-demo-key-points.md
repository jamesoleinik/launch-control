# Launch Control: business apps in Chat and Cowork

> Historical tracker for the completed 112-second Edition A. For the
> unverified expanded story, use the separate
> [Revision B draft tracker](revision-b-key-points.md).

**Status: tracker timed to the recorded Chat/Cowork review edition.**
The Microsoft plugin was enabled before the takes. The edit uses actual
native Chat, Cowork, glossary, and app-window recordings, not agent footage.
It retains the read retry and the assistant's assignee correction.

Layout: 12 seconds of opening cards, 88 seconds of recorded demo, and a
12-second held-frame close. The short edition is 112 seconds. Readable pickups
replace portions affected by window resizing; the original takes remain private.
Record identifiers are blurred and account-owner fields are outside the crop.

The full raw run is retained privately. Processing acceleration is approved.
No extra speed indicators, footer, result heading, or footage labels.
The recording is edited for time, not a response-latency demonstration.

```powershell
$env:PYTHONIOENCODING = "utf-8"
$scripts = Join-Path $HOME ".copilot\skills\panel-demo-video\scripts"
python "$scripts\build_panel_video.py" `
  --doc episodes\ep-12-business-apps-work-iq\panel-demo-key-points.md `
  --panes-only artifacts\ep12-panel-demo\chat-cowork\panes `
  --close-seconds 12 --result-label "" --footer "" `
  --agenda-subtitle "Ask in Chat. Follow up in Cowork."
```

## Opening cards

| Seconds | Kicker | Title | Text | Accent |
| --- | --- | --- | --- | --- |
| 6 | Launch Control | Your business apps. In Copilot. | Business Applications in Work IQ<br>Copilot Chat and Copilot Cowork | |
| 6 | Two experiences | Ask. Follow up. Verify. | Chat: understand the launch.<br>Cowork: propose the follow-up. | |

## Steps

### 1. Start with the launch (0:00-0:08)

- **Tag:** App evidence
- **Surface:** Launch Control Demo
- **Value:** Start with the recorded business facts before asking for an explanation.
- **0:01 Native record:** The launch and its related work.
- **Result 0:05:** [amber] Recorded launch status: At Risk

### 2. Put business meaning to work (0:08-0:18)

- **Tag:** Business context
- **Surface:** Power Apps
- **Value:** Prepared business definitions give the app evidence context.
- **0:09 Glossary:** Business vocabulary prepared earlier.
- **0:13 Risk versus blocker:** A risk does not establish a blocked task.
- **Result 0:16:** [teal] Prepared app context, not canned answers

### 3. Ask Copilot Chat directly (0:18-0:34)

- **Tag:** Direct chat
- **Surface:** Microsoft 365 Copilot Chat
- **Value:** Ask for launch status and blockers without creating a custom agent.
- **0:19 App scope:** Use only Launch Control Demo.
- **0:27 Evidence:** Read the returned facts and limitations.
- **Result 0:31:** [teal] Business evidence in the conversation

### 4. Check the answer's evidence (0:34-0:44)

- **Tag:** Source check
- **Surface:** Chat sources and Launch Control
- **Value:** Compare the answer with the actual task before acting on it.
- **0:35 Source records:** Verify the blocked flag and recorded reason.
- **Result 0:41:** [amber] A risk is not automatically a blocker

### 5. Confirm the Cowork connection (0:44-0:56)

- **Tag:** Plugin access
- **Surface:** Copilot Cowork
- **Value:** Business apps (preview) connects Cowork to business context when policy and permissions allow.
- **0:45 Built-in plugin:** Business apps (preview), published by Microsoft.
- **0:49 Access check:** Organization approval and a working connection.
- **Result 0:53:** [teal] Plugin access is a prerequisite

### 6. Give Cowork bounded work (0:56-1:12)

- **Tag:** Business follow-up
- **Surface:** Copilot Cowork
- **Value:** Ask for a follow-up proposal based on fresh evidence from the same app.
- **0:57 Fresh retrieval:** Cowork reads its own business-app evidence.
- **1:05 Clear boundary:** No record changes, messages, or schedules.
- **Result 1:09:** [teal] A proposal, not a saved action

### 7. Review reason and responsibility (1:12-1:20)

- **Tag:** Review
- **Surface:** Cowork verification response
- **Value:** Read saved assignees before trusting a draft.
- **1:13 Saved task fields:** Cowork corrects its earlier assignee claim.
- **Result 1:17:** [teal] Verified correction, still a proposal

### 8. Return to the source (1:20-1:28)

- **Tag:** Human decision
- **Surface:** Launch Control Demo
- **Value:** The app remains the source of truth. The answer is not a launch approval.
- **1:21 Native comparison:** Check the proposal against the saved task.
- **Result 1:25:** [amber] Evidence, not a launch approval

## Close

1. Business app context is available in Chat and Cowork.
2. Check access and verify the source.
3. Next: extend the scenario with agents.
