"""Build lc_scoutskill: the Scout Skill Registry table.

Idempotent. Adds (or ensures) a single table with name/description/trigger/
instructions/outputformat columns, into the existing LaunchControl solution.

Pattern mirrors scripts/_build_lc_session.py (lc-datamodel skill convention).
"""
import os
import sys
import time
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

PREFIX = "lc"
SOLUTION = "LaunchControl"
TABLE = f"{PREFIX}_scoutskill"


class OutputFormat(Enum):
    # Next free option-value range under PUBLISHER_OPTVAL_PREFIX=10600.
    # Existing sets use 10600101-808; pick 10600901+ to stay clear.
    TeamsHTML = 10600901
    Markdown = 10600902
    Plain = 10600903


TRANSIENT_HINTS = ("customizationlock", "timeout", "timed out", "throttle", "503", "504", "lock")


def _is_dup(e):
    s = str(e).lower()
    return "already exists" in s or "duplicate" in s or "0x80048408" in s


def _is_transient(e):
    s = str(e).lower()
    return any(h in s for h in TRANSIENT_HINTS)


def _retry(fn, label, delay=2.0):
    for attempt in range(1, 6):
        try:
            return fn()
        except Exception as e:
            if _is_dup(e):
                raise
            if not _is_transient(e) or attempt == 5:
                raise
            print(f"  ~ {label}: transient (attempt {attempt}): {str(e)[:120]}; retry in {delay:.0f}s")
            time.sleep(delay)
            delay = min(delay * 1.8, 30.0)


def ensure_table(client):
    if client.tables.get(TABLE):
        print(f"  = table {TABLE} (exists)")
        return
    cols = {
        f"{PREFIX}_description": "string",
        f"{PREFIX}_trigger": "memo",
        f"{PREFIX}_instructions": "memo",
        f"{PREFIX}_outputformat": OutputFormat,
    }
    primary = f"{PREFIX}_name"
    t0 = time.monotonic()
    def _do():
        client.tables.create(TABLE, cols, solution=SOLUTION, primary_column=primary)
    try:
        _retry(_do, label=f"table {TABLE}")
        print(f"  + table {TABLE} ({time.monotonic() - t0:.1f}s)")
    except Exception as e:
        if _is_dup(e):
            print(f"  = table {TABLE} (exists)")
        else:
            raise


def ensure_columns_on_existing(client):
    """If the table exists but is missing some columns (e.g. partial earlier
    run), add the missing ones.
    """
    try:
        existing = client.tables.list_columns(TABLE) or []
    except Exception as e:
        print(f"  ! could not list columns on {TABLE}: {e}")
        return
    have = set()
    for c in existing:
        ln = c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None)
        if ln:
            have.add(ln)
    wanted = {
        f"{PREFIX}_description": "string",
        f"{PREFIX}_trigger": "memo",
        f"{PREFIX}_instructions": "memo",
        f"{PREFIX}_outputformat": OutputFormat,
    }
    missing = {k: v for k, v in wanted.items() if k not in have}
    if missing:
        print(f"  + adding {len(missing)} column(s) to {TABLE}: {list(missing)}")
        client.tables.add_columns(TABLE, missing, solution=SOLUTION)
    else:
        print(f"  = columns on {TABLE} (all present)")


def bump_instructions_max_length(env_url, target_len=100000):
    """The lc_instructions memo defaults to 4000 chars; skill bodies blow
    past that. Raw Web API patch: the SDK doesn't expose attribute updates.
    """
    import json as _json
    import urllib.request
    from scripts.auth import get_token

    token = get_token()
    base = f"{env_url}/api/data/v9.2"
    # Cast to MemoAttributeMetadata so MaxLength is selectable.
    url = (
        f"{base}/EntityDefinitions(LogicalName='{TABLE}')/Attributes"
        f"(LogicalName='{PREFIX}_instructions')"
        "/Microsoft.Dynamics.CRM.MemoAttributeMetadata"
        "?$select=LogicalName,MaxLength,MetadataId"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    })
    try:
        with urllib.request.urlopen(req) as r:
            meta = _json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ! GET attribute failed ({e.code}): {body[:600]}")
        raise
    current = meta.get("MaxLength")
    if current and current >= target_len:
        print(f"  = lc_instructions MaxLength already {current}")
        return
    print(f"  ~ bumping lc_instructions MaxLength {current} -> {target_len}")
    # PATCH the attribute. AttributeType + @odata.type required for memo updates.
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
        "MetadataId": meta["MetadataId"],
        "SchemaName": f"{PREFIX}_instructions",
        "LogicalName": f"{PREFIX}_instructions",
        "AttributeType": "Memo",
        "AttributeTypeName": {"Value": "MemoType"},
        "MaxLength": target_len,
        "Format": "TextArea",
    }
    patch_url = f"{base}/EntityDefinitions(LogicalName='{TABLE}')/Attributes({meta['MetadataId']})"
    req = urllib.request.Request(
        patch_url,
        data=_json.dumps(payload).encode("utf-8"),
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "MSCRM.SolutionUniqueName": SOLUTION,
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            r.read()
        print(f"  + lc_instructions MaxLength now {target_len}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ! PUT failed ({e.code}): {body[:600]}")
        raise


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    print(f"Target env: {env_url}")
    cred = get_credential()
    client = DataverseClient(env_url, cred)
    print("Ensuring lc_scoutskill ...")
    if client.tables.get(TABLE):
        print(f"  = table {TABLE} (exists): checking columns")
        ensure_columns_on_existing(client)
    else:
        ensure_table(client)
    bump_instructions_max_length(env_url)
    print("Done.")


if __name__ == "__main__":
    main()
