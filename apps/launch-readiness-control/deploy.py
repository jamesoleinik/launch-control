"""Deploy the Launch Readiness PCF and attach it to the Launch main form."""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from PowerPlatform.Dataverse.client import DataverseClient

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from auth import get_credential, get_token, load_env  # noqa: E402

CONTROL_NAME = "lc_LaunchControl.LaunchReadiness"
SOLUTION_NAME = "LaunchControl"
FORM_NAME = "Information"
CONTROL_INSTANCE_ID = "lc_launchreadinessdashboard"
TEXT_CONTROL_CLASS_ID = "{4273EDBD-AC1D-40D3-9FB2-095C621B552D}"
PACKAGE = (
    ROOT
    / "solution"
    / "bin"
    / "Debug"
    / "LaunchReadinessControl.zip"
)
MANIFEST = ROOT / "LaunchReadiness" / "ControlManifest.Input.xml"


class Dataverse:
    def __init__(self) -> None:
        load_env()
        self.url = os.environ["DATAVERSE_URL"].rstrip("/")
        self.api = self.url + "/api/data/v9.2"
        self.headers = {
            "Authorization": f"Bearer {get_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    def get(self, path: str) -> dict:
        for attempt in range(1, 6):
            try:
                response = requests.get(
                    self.api + path,
                    headers=self.headers,
                    timeout=90,
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError:
                if response.status_code < 500 and response.status_code != 429:
                    raise
                if attempt == 5:
                    raise
                time.sleep(attempt * 3)
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(attempt * 3)
        raise RuntimeError("Dataverse GET retry loop exited unexpectedly")

    def post(self, path: str, payload: dict) -> requests.Response:
        response = requests.post(
            self.api + path,
            headers=self.headers,
            json=payload,
            timeout=180,
        )
        if not response.ok:
            raise RuntimeError(
                f"Dataverse POST {path} failed ({response.status_code}): "
                f"{response.text[:2000]}"
            )
        return response

def import_control(dv: Dataverse) -> None:
    if not PACKAGE.exists():
        raise FileNotFoundError(
            f"PCF package not found at {PACKAGE}. Build "
            "'solution\\LaunchReadinessControl.cdsproj' first."
        )
    job_id = str(uuid.uuid4())
    payload = {
        "OverwriteUnmanagedCustomizations": True,
        "PublishWorkflows": False,
        "CustomizationFile": base64.b64encode(PACKAGE.read_bytes()).decode("ascii"),
        "ImportJobId": job_id,
        "ConvertToManaged": False,
        "SkipProductUpdateDependencies": True,
        "HoldingSolution": False,
    }
    for attempt in range(1, 6):
        try:
            dv.post("/ImportSolution", payload)
            break
        except requests.RequestException:
            try:
                dv.get(f"/importjobs({job_id})?$select=importjobid")
                break
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(attempt * 5)
    for _ in range(60):
        job = dv.get(
            f"/importjobs({job_id})?$select=progress,completedon,data"
        )
        if job.get("completedon"):
            if "<result result=\"failure\"" in str(job.get("data") or ""):
                raise RuntimeError("PCF solution import failed. Inspect the import job data.")
            print(f"[ok] imported {CONTROL_NAME}")
            dv.post("/PublishAllXml", {})
            print("[ok] published imported control customizations")
            return
        time.sleep(3)
    raise TimeoutError(f"PCF import job {job_id} did not complete")


def inspect_environment(dv: Dataverse, dump_form: bool = False) -> None:
    safe_name = CONTROL_NAME.replace("'", "''")
    controls = dv.get(
        "/customcontrols?$select=customcontrolid,name,version"
        f"&$filter=name eq '{safe_name}'"
    ).get("value", [])
    if not controls:
        controls = dv.get(
            "/customcontrols?$select=customcontrolid,name,version"
            "&$filter=contains(name,'LaunchReadiness')"
        ).get("value", [])
    print(f"Controls: {controls}")
    forms = dv.get(
        "/systemforms?$select=formid,name,type,objecttypecode,formxml"
        "&$filter=objecttypecode eq 'lc_launch' and type eq 2"
    ).get("value", [])
    for form in forms:
        print(
            "Form: "
            f"{form.get('name')} ({form.get('formid')}), "
            f"XML length {len(form.get('formxml') or '')}"
        )
        if dump_form:
            print(form.get("formxml") or "")


def exactly_one(rows: list[dict], description: str) -> dict:
    if len(rows) != 1:
        raise RuntimeError(f"Expected one {description}; got {len(rows)}")
    return rows[0]


def add_solution_component(
    dv: Dataverse,
    component_id: str,
    component_type: int,
) -> None:
    try:
        dv.post(
            "/AddSolutionComponent",
            {
                "ComponentId": component_id,
                "ComponentType": component_type,
                "SolutionUniqueName": SOLUTION_NAME,
                "AddRequiredComponents": True,
                "DoNotIncludeSubcomponents": False,
            },
        )
        print(f"[ok] added component {component_type}/{component_id} to {SOLUTION_NAME}")
    except RuntimeError as error:
        if "already exists" not in str(error).lower():
            raise
        print(f"[skip] component {component_type}/{component_id} already in {SOLUTION_NAME}")


def apply_form(dv: Dataverse) -> None:
    control = exactly_one(
        dv.get(
            "/customcontrols?$select=customcontrolid,name"
            f"&$filter=name eq '{CONTROL_NAME}'"
        ).get("value", []),
        f"{CONTROL_NAME} custom control",
    )
    add_solution_component(dv, control["customcontrolid"], 66)

    with DataverseClient(dv.url, get_credential()) as client:
        forms = client.records.list(
            "systemform",
            select=["formid", "name", "formxml"],
            filter=(
                f"objecttypecode eq 'lc_launch' and type eq 2 "
                f"and name eq '{FORM_NAME}'"
            ),
            top=2,
        )
        form = exactly_one(
            list(forms),
            f"{FORM_NAME} Launch main form",
        )
        root = ET.fromstring(form["formxml"])
        original_xml = ET.tostring(root, encoding="unicode")
        if root.find(f".//customControl[@name='{CONTROL_NAME}']") is None:
            add_readiness_tab(root, control["customcontrolid"])
        configure_form_layout(root)
        form_xml = ET.tostring(root, encoding="unicode")
        if form_xml != original_xml:
            client.records.update(
                "systemform",
                form["formid"],
                {"formxml": form_xml},
            )
            print(f"[ok] staged side-by-side readiness layout on {FORM_NAME}")
        else:
            print(f"[skip] side-by-side readiness layout already configured on {FORM_NAME}")

    add_solution_component(dv, form["formid"], 60)
    publish_form(dv, form["formid"])
    if not form_layout_is_current(dv, form["formid"]):
        dv.post("/PublishAllXml", {})
        print("[ok] published all pending customizations")


def add_readiness_tab(root: ET.Element, control_id: str) -> None:
    tabs = root.find("tabs")
    if tabs is None:
        raise RuntimeError("Launch form has no tabs collection")

    unique_id = guid()
    tab = ET.Element(
        "tab",
        {
            "verticallayout": "true",
            "id": guid(),
            "IsUserDefined": "1",
        },
    )
    add_label(tab, "Launch Readiness")
    columns = ET.SubElement(tab, "columns")
    column = ET.SubElement(columns, "column", {"width": "100%"})
    sections = ET.SubElement(column, "sections")
    section = ET.SubElement(
        sections,
        "section",
        {
            "showlabel": "false",
            "showbar": "false",
            "IsUserDefined": "1",
            "id": guid(),
            "height": "520",
        },
    )
    add_label(section, "Launch Readiness")
    rows = ET.SubElement(section, "rows")
    row = ET.SubElement(rows, "row")
    cell = ET.SubElement(
        row,
        "cell",
        {
            "id": guid(),
            "showlabel": "false",
            "colspan": "1",
            "rowspan": "1",
            "auto": "false",
        },
    )
    add_label(cell, "Launch Readiness Dashboard")
    ET.SubElement(
        cell,
        "control",
        {
            "id": CONTROL_INSTANCE_ID,
            "uniqueid": unique_id,
            "classid": TEXT_CONTROL_CLASS_ID,
            "datafieldname": "lc_name",
        },
    )
    tabs.insert(0, tab)

    descriptions = root.find("controlDescriptions")
    if descriptions is None:
        descriptions = ET.Element("controlDescriptions")
        display_conditions = root.find("DisplayConditions")
        position = (
            list(root).index(display_conditions)
            if display_conditions is not None
            else len(root)
        )
        root.insert(position, descriptions)
    description = ET.SubElement(
        descriptions,
        "controlDescription",
        {"forControl": unique_id},
    )
    parameters_control = ET.SubElement(
        description,
        "customControl",
        {"id": "{" + control_id.upper() + "}"},
    )
    parameters = ET.SubElement(parameters_control, "parameters")
    parameter = ET.SubElement(
        parameters,
        "launchName",
        {"type": "SingleLine.Text"},
    )
    parameter.text = "lc_name"
    for form_factor in ("0", "1", "2"):
        ET.SubElement(
            description,
            "customControl",
            {
                "formFactor": form_factor,
                "name": CONTROL_NAME,
            },
        )


def configure_form_layout(root: ET.Element) -> None:
    readiness_tab = find_tab(root, "Launch Readiness")
    general_tab = find_tab(root, "General")
    if readiness_tab is None or general_tab is None:
        raise RuntimeError("Launch Readiness and General tabs are required")

    readiness_columns = readiness_tab.find("columns")
    general_columns = general_tab.find("columns")
    if readiness_columns is None or general_columns is None:
        raise RuntimeError("Launch form tabs have no columns collection")

    pcf_column = find_control_column(readiness_tab, CONTROL_INSTANCE_ID)
    if pcf_column is None:
        raise RuntimeError("Launch Readiness PCF column is missing")
    readiness_tab.set("verticallayout", "false")
    timeline_column = find_control_column(readiness_tab, "notescontrol")
    if timeline_column is None:
        timeline_column = find_control_column(general_tab, "notescontrol")
        if timeline_column is None:
            raise RuntimeError("Launch timeline column is missing")
        general_columns.remove(timeline_column)
        readiness_columns.append(timeline_column)

    pcf_column.set("width", "60%")
    timeline_column.set("width", "40%")
    for section in pcf_column.findall("./sections/section"):
        section.set("height", "540")
    for section in timeline_column.findall("./sections/section"):
        section.set("height", "auto")
    general_fields = next(
        (
            column
            for column in general_columns.findall("column")
            if column is not timeline_column
        ),
        None,
    )
    if general_fields is None:
        raise RuntimeError("General fields column is missing")
    general_fields.set("width", "100%")


def find_tab(root: ET.Element, label: str) -> ET.Element | None:
    for tab in root.findall("./tabs/tab"):
        node = tab.find("./labels/label")
        if node is not None and node.get("description") == label:
            return tab
    return None


def find_control_column(tab: ET.Element, control_id: str) -> ET.Element | None:
    for column in tab.findall("./columns/column"):
        if column.find(f".//control[@id='{control_id}']") is not None:
            return column
    return None


def add_label(parent: ET.Element, text: str) -> None:
    labels = ET.SubElement(parent, "labels")
    ET.SubElement(
        labels,
        "label",
        {"description": text, "languagecode": "1033"},
    )


def publish_form(dv: Dataverse, form_id: str) -> None:
    dv.post(
        "/PublishXml",
        {
            "ParameterXml": (
                "<importexportxml><forms><form>"
                f"{form_id}"
                "</form></forms></importexportxml>"
            )
        },
    )
    print(f"[ok] published form {form_id}")


def form_layout_is_current(dv: Dataverse, form_id: str) -> bool:
    form = dv.get(f"/systemforms({form_id})?$select=formxml")
    root = ET.fromstring(str(form.get("formxml") or ""))
    tab = find_tab(root, "Launch Readiness")
    if tab is None:
        return False
    widths = [column.get("width") for column in tab.findall("./columns/column")]
    general_tab = find_tab(root, "General")
    general_widths = (
        [
            column.get("width")
            for column in general_tab.findall("./columns/column")
        ]
        if general_tab is not None
        else []
    )
    return (
        root.find(f".//customControl[@name='{CONTROL_NAME}']") is not None
        and tab.get("verticallayout") == "false"
        and widths == ["60%", "40%"]
        and find_control_column(tab, "notescontrol") is not None
        and general_tab is not None
        and general_widths == ["100%"]
        and find_control_column(general_tab, "notescontrol") is None
    )


def verify(dv: Dataverse) -> None:
    expected_version = ET.parse(MANIFEST).getroot().find("control").get("version")
    control = exactly_one(
        dv.get(
            "/customcontrols?$select=customcontrolid,name,version"
            f"&$filter=name eq '{CONTROL_NAME}'"
        ).get("value", []),
        f"{CONTROL_NAME} custom control",
    )
    if control.get("version") != expected_version:
        raise RuntimeError(
            f"{CONTROL_NAME} live version {control.get('version')} does not "
            f"match source version {expected_version}"
        )
    form = exactly_one(
        dv.get(
            "/systemforms?$select=formid,name,formxml"
            f"&$filter=objecttypecode eq 'lc_launch' and type eq 2 "
            f"and name eq '{FORM_NAME}'"
        ).get("value", []),
        f"{FORM_NAME} Launch main form",
    )
    root = ET.fromstring(form["formxml"])
    binding = root.find(f".//customControl[@name='{CONTROL_NAME}']")
    tab = next(
        (
            candidate
            for candidate in root.findall("./tabs/tab")
            if candidate.find(
                "./labels/label[@description='Launch Readiness']"
            ) is not None
        ),
        None,
    )
    if binding is None or tab is None:
        raise RuntimeError("Launch Readiness PCF form binding is missing")
    if tab.get("verticallayout") != "false":
        raise RuntimeError("Launch Readiness tab is still using vertical layout")
    widths = [column.get("width") for column in tab.findall("./columns/column")]
    if widths != ["60%", "40%"]:
        raise RuntimeError(f"Unexpected Launch Readiness column widths: {widths}")
    general_tab = find_tab(root, "General")
    if find_control_column(tab, "notescontrol") is None:
        raise RuntimeError("Launch timeline is not beside the readiness PCF")
    if general_tab is None or find_control_column(general_tab, "notescontrol") is not None:
        raise RuntimeError("Launch timeline is still on the General tab")
    print(
        f"[PASS] {control['name']} v{control.get('version')} is bound to "
        f"{FORM_NAME} ({form['formid']}) beside the activity timeline"
    )


def export_solution(dv: Dataverse, output: Path) -> None:
    response = dv.post(
        "/ExportSolution",
        {
            "SolutionName": SOLUTION_NAME,
            "Managed": False,
        },
    )
    encoded = response.json().get("ExportSolutionFile")
    if not encoded:
        raise RuntimeError("ExportSolution returned no solution file")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(encoded))
    print(f"[ok] exported {SOLUTION_NAME} to {output}")


def guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-control", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--dump-form", action="store_true")
    parser.add_argument("--apply-form", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--export-path", type=Path)
    args = parser.parse_args()
    if not any(
        (
            args.import_control,
            args.inspect,
            args.dump_form,
            args.apply_form,
            args.verify,
            args.export_path,
        )
    ):
        parser.error(
            "select --import-control, --apply-form, --verify, --inspect, "
            "--dump-form, and/or --export-path"
        )

    dv = Dataverse()
    if args.import_control:
        import_control(dv)
    if args.inspect or args.dump_form:
        inspect_environment(dv, dump_form=args.dump_form)
    if args.apply_form:
        apply_form(dv)
    if args.verify:
        verify(dv)
    if args.export_path:
        export_solution(dv, args.export_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
