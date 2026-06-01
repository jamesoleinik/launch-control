"""Tear down all Episode 5 substrate so we can record from a clean state.

What this deletes (in dependency order):

  1. The test harness flow (workflows row, category=5)
  2. The lc_DraftLaunchBriefing AI Prompt + the sample variant
     (msdyn_aimodel rows; child msdyn_aiconfiguration rows cascade)
  3. The .NET CustomAPI lc_CalculateLaunchReadiness + the Fx twin
     CustomAPI lc_calculatelaunchreadinessfx + any orphan lc_* CustomAPIs
  4. The plugin assembly CalculateLaunchReadiness (cascades plugin types
     and registered steps)
  5. The custom connectors registered via PAPI under the "Launch Control"
     display-name prefix (REST + MCP)

What this PRESERVES (Eps 1-4 substrate + bindings):
  - LaunchControl solution shell
  - lc_launch, lc_milestone tables and their data
  - Connection references (lc_dataverse_harness, lc_githubreleases_harness,
    lc_teams, lc_msnweather)
  - The Ep 3 lc_launch Risk Summary AI Prompt (5b92b771)

Usage:
  python scripts/teardown_ep05.py            # dry run - prints plan
  python scripts/teardown_ep05.py --confirm  # actually deletes
"""
import json, sys, urllib.request, urllib.parse, urllib.error
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
ENV_ID = "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07"

# Names targeted by Episode 5
EP5_AI_PROMPT_NAMES = {"lc_DraftLaunchBriefing", "lc_DraftLaunchBriefing(sample)"}
EP5_CUSTOMAPI_NAMES = {
    "lc_CalculateLaunchReadiness",
    "lc_calculatelaunchreadinessfx",
    "lc_thisisafunction",  # earlier Fx exploration leftover
}
EP5_PLUGIN_ASSEMBLY = "CalculateLaunchReadiness"
EP5_FLOW_NAME = "LC - Custom Tools Test Harness"
EP5_CONNECTOR_DISPLAY_PREFIX = "Launch Control"

CONFIRM = "--confirm" in sys.argv

cred = AzureCliCredential()
DV_TOK = cred.get_token(ENV + "/.default").token
PAPI_TOK = cred.get_token("https://service.powerapps.com/.default").token


def dv(method, path, body=None):
    h = {"Authorization": "Bearer " + DV_TOK, "Accept": "application/json",
         "Content-Type": "application/json", "OData-MaxVersion": "4.0",
         "OData-Version": "4.0"}
    if "?" in path:
        base, qs = path.split("?", 1)
        path = base + "?" + urllib.parse.quote(qs, safe="=&$,'")
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            ENV + "/api/data/v9.2" + path, data=data, headers=h, method=method))
        txt = r.read().decode()
        return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def papi(method, url):
    h = {"Authorization": "Bearer " + PAPI_TOK, "Accept": "application/json"}
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h, method=method))
        body = r.read().decode()
        return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def action(label, fn):
    if CONFIRM:
        s, b = fn()
        ok = 200 <= s < 300 or s == 204
        print(f"   {'OK ' if ok else 'ERR'} [{s}] {label}")
        if not ok:
            print(f"        {b}")
    else:
        print(f"   would delete: {label}")


# ---------- 1. Flow ----------
print("\n[1/5] Test harness flow")
s, r = dv("GET", f"/workflows?$select=workflowid,name&$filter=name eq '{EP5_FLOW_NAME}' and category eq 5")
for w in (r.get("value", []) if isinstance(r, dict) else []):
    action(f"workflow '{w['name']}' ({w['workflowid']})",
           lambda wid=w["workflowid"]: dv("DELETE", f"/workflows({wid})"))

# ---------- 2. AI Prompts ----------
print("\n[2/5] AI Prompts (msdyn_aimodel)")
names_filter = " or ".join(f"msdyn_name eq '{n}'" for n in EP5_AI_PROMPT_NAMES)
s, r = dv("GET", f"/msdyn_aimodels?$select=msdyn_aimodelid,msdyn_name&$filter={names_filter}")
for m in (r.get("value", []) if isinstance(r, dict) else []):
    action(f"msdyn_aimodel '{m['msdyn_name']}' ({m['msdyn_aimodelid']})",
           lambda mid=m["msdyn_aimodelid"]: dv("DELETE", f"/msdyn_aimodels({mid})"))

# ---------- 3. Custom APIs ----------
print("\n[3/5] Custom APIs")
for uname in EP5_CUSTOMAPI_NAMES:
    s, r = dv("GET", f"/customapis?$select=customapiid,uniquename&$filter=uniquename eq '{uname}'")
    rows = r.get("value", []) if isinstance(r, dict) else []
    if not rows:
        print(f"   (none) {uname}")
        continue
    for c in rows:
        # Delete child customapirequestparameter + customapiresponseproperty rows first
        for child_set, child_id, fk in [
            ("customapirequestparameters", "customapirequestparameterid", "_customapiid_value"),
            ("customapiresponseproperties", "customapiresponsepropertyid", "_customapiid_value"),
        ]:
            s2, r2 = dv("GET", f"/{child_set}?$select={child_id}&$filter={fk} eq {c['customapiid']}")
            for ch in (r2.get("value", []) if isinstance(r2, dict) else []):
                action(f"  child {child_set} {ch[child_id]}",
                       lambda cid=ch[child_id], cs=child_set: dv("DELETE", f"/{cs}({cid})"))
        # Fx low-code-plugin twin (msdyn_function) references CustomAPIs as componenttype 10293.
        # Find via RetrieveDependenciesForDelete and clear before deleting the customapi.
        s2, r2 = dv("GET",
                    f"/RetrieveDependenciesForDelete(ComponentType=10038,ObjectId={c['customapiid']})")
        for dep in (r2.get("value", []) if isinstance(r2, dict) else []):
            doid = dep.get("dependentcomponentobjectid")
            dct = dep.get("dependentcomponenttype")
            if doid and dct == 10293:
                action(f"  blocking msdyn_function {doid}",
                       lambda mid=doid: dv("DELETE", f"/msdyn_functions({mid})"))
        action(f"customapi '{c['uniquename']}' ({c['customapiid']})",
               lambda cid=c["customapiid"]: dv("DELETE", f"/customapis({cid})"))

# ---------- 4. Plugin assembly ----------
print("\n[4/5] Plugin assembly (cascades plugintypes + sdkmessageprocessingsteps)")
s, r = dv("GET", f"/pluginassemblies?$select=pluginassemblyid,name&$filter=name eq '{EP5_PLUGIN_ASSEMBLY}'")
for a in (r.get("value", []) if isinstance(r, dict) else []):
    # First delete sdkmessageprocessingsteps that depend on plugintypes in this assembly
    s2, r2 = dv("GET",
                f"/plugintypes?$select=plugintypeid&$filter=_pluginassemblyid_value eq {a['pluginassemblyid']}")
    for pt in (r2.get("value", []) if isinstance(r2, dict) else []):
        s3, r3 = dv("GET",
                    f"/sdkmessageprocessingsteps?$select=sdkmessageprocessingstepid&$filter=_plugintypeid_value eq {pt['plugintypeid']}")
        for st in (r3.get("value", []) if isinstance(r3, dict) else []):
            action(f"  step {st['sdkmessageprocessingstepid']}",
                   lambda sid=st["sdkmessageprocessingstepid"]:
                   dv("DELETE", f"/sdkmessageprocessingsteps({sid})"))
        action(f"  plugintype {pt['plugintypeid']}",
               lambda pid=pt["plugintypeid"]: dv("DELETE", f"/plugintypes({pid})"))
    action(f"pluginassembly '{a['name']}' ({a['pluginassemblyid']})",
           lambda aid=a["pluginassemblyid"]: dv("DELETE", f"/pluginassemblies({aid})"))

# ---------- 5. Custom connectors via PAPI ----------
print("\n[5/5] Custom connectors (REST + MCP, via PAPI)")
q = urllib.parse.quote(f"environment eq '{ENV_ID}'")
s, r = papi("GET",
            f"https://api.powerapps.com/providers/Microsoft.PowerApps/apis"
            f"?api-version=2016-11-01&$filter={q}&$top=2000")
if isinstance(r, dict):
    matches = [a for a in r.get("value", [])
               if a.get("properties", {}).get("isCustomApi")
               and a["properties"].get("displayName", "").startswith(EP5_CONNECTOR_DISPLAY_PREFIX)]
    for a in matches:
        name = a["name"]
        disp = a["properties"]["displayName"]
        url = (f"https://api.powerapps.com/providers/Microsoft.PowerApps/apis/{name}"
               f"?api-version=2016-11-01&$filter={q}")
        action(f"PAPI connector '{disp}' ({name})",
               lambda u=url: papi("DELETE", u))
else:
    print(f"   PAPI list failed: {r}")

print("\n" + ("Done." if CONFIRM else "\nDRY RUN. Re-run with --confirm to actually delete."))
