# LinkedIn — Ep 8: The Code-First Agent

---

**Launch Control · Episode 8: The Code-First Agent.**

The declarative coordinator and the autonomous sentinel are great. But what if your team lives in Python, or runs a different agent runtime entirely?

This episode ships **`launch-coordinator-py/`** — a code-first Python agent that pulls the **same Business Skills** from Dataverse that the Copilot Studio agent uses.

Same skills. Different runtime.

That's the actual point of putting skills in Dataverse rather than baking them into one agent platform: Dataverse becomes the **skill registry**. Copilot Studio, Claude, a custom Python agent, the Copilot CLI — they all consume the same canonical rules. Change the rule once; every agent updates.

This is what "agent-portable business logic" looks like in practice.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-08`)

Next: the dashboard — a generative Power Apps page deployed from the CLI.

#Dataverse #Agents #Python
