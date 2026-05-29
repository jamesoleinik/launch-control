"""End-to-end: bind a Microsoft Teams connection to the Power Fx Function so it posts.

This is the "production" sibling of scripts/deploy_fx_with_connector.py (MSN Weather).
The MSN Weather variant proved Fx Functions CAN reach HTTPS via connectors. This variant
proves the same thing with an OAuth-gated first-party connector and a real side effect:
a Teams message lands in a channel every time lc_calculatelaunchreadinessfx is invoked.

Prereqs (one-time, manual):
  1. `pac auth create` profile + `az login` against the target tenant
  2. Create a Microsoft Teams connection in the target env via the maker portal
     (https://make.powerapps.com -> Connections -> +New connection -> Microsoft Teams)
     and complete OAuth consent. The connection's GUID goes into CONN_ID below.
  3. Pick a Team + Channel that the connection's identity is a member of. The
     Team's groupId and the Channel's channelId (the "19:...@thread.tacv2" form)
     go into TEAM_ID / CHANNEL_ID below.
  4. lc_calculatelaunchreadinessfx already deployed by scripts/deploy_fx_function.py.

What it does (idempotent):
  1. Find or create the `lc_teams` connectionreference bound to CONN_ID, in the
     LaunchControl solution.
  2. PATCH the existing fxexpression body to (a) declare `lc_teams` in
     context.ConnectionReferences and (b) call
         lc_teams.PostMessageToChannelV3(groupId, channelId, { content, contentType })
     inside the body. Note the *flat* record shape for the third arg --
     Power Fx low-code-plugin connector binding does NOT support nested records
     ("Missing property content, object is too complex or not supported" if you nest).
  3. Invoke the function for Q3 Widget Launch and print the live result, which
     now includes the Teams message id confirming the post landed.

Why these exact connector args:
  - PostMessageToChannelV3 swagger path params are groupId + channelId.
  - Swagger body is { subject?, body: { content, contentType } } but Power Fx
    flattens the single-required nested object, so callers pass the leaves directly.
  - First-found compile-passing shape (("Flow bot","Channel", record)) succeeds at
    compile time because all three positions accept text|record, but at runtime
    "Flow bot" / "Channel" are sent as groupId / channelId and the post fails.
    The correct positional binding is (groupId, channelId, body-record).
"""
import json, urllib.request, urllib.error, urllib.parse
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
SOLUTION = "LaunchControl"
CONNREF = "lc_teams"

# --- Pre-provisioned (see prereqs above) ---
CONN_ID = "9be4c207-0cd8-4b9e-9627-da5312731589"        # LC Teams connection (OAuth-authenticated)
TEAM_ID = "320c91d7-7c33-458b-9b5c-300947611d76"        # A365 Preview 001
CHANNEL_ID = "19:4bff40ddb1a74ef5a4a23c73b7c7467c@thread.tacv2"  # MCP Test Channel (renamed)

cred = AzureCliCredential()
dv = cred.get_token(ENV + "/.default").token
H = {"Authorization": "Bearer " + dv, "Accept": "application/json", "Content-Type": "application/json"}


def req(url, method="GET", body=None, extra=None):
    hh = dict(H)
    if extra:
        hh.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hh, method=method))
        return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers


# ---------- 1. Ensure connectionreference exists & is bound to CONN_ID ----------
q = urllib.parse.quote(f"connectionreferencelogicalname eq '{CONNREF}'")
s, b, _ = req(ENV + f"/api/data/v9.2/connectionreferences?$filter={q}")
existing = json.loads(b)["value"]
if existing:
    cref_id = existing[0]["connectionreferenceid"]
    print(f"[1] connectionreference exists: {cref_id}")
    if existing[0].get("connectionid") != CONN_ID:
        s, b, _ = req(ENV + f"/api/data/v9.2/connectionreferences({cref_id})", "PATCH",
                      {"connectionid": CONN_ID})
        print(f"    rebound connectionid -> {CONN_ID}: {s}")
else:
    s, b, _ = req(ENV + "/api/data/v9.2/connectionreferences", "POST",
                  {"connectionreferencelogicalname": CONNREF,
                   "connectionreferencedisplayname": "LC Teams (Fx)",
                   "connectorid": "/providers/Microsoft.PowerApps/apis/shared_teams",
                   "connectionid": CONN_ID},
                  {"MSCRM.SolutionUniqueName": SOLUTION})
    print(f"[1] connectionreference POST: {s}")
    assert s == 204, b

# ---------- 2. Find fxexpression to patch ----------
q = urllib.parse.quote("uniquename eq 'lc_calculatelaunchreadinessfx'")
s, b, _ = req(ENV + f"/api/data/v9.2/customapis?$filter={q}&$select=customapiid,_fxexpressionid_value")
fxexpr_id = json.loads(b)["value"][0]["_fxexpressionid_value"]
print(f"[2] fxexpression: {fxexpr_id}")

# ---------- 3. PATCH Fx body to post a Teams message ----------
FX_BODY = f'''With(
    {{ launch: LookUp(lc_launchs, lc_name = lc_LaunchName) }},
    If(IsBlank(launch),
        {{ lc_ReadinessScore: 0, lc_Verdict: "NO-GO",
           lc_ReadinessSummary: "Launch not found: " & lc_LaunchName }},
        With(
            {{ total: CountRows(Filter(lc_milestones, lc_launchid.lc_launchid = launch.lc_launchid)),
               msg: "Launch readiness check: " & launch.lc_name }},
            With(
                {{ posted: lc_teams.PostMessageToChannelV3(
                       "{TEAM_ID}",
                       "{CHANNEL_ID}",
                       {{ content: msg & " (" & Text(total) & " milestones tracked)", contentType: "html" }}
                   ) }},
                {{
                    lc_ReadinessScore: If(total = 0, 0, Min(100, total * 20)),
                    lc_Verdict: If(total = 0, "NO-GO", If(total >= 5, "GO", "CONDITIONAL")),
                    lc_ReadinessSummary: launch.lc_name & ": " & total & " milestone(s); posted to Teams id=" & posted.id
                }}
            )
        )
    )
)'''

ctx = json.dumps({
    "Tables": ["lc_launch", "lc_milestone"],
    "CustomApis": [],
    "ConnectionReferences": [CONNREF],
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
s, b, _ = req(ENV + f"/api/data/v9.2/fxexpressions({fxexpr_id})", "PATCH",
              {"expression": FX_BODY, "context": ctx, "parameters": params})
print(f"[3] fxexpression PATCH: {s}")
assert s == 204, b

# ---------- 4. Invoke & report ----------
s, b, _ = req(ENV + "/api/data/v9.2/lc_calculatelaunchreadinessfx", "POST",
              {"lc_LaunchName": "Q3 Widget Launch"})
print(f"[4] Invoke: {s}")
print(json.dumps(json.loads(b), indent=2))
