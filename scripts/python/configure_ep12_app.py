"""Create native Episode 12 evidence surfaces from live form/view templates."""

from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(
    0, str(ROOT / ".github/skills/dataverse-model-driven-app-builder/scripts")
)

from auth import get_credential, load_env
import model_app_builder as builder
from PowerPlatform.Dataverse.client import DataverseClient

CLASS_IDS = {
    "String": "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}",
    "Memo": "{E0DECE4B-6FC8-4a8f-A065-082708572369}",
    "Lookup": "{270BD3DB-D9AF-4782-9025-509E298DEC0A}",
    "Picklist": "{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}",
    "DateTime": "{5B773807-9FB2-42db-97C3-7A91EFF8ADFF}",
    "Integer": "{C6D124CA-7EDA-4a60-AEA9-7FB8D318B68F}",
    "Boolean": "{67FAC785-CD58-4f9f-ABB3-4B7DDC6ED5ED}",
}
SPEC = Path(__file__).with_name("launch-control-app.json")


def one(rows, description, *, optional=False):
    values = list(rows)
    if not values and optional:
        return None
    if len(values) != 1:
        raise RuntimeError(f"Expected one {description}; found {len(values)}")
    return values[0].data


def form(client, table, name, *, optional=False):
    return one(
        client.records.list(
            "systemform",
            filter=f"objecttypecode eq '{table}' and type eq 2 "
            f"and name eq '{builder.quote(name)}'",
            select=["formid", "name", "description", "formxml", "formpresentation", "formactivationstate"],
        ),
        f"{table} form {name}",
        optional=optional,
    )


def view(client, table, name, *, optional=False):
    return one(
        client.records.list(
            "savedquery",
            filter=f"returnedtypecode eq '{table}' and querytype eq 0 "
            f"and name eq '{builder.quote(name)}'",
            select=["savedqueryid", "name", "description", "fetchxml", "layoutxml"],
        ),
        f"{table} view {name}",
        optional=optional,
    )


def named_surface(reader, client, entry, kind, key):
    current = reader(client, entry["table"], entry[kind], optional=True)
    previous_name = entry.get(f"previous_{kind}")
    if previous_name and previous_name != entry[kind]:
        previous = reader(client, entry["table"], previous_name, optional=True)
        if current and previous and current[key] != previous[key]:
            raise RuntimeError(
                f"{entry['table']}: both current and previous {kind} names exist"
            )
        current = current or previous
    return current


def native_form(xml, entry, columns):
    """Keep the live envelope and PCF binding; move native fields to tab one."""
    root = ET.fromstring(xml)
    tabs = root.find("tabs")
    if tabs is None:
        raise RuntimeError("Source form has no tabs")
    native = [
        tab for tab in tabs
        if tab.find(".//control[@id='ownerid']") is not None
    ]
    if len(native) != 1:
        raise RuntimeError("Expected one native tab containing record owner")
    tab = native[0]
    tabs.remove(tab)
    tabs.insert(0, tab)
    rows = tab.find("./columns/column/sections/section/rows")
    if rows is None:
        raise RuntimeError("Native tab has no field rows")
    existing = {
        cell.find("control").get("datafieldname"): deepcopy(row)
        for row in rows
        for cell in row.findall("cell")
        if cell.find("control") is not None
    }
    fields = dict(entry["fields"])
    # Preserve original native fields after the curated evidence fields.
    for name in existing:
        fields.setdefault(name, "Record owner" if name == "ownerid" else None)
    rows.clear()
    for name, label in fields.items():
        row = existing.get(name)
        if row is None:
            kind = columns[name]["AttributeType"]
            if kind not in CLASS_IDS:
                raise RuntimeError(f"Unsupported native control: {name} ({kind})")
            row = ET.Element("row")
            cell = ET.SubElement(row, "cell", {
                "id": "{" + str(uuid5(NAMESPACE_URL, f"ep12/{entry['table']}/{name}")) + "}"
            })
            ET.SubElement(ET.SubElement(cell, "labels"), "label", {
                "description": label, "languagecode": "1033",
            })
            ET.SubElement(cell, "control", {
                "id": name, "classid": CLASS_IDS[kind], "datafieldname": name,
            })
        elif label:
            row.find("./cell/labels/label").set("description", label)
        rows.append(row)
    return ET.tostring(root, encoding="unicode")


def native_view(source, entry):
    fetch = ET.fromstring(source["fetchxml"])
    fetch.attrib.pop("savedqueryid", None)
    entity = fetch.find("entity")
    grid = ET.fromstring(source["layoutxml"])
    row = grid.find("row")
    if entity is None or row is None:
        raise RuntimeError("View template is missing entity or grid row")
    if entity.get("name") != entry["table"]:
        raise RuntimeError("View template targets the wrong table")
    for child in list(entity):
        if child.tag in ("attribute", "order"):
            entity.remove(child)
    for name in dict.fromkeys([row.get("id"), *entry["view_fields"]]):
        ET.SubElement(entity, "attribute", {"name": name})
    ET.SubElement(entity, "order", {
        "attribute": entry["sort_field"],
        "descending": str(entry.get("sort_descending", False)).lower(),
    })
    for cell in list(row):
        row.remove(cell)
    for name in entry["view_fields"]:
        ET.SubElement(row, "cell", {"name": name, "width": "220"})
    return {
        "fetchxml": ET.tostring(fetch, encoding="unicode"),
        "layoutxml": ET.tostring(grid, encoding="unicode"),
    }


def plan(client, spec):
    changes = []
    for entry in spec["navigation"]:
        table = entry["table"]
        columns = {
            c["LogicalName"]: c for c in client.tables.list_columns(
                table, select=["LogicalName", "AttributeType"]
            )
        }
        required = set(entry["fields"]) | set(entry["view_fields"]) | {entry["sort_field"]}
        if required - columns.keys():
            raise RuntimeError(f"{table}: missing columns {required - columns.keys()}")
        current_form = named_surface(form, client, entry, "form", "formid")
        source_form = form(client, table, "Information")
        template = current_form or source_form
        form_body = {
            "name": entry["form"],
            "description": entry["evidence_description"],
            "formxml": native_form(template["formxml"], entry, columns),
            "formpresentation": source_form["formpresentation"],
            "formactivationstate": source_form["formactivationstate"],
        }
        current_view = named_surface(view, client, entry, "view", "savedqueryid")
        source_view = view(client, table, entry["source_view"])
        view_body = {
            "name": entry["view"],
            "description": entry["evidence_description"],
            **native_view(source_view, entry),
        }
        changes.extend([
            ("systemform", "formid", table, current_form, form_body, 60),
            ("savedquery", "savedqueryid", table, current_view, view_body, 26),
        ])
    return changes


def matches(current, body):
    if current is None:
        return False
    for key, expected in body.items():
        actual = current.get(key)
        if key.endswith("xml") and actual:
            left, right = ET.fromstring(actual), ET.fromstring(expected)
            if key == "fetchxml":
                # Dataverse stamps the saved view's own ID during creation.
                left.attrib.pop("savedqueryid", None)
                right.attrib.pop("savedqueryid", None)
            actual = ET.canonicalize(ET.tostring(left, encoding="unicode"))
            expected = ET.canonicalize(ET.tostring(right, encoding="unicode"))
        if actual != expected:
            return False
    return True


def original_app_components(dv, client, spec):
    app, _, _, _, _, _, _ = builder.resolve(dv, spec)
    if app is None:
        return []
    selected = {
        (row["componenttype"], row["objectid"].lower())
        for row in dv.rows(
            "appmodulecomponents?$select=objectid,componenttype"
            f"&$filter=_appmoduleidunique_value eq {app['appmoduleidunique']}"
        )
    }
    originals = []
    for entry in spec["navigation"]:
        source_form = form(client, entry["table"], "Information")
        source_view = view(client, entry["table"], entry["source_view"])
        for kind, collection, key, record in (
            (60, "systemforms", "formid", source_form),
            (26, "savedqueries", "savedqueryid", source_view),
        ):
            if (kind, record[key].lower()) in selected:
                originals.append({"@odata.id": f"{collection}({record[key]})"})
    return originals


def bind_app(dv, client, spec):
    builder.apply(dv, spec)
    originals = original_app_components(dv, client, spec)
    app, _, _, entities, _, _, _ = builder.resolve(dv, spec)
    for metadata_id in entities.values():
        builder.ensure_solution_component(dv, metadata_id, 1, spec["solution"])
    if originals:
        # Remove only source selections from this app, not the shared components.
        dv.request("POST", "RemoveAppComponents", body={
            "AppId": app["appmoduleid"], "Components": originals,
        }, solution=spec["solution"])
        dv.request("POST", "PublishXml", body={
            "ParameterXml": "<importexportxml><appmodules><appmodule>"
            + app["appmoduleid"] + "</appmodule></appmodules></importexportxml>"
        }, solution=spec["solution"])
    if not builder.verify(dv, spec) or original_app_components(dv, client, spec):
        raise RuntimeError("App component selection verification failed")


def verify_surfaces(client, spec):
    for entry in spec["navigation"]:
        table = entry["table"]
        columns = {
            c["LogicalName"]: c for c in client.tables.list_columns(
                table, select=["LogicalName", "AttributeType"]
            )
        }
        current = form(client, table, entry["form"])
        source = form(client, table, "Information")
        if current["formpresentation"] != source["formpresentation"] or current["formactivationstate"] != 1:
            raise RuntimeError(f"{table}: form is not active in the source presentation")
        root = ET.fromstring(current["formxml"])
        tab = root.find("./tabs/tab")
        fields = {c.get("datafieldname") for c in tab.findall(".//control")}
        if not set(entry["fields"]) <= fields:
            raise RuntimeError(f"{table}: native first-tab fields are missing")
        if tab.find(".//control[@uniqueid]") is not None:
            raise RuntimeError(f"{table}: PCF unexpectedly on first tab")
        for name, label in entry["fields"].items():
            control = tab.find(f".//control[@datafieldname='{name}']")
            if control.get("classid").lower() != CLASS_IDS[
                columns[name]["AttributeType"]
            ].lower():
                raise RuntimeError(f"{table}: {name} is not a native control")
            cell = next(
                (cell for cell in tab.findall(".//cell")
                 if cell.find(f"control[@datafieldname='{name}']") is not None),
                None,
            )
            if cell is None or cell.find("./labels/label").get("description") != label:
                raise RuntimeError(f"{table}: {name} label mismatch")
        current_view = view(client, table, entry["view"])
        fetched = {a.get("name") for a in ET.fromstring(
            current_view["fetchxml"]).findall("./entity/attribute")}
        displayed = [c.get("name") for c in ET.fromstring(
            current_view["layoutxml"]).findall("./row/cell")]
        if displayed != entry["view_fields"] or not set(displayed) <= fetched:
            raise RuntimeError(f"{table}: view field mismatch")
        if table == "lc_launch":
            original = ET.fromstring(source["formxml"])
            expected = original.find("controlDescriptions")
            actual = root.find("controlDescriptions")
            if expected is None or actual is None or ET.tostring(expected) != ET.tostring(actual):
                raise RuntimeError("Launch PCF binding was not preserved")
        print(f"[PASS] {table}: native first-tab evidence and view fields")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", help="Optional environment override; defaults to root .env")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    load_env(args.env)
    spec = builder.load_spec(SPEC)
    dv = builder.Dataverse(args.env)
    with DataverseClient(os.environ["DATAVERSE_URL"], get_credential()) as client:
        solution = one(client.records.list(
            "solution", filter=f"uniquename eq '{builder.quote(spec['solution'])}'",
            select=["solutionid", "ismanaged", "uniquename"],
        ), "unmanaged solution")
        if solution["ismanaged"]:
            raise RuntimeError("Cannot customize a managed solution")
        if args.verify:
            verify_surfaces(client, spec)
            if not builder.verify(dv, spec) or original_app_components(dv, client, spec):
                raise RuntimeError("App component selection verification failed")
            return
        changes = plan(client, spec)
        for table, key, target, current, body, component_type in changes:
            action = "create" if current is None else (
                "keep" if matches(current, body) else "update"
            )
            print(f"[{'dry-run' if args.dry_run else action}] {action} {target}: {body['name']}")
            if args.dry_run:
                continue
            if current is None:
                extra = (
                    {"objecttypecode": target, "type": 2}
                    if table == "systemform" else
                    {"returnedtypecode": target, "querytype": 0, "isdefault": False}
                )
                component_id = client.records.create(table, {**body, **extra})
            else:
                component_id = current[key]
                if action == "update":
                    client.records.update(table, component_id, body)
            builder.ensure_solution_component(dv, component_id, component_type, spec["solution"])
        if args.apply:
            entities = "".join(f"<entity>{e['table']}</entity>" for e in spec["navigation"])
            dv.request("POST", "PublishXml", body={
                "ParameterXml": f"<importexportxml><entities>{entities}</entities></importexportxml>"
            }, solution=spec["solution"])
            verify_surfaces(client, spec)
            bind_app(dv, client, spec)
        else:
            print("[dry-run] publish native surfaces, include four tables and their evidence forms/views")
            print("[dry-run] replace only this app's source Information/Active view selections; retain shared originals")


if __name__ == "__main__":
    main()
