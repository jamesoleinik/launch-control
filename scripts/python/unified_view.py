"""
Episode 4 demo — unified query across the relational core (lc_task) and
the GitHub Issues virtual entity, joined through the new lc_GitHubIssueId
lookup. One Web API call. One result set. Three systems' truth.
"""
import os
import json
import urllib.parse
import urllib.request
from azure.identity import AzureCliCredential

_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

env_url = os.environ["DATAVERSE_URL"].rstrip("/")
token = AzureCliCredential().get_token(f"{env_url}/.default").token

select = "lc_taskid,lc_title,lc_stagingsource,_lc_githubissueid_value"
expand = "lc_GitHubIssueId($select=lc_issuenumber,lc_name,lc_state,lc_url)"
qs = urllib.parse.urlencode({
    "$select": select,
    "$expand": expand,
})
url = f"{env_url}/api/data/v9.2/lc_tasks?{qs}"

req = urllib.request.Request(url)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/json")
req.add_header("OData-Version", "4.0")

with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())

rows = data.get("value", [])
linked = [t for t in rows if t.get("_lc_githubissueid_value")]
print(f"\n=== Tasks linked to live GitHub Issues ({len(linked)} of {len(rows)} total) ===\n")
print(f"{'Task':<48}  {'Issue':<7}  {'State':<6}  GitHub Title")
print("-" * 120)
for t in linked:
    issue = t.get("lc_GitHubIssueId") or {}
    print(
        f"{t['lc_title'][:46]:<48}  "
        f"#{issue.get('lc_issuenumber','?'):<6}  "
        f"{issue.get('lc_state','?'):<6}  "
        f"{issue.get('lc_name','')[:50]}"
    )
print()
