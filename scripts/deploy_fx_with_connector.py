"""End-to-end: provision MSN Weather connection + connection reference + Fx body that uses it.

This script proves Power Fx Functions in Dataverse CAN make HTTPS calls via Power Platform
connectors, contradicting the common "Dataverse plugins are sandboxed from the internet" claim.

Prereqs:
  - `pac auth create` profile selected against target env
  - `azure-identity` (pip install azure-identity)
  - lc_calculatelaunchreadinessfx already deployed by scripts/deploy_fx_function.py

What it does:
  1. Create a no-auth MSN Weather connection in the env (via PAPI)
  2. Create a Dataverse connectionreference (`lc_msnweather`) pointing at it
  3. PATCH the existing fxexpression to (a) declare the ref in context.ConnectionReferences
     and (b) call new_msnweather.CurrentWeather(...) inside the body
  4. Invoke the function and print the live result
"""
import json, urllib.request, urllib.error, urllib.parse, uuid
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
ENV_ID = "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07"
SOLUTION = "LaunchControl"
CONNREF_LOGICAL = "lc_msnweather"

cred = AzureCliCredential()


def _req(token, url, method="GET", body=None, extra_headers=None):
    h = {"Authorization": "Bearer " + token, "Accept": "application/json", "Content-Type": "application/json"}
    if extra_headers:
        h.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method))
        return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers


# ---------- 1. PAPI: create MSN Weather connection ----------
papi = cred.get_token("https://service.powerapps.com/.default").token
conn_id = str(uuid.uuid4())
url = (f"https://api.powerapps.com/providers/Microsoft.PowerApps/apis/shared_msnweather/connections/"
       f"{conn_id}?api-version=2020-06-01&%24filter=environment%20eq%20%27{ENV_ID}%27")
s, b, _ = _req(papi, url, "PUT", {"properties": {"displayName": "LC MSN Weather", "environment": {"name": ENV_ID}}})
print(f"[1] PAPI connection: {s}")
assert s in (200, 201), b

# ---------- 2. Dataverse: create connection reference (idempotent) ----------
dv = cred.get_token(ENV + "/.default").token
q = urllib.parse.quote(f"connectionreferencelogicalname eq '{CONNREF_LOGICAL}'")
s, b, _ = _req(dv, ENV + f"/api/data/v9.2/connectionreferences?$filter={q}")
existing = json.loads(b)["value"]
if existing:
    cref_id = existing[0]["connectionreferenceid"]
    print(f"[2] connectionreference exists: {cref_id} (skipping create)")
else:
    body = {"connectionreferencelogicalname": CONNREF_LOGICAL,
            "connectionreferencedisplayname": "LC MSN Weather",
            "connectorid": "/providers/Microsoft.PowerApps/apis/shared_msnweather",
            "connectionid": conn_id}
    s, b, hdrs = _req(dv, ENV + "/api/data/v9.2/connectionreferences", "POST", body,
                      {"MSCRM.SolutionUniqueName": SOLUTION})
    print(f"[2] connectionreference create: {s}")
    assert s == 204, b

# ---------- 3. PATCH fxexpression body ----------
q = urllib.parse.quote("uniquename eq 'lc_calculatelaunchreadinessfx'")
s, b, _ = _req(dv, ENV + f"/api/data/v9.2/customapis?$filter={q}&$select=customapiid,_fxexpressionid_value")
api = json.loads(b)["value"][0]
fxexpr_id = api["_fxexpressionid_value"]

FX_BODY = '''With(
    { launch: LookUp(lc_launchs, lc_name = lc_LaunchName),
      weather: lc_msnweather.CurrentWeather("Redmond, WA", "Imperial").responses.weather.current },
    If(IsBlank(launch),
        { lc_ReadinessScore: 0, lc_Verdict: "NO-GO",
          lc_ReadinessSummary: "Launch not found: " & lc_LaunchName },
        With(
            { total: CountRows(Filter(lc_milestones, lc_launchid.lc_launchid = launch.lc_launchid)) },
            {
                lc_ReadinessScore: If(total = 0, 0, Min(100, total * 20)),
                lc_Verdict: If(total = 0, "NO-GO", If(total >= 5, "GO", "CONDITIONAL")),
                lc_ReadinessSummary: launch.lc_name & ": " & total & " milestone(s); Redmond is "
                    & Text(weather.temp) & "F (feels " & Text(weather.feels) & "F)"
            }
        )
    )
)'''

ctx = json.dumps({
    "Tables": ["lc_launch", "lc_milestone"],
    "CustomApis": [],
    "ConnectionReferences": [CONNREF_LOGICAL],
    "TabularConnectionReferences": [],
    "ActionConnectorConnectionReferences": [],
})
params = json.dumps({
    "InputParameter": [{"type": 10, "name": "lc_LaunchName", "required": True, "entityLogicalName": None}],
    "OutputParameter": [
        {"type": 2, "name": "lc_ReadinessScore", "required": True, "entityLogicalName": None},
        {"type": 10, "name": "lc_Verdict", "required": True, "entityLogicalName": None},
        {"type": 10, "name": "lc_ReadinessSummary", "required": True, "entityLogicalName": None},
    ],
})
s, b, _ = _req(dv, ENV + f"/api/data/v9.2/fxexpressions({fxexpr_id})", "PATCH",
               {"expression": FX_BODY, "context": ctx, "parameters": params})
print(f"[3] fxexpression PATCH: {s}")
assert s == 204, b

# ---------- 4. Invoke & report ----------
s, b, _ = _req(dv, ENV + "/api/data/v9.2/lc_calculatelaunchreadinessfx", "POST",
               {"lc_LaunchName": "Q3 Widget Launch"})
print(f"[4] Invoke: {s}")
print(json.dumps(json.loads(b), indent=2))
