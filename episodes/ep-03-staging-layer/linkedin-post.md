# LinkedIn — Ep 3: Promoting the Staging Layer

---

**Launch Control · Episode 3: Promoting the Staging Layer.**

Real data is dirty. Pretending otherwise is how data products die.

So Launch Control has a **staging layer** — a Dataverse mirror of every raw source — and a `promote.py` script that lifts clean rows into the unified model. The promotion is written in pandas and runs through the **official Dataverse Python SDK**, so it gets connection pooling, batched writes, and CreateMultiple/UpdateMultiple under the hood for free.

Three things this episode unlocks:
• Sources can be added without touching the unified model
• Promotion logic is testable in a notebook before it ever hits prod
• A pandas dataframe round-trips to Dataverse in two lines of code

The result: a 46-row Smart Widget Pro launch dataset with real risks, real owners, real dates — the substrate every subsequent episode runs on.

➡️ Repo: github.com/jamesoleinik/launch-control (tag `ep-03`)

Next: virtual entities — making GitHub Issues show up in Dataverse with zero replication.

#Dataverse #Python #pandas #PowerPlatform
