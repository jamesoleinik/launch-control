"""Create a test launch record to trigger prompt column generation."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient
import time

load_env()
with DataverseClient(os.environ["DATAVERSE_URL"].rstrip("/"), get_credential()) as client:
    print("Creating test launch...")
    launch_id = client.records.create("lc_launch", {
        "lc_name": "Test Prompt Column Launch",
        "lc_targetdate": "2026-12-01",
        "lc_description": "Testing prompt column generation with a fresh record.",
        "lc_launchstatus": 10600001,  # Planning
    })
    print("Created: %s" % launch_id)

    # Create a milestone linked to it
    ms_id = client.records.create("lc_milestone", {
        "lc_name": "Test Milestone",
        "lc_duedate": "2026-11-15",
        "lc_milestonestatus": 10600014,  # Blocked
        "lc_LaunchId@odata.bind": "/lc_launchs(%s)" % launch_id,
    })
    print("Created milestone: %s (Blocked)" % ms_id)

    print("\nWaiting 15 seconds for prompt column to process...")
    time.sleep(15)

    # Check the record
    pages = client.records.get("lc_launch", record_id=launch_id)
    for page in pages:
        for r in page:
            print("\n=== Test Launch Result ===")
            for k, v in sorted(r.items()):
                if "risk" in k.lower() or "prompt" in k.lower() or "summary" in k.lower():
                    print("  %s: %s" % (k, v))

    # Clean up
    print("\nCleaning up test records...")
    client.records.delete("lc_milestone", ms_id)
    client.records.delete("lc_launch", launch_id)
    print("Done.")
