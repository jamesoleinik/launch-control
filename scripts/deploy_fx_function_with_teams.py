"""Deploy lc_CalculateLaunchReadinessFx — Power Fx twin of the .NET Custom API.

Same I/O shape as lc_CalculateLaunchReadiness, plus:
  + lc_NotifiedAt (DateTime) — when the verdict was posted to Teams
  + side effect: posts an HTML card to a Teams channel via the first-party
    MicrosoftTeams connector (resolved through the `lc_teams` connection
    reference, so DLP / OAuth are governed by the platform).

Idempotent. Re-runs PATCH instead of POSTing duplicates.

GRACEFUL FAILURE — exits 0 with remediation steps (does NOT raise) when:
  * The low-code plug-ins app is not installed (fxexpressions / msdyn_functions
    entities are missing or the Microsoft.PowerFx.Evaluator plugintype row is
    absent).
  * The `lc_teams` connection reference is missing from this env.
Any other Dataverse error is still surfaced normally.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env

SOLUTION = "LaunchControl"
UNIQUENAME = "lc_calculatelaunchreadinessfx"
DISPLAY = "Calculate Launch Readiness (Power Fx twin)"
DESCRIPTION = (
    "Power Fx twin of lc_CalculateLaunchReadiness. Same response contract "
    "plus lc_NotifiedAt; posts an HTML readiness card to a Teams channel "
    "via the lc_teams connection reference."
)
CONNREF = "lc_teams"

# Target Teams channel for the verdict post. Replace these per env (or move
# them onto lc_launch as lc_TeamsTeamId / lc_TeamsChannelId columns and have
# the Fx body read them off the launch record).
TEAM_ID = "320c91d7-7c33-458b-9b5c-300947611d76"
CHANNEL_ID = "19:4bff40ddb1a74ef5a4a23c73b7c7467c@thread.tacv2"

REMEDIATION = """
The low-code plug-ins app (a.k.a. "Functions in Dataverse" / Power Fx
plug-ins, preview) is required for this Custom API. To enable it:

  1. Sign in to the Power Platform admin center as a Power Platform admin:
       https://admin.powerplatform.microsoft.com
  2. Environments -> select this env -> Settings -> Product -> Features
     -> turn ON "Power Fx for Dataverse plug-ins (preview)".
     (CLI equivalent:
        pac admin update-org-feature --feature LowCodePluginsEnabled --value true )
  3. Install the "Power Platform Tools" / "Power Fx plug-ins" managed
     solution from AppSource if it isn't already present in this env.
  4. Wait ~2 minutes for the fxexpressions + msdyn_functions tables to
     provision, then re-run this script.

The .NET-backed twin (lc_CalculateLaunchReadiness) is unaffected and
continues to work — only the Fx twin requires the preview runtime.
"""

CREF_REMEDIATION = """
The `lc_teams` connection reference is missing from this environment.
The Fx body posts to a Teams channel via the first-party MicrosoftTeams
connector, which requires an OAuth-authenticated connection bound through
a connection reference. To create one:

  1. https://make.powerapps.com -> select this env -> Connections ->
     + New connection -> "Microsoft Teams" -> sign in and consent.
     Copy the resulting connection GUID.
  2. Solutions -> LaunchControl -> + New -> More -> Connection reference
     -> Display name "LC Teams (Fx)", Name "lc_teams",
     Connector "Microsoft Teams", Connection = the GUID from step 1.
  3. Re-run this script.

The .NET-backed twin (lc_CalculateLaunchReadiness) is unaffected.
"""


def _client():
    load_env()
    env = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_token()
    headers_base = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "MSCRM.SolutionUniqueName": SOLUTION,
    }

    def req(method, path, body=None):
        url = f"{env}/api/data/v9.2/{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        r = urllib.request.Request(url, data=data, headers=headers_base, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                txt = resp.read().decode("utf-8")
                return resp.status, (json.loads(txt) if txt else {}), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), dict(e.headers)

    return env, req


def _extract_id(headers):
    loc = headers.get("OData-EntityId") or headers.get("odata-entityid", "")
    return loc.rsplit("(", 1)[1].rstrip(")") if "(" in loc else None


def _find_one(req, entity_set, filt, select):
    s, b, _ = req("GET", f"{entity_set}?$filter={urllib.parse.quote(filt)}&$select={select}")
    if s != 200:
        return None
    rows = (b if isinstance(b, dict) else {}).get("value", [])
    return rows[0] if rows else None


def _preflight(req):
    """Return (ok, reason). Never raises for the documented graceful-failure cases."""
    # 1. fxexpressions table exists?
    s, b, _ = req("GET", "fxexpressions?$top=1")
    if s in (404, 400) or (isinstance(b, str) and "ResourceNotFound" in b):
        return False, "fxexpressions entity not found (low-code plug-ins app not installed)."
    # 2. msdyn_functions table exists?
    s, b, _ = req("GET", "msdyn_functions?$top=1")
    if s in (404, 400) or (isinstance(b, str) and "ResourceNotFound" in b):
        return False, "msdyn_functions entity not found (low-code plug-ins app not installed)."
    # 3. PowerFx evaluator plugin type registered?
    row = _find_one(req, "plugintypes",
                    "typename eq 'Microsoft.PowerFx.Evaluator'", "plugintypeid")
    if not row:
        return False, "Microsoft.PowerFx.Evaluator plugintype not found (low-code plug-ins app not installed)."
    return True, row["plugintypeid"]


def _fx_body():
    """Power Fx source — milestone tally, Teams post, contract output."""
    return f'''With(
    {{ launch: LookUp(lc_launchs, lc_name = lc_LaunchName) }},
    If(IsBlank(launch),
        {{
            lc_ReadinessScore: 0,
            lc_Verdict: "NO-GO",
            lc_ReadinessSummary: "Launch not found: " & lc_LaunchName,
            lc_NotifiedAt: Blank()
        }},
        With(
            {{
                ms: Filter(lc_milestones, lc_launchid.lc_launchid = launch.lc_launchid)
            }},
            With(
                {{
                    total: CountRows(ms),
                    score: If(CountRows(ms) = 0, 0, Min(100, CountRows(ms) * 20)),
                    verdict: If(CountRows(ms) = 0, "NO-GO",
                                If(CountRows(ms) >= 5, "GO", "CONDITIONAL"))
                }},
                With(
                    {{
                        posted: lc_teams.PostMessageToChannelV3(
                            "{TEAM_ID}",
                            "{CHANNEL_ID}",
                            {{
                                content: "<b>" & launch.lc_name & " — " & verdict
                                    & " (" & Text(score) & "/100)</b><br/>"
                                    & Text(total) & " milestone(s) tracked.",
                                contentType: "html"
                            }}
                        )
                    }},
                    {{
                        lc_ReadinessScore: score,
                        lc_Verdict: verdict,
                        lc_ReadinessSummary: launch.lc_name & ": " & Text(total)
                            & " milestone(s); posted to Teams id=" & posted.id,
                        lc_NotifiedAt: Now()
                    }}
                )
            )
        )
    )
)'''


def _fx_context():
    return json.dumps({
        "Tables": ["lc_launch", "lc_milestone"],
        "CustomApis": [],
        "ConnectionReferences": [CONNREF],
        "TabularConnectionReferences": [],
        "ActionConnectorConnectionReferences": [],
    })


def _fx_parameters():
    return json.dumps({
        "InputParameter": [
            {"type": 10, "name": "lc_LaunchName", "required": True, "entityLogicalName": None},
        ],
        "OutputParameter": [
            {"type": 2,  "name": "lc_ReadinessScore",   "required": True, "entityLogicalName": None},
            {"type": 10, "name": "lc_Verdict",          "required": True, "entityLogicalName": None},
            {"type": 10, "name": "lc_ReadinessSummary", "required": True, "entityLogicalName": None},
            {"type": 1,  "name": "lc_NotifiedAt",       "required": False, "entityLogicalName": None},
        ],
    })


REQUEST_PARAMS = [
    {"name": "lc_LaunchName", "type": 10, "isoptional": False,
     "description": "Name of the lc_launch record to score and notify."},
]
RESPONSE_PROPS = [
    {"name": "lc_ReadinessScore",   "type": 2,  "description": "0-100 readiness score."},
    {"name": "lc_Verdict",          "type": 10, "description": "GO | CONDITIONAL | NO-GO."},
    {"name": "lc_ReadinessSummary", "type": 10, "description": "Human-readable summary."},
    {"name": "lc_NotifiedAt",       "type": 1,  "description": "Timestamp the Teams card was posted."},
]


def main():
    env, req = _client()

    print("[0/5] preflight: low-code plug-ins app")
    ok, info = _preflight(req)
    if not ok:
        print(f"  SKIPPED — {info}")
        print(REMEDIATION)
        return 0
    plugintype_id = info
    print(f"  ok. PowerFx evaluator plugintype={plugintype_id}")

    print(f"[0b/5] preflight: connection reference '{CONNREF}'")
    cref = _find_one(req, "connectionreferences",
                     f"connectionreferencelogicalname eq '{CONNREF}'",
                     "connectionreferenceid,connectionid")
    if not cref:
        print(f"  SKIPPED — connection reference '{CONNREF}' is not present in this env.")
        print(CREF_REMEDIATION)
        return 0
    print(f"  ok. cref={cref['connectionreferenceid']} bound to connectionid={cref.get('connectionid')}")

    # 1. fxexpression
    print(f"[1/5] fxexpression '{UNIQUENAME}'")
    fx_payload = {
        "uniquename": UNIQUENAME,
        "name": DISPLAY,
        "category": 0,
        "expression": _fx_body(),
        "context": _fx_context(),
        "parameters": _fx_parameters(),
    }
    existing = _find_one(req, "fxexpressions",
                         f"uniquename eq '{UNIQUENAME}'", "fxexpressionid")
    if existing:
        fx_id = existing["fxexpressionid"]
        s, b, _ = req("PATCH", f"fxexpressions({fx_id})", fx_payload)
        print(f"  PATCH {s}")
        if s >= 400:
            print(f"  body: {b}"); return 1
    else:
        s, b, hdrs = req("POST", "fxexpressions", fx_payload)
        print(f"  POST {s}")
        if s >= 400:
            print(f"  body: {b}"); return 1
        fx_id = _extract_id(hdrs)
    print(f"  fxexpressionid={fx_id}")

    # 2. customapi (with optional fxexpression binding)
    print(f"[2/5] customapi '{UNIQUENAME}'")
    ca_payload = {
        "uniquename": UNIQUENAME,
        "name": DISPLAY,
        "displayname": DISPLAY,
        "description": DESCRIPTION,
        "allowedcustomprocessingsteptype": 0,
        "bindingtype": 0,
        "isfunction": False,
        "isprivate": False,
        "workflowsdkstepenabled": False,
        "PluginTypeId@odata.bind": f"/plugintypes({plugintype_id})",
        "fxexpression@odata.bind": f"/fxexpressions({fx_id})",
    }
    existing_ca = _find_one(req, "customapis",
                            f"uniquename eq '{UNIQUENAME}'", "customapiid")
    if existing_ca:
        ca_id = existing_ca["customapiid"]
        s, b, _ = req("PATCH", f"customapis({ca_id})", ca_payload)
        print(f"  PATCH {s}")
        if s >= 400:
            print(f"  body: {b}"); return 1
    else:
        s, b, hdrs = req("POST", "customapis", ca_payload)
        print(f"  POST {s}")
        if s >= 400:
            print(f"  body: {b}"); return 1
        ca_id = _extract_id(hdrs)
    print(f"  customapiid={ca_id}")

    # 3. request params + response props (idempotent)
    print("[3/5] request params + response properties")
    for p in REQUEST_PARAMS:
        body = {
            "uniquename": p["name"], "name": p["name"], "displayname": p["name"],
            "description": p["description"], "type": p["type"],
            "isoptional": p["isoptional"],
            "CustomAPIId@odata.bind": f"/customapis({ca_id})",
        }
        found = _find_one(req, "customapirequestparameters",
                          f"uniquename eq '{p['name']}' and _customapiid_value eq {ca_id}",
                          "customapirequestparameterid")
        if found:
            s, _, _ = req("PATCH",
                          f"customapirequestparameters({found['customapirequestparameterid']})",
                          body)
            print(f"  req {p['name']}: PATCH {s}")
        else:
            s, b, _ = req("POST", "customapirequestparameters", body)
            print(f"  req {p['name']}: POST {s}")
            if s >= 400:
                print(f"    {b}")

    for p in RESPONSE_PROPS:
        body = {
            "uniquename": p["name"], "name": p["name"], "displayname": p["name"],
            "description": p["description"], "type": p["type"],
            "CustomAPIId@odata.bind": f"/customapis({ca_id})",
        }
        found = _find_one(req, "customapiresponseproperties",
                          f"uniquename eq '{p['name']}' and _customapiid_value eq {ca_id}",
                          "customapiresponsepropertyid")
        if found:
            s, _, _ = req("PATCH",
                          f"customapiresponseproperties({found['customapiresponsepropertyid']})",
                          body)
            print(f"  resp {p['name']}: PATCH {s}")
        else:
            s, b, _ = req("POST", "customapiresponseproperties", body)
            print(f"  resp {p['name']}: POST {s}")
            if s >= 400:
                print(f"    {b}")

    # 4. msdyn_function registration row
    print("[4/5] msdyn_function registration")
    existing_fn = _find_one(req, "msdyn_functions",
                            f"_customapi_value eq {ca_id}", "msdyn_functionid")
    fn_body = {
        "name": DISPLAY,
        "language": 100000000,  # PowerFx
        "customapi@odata.bind": f"/customapis({ca_id})",
    }
    if existing_fn:
        s, b, _ = req("PATCH", f"msdyn_functions({existing_fn['msdyn_functionid']})", fn_body)
        print(f"  PATCH {s}")
    else:
        s, b, hdrs = req("POST", "msdyn_functions", fn_body)
        print(f"  POST {s}")
        if s >= 400:
            print(f"  body: {b}"); return 1

    # 5. Ensure the Custom API is in the LaunchControl solution (10038 = CustomAPI).
    print("[5/5] LaunchControl solution membership")
    s, b, _ = req("POST", "AddSolutionComponent", {
        "ComponentId": ca_id,
        "ComponentType": 10038,
        "SolutionUniqueName": SOLUTION,
        "AddRequiredComponents": True,
        "IncludedComponentSettingsValues": None,
    })
    print(f"  AddSolutionComponent: {s}")
    if s >= 400 and "already" not in str(b).lower():
        print(f"  body: {b}")

    print("\n[DONE]")
    print(f"  Invoke (function, GET): {env}/api/data/v9.2/{UNIQUENAME}(lc_LaunchName='Q3 Widget Launch')")
    print("  (URL-encode spaces as %20)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
