# LinkedIn — Ep 5: Custom Tools

---

**Launch Control · Episode 5: Custom Tools.**

Out-of-the-box tools cover 80%. Every interesting agent needs the other 20%.

This episode ships three patterns for the long tail:

**1. Custom API.** `CalculateLaunchReadiness` runs server-side on Dataverse, gets registered into the solution, and is callable by every agent and app from day one. Write the logic once.

**2. Plugin.** A classic Dataverse plugin assembly registered against the table — same code path, but for the deeper extensibility you need when business logic must be transactional.

**3. BYO MCP server.** Two external MCP servers registered as **Power Platform custom connectors via `paconn`** — and now they show up in Copilot Studio, agent flows, and Copilot CLI as first-class tools. No glue code per surface.

The pattern: build the tool once, expose it to every agent runtime through Dataverse.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-05`)

Next: the Copilot Studio agent that uses all of this.

#Dataverse #MCP #CopilotStudio #PowerPlatform
