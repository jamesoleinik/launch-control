# LinkedIn — Ep 1: AI-Powered Data Modeling

> Tone: builder/PM-hybrid, first-person. ~180 words. Open with a real friction, show the artifact, hand off to next episode.

---

🚀 New series: **Launch Control**.

12 episodes. One project: a launch-management system where Microsoft Dataverse is the source of truth and a small team of agents handles the rest.

Every line of code is going up on GitHub.

---

**Episode 1: AI-Powered Data Modeling.**

Most launches die in spreadsheets. So before any agents, we need a real data model — Launches, Milestones, Tasks, TeamMembers, StatusUpdates — with the relationships an agent can actually reason over.

I didn't draw this in the maker portal. I described the business in plain English and let the **Dataverse modeling skill** propose the tables, columns, and relationships. Then I added a **prompt column** for "Risk Summary" that an LLM populates from the row's own context.

The repo at this point is one solution, five tables, one prompt column, and a unified mapping that the next episodes build on.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-01`)

Next: turning my launch playbook into Business Skills the agents can follow.

#Dataverse #PowerPlatform #AI #Copilot
