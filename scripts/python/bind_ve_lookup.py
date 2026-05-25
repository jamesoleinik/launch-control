"""
Bind 6 lc_task records to lc_githubissue virtual entities via the
new lc_GitHubIssueId lookup column.

Looks up tasks by `lc_title` so this works across env rebuilds (the
previous hard-coded GUID list was env-specific). Idempotent.

Issue GUID format (from Class1.cs DeterministicGuid):
  bytes[0]=0xAB, bytes[1]=0xCD, bytes[12..15] = issue number (LE int32)
  Rendered: 0000cdab-0000-0000-0000-0000NN000000
"""
import os
import sys
import time
import json
import urllib.parse
import urllib.request
import urllib.error
from azure.identity import AzureCliCredential

# Load .env if present
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

env_url = os.environ["DATAVERSE_URL"].rstrip("/")
token = AzureCliCredential().get_token(f"{env_url}/.default").token

# task lc_title  ->  GitHub issue number
PAIRS_BY_TITLE = [
    ("Audit widget API rate limits", 1),         # rate limiting
    ("k6 Cloud subscription", 2),                # load test
    ("Customer-facing widget documentation", 3), # docs
    ("Snyk for SCA scanning", 4),                # security
    ("Landing page copy VP approval", 5),        # marketing
    ("Open-source license audit", 6),            # legal
]


def issue_guid(n: int) -> str:
    return f"0000cdab-0000-0000-0000-0000{n:02x}000000"


def find_task_id(title: str) -> str | None:
    flt = urllib.parse.quote(f"lc_title eq '{title}'", safe="")
    url = f"{env_url}/api/data/v9.2/lc_tasks?$filter={flt}&$select=lc_taskid"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode("utf-8"))
    rows = data.get("value", [])
    return rows[0]["lc_taskid"] if rows else None


bound = 0
for title, issue_n in PAIRS_BY_TITLE:
    task_id = find_task_id(title)
    if not task_id:
        print(f"  SKIP (task not found by title): {title!r}")
        continue
    guid = issue_guid(issue_n)
    url = f"{env_url}/api/data/v9.2/lc_tasks({task_id})"
    body = json.dumps({
        "lc_GitHubIssueId@odata.bind": f"/lc_githubissues({guid})"
    }).encode()

    # PATCH with cache-lag retry: when the lc_GitHubIssueId lookup column
    # was just created by add_ve_lookup.py, the very first few PATCHes
    # can fail with 0x80048d19 "Error identified in Payload" until the
    # metadata cache catches up. Up to 4 attempts with 5s backoff.
    last_err = None
    for attempt in range(4):
        req = urllib.request.Request(url, data=body, method="PATCH")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("OData-MaxVersion", "4.0")
        req.add_header("OData-Version", "4.0")
        req.add_header("If-Match", "*")
        try:
            with urllib.request.urlopen(req) as resp:
                tag = "" if attempt == 0 else f" [retry {attempt}]"
                print(f"  OK  {title}  -> #{issue_n}  (HTTP {resp.status}){tag}")
                bound += 1
                last_err = None
                break
        except urllib.error.HTTPError as e:
            last_err = e
            body_text = e.read().decode("utf-8")
            # Cache-lag indicator: lookup column not yet materialized
            if "0x80048d19" in body_text and attempt < 3:
                print(f"  [retry {attempt+1}/3] cache lag for {title}; sleeping 5s...")
                time.sleep(5)
                continue
            print(f"  FAIL {title} -> #{issue_n}: {e.code} {body_text[:200]}")
            break

print()
print(f"Bound {bound}/{len(PAIRS_BY_TITLE)} tasks to GitHub issues.")
