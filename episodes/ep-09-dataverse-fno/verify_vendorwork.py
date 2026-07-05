"""Verify the WIDGET-Q3 vendor-outsourcing model over both Dataverse APIs.

This proves the launch-to-procurement join is queryable two ways:

1. OData Web API (v9.2): the ``lc_vendorwork`` rows resolve their real F&O
   vendor and purchase order through the generated ``mserp_*`` virtual entities
   (the live "better together" join).
2. SQL / TDS endpoint (host,5558): ``lc_vendorwork`` joins to ``lc_task`` and
   ``lc_launch`` and aggregates, using an Azure AD access token. Virtual
   entities are not exposed over TDS, which is exactly why ``lc_vendorwork``
   stores the F&O business keys as its own columns.

Run:
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/verify_vendorwork.py

Requires ``pyodbc`` and an ODBC Driver for SQL Server (17 or 18). The TDS
connection string must set ``TrustServerCertificate=yes`` or Driver 17 fails
with 08S01 at the first execute (it rejects the redirected backend node cert).
"""

import os
import struct
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
LAUNCH_CODE = "WIDGET-Q3"
SQL_COPT_SS_ACCESS_TOKEN = 1256

VENDOR_ES = "mserp_vendvendorv2entities"
PO_ES = "mserp_purchpurchaseorderheaderv2entities"


def verify_odata(url, token):
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def g(q):
        r = requests.get(f"{url}/api/data/v9.2/{q}", headers=h, timeout=90)
        return r.json().get("value", []) if r.status_code == 200 else None

    rows = g(
        "lc_vendorworks?$select=lc_workkey,lc_vendoraccount,lc_ponumber,"
        "lc_committedamount,lc_status&$expand=lc_taskid($select=lc_title)"
        f"&$filter=lc_launchcode eq '{LAUNCH_CODE}'&$orderby=lc_ponumber"
    )
    if rows is None:
        print("[odata] could not read lc_vendorwork")
        return False

    print("== OData: lc_vendorwork -> live F&O virtual vendor + PO ==\n")
    resolved = 0
    for v in rows:
        acct, po = v["lc_vendoraccount"], v["lc_ponumber"]
        task = (v.get("lc_taskid") or {}).get("lc_title")
        vend = g(
            f"{VENDOR_ES}?$filter=mserp_vendoraccountnumber eq '{acct}'"
            "&$select=mserp_vendoraccountnumber,mserp_vendororganizationname"
        )
        poh = g(
            f"{PO_ES}?$filter=mserp_purchaseordernumber eq '{po}'"
            "&$select=mserp_purchaseordernumber,mserp_ordervendoraccountnumber"
        )
        vn = vend[0].get("mserp_vendororganizationname") if vend else None
        pv = poh[0] if poh else None
        ok = bool(vend) and bool(pv) and pv.get("mserp_ordervendoraccountnumber") == acct
        resolved += 1 if ok else 0
        flag = "OK" if ok else "XX"
        print(f"  [{flag}] {task:28} {acct}->{vn or '?':26} {po}")
    print(f"\n  Resolved {resolved}/{len(rows)} engagements against live F&O virtual entities\n")
    return resolved == len(rows) and len(rows) > 0


def verify_sql(url, token):
    try:
        import pyodbc
    except ImportError:
        print("[sql] pyodbc not installed; skipping TDS check (pip install pyodbc)")
        return None

    host = url.replace("https://", "").rstrip("/")
    raw = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(raw)}s", len(raw), raw)
    driver = next(
        (d for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server")
         if d in pyodbc.drivers()), None)
    if not driver:
        print("[sql] no SQL Server ODBC driver found; skipping TDS check")
        return None

    conn_str = (
        f"Driver={{{driver}}};Server={host},5558;Database={host};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    cn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
                        timeout=60, autocommit=True)
    cur = cn.cursor()

    print(f"== SQL / TDS ({driver}): lc_vendorwork -> lc_task -> lc_launch ==\n")
    cur.execute(
        """
        SELECT l.lc_code AS launch, t.lc_title AS task, vw.lc_vendorname AS vendor,
               vw.lc_ponumber AS po, vw.lc_committedamount AS committed,
               vw.lc_invoicedamount AS invoiced, vw.lc_status AS status
        FROM lc_vendorwork vw
        JOIN lc_task t   ON vw.lc_taskid  = t.lc_taskid
        JOIN lc_launch l ON t.lc_launchid = l.lc_launchid
        WHERE l.lc_code = ?
        ORDER BY vw.lc_ponumber
        """,
        LAUNCH_CODE,
    )
    rows = cur.fetchall()
    for r in rows:
        print(f"  {r.launch:10}{r.task:28}{r.vendor:26}{r.po:10}"
              f"{r.committed:>8.0f}{r.invoiced:>8.0f}  {r.status}")

    print("\n  SQL GROUP BY vendor:")
    cur.execute(
        "SELECT lc_vendorname, COUNT(*) c, SUM(lc_committedamount) tot, "
        "SUM(lc_invoicedamount) inv FROM lc_vendorwork "
        "GROUP BY lc_vendorname ORDER BY tot DESC"
    )
    for r in cur.fetchall():
        print(f"    {r.lc_vendorname:26} {r.c} eng  committed={r.tot:>8.0f}  invoiced={r.inv:>8.0f}")
    cn.close()
    print()
    return len(rows) > 0


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    print(f"Dataverse env: {url}\n")

    odata_ok = verify_odata(url, token)
    sql_ok = verify_sql(url, token)

    print("== Result ==")
    print(f"  OData live join : {'PASS' if odata_ok else 'FAIL'}")
    if sql_ok is None:
        print("  SQL / TDS join  : SKIPPED (driver or pyodbc missing)")
    else:
        print(f"  SQL / TDS join  : {'PASS' if sql_ok else 'FAIL'}")

    if not odata_ok or sql_ok is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
