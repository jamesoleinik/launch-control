# LinkedIn — Ep 4: Connecting the Dots (Virtual Entities)

---

**Launch Control · Episode 4: Connecting the Dots.**

The launch lives in Dataverse. The engineering work lives in GitHub. Replicating GitHub Issues into Dataverse is a sync nightmare — stale data, race conditions, two systems of record.

So I didn't replicate them.

This episode ships a **custom virtual entity provider** that makes GitHub Issues appear as Dataverse records — read on demand, no copy. Then I wired it as a **lookup target on `lc_task`** so a launch task can point directly at a live issue. Click the lookup, see the live state.

Two systems. One source of truth per fact. Zero sync.

This is the unlock for everything that comes next: agents can reason across the launch *and* the engineering work without me building a pipeline.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-04`)

Next: custom tools — Custom APIs and BYO MCP servers wired in via paconn.

#Dataverse #VirtualEntities #PowerPlatform #GitHub
