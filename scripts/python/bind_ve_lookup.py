"""
Bind 6 lc_task records to lc_githubissue virtual entities via the
new lc_GitHubIssueId lookup column.

Issue GUID format (from Class1.cs DeterministicGuid):
  bytes[0]=0xAB, bytes[1]=0xCD, bytes[12..15] = issue number (LE int32)
  Rendered: 0000cdab-0000-0000-0000-0000NN000000
"""
import os
import json
import urllib.request
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

PAIRS = [
    ("787a0bd0-f843-f111-bec6-000d3a33661c", 1),  # Audit rate limits -> #1 rate limiting
    ("4b78c212-f943-f111-bec6-000d3a33661c", 2),  # k6 Cloud -> #2 load test
    ("4c56b6e8-f843-f111-bec6-000d3a33661c", 3),  # Customer docs -> #3 docs
    ("f877c212-f943-f111-bec6-000d3a33661c", 4),  # Snyk -> #4 security
    ("33ceaef4-f843-f111-bec6-000d3a33661c", 5),  # GTM campaign -> #5 marketing
    ("6656b6e8-f843-f111-bec6-000d3a33661c", 6),  # OSS license audit -> #6 legal
]

def issue_guid_v2(n: int) -> str:
    # Format observed in lc_githubissue records: 0000cdab-0000-0000-0000-0000NN000000
    return f"0000cdab-0000-0000-0000-0000{n:02x}000000"

for task_id, issue_n in PAIRS:
    guid = issue_guid_v2(issue_n)
    url = f"{env_url}/api/data/v9.2/lc_tasks({task_id})"
    body = json.dumps({
        "lc_GitHubIssueId@odata.bind": f"/lc_githubissues({guid})"
    }).encode()
    req = urllib.request.Request(url, data=body, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("If-Match", "*")
    try:
        with urllib.request.urlopen(req) as r:
            print(f"  {task_id} -> issue #{issue_n} ({guid}) [{r.status}]")
    except urllib.error.HTTPError as e:
        print(f"  FAIL {task_id} -> #{issue_n}: {e.code} {e.read().decode()[:300]}")
