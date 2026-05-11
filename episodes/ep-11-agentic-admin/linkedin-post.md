# LinkedIn — Ep 11: Agentic Administration

---

**Launch Control · Episode 11: Agentic Administration.**

Everyone talks about agents on the data plane. Almost nobody talks about agents on the **management plane** — the stuff Dataverse admins do every day.

This episode flips that.

Using **Copilot CLI** with the `dataverse@awesome-copilot` plugin (v1.0.0), I drove four real admin scenarios from a terminal — no admin portal:

• **Capacity report** — pulled storage + capacity telemetry programmatically. No screenshots.
• **Agent blast-radius audit** — enumerated every Dataverse object the agent identity can read or write in this environment. Surprising. Sometimes terrifying.
• **Skill freshness check** — listed the Business Skills published into the env so I can prove what the agents are actually using.
• **Backdated cleanup** — seeded then triaged stale rows the audit beat needs to chew on.

Same plugin. Same CLI. Real admin work. Auditable. Scriptable. CI-able.

The management plane is agent-ready. That's the news.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-11`)

Next: full orchestra — six surfaces in 60 seconds, then it's your turn.

#Dataverse #Admin #Copilot #CLI
