"""Episode 9, Act 2 signal producer: emit vendor-invoice reconciliation signals.

This is the **producer** half of the event-driven Act 2. It plays the exact role the
recurring Finance & Operations batch plays in production (native X++ SysOperation
class, see ``fno-batch/`` -- authored and deployed in Visual Studio via the unified
developer experience; the CLI ERP build path is still flighted off, so the X++ is
documented but not run on camera). The producer's only job is to **detect
under-invoiced engagements and drop one ``lc_reconciliation`` row per gap**. It does
not reconcile anything: the reconciliation reasoning lives in the
``ep09-vendor-invoice-reconciliation`` Business Skill that the asynchronous Copilot
Studio agent pulls in when the row-add trigger fires.

  producer (this script / the F&O X++ batch)  -- writes -->  lc_reconciliation (Open)
                                                                     |
                                                          row-add trigger fires
                                                                     v
  consumer (async agent + Business Skill)  -- reads F&O, drafts action, marks reconciled

For the demo recording we usually write **one** signal by hand
(``--po PO-10502``) so a single row-add cleanly wakes the agent on camera. The full
sweep (all gaps) and the production F&O batch + deploy steps are documented in the
README; the sweep is what a schedule would run.

Steps:
  1. Read the unified model through the **Dataverse MCP server** and find every
     vendor engagement under-invoiced against its committed amount.
  2. For each gap (or the single ``--po`` you name), write one ``lc_reconciliation``
     row (status ``Open``) back through the **Dataverse MCP server**
     (``create_record``), linked to both the launch (``lc_launchid``) and the source
     engagement (``lc_vendorworkid``).

Idempotent: a fresh ``Open`` signal is written only when one does not already exist
for that engagement, so the producer is safe to re-run on its schedule.

Run:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    # demo: emit exactly one signal to trigger the agent on camera
    python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py --po PO-10502
    # preview the full sweep without writing
    python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py --dry-run
    # full sweep (what the recurring batch would do)
    python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
from mcp_client import DataverseMcp  # noqa: E402
from reconciliation_model import ensure_reconciliation_table  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
HERE = os.path.dirname(os.path.abspath(__file__))


def _launch_index(mcp):
    """Map launch code -> launch id, for the lc_launchid lookup."""
    rows = mcp.read_query("SELECT lc_launchid, lc_code FROM lc_launch")
    return {r["lc_code"]: r["lc_launchid"] for r in rows if r.get("lc_code")}


def _open_signal_keys(mcp):
    """Engagement keys that already have an Open reconciliation signal."""
    rows = mcp.read_query(
        "SELECT lc_signalkey FROM lc_reconciliation WHERE lc_status = 'Open'"
    )
    return {r["lc_signalkey"] for r in rows if r.get("lc_signalkey")}


def find_gaps(mcp, min_gap):
    """Return the under-invoiced engagements from the unified model."""
    rows = mcp.read_query(
        "SELECT lc_vendorworkid, lc_workkey, lc_launchcode, lc_tasktitle, "
        "lc_vendoraccount, lc_vendorname, lc_ponumber, lc_committedamount, "
        "lc_invoicedamount, lc_status FROM lc_vendorwork"
    )
    gaps = []
    for r in rows:
        committed = float(r.get("lc_committedamount") or 0)
        invoiced = float(r.get("lc_invoicedamount") or 0)
        gap = round(committed - invoiced, 2)
        if gap >= min_gap:
            r["_gap"] = gap
            gaps.append(r)
    return sorted(gaps, key=lambda x: x["_gap"], reverse=True)


def write_signal(mcp, row, launch_id):
    """Create one Open lc_reconciliation row through the Dataverse MCP server."""
    committed = float(row.get("lc_committedamount") or 0)
    invoiced = float(row.get("lc_invoicedamount") or 0)
    item = {
        "lc_name": f"Reconcile {row['lc_ponumber']} ({row.get('lc_vendorname') or row['lc_vendoraccount']})",
        "lc_signalkey": row["lc_workkey"],
        "lc_launchcode": row.get("lc_launchcode"),
        "lc_vendoraccount": row.get("lc_vendoraccount"),
        "lc_vendorname": row.get("lc_vendorname"),
        "lc_ponumber": row.get("lc_ponumber"),
        "lc_committedamount": committed,
        "lc_invoicedamount": invoiced,
        "lc_gapamount": row["_gap"],
        "lc_status": "Open",
        "lc_vendorworkid": {
            "relatedTable": "lc_vendorwork",
            "recordId": row["lc_vendorworkid"],
        },
    }
    if launch_id:
        item["lc_launchid"] = {"relatedTable": "lc_launch", "recordId": launch_id}
    return mcp.create_record("lc_reconciliation", item)


def kick_fno_batch():
    """Best-effort: submit the real F&O DMF export as a native batch job."""
    print("\n== kicking native F&O DMF batch (fno_batch_export --run) ==")
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fno_batch_export.py"), "--run"],
        capture_output=True, text=True, timeout=900,
    )
    tail = (proc.stdout or "")[-800:]
    print(tail if tail.strip() else "(no output)")
    if proc.returncode != 0:
        print(f"[warn] F&O batch kick returned {proc.returncode}: {proc.stderr[-300:]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--po", metavar="PONUMBER",
                    help="emit a signal for only this PO (the one-row demo trigger)")
    ap.add_argument("--min-gap", type=float, default=0.01,
                    help="minimum committed-minus-invoiced gap to flag (default 0.01)")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute and print gaps; do not write any signal")
    ap.add_argument("--kick-fno-batch", action="store_true",
                    help="also submit the real F&O DMF export batch (cosmetic)")
    args = ap.parse_args()

    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)

    # Ensure the trigger table exists (safe/idempotent) before writing to it.
    if not args.dry_run:
        client = DataverseClient(url, auth.get_credential(EPISODE))
        ensure_reconciliation_table(client)

    mcp = DataverseMcp(url, token)
    mcp.initialize(client_name="emit_reconciliation_signals")

    launches = _launch_index(mcp)
    already_open = set() if args.dry_run else _open_signal_keys(mcp)
    gaps = find_gaps(mcp, args.min_gap)
    if args.po:
        want = args.po.strip().upper()
        gaps = [g for g in gaps if (g.get("lc_ponumber") or "").upper() == want]
        if not gaps:
            print(f"[FAIL] no under-invoiced engagement found for PO {args.po}")
            raise SystemExit(1)

    scope = f"PO {args.po}" if args.po else "full sweep"
    print(f"\nReconciliation signal producer (via Dataverse MCP) -- {url}")
    print(f"  scope: {scope}  |  under-invoiced engagements: {len(gaps)}  "
          f"(min gap {args.min_gap})\n")
    header = f"  {'PO':10}{'VENDOR':26}{'COMMITTED':>11}{'INVOICED':>11}{'GAP':>11}  ACTION"
    print(header)
    print("  " + "-" * (len(header) - 2))

    written = 0
    for g in gaps:
        vendor = (g.get("lc_vendorname") or g.get("lc_vendoraccount") or "")[:24]
        launch_id = launches.get(g.get("lc_launchcode"))
        if args.dry_run:
            action = "would write"
        elif g["lc_workkey"] in already_open:
            action = "skip (open signal exists)"
        else:
            write_signal(mcp, g, launch_id)
            written += 1
            action = "SIGNAL WRITTEN"
        print(f"  {g['lc_ponumber']:10}{vendor:26}"
              f"{float(g.get('lc_committedamount') or 0):>11,.0f}"
              f"{float(g.get('lc_invoicedamount') or 0):>11,.0f}"
              f"{g['_gap']:>11,.0f}  {action}")

    print(f"\n  signals written: {written}"
          + ("  (dry run)" if args.dry_run else ""))

    if args.kick_fno_batch:
        kick_fno_batch()

    if not gaps:
        print("\n[FAIL] no engagements read from lc_vendorwork")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
