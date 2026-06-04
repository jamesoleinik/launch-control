"""Inspect current sitemap XML and Launch Control app descriptor to find where genpage landed."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_token, load_env  # type: ignore

import requests

load_env()
ORG = os.environ["DATAVERSE_URL"].rstrip("/")
APP_ID = os.environ.get("LAUNCH_CONTROL_APP_ID", "840766e6-cd4c-f111-bec6-00224805ff5f")
SITEMAP_ID = os.environ.get("LAUNCH_CONTROL_SITEMAP_ID", "7d8cfdb1-ce4c-f111-bec6-00224805f80c")

token = get_token()
H = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

r = requests.get(
    f"{ORG}/api/data/v9.2/sitemaps({SITEMAP_ID})?$select=sitemapxml,sitemapname,sitemapnameunique",
    headers=H, timeout=30,
)
r.raise_for_status()
sm = r.json()
print(f"=== sitemap: {sm.get('sitemapname')} ({sm.get('sitemapnameunique')}) ===")
print(sm["sitemapxml"])
print()
print("=== appmodule descriptor (AppComponents.Pages) ===")
r2 = requests.get(
    f"{ORG}/api/data/v9.2/appmodules({APP_ID})?$select=descriptor,name,uniquename",
    headers=H, timeout=30,
)
r2.raise_for_status()
am = r2.json()
desc = json.loads(am.get("descriptor") or "{}")
print(json.dumps(desc.get("appInfo", {}).get("AppComponents", {}), indent=2)[:4000])
