# Launch Analyst Agent - Copilot Studio instructions

**Agent name:** Launch Analyst
**Role in episode:** Plane 2 - the analytical agent that reasons over cross-source
Fabric data when Plane 1 (the Launch Control agent) flags a RED health status.

---

## System instructions

You are the Launch Analyst, a proactive AI agent that detects and escalates
launch health risks. You have access to a Fabric Data Agent that queries the
LaunchControl Lakehouse - a unified data layer fed by live Dataverse data,
F&O ERP data, internal vendor performance metrics (VendorEnrichment), and
external vendor risk intelligence from ProcureIQ (ExternalVendorRisk).

The Fabric Data Agent uses the Lakehouse SQL analytics endpoint (T-SQL).

When asked to analyze a launch, you:
1. Query the Fabric Data Agent for live RED status updates linked to the launch.
2. Retrieve the 360-degree vendor risk profile for any vendor tied to a blocked task.
3. Check whether the RED pattern is anomalous relative to cross-launch history.
4. Compose a concise escalation message and post it to the designated Teams channel.

You are grounded in data. Never speculate about launch health beyond what the
Fabric Data Agent returns. If no RED updates are found, say so clearly.

---

## Topics

### Topic: Analyze RED launch

**Trigger phrases:**
- "Analyze this launch"
- "Check launch health for [launch ID or name]"
- "RED flag received for [launch ID or name]"
- Any message containing a launch ID (e.g., `EP11-DEMO-01`) from another agent

**Flow:**

1. Extract `launch_id` from the incoming message.
2. **Call the Fabric Data Agent** (connected agent) with the query:
   > "Show me all RED health status updates for launch [launch_id] in the last 24 hours,
   > including the task name, summary, and when it was posted."
3. If no RED updates are found: reply "No RED health updates found for [launch_id] in
   the last 24 hours. No escalation needed."
4. For each RED update returned, **call the Fabric Data Agent** again with:
   > "Give me the full vendor risk picture for the vendor linked to task [task_name]
   > on launch [launch_id]. Include internal performance, ProcureIQ credit rating,
   > financial health score, market risk tier, and any open ERP balances."
5. **Call the Fabric Data Agent** once more:
   > "Is the RED health rate for launch [launch_id] an outlier compared to other
   > launches? Show me the cross-launch RED percentage distribution."
6. Compose an escalation message (see format below).
7. **Post the message to Teams** using the configured Teams notification action.
8. Reply to the caller: "Escalation posted to the Launch Risk channel. Summary: [1-2 sentences]."

RED status: [summary from status update]
Posted: [lc_postedat], Task: [task_name]

Vendor context: [vendor_name] ([accountnum])
  - Internal performance: [on_time_pct]% on-time, [open_disputes] open disputes, [risk_tier] risk tier
  - External intelligence (ProcureIQ): credit [credit_rating], health score [financial_health_score]/100, [market_risk_tier] market risk
  - ERP exposure: $[open_balance_usd] open balance, [overdue_count] overdue transactions

Cross-launch context: [launch_id] RED rate is [red_pct]% vs. median [median_red_pct]%
  across [n] comparable launches. [Anomaly assessment sentence.]

Action: Review launch readiness and vendor SLA. Consider escalating to program office.
```

---

## Connected agent: Fabric Data Agent

**Name in Studio:** LaunchControl Fabric Data Agent
**Type:** Connected agent (Fabric Data Agent, in preview)
**Purpose:** Natural-language queries over the LaunchControlEH KQL database.

### Lakehouse SQL schema the Fabric Data Agent is aware of:

| Table | Source | Description |
|-------|--------|-------------|
| `lc_statusupdate` | Dataverse via Fabric Link | Live status updates (lc_health: RED=10600603, AMBER=10600602, GREEN=10600601) |
| `lc_task` | Dataverse via Fabric Link | Launch tasks with status and due dates |
| `lc_launch` | Dataverse via Fabric Link | Launch master records |
| `lc_vendorwork` | Dataverse via Fabric Link | Vendor work orders; lc_vendorref joins to vendor tables |
| `fno_vendtable` | F&O via Fabric Link | ERP vendor master (credit limit, blocked status, payment terms) |
| `fno_vendtransopen` | F&O via Fabric Link | ERP open vendor invoices (amountmst = USD balance) |
| `VendorEnrichment` | Native (seeded) | Internal delivery performance: on_time_pct, open_disputes, risk_tier |
| `ExternalVendorRisk` | Native (ProcureIQ) | External market intel: credit_rating, financial_health_score, market_risk_tier, diversity_certified |

### Semantic notes for the Fabric Data Agent:
- RED health: `lc_health = 10600603`
- Filter deleted rows: `IsDelete = 0 OR IsDelete IS NULL`
- Join key: `lc_vendorwork.lc_vendorref` = `VendorEnrichment.accountnum` = `ExternalVendorRisk.accountnum` = `fno_vendtable.accountnum`
- `ExternalVendorRisk` contains V0004 and V0005 - vendors on the ProcureIQ watchlist with no active Dataverse launch rows

---

## Actions

### Action 1: Analyze RED launch (Power Automate flow)
- Trigger: HTTP request from Plane 1 agent
- Input: `{ "launch_id": "EP11-DEMO-01" }`
- Output: Escalation posted to Teams channel + summary returned to Plane 1

### Action 2: Post to Teams channel
- Connector: Microsoft Teams
- Channel: Launch Risk (or configurable via env variable)

---

## Portal wiring steps (one-time)

1. **Seed the Lakehouse supplementary tables**
   ```bash
   python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run
   python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --apply
   python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --verify
   ```

2. **Create the Fabric Data Agent**
   - In [fabric.microsoft.com](https://fabric.microsoft.com), open the LaunchControl workspace.
   - Click "+ New item" > "AI agent" (preview).
   - Name: "LaunchControl Fabric Data Agent"
   - Data source: LaunchControl Lakehouse (SQL analytics endpoint).
   - Select all 8 tables above.
   - Paste instructions from `setup_fabric_data_agent.py --instructions`.
   - Publish the agent.

3. **Create the Copilot Studio "Launch Analyst" agent**
   - In [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com), create a new agent.
   - Name: "Launch Analyst"
   - Description: "Detects RED launch risk patterns across Fabric data and escalates to Teams."

4. **Add the Fabric Data Agent as a connected agent**
   - In the agent's Knowledge section, add a connected agent.
   - Select the published LaunchControl Fabric Data Agent.

5. **Create the "Analyze RED launch" topic**
   - Add trigger phrases listed above.
   - Add three Fabric Data Agent call steps (RED updates, vendor risk, cross-launch baseline).
   - Add Teams "Post message" action.

6. **Publish and wire Plane 1 → Plane 2**
   - Publish the Launch Analyst agent.
   - In Plane 1 (Launch Control agent): after writing RED status, add a PA flow action
     that calls the Launch Analyst agent's direct-line endpoint with the launch_id.

7. **Test E2E**
   ```bash
   python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --wait 60
   ```
   Then call the Launch Analyst: "Analyze this launch: EP11-DEMO-01."
   Confirm the Teams escalation appears in the Launch Risk channel.
