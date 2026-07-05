"""Recurring batch job: nightly launch-procurement exposure digest.

This is the body of a scheduled batch job (see
``.github/workflows/nightly-launch-procurement.yml``) that keeps an eye on how
much launch work is outsourced to Finance & Operations vendors and how much of
that spend is still outstanding. It reads the **unified** launch-plus-procurement
model and emits a per-launch rollup:

    engagements | committed | invoiced | outstanding | open POs | risk

Two ways to read the same unified model, selectable so the identical logic runs
locally and in CI:

* ``--via mcp`` (default): read through the **Dataverse MCP server** with the
  ``read_query`` tool. Great for a laptop run; no CLI profile required, just a
  Dataverse token from ``scripts/auth``.
* ``--via cli``: shell out to the **unified Dataverse CLI**
  (``dataverse data query``). This is what the GitHub Actions job uses, where the
  CLI is authenticated with GitHub federated credentials
  (``dataverse auth create --githubFederated``). The CLI is also how the workflow
  monitors F&O batch jobs (``dataverse erp batch list``).

Output goes to stdout as a table; pass ``--out <path.json>`` to also write a JSON
artifact (the workflow uploads it).

Run:
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/batch_launch_sync.py
    python episodes/ep-09-dataverse-fno/batch_launch_sync.py --out digest.json
    python episodes/ep-09-dataverse-fno/batch_launch_sync.py --via cli   # in CI
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
from mcp_client import DataverseMcp  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
# Outstanding-commitment ratio above which a launch's ERP posture is flagged.
RISK_OUTSTANDING_RATIO = 0.5


def _rows_via_mcp():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    mcp = DataverseMcp(url, token)
    mcp.initialize(client_name="batch_launch_sync")
    return mcp.read_query(
        "SELECT lc_launchcode, lc_vendoraccount, lc_ponumber, "
        "lc_committedamount, lc_invoicedamount, lc_status FROM lc_vendorwork"
    )


def _rows_via_cli():
    """Read lc_vendorwork through the unified Dataverse CLI (used in CI)."""
    sql = (
        "SELECT lc_launchcode, lc_vendoraccount, lc_ponumber, "
        "lc_committedamount, lc_invoicedamount, lc_status FROM lc_vendorwork"
    )
    proc = subprocess.run(
        ["npx", "-y", "@microsoft/dataverse@latest", "data", "query",
         "--sql", sql, "--json"],
        capture_output=True, text=True, timeout=300, shell=(os.name == "nt"),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dataverse data query failed: {proc.stderr[-500:]}")
    payload = json.loads(proc.stdout)
    if isinstance(payload, list):
        return payload
    return payload.get("value", [])


def rollup(rows):
    launches = {}
    for r in rows:
        code = r.get("lc_launchcode") or "(unassigned)"
        agg = launches.setdefault(code, {
            "launch": code, "engagements": 0, "committed": 0.0,
            "invoiced": 0.0, "open_pos": 0, "vendors": set(),
        })
        committed = float(r.get("lc_committedamount") or 0)
        invoiced = float(r.get("lc_invoicedamount") or 0)
        agg["engagements"] += 1
        agg["committed"] += committed
        agg["invoiced"] += invoiced
        agg["vendors"].add(r.get("lc_vendoraccount"))
        status = (r.get("lc_status") or "").lower()
        if "open" in status or "pending" in status or invoiced < committed:
            agg["open_pos"] += 1

    out = []
    for agg in launches.values():
        outstanding = agg["committed"] - agg["invoiced"]
        ratio = outstanding / agg["committed"] if agg["committed"] else 0.0
        out.append({
            "launch": agg["launch"],
            "engagements": agg["engagements"],
            "vendors": len([v for v in agg["vendors"] if v]),
            "committed": round(agg["committed"], 2),
            "invoiced": round(agg["invoiced"], 2),
            "outstanding": round(outstanding, 2),
            "open_pos": agg["open_pos"],
            "risk": "AT-RISK" if ratio >= RISK_OUTSTANDING_RATIO else "OK",
        })
    return sorted(out, key=lambda x: x["outstanding"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--via", choices=("mcp", "cli"), default="mcp",
                        help="read the unified model via the Dataverse MCP server "
                             "(default) or the unified Dataverse CLI")
    parser.add_argument("--out", help="also write the digest as JSON to this path")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    rows = _rows_via_cli() if args.via == "cli" else _rows_via_mcp()
    digest = {
        "generated_utc": now.isoformat(),
        "source": args.via,
        "launches": rollup(rows),
    }

    print(f"Launch procurement digest ({now.isoformat()}, via {args.via})\n")
    header = (f"  {'LAUNCH':12}{'ENG':>4}{'VEND':>5}{'COMMITTED':>12}"
              f"{'INVOICED':>11}{'OUTSTANDING':>13}{'OPEN':>5}  RISK")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for lo in digest["launches"]:
        print(f"  {lo['launch']:12}{lo['engagements']:>4}{lo['vendors']:>5}"
              f"{lo['committed']:>12,.0f}{lo['invoiced']:>11,.0f}"
              f"{lo['outstanding']:>13,.0f}{lo['open_pos']:>5}  {lo['risk']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(digest, f, indent=2)
        print(f"\n  wrote {args.out}")

    if not digest["launches"]:
        print("\n[FAIL] no launch procurement data returned")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
