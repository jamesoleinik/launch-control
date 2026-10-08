# Episode 12 voiceover: Launch Readiness Checker through Work IQ

**Edition:** Recorded read-only run in Copilot Studio draft Preview.
**Video duration:** 6:06, including a 30-second opening and 28-second close.
**Timing:** Cues below use the 5:08 master cut. Add 30 seconds for the backup
edition. Keep the original AI response waits. Silence between cues is deliberate.
The synthetic voice is a timing aid, not the presenter's final narration.

## The script at a glance

| Section | Script |
| --- | --- |
| **Set the stage** (0:00) | I'm acting as a launch coordinator. I want to understand what is blocking this launch without piecing together every record myself. This is a recording of the draft agent in Copilot Studio. The records were prepared earlier, and all data is simulated. The answers come from a real Work IQ run. |
| **1. Start with the source** (0:30) | I start in Launch Control. The overview shows an open blocker and Yellow reported health. The Activity view shows the updates behind that status. |
| **2. Catch up through Work IQ** (0:55) | I ask the agent to catch me up on the launch. It uses Work IQ to find the business app and retrieve the launch evidence. I haven't pasted the answer into the conversation. The first answer needs discovery as well as record retrieval. This recording keeps that wait at its original speed. The agent follows the matching app and environment returned by Work IQ. It doesn't use a separate Dataverse MCP connection. I want recorded facts here, not a prediction dressed up as a decision. The answer identifies the blocker and unfinished tasks. It flags missing gate evidence instead of filling in the blanks. |
| **3. Identify the blocker** (3:15) | Now I ask what's blocking it. The answer links the blocker to its owner and task. It clearly says it reused the recent records. |
| **4. Check for a recorded verdict** (3:53) | Next I ask whether the launch is ready. This time the agent checks the launch and gate fields again. It distinguishes that fresh read from the related evidence already retrieved. There is no recorded verdict. The agent doesn't invent a decision. |
| **5. Show the agent connection** (4:46) | Here I can see Work IQ as the only connected tool source. This is an agent, not a workflow. This run is read-only. Instructions alone are not a technical write barrier. |
| **6. Return to the evidence** (5:12) | Back in Launch Control, I see the same blocker. These updates were prepared earlier. I haven't created tasks or changed the readiness record. The evidence stays in the app. |
| **Close** (5:38) | What I get is a grounded explanation of what needs attention. The agent helps me find the evidence, but it doesn't grant launch approval. This is an unpublished draft demonstration. Publication and private sharing still need their own review. The next decision belongs to the team. |

## Set the stage (over the opening slide)

> I'm acting as a launch coordinator. I want to understand what is blocking this launch without piecing together every record myself. This is a recording of the draft agent in Copilot Studio. The records were prepared earlier, and all data is simulated. The answers come from a real Work IQ run.

## Script

### 1. Start with the source (0:00-0:25)

*On screen:* Launch Control's Overview, then its custom Activity view.

- **0:01** I start in Launch Control. The overview shows an open blocker and Yellow reported health.
- **0:15** The Activity view shows the updates behind that status.

### 2. Catch up through Work IQ (0:25-2:45)

*On screen:* "Catch me up on the Q3 Widget Launch." Discovery, retrieval and
the actual response wait remain visible. The complete answer is shown at 2:35.

- **0:27** I ask the agent to catch me up on the launch.
- **0:45** It uses Work IQ to find the business app and retrieve the launch evidence. I haven't pasted the answer into the conversation.
- **1:10** The first answer needs discovery as well as record retrieval. This recording keeps that wait at its original speed.
- **1:35** The agent follows the matching app and environment returned by Work IQ. It doesn't use a separate Dataverse MCP connection.
- **2:00** I want recorded facts here, not a prediction dressed up as a decision.
- **2:35** The answer identifies the blocker and unfinished tasks. It flags missing gate evidence instead of filling in the blanks.

### 3. Identify the blocker (2:45-3:23)

*On screen:* "What's the current status, and what is blocking it?" The answer
explicitly says it reused the recent read rather than retrieving fresh records.

- **2:47** Now I ask what's blocking it.
- **3:13** The answer links the blocker to its owner and task. It clearly says it reused the recent records.

### 4. Check for a recorded verdict (3:23-4:16)

*On screen:* "Is the Q3 Widget Launch ready to launch?" The agent re-reads the
launch and gate fields, while distinguishing the earlier related-record evidence.

- **3:25** Next I ask whether the launch is ready.
- **3:35** This time the agent checks the launch and gate fields again. It distinguishes that fresh read from the related evidence already retrieved.
- **4:09** There is no recorded verdict. The agent doesn't invent a decision.

### 5. Show the agent connection (4:16-4:42)

*On screen:* Launch Readiness Checker in Build, with Work IQ (Preview) as its
only connected tool source. The agent remains unpublished.

- **4:19** Here I can see Work IQ as the only connected tool source. This is an agent, not a workflow.
- **4:33** This run is read-only. Instructions alone are not a technical write barrier.

### 6. Return to the evidence (4:42-5:08)

*On screen:* The same launch and its unchanged custom Activity entries, not
the empty standard Dataverse timeline.

- **4:44** Back in Launch Control, I see the same blocker.
- **4:52** These updates were prepared earlier. I haven't created tasks or changed the readiness record.
- **5:00** The evidence stays in the app.

## Close (over the closing slide)

> What I get is a grounded explanation of what needs attention. The agent helps me find the evidence, but it doesn't grant launch approval. This is an unpublished draft demonstration. Publication and private sharing still need their own review. The next decision belongs to the team.

## Delivery notes

Use a natural first-person delivery. Do not describe the synthetic preview as
the presenter's voice. Do not imply this recording proves the published
Microsoft 365 experience, server-enforced read-only access, or a completed
quality-gate review. The launch name and release-window mismatch are present
in the prepared data and are flagged by the agent, not silently corrected.
