# LinkedIn — Ep 7: Autonomous Agents

---

**Launch Control · Episode 7: Autonomous Agents.**

The Copilot Studio agent in Episode 6 only acts when I talk to it. That's fine for status questions. It's not fine for "ship blocker just appeared at 2am."

Enter **Launch Sentinel** — an autonomous agent triggered by Dataverse events. New high-severity risk row? Sentinel reads the row, checks the **escalation policy** (a Business Skill — same one the declarative agent uses), figures out who to page, and posts to the right channel.

The non-obvious thing: the escalation rules don't live inside the agent. They live in `business-skills/` so both the conversational coordinator and the autonomous sentinel route the same way. One source of truth for "what should happen."

If you've ever seen two automations disagree about who owns an incident, you know why this matters.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-07`)

Next: same skills, different runtime — a code-first Python agent.

#Dataverse #AutonomousAgents #CopilotStudio
