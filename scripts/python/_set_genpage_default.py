"""Reorder the Launch Control sitemap so the generative page is the first SubArea (default landing)."""
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_token, load_env  # type: ignore

import requests

load_env()
ORG = os.environ["DATAVERSE_URL"].rstrip("/")
APP_ID = os.environ.get("LAUNCH_CONTROL_APP_ID", "840766e6-cd4c-f111-bec6-00224805ff5f")
SITEMAP_ID = os.environ.get("LAUNCH_CONTROL_SITEMAP_ID", "7d8cfdb1-ce4c-f111-bec6-00224805f80c")
GEN_PAGE_SUBAREA_ID = os.environ.get(
    "LAUNCH_CONTROL_GENPAGE_SUBAREA_ID",
    "subarea_bc6937e3_49c9_4422_9ef6_57df822b6eee",
)

token = get_token()
H = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "OData-Version": "4.0",
}

r = requests.get(
    f"{ORG}/api/data/v9.2/sitemaps({SITEMAP_ID})?$select=sitemapxml",
    headers=H, timeout=30,
)
r.raise_for_status()
xml_str = r.json()["sitemapxml"]

root = ET.fromstring(xml_str)
group = root.find(".//Group")
assert group is not None, "Group not found"

subareas = list(group.findall("SubArea"))
gen = next((sa for sa in subareas if sa.get("Id") == GEN_PAGE_SUBAREA_ID), None)
assert gen is not None, f"GenPage SubArea {GEN_PAGE_SUBAREA_ID} not found"

for sa in subareas:
    group.remove(sa)
group.append(gen)
for sa in subareas:
    if sa.get("Id") != GEN_PAGE_SUBAREA_ID:
        group.append(sa)

new_xml = ET.tostring(root, encoding="unicode")
print("=== new sitemap ===")
print(new_xml)

patch = requests.patch(
    f"{ORG}/api/data/v9.2/sitemaps({SITEMAP_ID})",
    headers=H, timeout=30,
    json={"sitemapxml": new_xml},
)
print(f"PATCH sitemap: {patch.status_code}")
patch.raise_for_status()

pub_body = {"ParameterXml": f"<importexportxml><sitemaps><sitemap>{SITEMAP_ID}</sitemap></sitemaps><appmodules><appmodule>{APP_ID}</appmodule></appmodules></importexportxml>"}
pub = requests.post(
    f"{ORG}/api/data/v9.2/PublishXml",
    headers=H, timeout=120,
    json=pub_body,
)
print(f"PublishXml: {pub.status_code} {pub.text[:200]}")
pub.raise_for_status()
print("Done — gen page is now the first SubArea (default landing).")
