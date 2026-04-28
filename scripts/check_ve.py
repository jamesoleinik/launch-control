import os, sys, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env
load_env()
env_url = os.environ["DATAVERSE_URL"].rstrip("/")
token = get_token()
url = env_url + "/api/data/v9.2/EntityDefinitions(LogicalName=%27lc_githubissue%27)?%24select=LogicalName,SchemaName,TableType"
req = urllib.request.Request(url)
req.add_header("Authorization", "Bearer " + token)
req.add_header("Accept", "application/json")
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print("EXISTS: %s (TableType=%s)" % (data.get("LogicalName"), data.get("TableType")))
except urllib.error.HTTPError as e:
    print("NOT FOUND (HTTP %s)" % e.code)
