"""
measure_sync_latency.py  --  Ep 10, Section 2: measure Fabric Link sync latency.

Backfills a batch of historical launch status records into Dataverse, then polls
the Fabric OneLake mirror (via the Lakehouse SQL analytics endpoint) to detect
exactly when each record shows up. For every record it computes:

    latency = (first seen in OneLake) - (write acknowledged by Dataverse)

and reports the distribution (min / median / mean / p95 / max) plus a histogram
image, so you can show, to the second, how fast Dataverse writes replicate into
Fabric.

Each record is tagged in lc_title with a unique token under SYNC_TAG, so the run
is self-correlating and idempotent: --cleanup removes every record this script
has ever written.

Usage (PowerShell):
    $env:LC_ENV = "ep-10-dataverse-fabriciq"; $env:PYTHONIOENCODING = "utf-8"
    python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --dry-run
    python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --apply --count 100
    python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --cleanup

Auth: az login (AzureCliCredential). Requires pyodbc + ODBC Driver 18 and, for
the histogram, matplotlib (falls back to an ASCII chart if it is not installed).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import struct
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import scripts.auth as auth  # noqa: E402

import urllib.request  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.error  # noqa: E402

HEALTH = [10600601, 10600602, 10600603]  # GREEN / AMBER / RED
SYNC_TAG = "[LCSYNC] "
API = "/api/data/v9.2/"
FABRIC_API = "https://api.fabric.microsoft.com/v1"


# --------------------------------------------------------------------------- #
# Dataverse (write side)
# --------------------------------------------------------------------------- #
def _dv_req(method: str, base: str, tok: str, path: str, body: dict | None = None) -> dict:
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


def _write_batch(base: str, tok: str, count: int) -> dict[str, float]:
    """Create `count` tagged status updates; return {token: write_epoch_seconds}."""
    write_times: dict[str, float] = {}
    for i in range(count):
        token = uuid.uuid4().hex[:12]
        payload = {
            "lc_title": f"{SYNC_TAG}{token}",
            "lc_summary": "Sync-latency probe record.",
            "lc_health": HEALTH[i % 3],
            "lc_postedat": datetime.now(timezone.utc).isoformat(),
        }
        _dv_req("POST", base, tok, "lc_statusupdates", payload)
        write_times[token] = time.time()  # Dataverse has acknowledged the create
        if (i + 1) % 10 == 0 or i + 1 == count:
            print(f"  wrote {i + 1}/{count}")
    return write_times


def _cleanup(base: str, tok: str) -> int:
    # Dataverse OData startswith misbehaves on a leading '[', so match on the
    # bracket-free marker instead (the token is unique to this probe script).
    flt = urllib.parse.quote("contains(lc_title,'LCSYNC')")
    q = ("lc_statusupdates?$select=lc_statusupdateid,lc_title&$filter=" + flt)
    n = 0
    for r in _dv_req("GET", base, tok, q).get("value", []):
        _dv_req("DELETE", base, tok, f"lc_statusupdates({r['lc_statusupdateid']})")
        n += 1
    return n


# --------------------------------------------------------------------------- #
# Fabric OneLake mirror (read side)
# --------------------------------------------------------------------------- #
def _fabric_get(path: str) -> dict:
    """GET a Fabric REST resource with an AAD token."""
    tok = auth.get_credential(os.environ.get("LC_ENV")).get_token(
        "https://api.fabric.microsoft.com/.default").token
    req = urllib.request.Request(FABRIC_API + path,
                                 headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _resolve_sql_endpoint() -> tuple[str, str]:
    """Resolve (server, database) for the Lakehouse SQL analytics endpoint at
    runtime from Fabric REST, so no environment identifiers are hardcoded."""
    ws_id = os.environ["FABRIC_WORKSPACE_ID"]
    lh_id = os.environ["FABRIC_LAKEHOUSE_ID"]
    lh = _fabric_get(f"/workspaces/{ws_id}/lakehouses/{lh_id}")
    props = lh.get("properties", {}).get("sqlEndpointProperties", {})
    server = props.get("connectionString")
    if not server:
        raise RuntimeError(
            "SQL endpoint not provisioned yet for this Lakehouse. Open the "
            "Lakehouse in Fabric once to provision the SQL analytics endpoint.")
    database = os.environ.get("FABRIC_LAKEHOUSE_NAME") or lh.get("displayName", "")
    return server, database


def _sql_connect():
    import pyodbc
    server, database = _resolve_sql_endpoint()
    tok = auth.get_credential(os.environ.get("LC_ENV")).get_token(
        "https://database.windows.net/.default").token
    ts = tok.encode("utf-16-le")
    ts = struct.pack("<i", len(ts)) + ts
    cs = (f"Driver={{ODBC Driver 18 for SQL Server}};Server={server};"
          f"Database={database};Encrypt=yes;TrustServerCertificate=no")
    return pyodbc.connect(cs, attrs_before={1256: ts})


def _seen_tokens(cur) -> set[str]:
    # In T-SQL LIKE, '[' opens a character class, so a literal '[LCSYNC]' prefix
    # must be escaped. Use ESCAPE '!' and match the literal '[LCSYNC]' opener.
    cur.execute("SELECT lc_title FROM lc_statusupdate "
                "WHERE lc_title LIKE '![LCSYNC]%' ESCAPE '!'")
    out = set()
    for (title,) in cur.fetchall():
        if title and title.startswith(SYNC_TAG):
            out.add(title[len(SYNC_TAG):])
    return out


def _poll_latencies(write_times: dict[str, float], timeout_s: float,
                    poll_s: float) -> dict[str, float]:
    """Poll the mirror until all tokens appear (or timeout). Returns {token: latency_s}."""
    latencies: dict[str, float] = {}
    pending = set(write_times)
    deadline = time.time() + timeout_s
    print(f"Polling OneLake mirror every {poll_s:g}s (timeout {timeout_s:g}s) ...")
    while pending and time.time() < deadline:
        time.sleep(poll_s)
        now = time.time()
        # Open a FRESH connection each poll. The Fabric SQL analytics endpoint
        # resolves newly replicated Delta commits at connect/metadata-sync time;
        # a long-lived session can stay pinned to a stale snapshot and never see
        # rows that a fresh connection sees immediately.
        try:
            cn = _sql_connect()
            cur = cn.cursor()
            seen = _seen_tokens(cur)
            cn.close()
        except Exception as exc:  # transient endpoint hiccup; retry next poll
            print(f"  (poll error: {exc}; retrying)")
            continue
        newly = pending & seen
        for tok in newly:
            latencies[tok] = now - write_times[tok]
        if newly:
            pending -= newly
            print(f"  +{len(newly)} appeared, {len(pending)} pending "
                  f"(elapsed {int(now - min(write_times.values()))}s)")
    if pending:
        print(f"  timeout: {len(pending)} record(s) never appeared within "
              f"{timeout_s:g}s")
    return latencies


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return float("nan")
    s = sorted(data)
    k = (len(s) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _ascii_hist(latencies: list[float], bins: int = 12, width: int = 48) -> None:
    if not latencies:
        return
    lo, hi = min(latencies), max(latencies)
    span = (hi - lo) or 1.0
    counts = [0] * bins
    for v in latencies:
        idx = min(int((v - lo) / span * bins), bins - 1)
        counts[idx] += 1
    peak = max(counts) or 1
    print("\nSync latency distribution (seconds):")
    for i, c in enumerate(counts):
        left = lo + span * i / bins
        right = lo + span * (i + 1) / bins
        bar = "#" * int(c / peak * width)
        print(f"  {left:6.1f}-{right:6.1f}s | {bar} {c}")


def _summary(latencies: list[float]) -> None:
    n = len(latencies)
    print("\n=== Fabric Link sync latency (Dataverse write -> OneLake) ===")
    print(f"  records measured : {n}")
    if not n:
        return
    print(f"  min              : {min(latencies):.1f}s")
    print(f"  median           : {statistics.median(latencies):.1f}s")
    print(f"  mean             : {statistics.mean(latencies):.1f}s")
    print(f"  p95              : {_percentile(latencies, 0.95):.1f}s")
    print(f"  max              : {max(latencies):.1f}s")


def _save_outputs(latencies: list[float], out_png: Path, out_csv: Path) -> None:
    if not latencies:
        print("\nNo latencies measured (no records detected); skipping CSV/PNG.")
        return
    out_csv.write_text("token_index,latency_seconds\n" +
                       "\n".join(f"{i},{v:.3f}" for i, v in enumerate(latencies)),
                       encoding="utf-8")
    print(f"\nWrote raw latencies: {out_csv}")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(latencies, bins=min(20, max(5, len(latencies) // 5)),
                color="#2E7D9A", edgecolor="white")
        med = statistics.median(latencies)
        p95 = _percentile(latencies, 0.95)
        ax.axvline(med, color="#4E9F3D", linestyle="--", label=f"median {med:.1f}s")
        ax.axvline(p95, color="#D64550", linestyle="--", label=f"p95 {p95:.1f}s")
        ax.set_title("Fabric Link sync latency: Dataverse write to OneLake")
        ax.set_xlabel("Latency (seconds)")
        ax.set_ylabel("Records")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_png, dpi=120)
        print(f"Wrote histogram: {out_png}")
    except ImportError:
        print("(matplotlib not installed; skipping PNG, see ASCII chart above)")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Ep 10 Section 2: Fabric Link sync-latency probe.")
    ap.add_argument("--apply", action="store_true", help="write records and measure latency")
    ap.add_argument("--cleanup", action="store_true", help="delete all probe records")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--timeout", type=float, default=900.0, help="max seconds to poll")
    ap.add_argument("--poll", type=float, default=2.0, help="poll interval seconds")
    ap.add_argument("--out", default=str(Path(__file__).with_name("sync_latency_hist.png")))
    args = ap.parse_args()

    if not (args.apply or args.cleanup or args.dry_run):
        ap.print_help()
        return 1

    auth.load_env(os.environ.get("LC_ENV", "ep-10-dataverse-fabriciq"))
    base = os.environ["DATAVERSE_URL"].rstrip("/")

    if args.dry_run:
        print(f"[DRY RUN] would write {args.count} tagged status updates to {base}, "
              f"poll the Lakehouse SQL analytics endpoint every {args.poll:g}s up to "
              f"{args.timeout:g}s, then emit latency stats + {args.out}.")
        return 0

    tok = auth.get_token(os.environ.get("LC_ENV", "ep-10-dataverse-fabriciq"))

    if args.cleanup:
        print("Deleting probe records ...")
        print(f"Deleted {_cleanup(base, tok)} record(s).")
        return 0

    print(f"Writing {args.count} probe records to Dataverse ...")
    write_times = _write_batch(base, tok, args.count)
    latencies_map = _poll_latencies(write_times, args.timeout, args.poll)
    latencies = list(latencies_map.values())

    _summary(latencies)
    _ascii_hist(latencies)
    out_png = Path(args.out)
    out_csv = out_png.with_suffix(".csv")
    _save_outputs(latencies, out_png, out_csv)

    print("\nTip: re-run with --cleanup to remove the probe records when done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
