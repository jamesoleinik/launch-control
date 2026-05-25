"""Register the three lc_task server-side rule plugin steps + PreImages.

Pure Web API (no PRT). Idempotent — re-registers steps that already exist by
name. Each step is Pre-Operation, Synchronous, scoped to message=Update,
entity=lc_task.

  Rule                          | rank | filtering                       | PreImage
  ------------------------------+------+---------------------------------+----------
  TaskCompletionGuardRulePlugin |   1  | lc_taskstatus                   | lc_blockerreason
  TaskBlockedRulePlugin         |   2  | lc_blockerreason                | (none)
  TaskUnblockedRulePlugin       |   3  | lc_blockerreason                | lc_taskstatus

Rank ordering matters: CompletionGuard runs first so a caller setting
status=Done while a blocker is still set is rejected before TaskBlockedRule
could silently overwrite Done with Blocked.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from auth import get_token, load_env

ASSEMBLY_NAME = "GitHubIssuesProvider"

# Step definitions. PreImage attributes are the columns the plugin needs to
# read from the row's pre-update state.
STEPS = [
    {
        "name": "lc_task: TaskCompletionGuardRule (Pre-Update)",
        "plugin_typename": "GitHubIssuesProvider.TaskCompletionGuardRulePlugin",
        "rank": 1,
        "filteringattributes": "lc_taskstatus",
        "description": "Refuse to mark lc_task Done while lc_blockerreason is set.",
        "preimage_attributes": "lc_blockerreason,lc_taskstatus",
    },
    {
        "name": "lc_task: TaskBlockedRule (Pre-Update)",
        "plugin_typename": "GitHubIssuesProvider.TaskBlockedRulePlugin",
        "rank": 2,
        "filteringattributes": "lc_blockerreason",
        "description": "Force lc_taskstatus=Blocked when lc_blockerreason is set.",
        "preimage_attributes": None,
    },
    {
        "name": "lc_task: TaskUnblockedRule (Pre-Update)",
        "plugin_typename": "GitHubIssuesProvider.TaskUnblockedRulePlugin",
        "rank": 3,
        "filteringattributes": "lc_blockerreason",
        "description": "Revert lc_taskstatus to InProgress when lc_blockerreason cleared on a Blocked task.",
        "preimage_attributes": "lc_taskstatus,lc_blockerreason",
    },
]


def api(method, path, base, tok, body=None):
    url = f"{base}/api/data/v9.2/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode("utf-8")
            payload = json.loads(txt) if txt else None
            eid = r.headers.get("OData-EntityId", "")
            new_id = eid.split("(")[-1].rstrip(")") if "(" in eid else None
            return r.status, payload, new_id
    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {err_text}") from None


def get_one(path, base, tok):
    code, payload, _ = api("GET", path, base, tok)
    rows = payload.get("value", []) if payload else []
    return rows[0] if rows else None


def main():
    load_env()
    base = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_token()
    print(f"Target: {base}\n")

    # 1) Look up plugin types by name
    flt = urllib.parse.quote(f"name eq '{ASSEMBLY_NAME}'", safe="")
    asm = get_one(f"pluginassemblies?$filter={flt}&$select=pluginassemblyid", base, tok)
    asm_id = asm["pluginassemblyid"]
    print(f"Assembly: {asm_id}")

    flt = urllib.parse.quote(f"_pluginassemblyid_value eq {asm_id}", safe="")
    _, payload, _ = api("GET",
        f"plugintypes?$filter={flt}&$select=plugintypeid,typename", base, tok)
    pt_by_name = {r["typename"]: r["plugintypeid"] for r in payload["value"]}

    # 2) Look up Update SDK message
    msg = get_one(
        "sdkmessages?$filter=" + urllib.parse.quote("name eq 'Update'", safe="") +
        "&$select=sdkmessageid", base, tok)
    update_msg_id = msg["sdkmessageid"]
    print(f"sdkmessage Update: {update_msg_id}")

    # 3) Look up filter for lc_task + Update
    flt = urllib.parse.quote(
        f"primaryobjecttypecode eq 'lc_task' and _sdkmessageid_value eq {update_msg_id}",
        safe="",
    )
    fltrow = get_one(
        f"sdkmessagefilters?$filter={flt}&$select=sdkmessagefilterid", base, tok)
    filter_id = fltrow["sdkmessagefilterid"]
    print(f"sdkmessagefilter lc_task/Update: {filter_id}\n")

    # 4) For each rule: upsert the step, then upsert its PreImage if needed
    for step in STEPS:
        pt_id = pt_by_name.get(step["plugin_typename"])
        if not pt_id:
            raise RuntimeError(
                f"plugintype {step['plugin_typename']} not registered on assembly")

        # Check for existing step by name
        name_q = urllib.parse.quote(f"name eq '{step['name']}'", safe="")
        existing = get_one(
            f"sdkmessageprocessingsteps?$filter={name_q}&$select=sdkmessageprocessingstepid",
            base, tok)

        step_body = {
            "name": step["name"],
            "description": step["description"],
            "mode": 0,            # Synchronous
            "stage": 20,          # Pre-operation
            "rank": step["rank"],
            "supporteddeployment": 0,  # Server only
            "invocationsource": 0,
            "filteringattributes": step["filteringattributes"],
            "asyncautodelete": False,
            "plugintypeid@odata.bind": f"/plugintypes({pt_id})",
            "sdkmessageid@odata.bind": f"/sdkmessages({update_msg_id})",
            "sdkmessagefilterid@odata.bind": f"/sdkmessagefilters({filter_id})",
        }
        if existing:
            step_id = existing["sdkmessageprocessingstepid"]
            # PATCH a slim body (binds can't be changed on PATCH the same way;
            # update behavioral columns only).
            patch_body = {
                "description": step["description"],
                "mode": 0, "stage": 20, "rank": step["rank"],
                "filteringattributes": step["filteringattributes"],
            }
            api("PATCH", f"sdkmessageprocessingsteps({step_id})", base, tok, patch_body)
            print(f"  [step]  PATCH {step['name']} -> {step_id}")
        else:
            _, _, step_id = api("POST", "sdkmessageprocessingsteps", base, tok, step_body)
            print(f"  [step]  POST  {step['name']} -> {step_id}")

        # PreImage
        if step["preimage_attributes"]:
            img_filter = urllib.parse.quote(
                f"_sdkmessageprocessingstepid_value eq {step_id} and name eq 'PreImage'",
                safe="",
            )
            existing_img = get_one(
                f"sdkmessageprocessingstepimages?$filter={img_filter}"
                "&$select=sdkmessageprocessingstepimageid", base, tok)
            img_body = {
                "name": "PreImage",
                "entityalias": "PreImage",
                "imagetype": 0,                 # PreImage
                "messagepropertyname": "Target",
                "attributes": step["preimage_attributes"],
                "sdkmessageprocessingstepid@odata.bind":
                    f"/sdkmessageprocessingsteps({step_id})",
            }
            if existing_img:
                img_id = existing_img["sdkmessageprocessingstepimageid"]
                api("PATCH", f"sdkmessageprocessingstepimages({img_id})",
                    base, tok, {"attributes": step["preimage_attributes"]})
                print(f"  [image] PATCH PreImage on step -> {img_id}")
            else:
                _, _, img_id = api("POST", "sdkmessageprocessingstepimages",
                                   base, tok, img_body)
                print(f"  [image] POST  PreImage on step -> {img_id}")

    print("\nDone. 3 rule steps + 2 PreImages registered.")


if __name__ == "__main__":
    main()
