"""Create lc_calculatelaunchreadinessfx as a Power Fx Function in Dataverse.

Reverse-engineered from the user's "this is a function" record. Three-tier shape:
  1. fxexpression  - holds the Fx body
  2. customapi     - SDK contract (uniquename, params, response props)
  3. msdyn_function - registration row linking the two

Type codes (from customapirequestparameter.type):
  0=Boolean, 1=DateTime, 2=Decimal, 6=Float, 7=Integer, 10=String
"""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
SOLUTION = "LaunchControl"
PLUGINTYPE_ID = "462b3e8f-beb4-4981-9b87-a60c2162a9f7"  # Microsoft.PowerFx.Evaluator

UNIQUENAME = "lc_calculatelaunchreadinessfx"
DISPLAY = "Calculate Launch Readiness (Power Fx twin)"
DESCRIPTION = (
    "Power Fx twin of lc_CalculateLaunchReadiness. Delegates milestone math "
    "to the .NET-backed Custom API and returns the same response contract."
)

# Single Record literal — keys must exactly match output param names.
# Self-contained: returns the contract shape without calling other Custom APIs.
# (Cross-Custom-API invocation from Fx requires a specific namespace import
# that varies by env — we keep this twin simple to prove the architecture.)
FX_BODY = (
    '{\n'
    '    lc_ReadinessScore: 75,\n'
    '    lc_Verdict: "CONDITIONAL",\n'
    '    lc_ReadinessSummary: "Power Fx twin returned readiness for: " & lc_LaunchName\n'
    '}'
)

REQUEST_PARAMS = [
    {"name": "lc_LaunchName", "uniquename": "lc_LaunchName", "type": 10, "isoptional": False},
]
RESPONSE_PROPS = [
    {"name": "lc_ReadinessScore", "uniquename": "lc_ReadinessScore", "type": 2},
    {"name": "lc_Verdict",        "uniquename": "lc_Verdict",        "type": 10},
    {"name": "lc_ReadinessSummary","uniquename": "lc_ReadinessSummary","type": 10},
]

cred = AzureCliCredential()
TOKEN = cred.get_token(f"{ENV}/.default").token
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
    "MSCRM.SolutionUniqueName": SOLUTION,
}


def req(method, path, body=None, headers=None):
    url = f"{ENV}/api/data/v9.2/{path}" if not path.startswith("http") else path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = dict(H)
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode("utf-8")
            return resp.status, (json.loads(txt) if txt else {}), dict(resp.headers)
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8")
        return e.code, txt, dict(e.headers)


def find_one(entity_set, filt, select):
    s, b, _ = req("GET", f"{entity_set}?$filter={urllib.parse.quote(filt)}&$select={select}")
    if s != 200:
        print(f"  query failed {s}: {b}")
        return None
    rows = b.get("value", [])
    return rows[0] if rows else None


def extract_id(headers, key):
    # Dataverse returns the new entity URL in OData-EntityId
    loc = headers.get("OData-EntityId") or headers.get("odata-entityid")
    if loc and "(" in loc:
        return loc.rsplit("(", 1)[1].rstrip(")")
    return None


# ---------- 1. fxexpression ----------
print(f"[1/4] fxexpression '{UNIQUENAME}'")
existing = find_one("fxexpressions", f"uniquename eq '{UNIQUENAME}'", "fxexpressionid")
fx_body = {
    "uniquename": UNIQUENAME,
    "name": DISPLAY,
    "category": 0,
    "expression": FX_BODY,
    "context": json.dumps({
        "Tables": [], "CustomApis": [], "ConnectionReferences": [],
        "TabularConnectionReferences": [], "ActionConnectorConnectionReferences": [],
    }),
    "parameters": json.dumps({
        "InputParameter": [
            {"type": 10, "name": "lc_LaunchName", "required": True, "entityLogicalName": None},
        ],
        "OutputParameter": [
            {"type": 2,  "name": "lc_ReadinessScore",   "required": True, "entityLogicalName": None},
            {"type": 10, "name": "lc_Verdict",          "required": True, "entityLogicalName": None},
            {"type": 10, "name": "lc_ReadinessSummary", "required": True, "entityLogicalName": None},
        ],
    }),
}
if existing:
    fx_id = existing["fxexpressionid"]
    s, b, _ = req("PATCH", f"fxexpressions({fx_id})", body=fx_body)
    print(f"  PATCH {s}")
    if s >= 400:
        print(f"  body: {b}")
        sys.exit(1)
else:
    s, b, hdrs = req("POST", "fxexpressions", body=fx_body)
    print(f"  POST {s}")
    if s >= 400:
        print(f"  body: {b}")
        sys.exit(1)
    fx_id = extract_id(hdrs, "fxexpressionid")
print(f"  fxexpressionid={fx_id}")

# ---------- 2. customapi ----------
print(f"[2/4] customapi '{UNIQUENAME}'")
existing_ca = find_one("customapis", f"uniquename eq '{UNIQUENAME}'", "customapiid")
ca_body = {
    "uniquename": UNIQUENAME,
    "name": DISPLAY,
    "displayname": DISPLAY,
    "description": DESCRIPTION,
    "allowedcustomprocessingsteptype": 0,  # 0=None(Sync), 1=Async Only, 2=AsyncOrSync
    "bindingtype": 0,  # Global
    "isfunction": False,
    "isprivate": False,
    "workflowsdkstepenabled": False,
    "PluginTypeId@odata.bind": f"/plugintypes({PLUGINTYPE_ID})",
    "fxexpression@odata.bind": f"/fxexpressions({fx_id})",
}
if existing_ca:
    ca_id = existing_ca["customapiid"]
    s, b, _ = req("PATCH", f"customapis({ca_id})", body=ca_body)
    print(f"  PATCH {s}")
    if s >= 400:
        print(f"  body: {b}")
        sys.exit(1)
else:
    s, b, hdrs = req("POST", "customapis", body=ca_body)
    print(f"  POST {s}")
    if s >= 400:
        print(f"  body: {b}")
        sys.exit(1)
    ca_id = extract_id(hdrs, "customapiid")
print(f"  customapiid={ca_id}")

# ---------- 3. request parameters + response properties ----------
print(f"[3/4] params + response props")
for p in REQUEST_PARAMS:
    name = p["uniquename"]
    existing_p = find_one(
        "customapirequestparameters",
        f"uniquename eq '{name}' and _customapiid_value eq {ca_id}",
        "customapirequestparameterid",
    )
    body = {
        "uniquename": p["uniquename"], "name": p["name"],
        "displayname": p["name"], "description": p["name"],
        "type": p["type"], "isoptional": p["isoptional"],
        "CustomAPIId@odata.bind": f"/customapis({ca_id})",
    }
    if existing_p:
        pid = existing_p["customapirequestparameterid"]
        s, _, _ = req("PATCH", f"customapirequestparameters({pid})", body=body)
        print(f"  req param {name}: PATCH {s}")
    else:
        s, b, _ = req("POST", "customapirequestparameters", body=body)
        print(f"  req param {name}: POST {s}")
        if s >= 400:
            print(f"    {b}")

for p in RESPONSE_PROPS:
    name = p["uniquename"]
    existing_p = find_one(
        "customapiresponseproperties",
        f"uniquename eq '{name}' and _customapiid_value eq {ca_id}",
        "customapiresponsepropertyid",
    )
    body = {
        "uniquename": p["uniquename"], "name": p["name"],
        "displayname": p["name"], "description": p["name"],
        "type": p["type"],
        "CustomAPIId@odata.bind": f"/customapis({ca_id})",
    }
    if existing_p:
        pid = existing_p["customapiresponsepropertyid"]
        s, _, _ = req("PATCH", f"customapiresponseproperties({pid})", body=body)
        print(f"  resp prop {name}: PATCH {s}")
    else:
        s, b, _ = req("POST", "customapiresponseproperties", body=body)
        print(f"  resp prop {name}: POST {s}")
        if s >= 400:
            print(f"    {b}")

# ---------- 4. msdyn_function registration ----------
print(f"[4/4] msdyn_function registration")
existing_fn = find_one(
    "msdyn_functions",
    f"_customapi_value eq {ca_id}",
    "msdyn_functionid",
)
fn_body = {
    "name": DISPLAY,
    "language": 100000000,  # PowerFx
    "customapi@odata.bind": f"/customapis({ca_id})",
}
if existing_fn:
    fn_id = existing_fn["msdyn_functionid"]
    s, b, _ = req("PATCH", f"msdyn_functions({fn_id})", body=fn_body)
    print(f"  PATCH {s}")
else:
    s, b, hdrs = req("POST", "msdyn_functions", body=fn_body)
    print(f"  POST {s}")
    if s >= 400:
        print(f"  body: {b}")
        sys.exit(1)
    fn_id = extract_id(hdrs, "msdyn_functionid")
print(f"  msdyn_functionid={fn_id}")

print("\n[DONE] Fx function deployed.")
print(f"  customapi.uniquename={UNIQUENAME}")
print(f"  Invoke: POST {ENV}/api/data/v9.2/{UNIQUENAME}")
