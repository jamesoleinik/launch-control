# Power Apps Agent — Build Guide

Companion path for Episode 13. Builds a **Power Apps agent** that surfaces the
Launch Control Dataverse data inline in Microsoft 365 Copilot chat with
canvas-app UI (status board, readiness card, milestone heatmap).

Different surface from the declarative-agent + MCP build (`../declarative-agent/`)
— this one bypasses the Dataverse MCP server entirely and uses the Power
Platform Dataverse connector, which gives us native canvas controls but
loses the Business Skills runtime hook from Ep 2.

> 📣 Power Apps agents are in **public preview** as of the March 2026
> Microsoft 365 Dev Blog announcement. Expect schema and UX changes before
> GA. See https://www.microsoft.com/en-us/power-platform/blog/power-apps/public-preview-your-business-apps-now-part-of-every-conversation/

---

## 0. Prerequisites

- Microsoft 365 tenant with the same Dataverse environment used by earlier
  episodes (`<your-org>.crm.dynamics.com`).
- **Power Apps Premium / per-app license** assigned to the user who will
  build the canvas app. Power Apps agents currently require Premium.
- Power Apps **public preview** features enabled on the environment.
  (PPAC → Environment → Settings → **Features** → toggle
  "Power Apps agents (preview)" on.)
- Microsoft 365 admin in your tenant who can approve the agent in
  **Integrated apps** when you publish.
- The `lc_*` tables and `lc_CalculateLaunchReadiness` Custom API from Eps 1
  and 5 already deployed in the environment.

> Tenant admin consent / PPAC MCP allowed-clients steps from the
> declarative-agent path are **not** needed — there's no MCP server in this
> path.

---

## 1. Create the canvas app

1. Go to https://make.powerapps.com → select your environment.
2. **+ Create** → **Blank canvas app** → name it **Launch Control** →
   format **Tablet**.
3. Tree view → **Data** → **+ Add data** → search **Microsoft Dataverse**
   → connect.
4. Add these tables to the data sources:
   - `Launches` (`lc_launch`)
   - `Milestones` (`lc_milestone`)
   - `Tasks` (`lc_task`)
   - `Team members` (`lc_teammember`)
   - `Status updates` (`lc_statusupdate`)
   - `GitHub issues` (`lc_githubissue` — virtual entity, read-only)

## 2. Build the three required screens

A Power Apps agent in Copilot chat will render whichever screen the user
navigates to. We want three: a **status board**, a **readiness card**, and
a **blocker drilldown**.

### Screen 1 — `scrStatusBoard` (entry screen)

Header label `lblTitle`:

```powerfx
"Launch Control"
```

Gallery `galLaunches` bound to:

```powerfx
SortByColumns(
    Filter('Launches', 'Launch status' <> 'Launch status'.Launched),
    "lc_targetdate",
    SortOrder.Ascending
)
```

Inside each gallery row, show:

- `ThisItem.Name`
- `ThisItem.'Launch status'` (rendered as a colored pill — green for
  `InProgress`, yellow for `Planning`, red for `OnHold`)
- `ThisItem.'Target date'`
- An icon button `iconReadiness` with `OnSelect`:

  ```powerfx
  Navigate(scrReadiness, ScreenTransition.None, { selectedLaunch: ThisItem })
  ```

### Screen 2 — `scrReadiness` (the hero card)

This is the "money shot" for the demo. Render the output of
`lc_CalculateLaunchReadiness` as a card with a verdict pill, a score gauge,
and a milestone status grid.

Add a button (or `OnVisible` of the screen) that calls the Custom API. The
Dataverse connector exposes Custom APIs as actions:

```powerfx
Set(
    readiness,
    Dataverse.lc_CalculateLaunchReadiness({ lc_LaunchName: selectedLaunch.Name })
)
```

Then bind to:

- `lblVerdict.Text = readiness.lc_Verdict` (color via Switch on the string)
- `lblScore.Text = Text(readiness.lc_ReadinessScore, "[$-en-US]0") & " / 100"`
- `lblSummary.Text = readiness.lc_ReadinessSummary`

Gallery `galMilestones`:

```powerfx
Filter(Milestones, Launch.Launch = selectedLaunch.Launch)
```

In each row render an emoji based on `'Milestone status'` — 🟢 Complete,
🟡 At risk, 🔴 Blocked, ⚪ NotStarted, 🔵 InProgress — and the milestone
`'Due date'`.

### Screen 3 — `scrBlockers` (drilldown)

Gallery bound to:

```powerfx
Filter(Tasks, 'Is blocked' = true, Milestone.Launch.Launch = selectedLaunch.Launch)
```

For each row show the task title, assignee (`'Assigned to'.Name`), blocker
reason, milestone due date, and — if `'GitHub issue'` lookup is populated
— the GitHub `'Issue number'` + `'State'` from the virtual entity. This
gives the Escalation Policy demo a place to land.

## 3. Wire up the Copilot starter prompts

In **Tree view** select **App** → **OnStart**:

```powerfx
Set(
    copilotIntents,
    Table(
        { intent: "status",     screen: scrStatusBoard },
        { intent: "readiness",  screen: scrReadiness },
        { intent: "blockers",   screen: scrBlockers }
    )
)
```

(Optional — used by the agent registration step below to wire starter
prompts to specific screens.)

## 4. Register the app as a Copilot agent

1. From the canvas app maker view → top-right **Edit** menu → **Agent
   settings** (preview-only menu — if you don't see it, confirm step 0
   feature toggle).
2. Toggle **Make this app available as an agent in Microsoft 365 Copilot**.
3. Fill in:
   - **Agent name:** `Launch Control`
   - **Description:** `Track launches, run readiness gates, and escalate
     blockers in Dataverse — inline in Microsoft 365 Copilot chat.`
   - **Conversation starters:**
     - *Status:* `Show me the status board.` → routes to `scrStatusBoard`
     - *Readiness:* `What's the readiness for Q3 Widget Launch?` → routes
       to `scrReadiness` with `selectedLaunch` set
     - *Blockers:* `What's blocking the Q3 Widget Launch?` → routes to
       `scrBlockers`
4. Add **instruction text** (paste from
   `../declarative-agent/appPackage/instruction.txt`; the Power Apps
   runtime uses it the same way the declarative agent does).
5. **Save** → **Publish**.

## 5. Approve the agent in the tenant

1. M365 admin → https://admin.microsoft.com → **Integrated apps**.
2. Find **Launch Control** in the pending list → review the requested
   Dataverse / Power Platform permissions → **Approve**.

(If you want a personal-only demo, skip this and use the **Try in Copilot**
preview from inside Power Apps Studio instead.)

## 6. Verify in Microsoft 365 Copilot

1. Open https://m365.cloud.microsoft/chat.
2. Agents rail → **Launch Control**. Click it.
3. Pick a conversation starter — e.g., *"What's the readiness for Q3 Widget
   Launch?"*
4. The agent should:
   - Land on `scrReadiness` with the canvas-rendered verdict card.
   - Show the milestone gallery with status emojis.
   - Let you click `iconBack` to bounce to the status board.
5. Try **typing** a question instead — *"What's blocking us?"* — the agent
   should route to `scrBlockers` (uses the conversation starter intents
   as routing hints).

## 7. (Recording day) Reset the dataset

For the demo to look interesting:

```powershell
# from repo root
python episodes/ep-06-the-agent/setup_table.py    # ensures lc_launch seed
python episodes/ep-06-the-agent/upload_knowledge.py
```

Then set the Q3 Widget Launch milestones so the readiness card has at
least two blockers and one at-risk gate.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Agent settings" menu missing | Re-check the preview feature toggle in PPAC → Features. Sign out / back in. |
| Readiness button returns null | The Custom API isn't in the Premium connector surface for your environment. Confirm `lc_CalculateLaunchReadiness` is **published** with `IsCustomizable=true` and `BindingType=Entity` on `lc_launch`. |
| Gallery filters return empty | Check that `lc_launch.Launch` (GUID) and `lc_milestone.Launch.Launch` are spelled correctly — the Power Apps schema name is `Launch`, not `lc_launchid`, despite the Web API name. |
| Agent doesn't show in M365 Copilot | The Integrated Apps approval is pending or the user lacks the Premium license. |
| "Power Apps agent" tab shows but agent rail is empty | Toggle the **Power Apps agents** preview switch in M365 admin → **Settings → Copilot** as well — both org-side and Power Platform-side toggles are required. |
| Canvas screens don't render in chat | Currently the inline-canvas rendering supports a single screen per turn. If the agent navigates twice in one turn, the second navigation falls back to a text response. Keep flows shallow. |

---

## Files this agent depends on (cross-episode)

| Dep | Episode | Notes |
|---|---|---|
| `lc_launch` / `lc_milestone` / `lc_task` / `lc_teammember` / `lc_statusupdate` | Ep 1 | Read by the canvas data sources. |
| `lc_githubissue` virtual entity | Ep 4 | Read-only, surfaced in the blocker drilldown. |
| `lc_CalculateLaunchReadiness` Custom API | Ep 5 | Invoked from `scrReadiness.OnVisible`. |
| `instruction.txt` | this episode (`../declarative-agent/appPackage/`) | Reused verbatim — same persona, same formatting rules. |
| Power Apps Premium license | this episode | Required for the agent surface. |

---

## What's different vs. the declarative-agent path

| | `../declarative-agent/` (MCP) | this folder (Power Apps) |
|---|---|---|
| Where you build | VS Code + M365 Agents Toolkit | Power Apps Studio (browser) |
| Files in repo | manifest.json, declarativeAgent.json, action JSON, env files | none — the canvas app lives in the environment |
| Auth | OAuth via Entra app reg + Dataverse `/api/mcp` | Power Platform Dataverse connector (user identity) |
| UI fidelity | Markdown card | Canvas controls (charts, galleries, write-back forms) |
| Reuses Business Skills | ✅ via MCP | ❌ direct Dataverse |
| Provision time | ~10 min once env vars + icons set | ~1-2 hr canvas-app build |

Pick whichever path matches the audience you're recording for. The
declarative-agent path closes the "MCP everywhere" arc; the Power Apps
path produces a louder visual.

---

## Why no files in this folder

Power Apps doesn't have a clean source-of-truth file format the way the
declarative agent does — canvas apps live in Dataverse as MSAPP blobs. The
canonical export is the **.msapp file** you get from Power Apps Studio
(**File → Save as → This computer**). Drop it here as
`LaunchControl.msapp` after you build, and add a row to the table above.
