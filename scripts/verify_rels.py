"""Verify lookup relationships exist on Launch Control tables."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

load_env()
with DataverseClient(os.environ["DATAVERSE_URL"].rstrip("/"), get_credential()) as client:
    checks = [
        ("lc_milestone", "_lc_launchid_value", "Launch"),
        ("lc_task", "_lc_milestoneid_value", "Milestone"),
        ("lc_task", "_lc_assignedtoid_value", "TeamMember"),
        ("lc_statusupdate", "_lc_launchid_value", "Launch"),
        ("lc_teammember", "_lc_launchid_value", "Launch"),
    ]
    for table, lookup_col, target in checks:
        try:
            pages = client.records.get(table, select=[lookup_col], top=1)
            found = False
            for page in pages:
                for r in page:
                    val = r.get(lookup_col)
                    found = True
                    status = "OK (value: %s)" % val if val else "OK (null - no data linked)"
                    print("%s -> %s: %s" % (table, target, status))
            if not found:
                print("%s -> %s: OK (no records yet)" % (table, target))
        except Exception as e:
            if "select" in str(e).lower() or "not found" in str(e).lower():
                print("%s -> %s: MISSING - lookup column does not exist" % (table, target))
            else:
                print("%s -> %s: ERROR - %s" % (table, target, e))

