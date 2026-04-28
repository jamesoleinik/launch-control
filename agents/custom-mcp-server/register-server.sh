#!/bin/bash
# Register the Launch Readiness Checker BYO MCP Server
#
# Prerequisites:
# - a365 CLI installed (dotnet tool install -g Microsoft.Agents.A365.DevTools.Cli)
# - Authenticated via az login
#
# Replace YOUR-API-URL with your actual readiness checker endpoint

a365 develop-mcp register-external-mcp-server \
  --server-name "ext_LaunchReadinessChecker" \
  --server-url "https://YOUR-READINESS-API-URL/mcp" \
  --auth-type APIKey \
  --api-key-location Header \
  --api-key-name token \
  --tools "check_docs_site,check_marketing_page,check_cdn"

echo ""
echo "Server registered. Next steps:"
echo "  1. Admin approves in M365 Admin Center → Agent Tools → Requests"
echo "  2. Grant consent in Azure Portal → App Registrations"
echo "  3. Add to your Copilot Studio agent as a tool"
