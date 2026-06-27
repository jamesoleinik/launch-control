"""Ep 10 preflight: verify the Web IQ MCP substrate is recording-ready.

Read-only. Exits non-zero if the agent's external-signal source is not reachable
or the required `web` tool is not entitled to the key.

Run:
    # PowerShell: $env:LC_ENV = "ep-10-dataverse-webiq"
    python episodes/ep-10-dataverse-webiq/preflight.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from webiq_client import WebIqClient, WebIqError

REQUIRED_TOOLS = {"web"}
NICE_TO_HAVE = {"news", "browse", "videos", "images"}


def main():
    try:
        client = WebIqClient(env_name="ep-10-dataverse-webiq")
    except WebIqError as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        info = client.initialize().get("serverInfo", {})
        print(f"OK   reachable: {info.get('name')} {info.get('version')}")
    except Exception as exc:
        print(f"FAIL: could not initialize Web IQ MCP ({exc})")
        return 1

    try:
        tools = set(client.tool_names())
    except Exception as exc:
        print(f"FAIL: could not list tools ({exc})")
        return 1

    missing = REQUIRED_TOOLS - tools
    if missing:
        print(f"FAIL: key is not entitled to required tool(s): {sorted(missing)}")
        return 1
    print(f"OK   required tools entitled: {sorted(REQUIRED_TOOLS)}")
    print(f"OK   also available: {sorted(tools & NICE_TO_HAVE)}")

    try:
        hits = client.web("Microsoft Dataverse", max_results=1)
        if not hits:
            print("WARN: web() returned no results (entitlement or transient).")
        else:
            print(f"OK   live web() query returned {len(hits)} result(s).")
    except Exception as exc:
        print(f"FAIL: live web() query failed ({exc})")
        return 1

    print("\nPreflight passed: Ep 10 external substrate is recording-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
