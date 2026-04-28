# Python SDK Scripts

Scripts for managing and analyzing Launch Control data using the [Dataverse Python SDK](https://github.com/microsoft/PowerPlatform-DataverseClient-Python) with pandas DataFrame support.

## Setup

```bash
pip install -r requirements.txt
```

Configure `.env` at the repo root (see `.env.example`). Auth uses `AzureCliCredential` — run `az login` first.

## Scripts

### `seed_launch_data.py`
Seeds the Q3 Widget Launch with realistic sample data:
- 1 Launch (Q3 Widget Launch, In Progress, target Sep 15)
- 5 Team Members (Alex Chen, Sarah Kim, Marcus Johnson, Priya Patel, James Rivera)
- 4 Milestones (Engineering ✓, QA ✓, Marketing ⚠, Legal ○)
- 12 Tasks (7 done, 1 in progress, 1 blocked, 3 not started)
- 3 Status Updates

```bash
python scripts/python/seed_launch_data.py
```

### `status_report.py`
Terminal-based status report with ASCII progress bars and pandas analytics:
- Milestone status indicators (`[OK]`, `[!!]`, `[  ]`)
- Task progress bar with completion percentage
- Blocked task details with owner and reason
- pandas `value_counts()` for status distributions

```bash
python scripts/python/status_report.py
```

### `status_report_html.py`
Power BI-style HTML dashboard that opens in the browser:
- **KPI cards**: Task completion %, milestones complete, at-risk count, blocked count
- **Milestone timeline**: Vertical timeline with color-coded status dots and badges
- **Donut chart**: Task status distribution with CSS conic-gradient
- **Horizontal bar chart**: Task counts by status
- **Blocked items table**: Tabular view with owner, due date, and blocker reason

```bash
python scripts/python/status_report_html.py
```

### `escalation_summary.py`
Identifies blocked tasks and generates an escalation report grouped by owner:
- SQL JOIN across tasks and milestones via `client.query.sql()`
- pandas merge with team members for contact info
- Grouped by owner with email, role, and blocker details

```bash
python scripts/python/escalation_summary.py
```

## Key SDK Features Demonstrated

| Feature | Script | SDK Method |
|---------|--------|------------|
| DataFrame query | All | `client.dataframe.get(table, select=, filter=)` |
| SQL JOINs | escalation_summary | `client.query.sql("SELECT ... JOIN ...")` |
| pandas merge | escalation_summary | `tasks_df.merge(members_df, ...)` |
| pandas analytics | status_report | `df.value_counts()`, `df.groupby()` |
| Record creation | seed_launch_data | `client.records.create(table, {...})` |
| Lookup bindings | seed_launch_data | `"lc_LaunchId@odata.bind": "/lc_launchs(id)"` |
