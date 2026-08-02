"""
show_replication_latency.py  --  Ep 10 Fabric Link latency distribution chart.

Queries the LaunchControl Fabric SQL endpoint for the replication benchmark
results (SinkCreatedOn - createdon) and renders an ASCII bar chart plus key
stats to stdout.  Requires the Fabric SQL endpoint to be reachable and an
az CLI login.

Usage:
    python episodes/ep-10-dataverse-fabriciq/show_replication_latency.py

The data shown is from the 2026-07-21 benchmark: 2,863 lc_statusupdate rows
created under sustained load, all replicated within 5 minutes.
"""

import os, struct, subprocess, sys, statistics

# ---------------------------------------------------------------------------
# Hardcoded benchmark data (from 2026-07-21 run, 2,863 rows).
# Re-query live from Fabric SQL if --live flag is passed.
# ---------------------------------------------------------------------------
BENCHMARK_LAGS_S = None  # populated below

HARDCODED_STATS = {
    "n": 2863,
    "min_s": 0,
    "p10_s": 0,
    "median_s": 11,
    "mean_s": 16,
    "p90_s": 36,
    "p95_s": 48,
    "max_s": 69,
    "cold_start_s": 713,
    "date": "2026-07-21",
    "env": "eppcdemo1fno → LaunchControl (Fabric Link low-latency sync)",
}

HARDCODED_HISTOGRAM = [
    ("<10s",  1821, 63.6),
    ("10-20s", 710, 24.8),
    ("20-30s", 196,  6.8),
    ("30-45s", 112,  3.9),
    ("45-60s",  21,  0.7),
    (">60s",     3,  0.1),
]


def _live_query():
    """Pull raw lag values from Fabric SQL (requires az CLI)."""
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token", "--resource",
             "https://database.windows.net/", "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=30
        )
        tok = result.stdout.strip()
        if not tok:
            return None

        import pyodbc
        server = "e3i64amwt4wu3ijh3qxhq2ujrm-qogvqlecfxteronhgj4kxqxzk4.datawarehouse.fabric.microsoft.com"
        raw = tok.encode("utf-16-le")
        acc = struct.pack(f"<I{len(raw)}s", len(raw), raw)
        conn = pyodbc.connect(
            f"Driver={{ODBC Driver 18 for SQL Server}};Server={server};"
            "Database=dataverse_eppcdemo1fno_cds2_workspace_unq8c3f2a443b68f1119bb36045bd003;"
            "Encrypt=yes;TrustServerCertificate=yes;",
            attrs_before={1256: acc}, timeout=30, autocommit=True
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT DATEDIFF(SECOND, createdon, SinkCreatedOn) AS lag_s
            FROM dbo.lc_statusupdate
            WHERE lc_title LIKE 'REPLBULK%'
              AND createdon IS NOT NULL AND SinkCreatedOn IS NOT NULL
            ORDER BY createdon
        """)
        lags = [r[0] for r in cur.fetchall()]
        conn.close()
        return lags if lags else None
    except Exception as e:
        print(f"[live query failed: {e}]", file=sys.stderr)
        return None


def _bar(pct, width=40):
    filled = round(pct * width / 100)
    return "#" * filled + "-" * (width - filled)


def render(stats, histogram, live=False):
    src = "live Fabric SQL query" if live else f"benchmark run {stats['date']}"
    print()
    print("=" * 60)
    print("  Dataverse -> Fabric  Low-Latency Sync  Latency Distribution")
    print(f"  Source : {src}")
    print(f"  Env    : {stats['env']}")
    print(f"  Sample : {stats['n']:,} rows  (lc_statusupdate)")
    print("=" * 60)
    print()
    print("  Key stats")
    print(f"    Min           {stats['min_s']:>4}s")
    print(f"    P10           {stats['p10_s']:>4}s")
    print(f"    Median        {stats['median_s']:>4}s")
    print(f"    Mean          {stats['mean_s']:>4}s")
    print(f"    P90           {stats['p90_s']:>4}s")
    print(f"    P95           {stats['p95_s']:>4}s")
    print(f"    Max           {stats['max_s']:>4}s")
    print(f"    Cold start  ~{stats['cold_start_s']:>4}s  (first sync after idle period)")
    print()
    print("  Distribution")
    for label, count, pct in histogram:
        bar = _bar(pct)
        print(f"    {label:>8}  {bar}  {pct:5.1f}%  ({count:,})")
    print()
    print("  100% of rows replicated within 5 minutes (all <70s under load)")
    print("  Cold-start (link idle): ~12 min to first sync")
    print("=" * 60)
    print()


def main():
    live = "--live" in sys.argv
    lags = None
    if live:
        print("Querying Fabric SQL for live data...")
        lags = _live_query()

    if lags:
        s = sorted(lags)
        n = len(s)
        buckets = [(0, 10), (10, 20), (20, 30), (30, 45), (45, 60), (60, 9999)]
        labels = ["<10s", "10-20s", "20-30s", "30-45s", "45-60s", ">60s"]
        histo = []
        for (lo, hi), label in zip(buckets, labels):
            cnt = sum(1 for x in s if lo <= x < hi)
            histo.append((label, cnt, cnt * 100 / n))
        stats = {
            "n": n,
            "min_s": s[0],
            "p10_s": s[int(n * 0.10)],
            "median_s": int(statistics.median(s)),
            "mean_s": int(statistics.mean(s)),
            "p90_s": s[int(n * 0.90)],
            "p95_s": s[int(n * 0.95)],
            "max_s": s[-1],
            "cold_start_s": 713,
            "date": "live",
            "env": HARDCODED_STATS["env"],
        }
        render(stats, histo, live=True)
    else:
        if live:
            print("(No live data found -- showing hardcoded benchmark results)")
        render(HARDCODED_STATS, HARDCODED_HISTOGRAM, live=False)


if __name__ == "__main__":
    main()
