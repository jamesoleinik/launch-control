# Episode 7 — Always-on: handing LaunchControl to Microsoft Scout

**Status:** 🟡 **BLOCKED** on Microsoft Scout (Frontier preview) access · 🎬 Not yet recorded
**Features:** ⭐ Custom Scout skill wrapping the Ep-6 / Ep-8 substrate · ⭐ Live Teams demo: prompt → MCP query → `lc_DraftLaunchBriefing` AI Prompt → posted briefing · ⭐ Autopilot identity / Purview / approval tiers as the "trust" story
**Layer:** 🟣 Layer 3 reach — the always-on agent surface
**Coding agent:** Microsoft Scout (Frontier desktop app)
**Runtime:** Microsoft Scout desktop (Windows / macOS) + Dataverse MCP + AI Prompt from Ep 5

---

## Why this episode is a placeholder

Microsoft Scout shipped via the [Frontier preview program](https://adoption.microsoft.com/en-us/copilot/frontier-program/) on **2026-06-02**. Access requires:

1. Frontier enrollment for the tenant
2. Intune policy configuration
3. Opt-in attestation
4. A GitHub Copilot license on the user account

Our tenant is **not yet** Frontier-enrolled, so we cannot record this
episode end-to-end. The episode is parked here so the numbering stays
stable and so we don't lose the research that's already been done.

When access lands, see **`NOTES.md`** for the capability summary and the
TODO list below for the production checklist.

---

## The hook (planned)

> _"Episodes 1-6 built the substrate. Episode 7 hands it to an agent
> that doesn't wait to be asked."_

We've built a Dataverse model (Ep 1), staged real data (Ep 3), enforced
shape (Ep 4), wired custom tools and an AI Prompt (Ep 5), and pushed it
into Cowork (Ep 6). Episode 7 demonstrates the payoff: an **Autopilot**
agent — Microsoft Scout — that reuses *exactly the same* MCP connector
and AI Prompt we shipped in Ep 5, but operates from the user's
desktop / Teams / calendar, with its own Entra identity and its own
Purview-respecting access controls.

---

## The planned demo (Idea A from the research round)

1. User opens a Teams chat and types: *"Give me a GO/HOLD/NO-GO on Q3
   Widget Launch and DM it to the sponsor."*
2. Scout invokes a custom skill (`launch-control/SKILL.md` shipped in
   this episode) that tells it to:
   - Query `lc_launch` + `lc_milestone` via the Ep-5 **BYO MCP custom
     connector** to get the launch by name.
   - Invoke the **`lc_DraftLaunchBriefing` AI Prompt** (also Ep 5) via
     the Dataverse connector's bound `Predict` action.
   - Resolve the sponsor's email via Scout's people-search, then DM
     them via the Teams M365 action.
3. The briefing lands in the sponsor's Teams in under 60 seconds.

No new Dataverse plumbing. No new flows. The Ep-5 substrate is reused
verbatim — Scout is the new *surface*, not new logic.

---

## TODO (when access lands)

- [ ] Obtain Frontier enrollment + Intune policy + opt-in attestation
- [ ] Install Microsoft Scout desktop (Windows + macOS for parity demo)
- [ ] Author `skill/launch-control/SKILL.md` — Scout skill that wraps
      the Ep-5 BYO MCP connector + the `lc_DraftLaunchBriefing` AI
      Prompt
- [ ] Smoke-test the skill against `Q3 Widget Launch`
- [ ] Optional follow-ups (Ideas B & C from the planning research,
      tracked in `NOTES.md`): scheduled automation that auto-DMs at
      risk; pointing Scout at the existing `episodes/*/SKILL.md` files
- [ ] Record the episode and write the recording-time `SKILL.md`
      (producer playbook, same shape as Ep-5's)

---

## References

- [Microsoft Scout announcement (Microsoft 365 Blog, 2026-06-02)](https://www.microsoft.com/en-us/microsoft-365/blog/2026/06/02/introducing-microsoft-scout-your-always-on-personal-agent/)
- [Microsoft Scout documentation hub](https://learn.microsoft.com/en-us/microsoft-scout/)
- [Overview — what Microsoft Scout is](https://learn.microsoft.com/en-us/microsoft-scout/overview)
- [Use Microsoft Scout (how-to)](https://learn.microsoft.com/en-us/microsoft-scout/use-microsoft-scout)
- [Set up Microsoft Scout with Intune (admin)](https://learn.microsoft.com/en-us/microsoft-scout/admin-intune-setup)
- [Frontier preview program](https://adoption.microsoft.com/en-us/copilot/frontier-program/)
