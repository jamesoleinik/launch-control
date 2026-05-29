"""Teardown the lc_calculatelaunchreadinessfx Power Fx Function.

Order: msdyn_function -> customapi (cascades request params + response props) -> fxexpression.
"""
import json, urllib.request, urllib.error, urllib.parse
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
UNIQUE = "lc_calculatelaunchreadinessfx"

TOKEN = AzureCliCredential().get_token(f"{ENV}/.default").token
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json",
     "OData-MaxVersion": "4.0", "OData-Version": "4.0"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H)) as r:
        return json.loads(r.read().decode())


def _delete(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=H, method="DELETE")) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 404
        print("  ! DELETE", url, "->", e.code, e.read().decode()[:400])
        raise


# 1. Find customapi (also captures fxexpression id for stage 3)
q = urllib.parse.quote("uniquename eq '" + UNIQUE + "'")
apis = _get(ENV + "/api/data/v9.2/customapis?$filter=" + q)["value"]
if not apis:
    print("(no customapi found - already torn down)")
api_ids = [a["customapiid"] for a in apis]
fxexpr_ids = [a.get("_fxexpressionid_value") for a in apis if a.get("_fxexpressionid_value")]

# 2. Delete every msdyn_function that points at one of these customapis
for aid in api_ids:
    fq = urllib.parse.quote("_customapi_value eq " + aid)
    fns = _get(ENV + "/api/data/v9.2/msdyn_functions?$filter=" + fq + "&$select=msdyn_functionid")["value"]
    for f in fns:
        fid = f["msdyn_functionid"]
        print("DELETE msdyn_function", fid, "->", _delete(ENV + "/api/data/v9.2/msdyn_functions(" + fid + ")"))

# 3. Delete the customapi(s)
for aid in api_ids:
    print("DELETE customapi", aid, "->", _delete(ENV + "/api/data/v9.2/customapis(" + aid + ")"))

# 4. Delete the fxexpression(s)
for fx in fxexpr_ids:
    print("DELETE fxexpression", fx, "->", _delete(ENV + "/api/data/v9.2/fxexpressions(" + fx + ")"))

print("Teardown complete.")
