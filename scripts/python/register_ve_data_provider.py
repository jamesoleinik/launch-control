"""Register a Dataverse virtual-entity data provider via Web API ONLY — no PRT.

Reverse-engineered from the rows PRT writes when you use Register New Data
Provider. Diff details captured in scripts/python/_ep04_pre_prt_snapshot.json
vs _ep04_post_prt_snapshot.json. PRT creates exactly two rows:

  1. A virtual-entity data SOURCE — a regular virtual entity backed by the
     built-in JsonConverter data provider (id b2112a7e-...) that stores the
     provider's configuration rows (in our case, the GitHub repo/owner/token).

  2. An entitydataprovider row that names the provider, points at the data
     source by *logical name*, and has one *plugin lookup column per SDK
     message* (retrievemultipleplugin, retrieveplugin, createplugin, ...).
     Unused operations are populated with the OOB "Not Implemented"
     plugintype (id c1919979-0021-4f11-a587-a8f904bdfdf9). PRT does NOT
     create sdkmessageprocessingsteps - those are only for "regular" plugins
     bound to a message, not virtual-entity data providers.

This script does both via Web API. SETUP-GUIDE.md (line 59-61) claimed this
wasn't possible; that claim is wrong and is now corrected with a footnote.

Usage:
    python scripts/python/register_ve_data_provider.py
      --provider-name GitHubIssuesProvider
      --datasource-logical lc_githubdatasource
      --datasource-display "GitHub Data Source"
      --datasource-plural  "GitHub Data Sources"
      --assembly-name      GitHubIssuesProvider

If a row with the same name already exists, it's left alone and the script
prints the existing id. Run with `--force-recreate` to delete the existing
rows first (destructive - do not do this on the working env without a plan).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from auth import get_token, load_env


JSON_CONVERTER_PROVIDER_ID = "b2112a7e-b26c-42f7-9b63-9a809a9d716f"
NOT_IMPLEMENTED_PLUGINTYPE_ID = "c1919979-0021-4f11-a587-a8f904bdfdf9"


def api(method, path, body=None, base=None, tok=None):
    url = f"{base}/api/data/v9.2/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            status = r.status
            text = r.read().decode("utf-8")
            payload = json.loads(text) if text else None
            entity_id = r.headers.get("OData-EntityId", "")
            new_id = entity_id.split("(")[-1].rstrip(")") if "(" in entity_id else None
            return status, payload, new_id, None
    except urllib.error.HTTPError as e:
        return e.code, None, None, e.read().decode("utf-8")


def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": 1033,
        }],
    }


def ensure_data_source_entity(base, tok, logical, display, plural):
    """Step 1: ensure the data-source virtual entity exists. This is a regular
    virtual entity (TableType=Virtual) whose data provider is the OOB
    JsonConverter, so it stores its own configuration rows.
    """
    code, _, _, _ = api(
        "GET",
        f"EntityDefinitions(LogicalName='{logical}')?$select=LogicalName,MetadataId",
        base=base, tok=tok,
    )
    if code == 200:
        print(f"  data-source entity '{logical}' already exists - skipping create")
        return False  # not created

    print(f"  creating data-source entity '{logical}'...")
    schema = logical[:3] + logical[3:4].upper() + logical[4:]  # crude PascalCase
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": schema,
        "DisplayName": label(display),
        "DisplayCollectionName": label(plural),
        "OwnershipType": "OrganizationOwned",
        "TableType": "Virtual",
        "ExternalName": display.replace(" ", ""),
        "ExternalCollectionName": display.replace(" ", ""),
        "IsActivity": False,
        "HasActivities": False,
        "HasNotes": False,
        "DataProviderId": JSON_CONVERTER_PROVIDER_ID,
        # Virtual-entity required managed properties — without these the create
        # is rejected with errors like "CanChangeTrackingBeEnabled can not be
        # active for <entity> virtual Entity." PRT sets these implicitly; the
        # Web API does not, so we must include them explicitly.
        "ChangeTrackingEnabled": False,
        "CanChangeTrackingBeEnabled": {"Value": False, "CanBeChanged": False},
        "IsAvailableOffline": False,
        "IsVisibleInMobileClient": {"Value": False, "CanBeChanged": False},
        "CanCreateCharts": {"Value": False, "CanBeChanged": False},
        "Attributes": [{
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "AttributeType": "String",
            "SchemaName": logical[:3] + "Name" if logical.startswith("lc_") else "lc_Name",
            "MaxLength": 100,
            "IsPrimaryName": True,
            "DisplayName": label("Name"),
            "ExternalName": "Name",
        }],
    }
    code, _, new_id, err = api(
        "POST", "EntityDefinitions", body, base=base, tok=tok,
    )
    if code >= 400:
        raise RuntimeError(f"failed to create data-source entity: HTTP {code} {err}")
    print(f"  created (MetadataId={new_id})")
    return True


def lookup_plugintypes(base, tok, assembly_name):
    """Look up the two plugin types (RetrieveMultiple + Retrieve) under the
    named assembly.
    """
    flt = urllib.parse.quote(f"name eq '{assembly_name}'", safe="")
    code, payload, _, err = api(
        "GET",
        f"pluginassemblies?$filter={flt}&$select=pluginassemblyid",
        base=base, tok=tok,
    )
    if code != 200 or not payload.get("value"):
        raise RuntimeError(
            f"plugin assembly '{assembly_name}' not found - run "
            f"scripts/register_ve_plugin.py first"
        )
    asm_id = payload["value"][0]["pluginassemblyid"]

    flt2 = urllib.parse.quote(f"_pluginassemblyid_value eq {asm_id}", safe="")
    code, payload, _, err = api(
        "GET",
        f"plugintypes?$filter={flt2}&$select=plugintypeid,typename",
        base=base, tok=tok,
    )
    types = {p["typename"]: p["plugintypeid"] for p in payload.get("value", [])}
    rm = next((v for k, v in types.items() if k.endswith("RetrieveMultiplePlugin")), None)
    r = next((v for k, v in types.items() if k.endswith("RetrievePlugin") and v != rm), None)
    if not rm or not r:
        raise RuntimeError(
            f"could not find RetrieveMultiplePlugin + RetrievePlugin under "
            f"assembly '{assembly_name}'. Found: {list(types.keys())}. "
            f"Run scripts/register_ve_plugin.py to register the plugin types."
        )
    return rm, r


def ensure_data_provider(base, tok, provider_name, ds_logical, rm_id, r_id):
    """Step 2: ensure the entitydataprovider row exists. This is the row PRT
    writes when you complete the Register New Data Provider dialog. It has
    one plugin-lookup column per SDK message; unused operations get the OOB
    "Not Implemented" plugintype.
    """
    flt = urllib.parse.quote(f"name eq '{provider_name}'", safe="")
    code, payload, _, _ = api(
        "GET",
        f"entitydataproviders?$filter={flt}&$select=entitydataproviderid",
        base=base, tok=tok,
    )
    if code == 200 and payload.get("value"):
        existing_id = payload["value"][0]["entitydataproviderid"]
        print(f"  data provider '{provider_name}' already exists (id={existing_id}) - skipping create")
        return existing_id, False

    print(f"  creating data provider '{provider_name}'...")
    # The xxxplugin columns on entitydataprovider are primitive Uniqueidentifier
    # GUIDs (NOT lookup attributes). They must be sent as plain string GUIDs,
    # not as @odata.bind navigation references. Verified via
    # EntityDefinitions(LogicalName='entitydataprovider')/Attributes — all 20
    # are AttributeType=Uniqueidentifier.
    body = {
        "name": provider_name,
        "datasourcelogicalname": ds_logical,
        # The two operations our plugin actually implements:
        "retrievemultipleplugin": rm_id,
        "retrieveplugin": r_id,
        # All other operations -> OOB "Not Implemented" plugintype. PRT sets
        # all of these explicitly; we mirror that behavior so the row looks
        # identical to a PRT-created one.
        "createplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "createmultipleplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "updateplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "updatemultipleplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "deleteplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "deletemultipleplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "upsertplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "upsertmultipleplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "retrieveentitychangesplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "archiveplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "bulkarchiveplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "retainplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "bulkretainplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "purgearchivedcontentplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "purgeretainedcontentplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "rollbackretainplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "validatearchiveconfigplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
        "validateretentionconfigplugin": NOT_IMPLEMENTED_PLUGINTYPE_ID,
    }
    # Metadata-cache lag: when the data-source virtual entity was just
    # created in step 2, Dataverse may not yet recognize its logical name
    # for the `datasourcelogicalname` dependency lookup. POST returns
    # `0x8004f036 dependent component Entity (...) does not exist`. Retry
    # with backoff — cache typically catches up in 10-30s.
    import time
    new_id = None
    last_err = None
    for attempt in range(1, 7):
        code, _, new_id, err = api(
            "POST", "entitydataproviders", body, base=base, tok=tok,
        )
        if code < 400:
            break
        last_err = err or ""
        if "0x8004f036" in last_err or "does not exist" in last_err.lower():
            wait_s = 5 * attempt
            print(f"  [retry {attempt}/6] datasource cache lag; sleeping {wait_s}s...")
            time.sleep(wait_s)
            continue
        raise RuntimeError(f"failed to create data provider: HTTP {code} {err}")
    if not new_id:
        raise RuntimeError(f"failed to create data provider after 6 retries: {last_err}")
    print(f"  created (id={new_id})")
    return new_id, True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--provider-name", default="GitHubIssuesProvider")
    parser.add_argument("--datasource-logical", default="lc_githubdatasource")
    parser.add_argument("--datasource-display", default="GitHub Data Source")
    parser.add_argument("--datasource-plural", default="GitHub Data Sources")
    parser.add_argument("--assembly-name", default="GitHubIssuesProvider")
    args = parser.parse_args()

    load_env()
    base = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_token()
    print(f"Target env: {base}")
    print(f"Provider  : {args.provider_name}")
    print(f"Datasource: {args.datasource_logical} ({args.datasource_display})\n")

    print("1. Looking up plugin types...")
    rm_id, r_id = lookup_plugintypes(base, tok, args.assembly_name)
    print(f"  RetrieveMultiplePlugin = {rm_id}")
    print(f"  RetrievePlugin         = {r_id}")

    print("\n2. Ensuring data-source virtual entity...")
    ensure_data_source_entity(
        base, tok,
        args.datasource_logical, args.datasource_display, args.datasource_plural,
    )

    print("\n3. Ensuring entitydataprovider row...")
    provider_id, created = ensure_data_provider(
        base, tok, args.provider_name, args.datasource_logical, rm_id, r_id,
    )

    print(f"\nDone. Data provider {args.provider_name} ready (id={provider_id}).")
    print("This is the same pair of rows PRT writes - no PRT, no GUI.")


if __name__ == "__main__":
    main()
