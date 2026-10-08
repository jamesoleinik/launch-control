# Episode 12 voiceover: enable business knowledge, build a declarative agent

**Status:** Provisional copy for a new recording, not timed to existing media.
**Format:** Full setup walkthrough. Target cues below budget three minutes,
including a ten-second opening and ten-second close. Replace every cue with
measured cut times after rehearsal. The separate
[LinkedIn script](linkedin-voiceover-script.md) targets under two minutes.

Show an already-enabled environment honestly. Speak answer/result lines only
after the new declarative-agent run and source comparison pass. The
[archived Studio narration](../ep-14-copilot-studio/studio-rehearsal-voiceover.md)
remains tied to the previous video; do not dub this script over that footage.

## The script at a glance

These are provisional shot-budget times, not measured recording cues.

| Section | Script |
| --- | --- |
| **Set the stage** (0:00) | My launch data already lives in Power Apps. I want to ask about it inside Microsoft 365 Copilot. |
| **1. Enable business knowledge** (0:10) | First I check that my pilot users can use Business Applications in Work IQ. Then I check Work IQ in the Power Platform environment. It's already enabled here. I leave that setting on. |
| **2. Include the intended app** (0:40) | These sample records were prepared earlier. The app's Copilot setting enables indexing. Then I select Launch Control as my agent's business knowledge. App indexing and agent knowledge selection are separate steps. |
| **3. Build a focused declarative agent** (1:05) | I give the Launch Readiness Checker a clear job: explain recorded status and blockers. This is a declarative agent. I supply instructions and knowledge. Microsoft 365 Copilot handles the orchestration. |
| **4. Ask and wait for the evidence** (1:30) | Now I ask what's blocking the launch. I haven't pasted the answer into the chat. This knowledge connection provides read access. I'm not adding a workflow or a write tool. |
| **5. Compare the answer with the app** (2:30) | I compare the answer with the source records. It identifies the blocker without inventing a launch approval. My team can follow the evidence back to the app. |
| **Close** (2:50) | Copilot Studio comes later for more integration and control. Here I extended Copilot with business knowledge. All data is simulated. |

## Set the stage (over the opening slide)

> My launch data already lives in Power Apps. I want to ask about it inside Microsoft 365 Copilot.

## Script

### 1. Enable business knowledge (0:00-0:30)

*On screen:* Microsoft 365 pilot availability, then the intended environment's
Features page. These are configuration checks, not a staged toggle.

- **0:00** First I check that my pilot users can use Business Applications in Work IQ.
- **0:12** Then I check Work IQ in the Power Platform environment. It's already enabled here. I leave that setting on.

### 2. Include the intended app (0:30-0:55)

*On screen:* Launch Control's M365 Copilot app setting, its published app,
then explicitly selected Dynamics 365 and Power Apps knowledge in Agent
Builder. Say "enabled" only after the approved setting is saved and published;
app discovery must also pass before recording.

- **0:30** These sample records were prepared earlier. The app's Copilot setting enables indexing.
- **0:40** Then I select Launch Control as my agent's business knowledge. App indexing and agent knowledge selection are separate steps.

### 3. Build a focused declarative agent (0:55-1:20)

*On screen:* Agent Builder in Microsoft 365 Copilot. Show the agent name,
instructions, and selected app. Do not show Studio Build as a substitute.

- **0:55** I give the Launch Readiness Checker a clear job: explain recorded status and blockers.
- **1:06** This is a declarative agent. I supply instructions and knowledge. Microsoft 365 Copilot handles the orchestration.

### 4. Ask and wait for the evidence (1:20-2:20)

*On screen:* A fresh Try it conversation. Send the exact stage prompt,
"What's the current status, and what is blocking it?" Preserve the full wait.

- **1:20** Now I ask what's blocking the launch. I haven't pasted the answer into the chat.
- **1:32** This knowledge connection provides read access. I'm not adding a workflow or a write tool.

### 5. Compare the answer with the app (2:20-2:40)

*On screen:* The completed answer and matching app records. Adjust this
result copy if the verified source differs. Missing gate evidence stays explicit.

- **2:20** I compare the answer with the source records. It identifies the blocker without inventing a launch approval.
- **2:31** My team can follow the evidence back to the app.

## Close (over the closing slide)

> Copilot Studio comes later for more integration and control. Here I extended Copilot with business knowledge. All data is simulated.

## Production notes

The full setup may exceed this provisional budget. Keep real response waits
at original speed and extend the full edition when necessary. Do not imply
that an instruction or **Only use specified sources** blocks general AI
knowledge. The selected Dataverse knowledge route supplies no record-write
capability; that statement does not apply to every declarative agent.

After recording, regenerate the reading table and synthetic-voice preview
using the supplied recording skill. Verify every line against its actual
window, then produce synchronized subtitles. No replacement video, final
cue timing, or presenter audio is verified yet.
