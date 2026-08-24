"""Create and verify a focused Dataverse model-driven app from JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import requests
from azure.identity import AzureCliCredential, ClientSecretCredential
from dotenv import load_dotenv

APP_COMPONENT = 80
SITEMAP_COMPONENT = 62


class Dataverse:
    def __init__(self, env_name: str | None) -> None:
        load_dotenv(Path.cwd() / ".env")
        if env_name:
            candidate = Path(env_name)
            paths = [
                candidate,
                candidate / ".env",
                Path.cwd() / "episodes" / env_name / ".env",
                Path.cwd() / f".env.{env_name}",
            ]
            env_file = next((path for path in paths if path.is_file()), None)
            if not env_file:
                raise RuntimeError(
                    f"Could not resolve environment configuration: {env_name}"
                )
            load_dotenv(env_file, override=True)
        self.url = os.environ["DATAVERSE_URL"].rstrip("/")
        self.api = self.url + "/api/data/v9.2"
        tenant_id = os.environ.get("TENANT_ID")
        client_id = os.environ.get("CLIENT_ID")
        client_secret = os.environ.get("CLIENT_SECRET")
        if tenant_id and client_id and client_secret:
            credential = ClientSecretCredential(
                tenant_id, client_id, client_secret
            )
        else:
            credential = AzureCliCredential(
                tenant_id=tenant_id, process_timeout=60
            )
        token = credential.get_token(f"{self.url}/.default").token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        solution: str | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
    ) -> requests.Response:
        headers = dict(self.headers)
        if solution:
            headers["MSCRM.SolutionUniqueName"] = solution
        response = requests.request(
            method,
            self.api + "/" + path.lstrip("/"),
            headers=headers,
            json=body,
            timeout=120,
        )
        if response.status_code not in expected:
            raise RuntimeError(
                f"{method} {path} failed ({response.status_code}): "
                f"{response.text[:800]}"
            )
        return response

    def rows(self, path: str) -> list[dict[str, Any]]:
        return self.request("GET", path).json().get("value", [])


def quote(value: str) -> str:
    return value.replace("'", "''")


def stable_id(prefix: str, value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return f"{prefix}_{clean}"


def load_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = ("name", "unique_name", "description", "solution", "navigation")
    missing = [name for name in required if not spec.get(name)]
    if missing:
        raise ValueError("Missing spec values: " + ", ".join(missing))
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", spec["unique_name"]):
        raise ValueError("unique_name must be a publisher-prefixed identifier")
    if not isinstance(spec["navigation"], list) or not spec["navigation"]:
        raise ValueError("navigation must contain at least one table")
    tables = [entry.get("table") for entry in spec["navigation"]]
    if any(not table for table in tables) or len(tables) != len(set(tables)):
        raise ValueError("navigation table names must be present and unique")
    return spec


def resolve_icon(dv: Dataverse, spec: dict[str, Any]) -> str:
    name = spec.get(
        "icon_webresource_name",
        "msdyn_/Images/AppModule_Default_Icon.png",
    )
    rows = dv.rows(
        "webresourceset?$select=webresourceid,name"
        f"&$filter=name eq '{quote(name)}'"
    )
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected exactly one app icon web resource named {name}; "
            f"found {len(rows)}"
        )
    return rows[0]["webresourceid"]


def sitemap_xml(spec: dict[str, Any]) -> str:
    area = escape(spec.get("area_title", spec["name"]), quote=True)
    group = escape(spec.get("group_title", "Launches"), quote=True)
    entries = []
    for entry in spec["navigation"]:
        table = escape(entry["table"], quote=True)
        title = escape(entry.get("label", entry["table"]), quote=True)
        entries.append(
            f'      <SubArea Id="{stable_id("sa", entry["table"])}" '
            f'Entity="{table}" Title="{title}" />'
        )
    return (
        "<SiteMap>\n"
        f'  <Area Id="{stable_id("area", spec["unique_name"])}" '
        f'Title="{area}" ShowGroups="true">\n'
        f'    <Group Id="{stable_id("group", spec["unique_name"])}" '
        f'Title="{group}">\n'
        + "\n".join(entries)
        + "\n    </Group>\n  </Area>\n</SiteMap>"
    )


def resolve(
    dv: Dataverse, spec: dict[str, Any]
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any],
    dict[str, str],
    dict[str, str],
]:
    apps = dv.rows(
        "appmodules?$select=appmoduleid,appmoduleidunique,name,uniquename,"
        "description,publishedon"
        f"&$filter=uniquename eq '{quote(spec['unique_name'])}'"
    )
    if len(apps) > 1:
        raise RuntimeError("Multiple apps have the requested unique name")
    sm_unique = spec["unique_name"] + "_sitemap"
    maps = dv.rows(
        "sitemaps?$select=sitemapid,sitemapname,sitemapnameunique,sitemapxml"
        f"&$filter=sitemapnameunique eq '{quote(sm_unique)}'"
    )
    if len(maps) > 1:
        raise RuntimeError("Multiple site maps have the requested unique name")
    solutions = dv.rows(
        "solutions?$select=solutionid,uniquename,ismanaged"
        f"&$filter=uniquename eq '{quote(spec['solution'])}'"
    )
    if len(solutions) != 1 or solutions[0].get("ismanaged"):
        raise RuntimeError("The target must be exactly one unmanaged solution")
    entities: dict[str, str] = {}
    for entry in spec["navigation"]:
        table = entry["table"]
        metadata = dv.request(
            "GET",
            "EntityDefinitions(LogicalName="
            f"'{quote(table)}')?$select=MetadataId,LogicalName",
        ).json()
        entities[table] = metadata["MetadataId"]
    workflows: dict[str, str] = {}
    for name in spec.get("processes", []):
        rows = dv.rows(
            "workflows?$select=workflowid,name,statecode,category"
            f"&$filter=name eq '{quote(name)}' and category eq 4 "
            "and statecode eq 1"
        )
        if len(rows) != 1:
            raise RuntimeError(
                f"Expected exactly one active BPF named {name}; found {len(rows)}"
            )
        workflows[name] = rows[0]["workflowid"]
    return (
        apps[0] if apps else None,
        maps[0] if maps else None,
        solutions[0],
        entities,
        workflows,
    )


def entity_id(response: requests.Response, field: str) -> str:
    if response.content:
        payload = response.json()
        if payload.get(field):
            return payload[field]
    location = response.headers.get("OData-EntityId") or response.headers.get(
        "Location", ""
    )
    match = re.search(r"\(([0-9a-fA-F-]{36})\)", location)
    if not match:
        raise RuntimeError(f"Create response did not identify {field}")
    return match.group(1)


def ensure_solution_component(
    dv: Dataverse,
    component_id: str,
    component_type: int,
    solution: str,
) -> None:
    response = requests.post(
        dv.api + "/AddSolutionComponent",
        headers=dv.headers,
        json={
            "ComponentId": component_id,
            "ComponentType": component_type,
            "SolutionUniqueName": solution,
            "AddRequiredComponents": False,
            "DoNotIncludeSubcomponents": False,
            "IncludedComponentSettingsValues": None,
        },
        timeout=120,
    )
    if response.status_code not in (200, 204):
        text = response.text.lower()
        if "already" not in text:
            raise RuntimeError(
                "AddSolutionComponent failed "
                f"({response.status_code}): {response.text[:800]}"
            )


def apply(dv: Dataverse, spec: dict[str, Any]) -> None:
    app, site_map, _, entities, workflows = resolve(dv, spec)
    icon_id = resolve_icon(dv, spec)
    if app:
        dv.request(
            "PATCH",
            f"appmodules({app['appmoduleid']})",
            body={
                "name": spec["name"],
                "description": spec["description"],
                "clienttype": 4,
                "navigationtype": 1,
                "webresourceid": icon_id,
            },
        )
        app_id = app["appmoduleid"]
    else:
        response = dv.request(
            "POST",
            "appmodules",
            body={
                "name": spec["name"],
                "uniquename": spec["unique_name"],
                "description": spec["description"],
                "clienttype": 4,
                "navigationtype": 1,
                "webresourceid": icon_id,
            },
        )
        app_id = entity_id(response, "appmoduleid")

    xml = sitemap_xml(spec)
    if site_map:
        dv.request(
            "PATCH",
            f"sitemaps({site_map['sitemapid']})",
            body={"sitemapname": spec["name"], "sitemapxml": xml},
        )
        site_map_id = site_map["sitemapid"]
    else:
        response = dv.request(
            "POST",
            "sitemaps",
            body={
                "sitemapname": spec["name"],
                "sitemapnameunique": spec["unique_name"] + "_sitemap",
                "sitemapxml": xml,
            },
        )
        site_map_id = entity_id(response, "sitemapid")

    components: list[dict[str, str]] = [
        {"@odata.id": f"sitemaps({site_map_id})"}
    ]
    components.extend(
        {"@odata.id": f"entities({metadata_id})"}
        for metadata_id in entities.values()
    )
    components.extend(
        {
            "@odata.type": "Microsoft.Dynamics.CRM.workflow",
            "workflowid": workflow_id,
        }
        for workflow_id in workflows.values()
    )
    dv.request(
        "POST",
        "AddAppComponents",
        body={"AppId": app_id, "Components": components},
        solution=spec["solution"],
    )
    ensure_solution_component(
        dv, app_id, APP_COMPONENT, spec["solution"]
    )
    ensure_solution_component(
        dv, site_map_id, SITEMAP_COMPONENT, spec["solution"]
    )
    dv.request(
        "POST",
        "PublishXml",
        body={
            "ParameterXml": (
                "<importexportxml><sitemaps><sitemap>"
                f"{site_map_id}</sitemap></sitemaps><appmodules><appmodule>"
                f"{app_id}</appmodule></appmodules></importexportxml>"
            )
        },
    )


def verify(dv: Dataverse, spec: dict[str, Any]) -> bool:
    app, site_map, solution, entities, workflows = resolve(dv, spec)
    checks: list[tuple[str, bool]] = [
        ("app exists", app is not None),
        ("site map exists", site_map is not None),
    ]
    if not app or not site_map:
        for label, passed in checks:
            print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        return False
    expected_tables = [entry["table"] for entry in spec["navigation"]]
    root = ElementTree.fromstring(site_map["sitemapxml"])
    actual_tables = [
        node.attrib.get("Entity", "") for node in root.findall(".//SubArea")
    ]
    component_rows = dv.rows(
        "appmodulecomponents?$select=objectid,componenttype"
        f"&$filter=_appmoduleidunique_value eq {app['appmoduleidunique']}"
    )
    object_ids = {
        str(row.get("objectid", "")).lower() for row in component_rows
    }
    memberships = dv.rows(
        "solutioncomponents?$select=objectid,componenttype"
        f"&$filter=_solutionid_value eq {solution['solutionid']} "
        f"and (objectid eq {app['appmoduleid']} "
        f"or objectid eq {site_map['sitemapid']})"
    )
    member_pairs = {
        (str(row["objectid"]).lower(), row["componenttype"])
        for row in memberships
    }
    checks.extend(
        [
            ("app name matches", app.get("name") == spec["name"]),
            (
                "app description matches",
                app.get("description") == spec["description"],
            ),
            ("app is published", bool(app.get("publishedon"))),
            ("navigation is exact", actual_tables == expected_tables),
            (
                "site map is associated",
                site_map["sitemapid"].lower() in object_ids,
            ),
            (
                "table components are included",
                sum(
                    1
                    for row in component_rows
                    if row.get("componenttype") == 1
                )
                == len(entities),
            ),
            (
                "BPF components are included",
                all(
                    value.lower() in object_ids for value in workflows.values()
                ),
            ),
            (
                "app is in solution",
                (app["appmoduleid"].lower(), APP_COMPONENT) in member_pairs,
            ),
            (
                "site map is in solution",
                (site_map["sitemapid"].lower(), SITEMAP_COMPONENT)
                in member_pairs,
            ),
        ]
    )
    for label, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    return all(passed for _, passed in checks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--env")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    dv = Dataverse(args.env)
    resolve_icon(dv, spec)
    if args.dry_run:
        app, site_map, _, _, workflows = resolve(dv, spec)
        print(
            "[dry-run] "
            + ("update" if app else "create")
            + f" app {spec['name']}"
        )
        print(
            "[dry-run] "
            + ("update" if site_map else "create")
            + f" site map with {len(spec['navigation'])} navigation entry"
        )
        print(f"[dry-run] include {len(workflows)} BPF component(s)")
        print("[dry-run] publish and verify without unrelated navigation")
        return 0
    if args.apply:
        apply(dv, spec)
    return 0 if verify(dv, spec) else 1


if __name__ == "__main__":
    raise SystemExit(main())
