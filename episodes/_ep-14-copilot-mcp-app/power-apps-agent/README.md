# Power Apps Agent — Companion Path for Episode 13

> 📚 **Build steps live in [`BUILD.md`](BUILD.md).**
> Why this exists and how it compares to the MCP path is in the parent
> [README.md](../README.md#the-power-apps-companion-path-acknowledged-but-not-built-here).

## TL;DR

Build a canvas Power App over the same `lc_*` Dataverse tables (Eps 1, 4, 5),
register the canvas app as a **Power Apps agent** via the preview toggle,
and approve it in Integrated Apps so it shows up in the M365 Copilot
Agents rail. The agent renders canvas screens inline in Copilot chat — real
controls, not Markdown.

## Three screens to build

| Screen | Purpose | Hero binding |
|---|---|---|
| `scrStatusBoard` | List of active launches with status pills | Gallery on `Filter('Launches', 'Launch status' <> 'Launch status'.Launched)` |
| `scrReadiness` | Per-launch verdict card | `Set(readiness, Dataverse.lc_CalculateLaunchReadiness({ lc_LaunchName: selectedLaunch.Name }))` |
| `scrBlockers` | Blocked tasks with GitHub state | `Filter(Tasks, 'Is blocked' = true, Milestone.Launch.Launch = selectedLaunch.Launch)` |

## Wiring it as an agent

In Power Apps Studio → **Edit menu → Agent settings (preview)** →
toggle on → fill name / description / conversation starters → paste the
declarative agent's `instruction.txt` as the agent instructions →
**Save** → **Publish** → admin approves in **Integrated apps** →
agent appears in M365 Copilot.

Full step-by-step (prereqs, screen-by-screen Power Fx, conversation
starters, troubleshooting): **[BUILD.md](BUILD.md)**.

## Files (after you build)

| File | Status |
|---|---|
| `BUILD.md` | ✅ in repo (steps to build) |
| `LaunchControl.msapp` | ⬜ export from Power Apps Studio after build (File → Save as → This computer) |
| screenshots / GIFs | ⬜ optional, drop in `screenshots/` |

The `.msapp` blob is the source-of-truth export. Canvas apps don't have a
clean text-diffable source format the way the declarative agent does.
