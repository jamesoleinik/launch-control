"""Check the Q3 Widget Launch record including Prompt Column status."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

load_env()
with DataverseClient(os.environ["DATAVERSE_URL"].rstrip("/"), get_credential()) as client:
    print("=== Q3 Widget Launch ===")
    pages = client.records.get(
        "lc_launch",
        filter="lc_name eq 'Q3 Widget Launch'",
        top=1,
    )
    for page in pages:
        for r in page:
            print("Name: %s" % r.get("lc_name"))
            print("Status: %s" % r.get("lc_launchstatus"))
            print("Target Date: %s" % r.get("lc_targetdate"))
            # Print all keys to find prompt column name
            prompt_keys = [k for k in r.keys() if "risk" in k.lower() or "prompt" in k.lower() or "summary" in k.lower()]
            if prompt_keys:
                for pk in prompt_keys:
                    print("%s: %s" % (pk, r.get(pk)))
            else:
                print("\nAll columns returned:")
                for k, v in sorted(r.items()):
                    if v is not None and not k.startswith("_") and not k.endswith("_value"):
                        print("  %s: %s" % (k, str(v)[:120]))

    print("\n=== Related Milestones ===")
    pages = client.records.get(
        "lc_milestone",
        select=["lc_name", "lc_milestonestatus", "lc_duedate"],
        filter="lc_name ne null",
    )
    for page in pages:
        for r in page:
            status_map = {"10600010": "Not Started", "10600011": "In Progress",
                         "10600012": "Complete", "10600013": "At Risk", "10600014": "Blocked"}
            s = str(r.get("lc_milestonestatus", ""))
            print("  %s - %s (due: %s)" % (r.get("lc_name"), status_map.get(s, s), r.get("lc_duedate", "?")))

    print("\n=== Blocked Tasks ===")
    pages = client.records.get(
        "lc_task",
        select=["lc_title", "lc_taskstatus", "lc_isblocked", "lc_blockerreason"],
        filter="lc_isblocked eq true",
    )
    for page in pages:
        for r in page:
            print("  %s - %s" % (r.get("lc_title"), r.get("lc_blockerreason", "no reason")))
