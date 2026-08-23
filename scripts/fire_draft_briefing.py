"""Fire the lc_DraftLaunchBriefing AI Prompt and print the response text.

Used by the pre-meeting-launch-brief Scout skill when the Dataverse MCP
server doesn't expose Custom Action invocation directly. Scout shells out
to this script, captures stdout, and embeds the result into the briefing
pack.

Usage:
    python scripts/fire_draft_briefing.py "Q3 Widget Launch"

Prints the AI-drafted text (no JSON, no banner) to stdout so Scout can
capture it cleanly. Errors go to stderr.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("usage: fire_draft_briefing.py \"<launch name>\"", file=sys.stderr)
        sys.exit(2)
    launch_name = sys.argv[1]
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()

    # Unbound action: see episodes/ep-05-custom-tools/README.md line ~410.
    url = f"{env_url}/api/data/v9.2/lc_DraftLaunchBriefing"
    payload = {"lc_LaunchName": launch_name}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        print(f"AI Prompt invocation failed ({e.code}): {msg[:500]}", file=sys.stderr)
        sys.exit(1)

    # Response shape: { "lc_Briefing": "..." } or similar. Print whichever
    # text-shaped output we find, falling back to the raw body.
    for key in ("lc_Briefing", "lc_briefing", "Result", "result", "output"):
        if key in body and isinstance(body[key], str):
            print(body[key].strip())
            return
    print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
