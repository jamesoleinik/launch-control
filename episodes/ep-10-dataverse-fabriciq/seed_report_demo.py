"""
seed_report_demo.py  --  Ep 10 demo data for the Launch Control 360 report.

Writes a richer, connected demo dataset into Dataverse so the Power BI report
(built over the Fabric Link mirror) tells the cross-source story:

  * lc_statusupdate: a varied RED / AMBER / GREEN mix across ALL launches
    (previously only "Q3 Widget Launch" had any health), each linked to its
    launch so vw_launch_health lights up per launch.
  * lc_vendorwork: vendor work items spread across the other launches (using the
    launch codes in vw_launch_code_map) so vw_launch_vendor_exposure shows every
    launch x vendor, joined to F&O + ProcureIQ risk.

Idempotent: --apply first removes any records this script previously created
(status updates whose title starts with the SEED_TAG, and vendorwork rows on the
seeded launch codes) before re-inserting, so it is safe to re-run. --cleanup
removes them without re-inserting.

After --apply, allow ~60s for Fabric Link replication before refreshing the
Direct Lake model / report.

Usage:
    python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --dry-run
    python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --apply
    python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --cleanup
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import scripts.auth as auth  # noqa: E402

HEALTH_GREEN = 10600601
HEALTH_AMBER = 10600602
HEALTH_RED = 10600603

SEED_TAG = "[LC360] "

# Launch codes seeded by this script (WIDGET-Q3 already exists; not touched).
SEEDED_CODES = ["API-Q2", "WHSE-Q3", "VPORTAL-Q2", "COMPLIANCE-Q3", "PRICING-Q1"]

# Status updates keyed by launch display name -> list of (health, title, summary).
STATUS_UPDATES: dict[str, list[tuple[int, str, str]]] = {
    "Q3 Widget Launch": [
        (HEALTH_RED,   "Contoso tooling defect blocks pilot", "Contoso Supply Co (V0001) shipped defective tooling; pilot line paused pending replacement parts."),
        (HEALTH_AMBER, "Packaging supplier capacity tight", "Fabrikam Media (V0002) at 68% on-time on launch packaging; buffer stock being staged."),
        (HEALTH_GREEN, "Retail channel readiness confirmed", "All flagship retail doors confirmed planogram-ready for the launch date."),
    ],
    "Q2 API Platform Upgrade": [
        (HEALTH_RED,   "Contoso component slip risks API GA", "Contoso Supply Co (V0001) at 61% on-time with 2 open disputes; hardware dependency threatens the GA date."),
        (HEALTH_AMBER, "Load test regressions under review", "p99 latency above target on the new gateway; mitigation in progress."),
        (HEALTH_GREEN, "Security review cleared", "Pen test passed with no criticals; on track."),
    ],
    "Q3 Warehouse Consolidation": [
        (HEALTH_AMBER, "SwiftLogix freight window tight", "SwiftLogix Freight Co. (V0003) 74% on-time; consolidation cutover window is compressed."),
        (HEALTH_AMBER, "Racking install one week behind", "Contractor delay on mezzanine racking; recovery plan being validated."),
        (HEALTH_GREEN, "WMS migration dry run passed", "Full dry run of the warehouse management cutover succeeded."),
    ],
    "Q2 Vendor Portal Cutover": [
        (HEALTH_RED,   "Fabrikam creative assets blocked", "Fabrikam Media (V0002) portal onboarding blocked on SSO federation; launch comms at risk."),
        (HEALTH_GREEN, "Portal UAT sign-off", "Business UAT signed off; ready for pilot."),
        (HEALTH_GREEN, "Data migration reconciled", "Vendor master migration reconciled to source with zero variance."),
    ],
    "Q3 Compliance Reporting": [
        (HEALTH_GREEN, "Controls testing complete", "All SOX-relevant controls tested and passing."),
        (HEALTH_GREEN, "Auditor walkthrough done", "External auditor walkthrough complete; no findings."),
        (HEALTH_AMBER, "One report pending data source", "Regulatory report blocked on a late ERP feed; low risk to date."),
    ],
    "Q1 Pricing Refresh": [
        (HEALTH_GREEN, "Price list published", "New price lists published across all regions."),
        (HEALTH_GREEN, "Channel partners notified", "Partner comms sent; acknowledgements tracking above 90%."),
        (HEALTH_AMBER, "FX rounding edge cases", "Minor rounding discrepancies in two currencies under review."),
    ],
}

# Vendor work items for the other launches: (launch_code, vendor_name, invoiced, committed).
VENDOR_WORK: list[tuple[str, str, float, float]] = [
    ("API-Q2",        "Contoso Supply Co",      45000.0, 60000.0),
    ("API-Q2",        "Fabrikam Media",         12000.0, 15000.0),
    ("WHSE-Q3",       "SwiftLogix Freight Co.", 62000.0, 80000.0),
    ("WHSE-Q3",       "Contoso Supply Co",      21000.0, 25000.0),
    ("VPORTAL-Q2",    "Fabrikam Media",         18000.0, 20000.0),
    ("COMPLIANCE-Q3", "Contoso Supply Co",       9000.0, 10000.0),
    ("PRICING-Q1",    "SwiftLogix Freight Co.", 22000.0, 30000.0),
]

API = "/api/data/v9.2/"


def _req(method: str, base: str, tok: str, path: str, body: dict | None = None) -> dict:
    url = base + API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0", "OData-Version": "4.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _launch_ids(base: str, tok: str) -> dict[str, str]:
    rows = _req("GET", base, tok, "lc_launchs?$select=lc_launchid,lc_name")["value"]
    return {r["lc_name"]: r["lc_launchid"] for r in rows}


def _delete_seeded(base: str, tok: str) -> None:
    # Status updates tagged with SEED_TAG.
    q = ("lc_statusupdates?$select=lc_statusupdateid,lc_title&"
         "$filter=startswith(lc_title,'" + SEED_TAG.strip() + "')")
    for r in _req("GET", base, tok, q).get("value", []):
        _req("DELETE", base, tok, f"lc_statusupdates({r['lc_statusupdateid']})")
    # Vendor work on the seeded launch codes.
    codes = " or ".join(f"lc_launchcode eq '{c}'" for c in SEEDED_CODES)
    q = f"lc_vendorworks?$select=lc_vendorworkid&$filter={urllib.parse.quote(codes)}"
    for r in _req("GET", base, tok, q).get("value", []):
        _req("DELETE", base, tok, f"lc_vendorworks({r['lc_vendorworkid']})")


def _apply(base: str, tok: str) -> None:
    print("Removing any previously seeded records ...")
    _delete_seeded(base, tok)

    launches = _launch_ids(base, tok)
    now = datetime.now(timezone.utc)

    n_su = 0
    for launch_name, updates in STATUS_UPDATES.items():
        lid = launches.get(launch_name)
        for i, (health, title, summary) in enumerate(updates):
            payload = {
                "lc_title": SEED_TAG + title,
                "lc_summary": summary,
                "lc_health": health,
                "lc_postedat": (now - timedelta(days=i)).isoformat(),
            }
            if lid:
                payload["lc_launchid@odata.bind"] = f"/lc_launchs({lid})"
            _req("POST", base, tok, "lc_statusupdates", payload)
            n_su += 1
    print(f"Inserted {n_su} status updates across {len(STATUS_UPDATES)} launches.")

    n_vw = 0
    for code, vendor, inv, com in VENDOR_WORK:
        payload = {
            "lc_vendorname": vendor,
            "lc_launchcode": code,
            "lc_invoicedamount": inv,
            "lc_committedamount": com,
        }
        _req("POST", base, tok, "lc_vendorworks", payload)
        n_vw += 1
    print(f"Inserted {n_vw} vendor work items across {len(SEEDED_CODES)} launch codes.")
    print("\nAllow ~60s for Fabric Link replication, then refresh the model/report.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Ep 10 Launch Control 360 demo data seed.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--cleanup", action="store_true")
    args = ap.parse_args()

    if not (args.apply or args.cleanup or args.dry_run):
        ap.print_help()
        return 1

    auth.load_env("ep-10-dataverse-fabriciq")
    base = os.environ["DATAVERSE_URL"].rstrip("/")

    if args.dry_run:
        total_su = sum(len(v) for v in STATUS_UPDATES.values())
        print(f"[DRY RUN] would seed {total_su} status updates and "
              f"{len(VENDOR_WORK)} vendor work items into {base}.")
        for ln, ups in STATUS_UPDATES.items():
            mix = ", ".join({HEALTH_RED: "RED", HEALTH_AMBER: "AMBER",
                             HEALTH_GREEN: "GREEN"}[h] for h, _, _ in ups)
            print(f"  {ln}: {mix}")
        return 0

    tok = auth.get_token("ep-10-dataverse-fabriciq")
    if args.cleanup:
        print("Deleting seeded records ...")
        _delete_seeded(base, tok)
        print("Done.")
        return 0

    _apply(base, tok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
