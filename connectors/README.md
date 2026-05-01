# Launch Control — BYO MCP Connectors

This folder contains [paconn](https://pypi.org/project/paconn/) connector definitions that register **remote MCP servers** as Power Platform custom connectors. Once registered, any maker in the environment can attach them to a Copilot Studio agent, an Agent Builder agent, or a Power Automate flow.

## The pattern (Episode 5 Part 2)

A remote MCP server becomes a Power Platform custom connector via a single Swagger 2.0 extension:

```json
"paths": {
  "/<your-mcp-path>": {
    "post": {
      "operationId": "InvokeServer",
      "x-ms-agentic-protocol": "mcp-streamable-1.0",
      "responses": { "200": { "description": "Immediate Response" } }
    }
  }
}
```

That single annotation tells the connector framework: "talk to this URL via streamable HTTP MCP." The framework handles tool discovery, invocation, and response streaming. No `connectionParameters` are needed for unauthenticated servers; for authenticated servers, declare them in `apiProperties.json` exactly like any other custom connector.

## What's here

| Folder | MCP server | Auth |
|---|---|---|
| `learn-mcp/` | `https://learn.microsoft.com/api/mcp` | None (public) |
| `github-mcp/` | `https://api.githubcopilot.com/mcp/` | GitHub PAT in `Authorization` header |

Each folder has three files:

- `apiDefinition.swagger.json` — Swagger 2.0 with the `x-ms-agentic-protocol` extension
- `apiProperties.json` — connector capabilities + `connectionParameters` (for auth, if any)
- `settings.example.json` — paconn settings template (real `settings.json` is gitignored because it contains an environment-specific GUID)

## Register in your own environment

Prereqs: Python 3.9+, `paconn` (`pip install paconn`), Power Platform environment with the **MCP Server** feature enabled.

```powershell
# 1. Authenticate (device-code flow)
paconn login

# 2. Get your environment ID
pac env list

# 3. Copy the template, fill in your env ID
cd connectors/learn-mcp
copy settings.example.json settings.json
# edit settings.json: replace <your-environment-id>

# 4. Register the connector
paconn create -s settings.json
```

The connector now shows up under **Power Apps → Custom Connectors**, ready to be attached to any Copilot Studio agent.

> **paconn quirk**: `paconn create` returns success but hangs on a final HTTP read for ~2 minutes after the connector has already been created server-side. Safe to Ctrl+C after ~30 seconds and verify via the Power Apps UI or REST API.

> **paconn validate quirk**: Skip `paconn validate` for MCP scenarios — it enforces certification rules (`info.contact`, `x-ms-connector-metadata`) that aren't required to actually create a working connector.

## Why this matters

The same pattern works for **any** remote MCP server — public ones like Microsoft Learn, GitHub, or Atlassian; vendor-hosted ones; or ones your team builds and hosts (FastMCP, mcp-go, etc.). The Power Platform tenant becomes the governance plane for every MCP your makers and agents use, with the same DLP, network, and Microsoft Defender for Cloud Apps coverage as any other custom connector.
