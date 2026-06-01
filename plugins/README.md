# Custom Tools — Episode 5

## Overview

This episode registers custom logic that agents can call — both internal (Dataverse plugins)
and external (BYO MCP servers). These tools become available to all agents built in Episodes 6-8.

## Part 1: Custom Dataverse Plugin → Custom Action

### What it does
`CalculateLaunchReadiness` evaluates all 4 launch gates and returns:
- **ReadinessScore** (0-100): 25 points per gate (Complete=25, AtRisk=12, InProgress=15, NotStarted=5, Blocked=0)
- **ReadinessSummary**: Gate-by-gate breakdown
- **Verdict**: "GO" (all pass), "NO-GO" (any blocked), "CONDITIONAL" (any at risk)

### Build
```bash
cd plugins/CalculateLaunchReadiness/CalculateLaunchReadiness
dotnet build --configuration Release
```

### Register
1. Register assembly via Web API or PAC CLI:
   ```bash
   pac plugin push --pluginId <assembly-id> \
     --pluginFile bin/Release/net462/CalculateLaunchReadiness.dll --type Assembly
   ```
2. Register the custom action `lc_CalculateLaunchReadiness` in Dataverse:
   - Input: `lc_LaunchName` (string)
   - Output: `lc_ReadinessScore` (int), `lc_ReadinessSummary` (string), `lc_Verdict` (string)
3. The action is automatically exposed via the MCP server — agents can invoke it

### Test via MCP
Once registered, agents can call:
```
"Run the CalculateLaunchReadiness action for 'Q3 Widget Launch'"
```

## Part 2: BYO MCP Server (External Readiness Checker)

### Registration
```bash
a365 develop-mcp register-external-mcp-server \
  --server-name "ext_LaunchReadinessChecker" \
  --server-url "https://your-readiness-api.com/mcp" \
  --auth-type APIKey \
  --api-key-location Header \
  --api-key-name token \
  --tools "check_docs_site,check_marketing_page,check_cdn"
```

### Admin Approval
1. M365 Admin Center → Agent Tools → Requests tab
2. Review and approve the server
3. Azure Portal → App Registrations → Grant admin consent on both auto-created apps

### Observability
```kql
-- Microsoft Defender Advanced Hunting
CloudAppEvents
| where ActionType in ("ExecuteToolByMCPServer")
| where RawEventData contains ("LaunchReadinessChecker")
```

## How Agents Use These Tools

| Agent Type | Custom Action (internal) | BYO MCP (external) |
|-----------|------------------------|-------------------|
| Copilot Studio (Ep 8) | Via MCP Server tool | Via registered MCP connector |
| Autonomous Agent (Ep 9) | Via event-triggered action | Via agent flow MCP step |
| Claude Code (Ep 10) | Via SDK/Web API | Via MCP client |
| M365 Copilot (Ep 11) | Via Dataverse Intelligence | Not directly available |
