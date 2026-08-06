"""
setup_powerbi_report.py  --  Ep 10 Power BI + Fabric consumption layer.

The Power BI Direct Lake semantic model and the report used to sit only in the
Fabric portal by hand. This script builds the semantic layer (the SQL views) AND
publishes the Direct Lake semantic model programmatically via the Fabric REST
API. This script:
  1. Prints the report + Fabric build steps (--instructions).
  2. Prints the semantic-layer SQL (--print-views).
  3. Applies semantic_views.sql to the Lakehouse SQL analytics endpoint
     (--apply-views), idempotent (every view is CREATE OR ALTER).
  4. Publishes the Direct Lake semantic model over the views (--create-model),
     idempotent (updateDefinition when a model of the same name exists).
  5. Publishes a 4-page report bound to that model (--create-report), also
     idempotent.
  6. Lists the Power BI semantic models / reports in the workspace (--verify).

This path needs NO Fabric Data Agent (which is capacity-gated). Power BI Direct
Lake and the Fabric data plugin both run on trial capacity.

Usage:
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --instructions
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --print-views
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views --dry-run
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model --dry-run
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-report
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --verify

Prerequisites for --apply-views:
    pip install pyodbc azure-identity   (plus the ODBC Driver 18 for SQL Server)
    If pyodbc is unavailable, paste semantic_views.sql into the Fabric SQL query
    editor over the LaunchControl Lakehouse SQL endpoint instead.

Auth:
    Uses AzureCliCredential (az login).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env, get_credential  # noqa: E402

FABRIC_API = "https://api.fabric.microsoft.com/v1"
VIEWS_FILE = Path(__file__).with_name("semantic_views.sql")
SPEC_FILE = Path(__file__).with_name("powerbi_report_spec.md")

MODEL_NAME = "Launch Control 360"
REPORT_NAME = "Launch Control 360"

# The semantic-layer views the Direct Lake model binds to (in apply order).
MODEL_VIEWS = [
    "vw_launch_health",
    "vw_launch_scorecard",
    "vw_vendor_360",
    "vw_launch_vendor_exposure",
    "vw_vendor_enrichment",
    "vw_vendor_risk",
    "vw_red_status_feed",
    "vw_watchlist_vendors",
]


def _fabric_token() -> str:
    return get_credential().get_token("https://api.fabric.microsoft.com/.default").token


def _sql_token() -> bytes:
    """AAD access token packed for the ODBC SQL_COPT_SS_ACCESS_TOKEN attribute."""
    raw = get_credential().get_token("https://database.windows.net/.default").token
    enc = raw.encode("utf-16-le")
    return struct.pack("<i", len(enc)) + enc


def _api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{FABRIC_API}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _api_post(path: str, token: str, body: dict) -> tuple[int, dict, bytes]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{FABRIC_API}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _poll_lro(location: str, token: str) -> tuple[int, bytes]:
    """Poll a Fabric long-running-operation URL until it stops returning 202."""
    for _ in range(60):
        req = urllib.request.Request(location, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status == 202:
                time.sleep(int(dict(r.headers).get("Retry-After", "3") or "3"))
                continue
            return r.status, r.read()
    return 408, b"LRO polling timed out"


def _sql_connection():
    """Open a pyodbc connection to the Lakehouse SQL analytics endpoint (AAD token)."""
    import pyodbc

    server = _resolve_sql_endpoint(_fabric_token())
    database = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={server};Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    return pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _sql_token()}), server, database


def _map_sql_type(sql_type: str, col_name: str) -> tuple[str, str]:
    """Map an INFORMATION_SCHEMA data type to a (TMSL dataType, summarizeBy)."""
    t = sql_type.lower()
    if t in ("varchar", "nvarchar", "char", "nchar", "text", "ntext", "uniqueidentifier"):
        return "string", "none"
    if t in ("bigint", "int", "smallint", "tinyint"):
        summ = "none" if re.search(r"pct|score|rating|id$", col_name.lower()) else "sum"
        return "int64", summ
    if t in ("decimal", "numeric", "money", "smallmoney"):
        return "decimal", "none" if "pct" in col_name.lower() else "sum"
    if t in ("float", "real"):
        return "double", "none" if re.search(r"pct|score", col_name.lower()) else "sum"
    if t == "bit":
        return "boolean", "none"
    if t in ("date", "datetime", "datetime2", "smalldatetime", "datetimeoffset", "time"):
        return "dateTime", "none"
    return "string", "none"


def _resolve_sql_endpoint(token: str) -> str:
    """Return the Lakehouse SQL analytics endpoint connection string (server)."""
    ws_id, lh_id = os.environ["FABRIC_WORKSPACE_ID"], os.environ["FABRIC_LAKEHOUSE_ID"]
    lh = _api_get(f"/workspaces/{ws_id}/lakehouses/{lh_id}", token)
    props = lh.get("properties", {}).get("sqlEndpointProperties", {})
    server = props.get("connectionString")
    if not server:
        raise RuntimeError(
            "SQL endpoint not provisioned yet for this Lakehouse. Open the "
            "Lakehouse in Fabric once to provision the SQL analytics endpoint."
        )
    return server


def _split_batches(sql_text: str) -> list[str]:
    batches, current = [], []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
        else:
            current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        batches.append(tail)
    # Keep only executable batches (skip the comment-only header block).
    return [b for b in batches if re.search(r"CREATE OR ALTER", b, re.IGNORECASE)]


def cmd_print_views() -> int:
    print(VIEWS_FILE.read_text(encoding="utf-8"))
    return 0


def cmd_instructions() -> int:
    print(SPEC_FILE.read_text(encoding="utf-8"))
    return 0


def cmd_apply_views(dry_run: bool) -> int:
    load_env()
    batches = _split_batches(VIEWS_FILE.read_text(encoding="utf-8"))
    view_names = re.findall(r"CREATE OR ALTER VIEW\s+(\w+)",
                            VIEWS_FILE.read_text(encoding="utf-8"), re.IGNORECASE)
    print(f"Semantic views to apply ({len(view_names)}): {', '.join(view_names)}")
    if dry_run:
        for i, b in enumerate(batches, 1):
            print(f"\n--- batch {i} ---\n{b[:200]}{'...' if len(b) > 200 else ''}")
        print("\n[DRY RUN] no statements executed.")
        return 0
    try:
        import pyodbc
    except ImportError:
        print("[ERR] pyodbc not installed. Paste semantic_views.sql into the "
              "Fabric SQL query editor instead, or `pip install pyodbc`.")
        return 2

    server = _resolve_sql_endpoint(_fabric_token())
    database = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={server};Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    print(f"Connecting to SQL endpoint: {server} / {database}")
    conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _sql_token()})
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        try:
            cur.execute(batch)
            conn.commit()
            print(f"  [OK] batch {i}/{len(batches)} applied")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR] batch {i}: {e}")
            return 1
    print("All semantic views applied.")
    return 0


def _build_model_bim(server: str, database: str, tables_meta: dict[str, list[tuple[str, str]]]) -> dict:
    """Build a Direct Lake TMSL (model.bim) document over the semantic views."""
    tables = []
    for view, cols in tables_meta.items():
        tmsl_cols = []
        for name, sql_type in cols:
            data_type, summarize_by = _map_sql_type(sql_type, name)
            tmsl_cols.append({
                "name": name,
                "dataType": data_type,
                "sourceColumn": name,
                "summarizeBy": summarize_by,
                "lineageTag": str(uuid.uuid4()),
            })
        tables.append({
            "name": view,
            "lineageTag": str(uuid.uuid4()),
            "columns": tmsl_cols,
            "partitions": [{
                "name": view,
                "mode": "directLake",
                "source": {
                    "type": "entity",
                    "entityName": view,
                    "expressionSource": "DatabaseQuery",
                    "schemaName": "dbo",
                },
            }],
        })

    m_expr = (
        "let\n"
        f'    database = Sql.Database("{server}", "{database}")\n'
        "in\n"
        "    database"
    )

    # Relationships that make the sources visibly come together (many -> one).
    # Dimensions: vw_vendor_360 (vendor), vw_launch_health (launch).
    def _rel(from_table, from_col, to_table, to_col):
        return {
            "name": str(uuid.uuid4()),
            "fromTable": from_table,
            "fromColumn": from_col,
            "toTable": to_table,
            "toColumn": to_col,
            "crossFilteringBehavior": "oneDirection",
        }

    present = set(tables_meta)
    wanted = [
        ("vw_launch_vendor_exposure", "vendor_name", "vw_vendor_360", "vendor_name"),
        ("vw_launch_vendor_exposure", "launch_name", "vw_launch_health", "launch_name"),
        ("vw_red_status_feed", "launch_name", "vw_launch_health", "launch_name"),
        ("vw_watchlist_vendors", "accountnum", "vw_vendor_360", "accountnum"),
    ]
    relationships = []
    for ft, fc, tt, tc in wanted:
        fcols = {c for c, _ in tables_meta.get(ft, [])}
        tcols = {c for c, _ in tables_meta.get(tt, [])}
        if ft in present and tt in present and fc in fcols and tc in tcols:
            relationships.append(_rel(ft, fc, tt, tc))

    return {
        "name": MODEL_NAME,
        "compatibilityLevel": 1604,
        "model": {
            "culture": "en-US",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "expressions": [{
                "name": "DatabaseQuery",
                "kind": "m",
                "expression": m_expr,
                "lineageTag": str(uuid.uuid4()),
                "annotations": [{"name": "PBI_IncludeFutureArtifacts", "value": "False"}],
            }],
            "tables": tables,
            "relationships": relationships,
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps(["DatabaseQuery"])},
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            ],
        },
    }


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def cmd_create_model(dry_run: bool) -> int:
    load_env()
    try:
        import pyodbc  # noqa: F401
    except ImportError:
        print("[ERR] pyodbc not installed. `pip install pyodbc` (plus ODBC Driver 18).")
        return 2

    # Introspect the live view columns so the model matches the applied views.
    conn, server, database = _sql_connection()
    cur = conn.cursor()
    tables_meta: dict[str, list[tuple[str, str]]] = {}
    for view in MODEL_VIEWS:
        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", view)
        cols = [(r[0], r[1]) for r in cur.fetchall()]
        if not cols:
            print(f"[ERR] view '{view}' not found. Run --apply-views first.")
            return 1
        tables_meta[view] = cols
    conn.close()

    model_bim = _build_model_bim(server, database, tables_meta)
    pbism = {"version": "4.0", "settings": {}}

    total_cols = sum(len(c) for c in tables_meta.values())
    print(f"Semantic model '{MODEL_NAME}': {len(tables_meta)} tables, {total_cols} columns "
          f"(Direct Lake over {database}).")

    if dry_run:
        print(json.dumps(model_bim, indent=2))
        print("\n[DRY RUN] model not published.")
        return 0

    parts = [
        {"path": "model.bim", "payload": _b64(json.dumps(model_bim)), "payloadType": "InlineBase64"},
        {"path": "definition.pbism", "payload": _b64(json.dumps(pbism)), "payloadType": "InlineBase64"},
    ]

    token = _fabric_token()
    ws_id = os.environ["FABRIC_WORKSPACE_ID"]

    # Idempotent: update the definition if a model of this name already exists.
    existing = _api_get(f"/workspaces/{ws_id}/semanticModels", token).get("value", [])
    match = next((it for it in existing if it.get("displayName") == MODEL_NAME), None)

    if match:
        model_id = match["id"]
        print(f"Updating existing semantic model definition [{model_id}] ...")
        status, headers, payload = _api_post(
            f"/workspaces/{ws_id}/semanticModels/{model_id}/updateDefinition",
            token, {"definition": {"parts": parts}})
    else:
        print("Creating new semantic model ...")
        status, headers, payload = _api_post(
            f"/workspaces/{ws_id}/semanticModels",
            token, {"displayName": MODEL_NAME, "definition": {"parts": parts}})

    if status == 202 and headers.get("Location"):
        print("  operation accepted, polling ...")
        status, payload = _poll_lro(headers["Location"], token)

    if status in (200, 201):
        try:
            info = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            info = {}
        model_id = info.get("id", match["id"] if match else "(see --verify)")
        print(f"[OK] semantic model published: {MODEL_NAME} [{model_id}]")
        print("Next: enable the Fabric data plugin in Copilot pointed at this "
              "model (UI toggle, the only non-scriptable step), then build the report "
              "with --instructions.")
        return 0

    print(f"[ERR] publish failed (HTTP {status}): {payload.decode('utf-8', 'replace')[:800]}")
    return 1


def _matrix(entity, row_cols, value_specs, x, y, w, h) -> dict:
    """A pivotTable (matrix) grouping row_cols with aggregated value_specs=(prop, fn)."""
    src = "q"
    selects, row_proj, val_proj = [], [], []
    for c in row_cols:
        selects.append({**_col_ref(src, c), "Name": f"{entity}.{c}"})
        row_proj.append({"queryRef": f"{entity}.{c}"})
    for prop, fn in value_specs:
        name = _fn_name(entity, prop, fn)
        selects.append({**_agg_ref(src, prop, fn), "Name": name})
        val_proj.append({"queryRef": name})
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "pivotTable",
            "projections": {"Rows": row_proj, "Values": val_proj},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": src, "Entity": entity, "Type": 0}],
                "Select": selects,
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _textbox(text, x, y, w, h) -> dict:
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": text}]}]}}]},
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _slicer(entity, field, x, y, w, h) -> dict:
    """A single-column slicer, used to filter a page to one vendor."""
    src = "q"
    name = f"{entity}.{field}"
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "slicer",
            "projections": {"Values": [{"queryRef": name}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": src, "Entity": entity, "Type": 0}],
                "Select": [{**_col_ref(src, field), "Name": name}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


_FN = {0: "Sum", 1: "Avg", 2: "Min", 3: "Max", 4: "Count", 5: "CountNonNull"}


def _fn_name(entity: str, prop: str, fn: int) -> str:
    return f"{_FN.get(fn, 'Sum')}({entity}.{prop})"


def _col_ref(src: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": prop}}


def _agg_ref(src: str, prop: str, fn: int = 0) -> dict:
    return {"Aggregation": {"Expression": _col_ref(src, prop), "Function": fn}}


def _container(x, y, w, h, config: dict) -> dict:
    return {"x": x, "y": y, "z": 0, "width": w, "height": h,
            "config": json.dumps(config), "filters": "[]"}


def _card(entity, prop, x, y, w, h, fn=0) -> dict:
    src = "q"
    name = _fn_name(entity, prop, fn)
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "card",
            "projections": {"Values": [{"queryRef": name}]},
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": src, "Entity": entity, "Type": 0}],
                "Select": [{**_agg_ref(src, prop, fn), "Name": name}],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _bar(entity, category, value, x, y, w, h, fn=1) -> dict:
    src = "q"
    valname = _fn_name(entity, value, fn)
    catname = f"{entity}.{category}"
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "clusteredBarChart",
            "projections": {
                "Category": [{"queryRef": catname}],
                "Y": [{"queryRef": valname}],
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": src, "Entity": entity, "Type": 0}],
                "Select": [
                    {**_col_ref(src, category), "Name": catname},
                    {**_agg_ref(src, value, fn), "Name": valname},
                ],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _stacked_bar(entity, category, values, colors, x, y, w, h) -> dict:
    """Horizontal stacked bar: one bar per category with multiple summed measures.

    Used for the RAG (red/amber/green) health mix per launch, with fixed colors.
    """
    src = "q"
    catname = f"{entity}.{category}"
    selects = [{**_col_ref(src, category), "Name": catname}]
    y_proj, data_points = [], []
    for val, color in zip(values, colors):
        vn = _fn_name(entity, val, 0)
        selects.append({**_agg_ref(src, val, 0), "Name": vn})
        y_proj.append({"queryRef": vn})
        data_points.append({
            "selector": {"metadata": vn},
            "properties": {"fill": {"solid": {"color": {"expr": {
                "Literal": {"Value": f"'{color}'"}}}}}},
        })
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "barChart",
            "projections": {
                "Category": [{"queryRef": catname}],
                "Y": y_proj,
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": src, "Entity": entity, "Type": 0}],
                "Select": selects,
            },
            "objects": {"dataPoint": data_points},
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _table(entity, cols, x, y, w, h, order_by=None, order_desc=True) -> dict:
    src = "q"
    selects, projections = [], []
    for c in cols:
        selects.append({**_col_ref(src, c), "Name": f"{entity}.{c}"})
        projections.append({"queryRef": f"{entity}.{c}"})
    proto = {
        "Version": 2,
        "From": [{"Name": src, "Entity": entity, "Type": 0}],
        "Select": selects,
    }
    if order_by:
        proto["OrderBy"] = [{
            "Direction": 2 if order_desc else 1,
            "Expression": _col_ref(src, order_by),
        }]
    cfg = {
        "name": str(uuid.uuid4()),
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {"Values": projections},
            "prototypeQuery": proto,
            "drillFilterOtherVisuals": True,
        },
    }
    return _container(x, y, w, h, cfg)


def _section(display_name: str, containers: list[dict]) -> dict:
    return {
        "name": str(uuid.uuid4()),
        "displayName": display_name,
        "displayOption": 1,
        "width": 1280,
        "height": 720,
        "config": "{}",
        "filters": "[]",
        "visualContainers": containers,
    }


def _build_report_json() -> dict:
    """The 'Launch Control 360' report: 3 focused pages over the model.

    Page 1 (Launch 360): every launch, ranked by risk, with the next action.
    Page 2 (Vendor List): the whole vendor roster plus the blind-spot vendors.
    Page 3 (Vendor 360): a single-vendor deep dive, driven by a vendor slicer.
    """
    sections = [
        _section("Launch 360", [
            _textbox("Launches ranked worst-first. Each row says what is wrong, "
                     "who is driving it, how much is exposed, and the next action. "
                     "Start at the top.", 20, 12, 1240, 44),
            _card("vw_launch_scorecard", "is_red", 20, 66, 290, 110, fn=0),
            _card("vw_launch_scorecard", "red_exposure_usd", 320, 66, 290, 110, fn=0),
            _card("vw_launch_scorecard", "is_at_risk", 620, 66, 290, 110, fn=0),
            _card("vw_launch_scorecard", "open_red_updates", 920, 66, 290, 110, fn=0),
            _table("vw_launch_scorecard",
                   ["launch_name", "risk_band", "current_health", "top_risk_vendor",
                    "top_vendor_market_risk", "vendor_exposure_usd", "launch_owner",
                    "recommended_action", "risk_score"],
                   20, 190, 1240, 300, order_by="risk_score", order_desc=True),
            _stacked_bar("vw_launch_health", "launch_name",
                         ["red_count", "amber_count", "green_count"],
                         ["#D64550", "#E8A33D", "#4E9F3D"],
                         20, 500, 620, 196),
            _bar("vw_launch_scorecard", "launch_name", "risk_score",
                 660, 500, 600, 196, fn=0),
        ]),
        _section("Vendor List", [
            _textbox("Every vendor across the portfolio: internal delivery "
                     "performance, ProcureIQ market risk, and the F&O open-invoice "
                     "ledger in one row. The lower table is the blind spot: risk "
                     "vendors with no F&O master record.", 20, 12, 1240, 44),
            _card("vw_vendor_360", "open_balance_usd", 20, 66, 290, 110, fn=0),
            _card("vw_vendor_360", "overdue_count", 320, 66, 290, 110, fn=0),
            _card("vw_vendor_360", "financial_health_score", 620, 66, 290, 110, fn=1),
            _table("vw_vendor_360",
                   ["vendor_name", "category", "on_time_pct", "internal_risk_tier",
                    "market_risk_tier", "credit_rating", "financial_health_score",
                    "open_balance_usd", "overdue_count"],
                   20, 190, 1240, 320),
            _textbox("Blind spots: ProcureIQ risk vendors with no F&O master record.",
                     20, 520, 1240, 30),
            _table("vw_watchlist_vendors",
                   ["accountnum", "vendor_name", "credit_rating",
                    "financial_health_score", "market_risk_tier"],
                   20, 552, 1240, 144),
        ]),
        _section("Vendor 360", [
            _textbox("Single-vendor deep dive. Pick a vendor in the slicer to focus "
                     "the whole page on that vendor.", 20, 12, 980, 44),
            _slicer("vw_vendor_360", "vendor_name", 20, 66, 280, 620),
            _card("vw_vendor_360", "financial_health_score", 320, 66, 220, 110, fn=1),
            _card("vw_vendor_360", "on_time_pct", 560, 66, 220, 110, fn=1),
            _card("vw_vendor_360", "open_balance_usd", 800, 66, 210, 110, fn=0),
            _card("vw_vendor_360", "overdue_count", 1030, 66, 210, 110, fn=0),
            _table("vw_vendor_360",
                   ["vendor_name", "category", "internal_risk_tier",
                    "market_risk_tier", "credit_rating", "financial_health_score",
                    "erp_credit_limit", "open_balance_usd"],
                   320, 190, 920, 150),
            _textbox("Launches exposed to this vendor:", 320, 356, 920, 30),
            _table("vw_launch_vendor_exposure",
                   ["launch_name", "dataverse_invoiced_amount",
                    "dataverse_committed_amount", "internal_risk_tier",
                    "market_risk_tier"],
                   320, 388, 920, 298),
        ]),
    ]
    return {
        "config": json.dumps({
            "version": "5.43",
            "themeCollection": {"baseTheme": {"name": "CY24SU02"}},
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
        }),
        "layoutOptimization": 0,
        "sections": sections,
    }


def _build_pbir(ws_name: str, model_id: str) -> dict:
    conn = (
        f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{ws_name};"
        f"Initial Catalog={MODEL_NAME};Integrated Security=ClaimsToken"
    )
    return {
        "version": "4.0",
        "datasetReference": {
            "byConnection": {
                "connectionString": conn,
                "pbiServiceModelId": None,
                "pbiModelVirtualServerName": "sobe_wowvirtualserver",
                "pbiModelDatabaseName": model_id,
                "name": "EntityDataSource",
                "connectionType": "pbiServiceXmlaStyleLive",
            }
        },
    }


def cmd_create_report(dry_run: bool) -> int:
    load_env()
    token = _fabric_token()
    ws_id = os.environ["FABRIC_WORKSPACE_ID"]
    ws_name = os.environ.get("FABRIC_WORKSPACE_NAME", "LaunchControl")

    models = _api_get(f"/workspaces/{ws_id}/semanticModels", token).get("value", [])
    model = next((m for m in models if m.get("displayName") == MODEL_NAME), None)
    if not model:
        print(f"[ERR] semantic model '{MODEL_NAME}' not found. Run --create-model first.")
        return 1
    model_id = model["id"]

    report_json = _build_report_json()
    pbir = _build_pbir(ws_name, model_id)
    print(f"Report '{REPORT_NAME}': {len(report_json['sections'])} pages, "
          f"bound to model [{model_id}].")

    if dry_run:
        print(json.dumps(report_json, indent=2)[:2000])
        print("\n[DRY RUN] report not published.")
        return 0

    parts = [
        {"path": "definition.pbir", "payload": _b64(json.dumps(pbir)), "payloadType": "InlineBase64"},
        {"path": "report.json", "payload": _b64(json.dumps(report_json)), "payloadType": "InlineBase64"},
    ]

    existing = _api_get(f"/workspaces/{ws_id}/reports", token).get("value", [])
    match = next((it for it in existing if it.get("displayName") == REPORT_NAME), None)

    if match:
        rid = match["id"]
        print(f"Updating existing report definition [{rid}] ...")
        status, headers, payload = _api_post(
            f"/workspaces/{ws_id}/reports/{rid}/updateDefinition",
            token, {"definition": {"parts": parts}})
    else:
        print("Creating new report ...")
        status, headers, payload = _api_post(
            f"/workspaces/{ws_id}/reports",
            token, {"displayName": REPORT_NAME, "definition": {"parts": parts}})

    if status == 202 and headers.get("Location"):
        print("  operation accepted, polling ...")
        status, payload = _poll_lro(headers["Location"], token)

    if status in (200, 201):
        try:
            info = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            info = {}
        rid = info.get("id", match["id"] if match else None)
        print(f"[OK] report published: {REPORT_NAME} [{rid or '(see --verify)'}]")
        if rid:
            print(f"Open: https://app.powerbi.com/groups/{ws_id}/reports/{rid}")
        return 0

    print(f"[ERR] report publish failed (HTTP {status}): "
          f"{payload.decode('utf-8', 'replace')[:1000]}")
    return 1


def cmd_verify() -> int:
    load_env()
    token = _fabric_token()
    ws_id = os.environ["FABRIC_WORKSPACE_ID"]
    for kind, path in (("Semantic models", "semanticModels"), ("Reports", "reports")):
        try:
            items = _api_get(f"/workspaces/{ws_id}/{path}", token).get("value", [])
            print(f"\n{kind} in workspace ({len(items)}):")
            for it in items:
                print(f"  - {it.get('displayName')}  [{it.get('id')}]")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR] listing {kind}: {e}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instructions", action="store_true", help="Print report + Fabric build steps.")
    ap.add_argument("--print-views", action="store_true", help="Print semantic_views.sql.")
    ap.add_argument("--apply-views", action="store_true", help="Apply semantic views to the SQL endpoint.")
    ap.add_argument("--create-model", action="store_true", help="Publish the Direct Lake semantic model over the views.")
    ap.add_argument("--create-report", action="store_true", help="Publish the 4-page report bound to the model.")
    ap.add_argument("--verify", action="store_true", help="List Power BI semantic models / reports.")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (with --apply-views / --create-model / --create-report).")
    args = ap.parse_args()

    if args.print_views:
        return cmd_print_views()
    if args.apply_views:
        return cmd_apply_views(args.dry_run)
    if args.create_model:
        return cmd_create_model(args.dry_run)
    if args.create_report:
        return cmd_create_report(args.dry_run)
    if args.verify:
        return cmd_verify()
    return cmd_instructions()


if __name__ == "__main__":
    raise SystemExit(main())
