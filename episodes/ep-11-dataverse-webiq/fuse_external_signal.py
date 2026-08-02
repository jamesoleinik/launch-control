"""Ep 11 outside-in demo: fuse internal launch blockers with live Web IQ signal.

This proves the Episode 11 thesis in code before it is wired into the Copilot
Studio agent: an internal blocker in Dataverse is far more actionable when joined
with what the outside world (web / news) already knows about it.

By default it runs on a bundled sample of blockers (sanitized from the live demo
env, no record IDs) so it works without Dataverse credentials. Pass --dataverse
to read live blocked tasks from the launch environment instead.

Run:
    # PowerShell: $env:LC_ENV = "ep-11-dataverse-webiq"
    python episodes/ep-11-dataverse-webiq/fuse_external_signal.py
    python episodes/ep-11-dataverse-webiq/fuse_external_signal.py --dataverse --max 5
"""

import argparse
import os
import re
import sys
import json
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from webiq_client import WebIqClient, WebIqError

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

# Sanitized from the live "Q3 Widget Launch" demo data (titles only, no IDs).
SAMPLE_BLOCKERS = [
    {"title": "Embedded widget blocked by CSP frame-ancestors on SharePoint pages",
     "category": "Engineering",
     "blockerreason": "Embedding rejected by host Content Security Policy."},
    {"title": "Mobile OAuth callback returns 500 after IdP SSO redirect",
     "category": "Engineering",
     "blockerreason": "Auth callback fails on the post-redirect leg."},
    {"title": "Canvas autosave drops edits after session token refresh",
     "category": "Engineering",
     "blockerreason": "State lost when the access token silently refreshes."},
]

_PREFIX = re.compile(r"^\s*(\[[^\]]+\]\s*)?(bug:\s*)?", re.IGNORECASE)


def to_query(title):
    """Turn a blocker title into a focused external-signal search query."""
    return _PREFIX.sub("", title).strip()


def fetch_dataverse_blockers(max_items):
    """Best-effort live read of blocked tasks from the launch environment."""
    import auth
    auth.load_env(os.environ.get("LC_ENV", "ep-11-dataverse-webiq"))
    base = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(os.environ.get("LC_ENV"))

    # Environment schemas differ slightly. Try the historical shape first,
    # then fall back to the current status-choice shape.
    queries = [
        "lc_tasks?$select=lc_title,lc_blockerreason&$filter=lc_isblocked eq true&$top=%d",
        "lc_tasks?$select=lc_title,lc_taskstatus&$filter=lc_taskstatus eq 10600303&$top=%d",
    ]
    last_exc = None
    for tmpl in queries:
        try:
            q = tmpl % max_items
            url = base + "/api/data/v9.2/" + urllib.parse.quote(q, safe="?=&$")
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/json",
                "OData-MaxVersion": "4.0", "OData-Version": "4.0",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.load(resp).get("value", [])
            return [{"title": r.get("lc_title", ""), "category": "",
                     "blockerreason": r.get("lc_blockerreason", "")} for r in rows]
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc


def briefing(client, blockers, per_blocker=2):
    print("=" * 72)
    print("OUTSIDE-IN BRIEFING  (internal blocker  x  live Web IQ signal)")
    print("=" * 72)
    for b in blockers:
        title = b["title"]
        query = to_query(title)
        print(f"\n[BLOCKER] {title}")
        if b.get("blockerreason"):
            print(f"  internal: {b['blockerreason']}")
        print(f"  query:    {query}")
        try:
            hits = client.web(query, max_results=per_blocker)
        except Exception as exc:
            print(f"  external: (Web IQ query failed: {exc})")
            continue
        if not hits:
            print("  external: (no external signal found)")
            continue
        print("  external signal:")
        for hit in hits:
            url = hit.get("url", "")
            ttl = (hit.get("title") or "").strip()
            print(f"    - {ttl}\n      {url}")
    print("\n" + "=" * 72)
    print("Each blocker now carries outside-in context the agent can cite.")


def main():
    ap = argparse.ArgumentParser(description="Fuse launch blockers with Web IQ.")
    ap.add_argument("--dataverse", action="store_true",
                    help="Read live blocked tasks instead of the bundled sample.")
    ap.add_argument("--max", type=int, default=3,
                    help="Max blockers to process (default 3).")
    ap.add_argument("--results", type=int, default=2,
                    help="External results per blocker (default 2).")
    ap.add_argument("--demo", action="store_true",
                    help="Show available Web IQ tools and run sample queries for the first blocker.")
    args = ap.parse_args()

    try:
        client = WebIqClient(env_name="ep-11-dataverse-webiq")
    except WebIqError as exc:
        print(f"FAIL: {exc}")
        return 1

    # Demo mode: list tools and run sample queries to showcase Web IQ capabilities
    if args.demo:
        print("Initializing Web IQ demo...")
        try:
            info = client.initialize().get("serverInfo", {})
            print("Server:", info.get("name"), info.get("version"))
        except Exception:
            pass
        tools = client.tool_names()
        print("Available Web IQ tools:", ", ".join([t for t in tools if t]))
        sample_query = to_query(SAMPLE_BLOCKERS[0]["title"]) if SAMPLE_BLOCKERS else "popular news"
        print(f"\nSample query: {sample_query}\n")
        if "news" in tools:
            print("-- news results --")
            try:
                for n in client.news(sample_query, max_results=2):
                    print(f" - {n.get('title')}\n   {n.get('url')}")
            except Exception as exc:
                print(f"  news call failed: {exc}")
        if "web" in tools:
            print("-- web results --")
            try:
                for w in client.web(sample_query, max_results=2):
                    print(f" - {w.get('title')}\n   {w.get('url')}")
            except Exception as exc:
                print(f"  web call failed: {exc}")
        if "browse" in tools:
            print("-- browse available (use for authoritative pages) --")
        print("\nDemo complete. Use --dataverse to run against live Dataverse blockers or omit to run the bundled sample.")
        return 0

    if args.dataverse:
        try:
            blockers = fetch_dataverse_blockers(args.max)
            print(f"(read {len(blockers)} blocked task(s) from Dataverse)")
        except Exception as exc:
            print(f"WARN: Dataverse read failed ({exc}); using bundled sample.")
            blockers = SAMPLE_BLOCKERS[:args.max]
    else:
        blockers = SAMPLE_BLOCKERS[:args.max]

    if not blockers:
        print("No blocked tasks to brief. (Nothing blocked is good news.)")
        return 0

    briefing(client, blockers, per_blocker=args.results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
