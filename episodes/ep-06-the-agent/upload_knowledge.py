"""Episode 3 Part 2 — Upload sample knowledge-base articles into Dataverse.

Reads:
    data/knowledge/index.yaml      (file -> title, summary, category, launch)
    data/knowledge/<file>          (the actual KB markdown/PDF/DOCX bytes)

For every entry in index.yaml:
    1. Upsert an `lc_KnowledgeArticle` record keyed by lc_Title.
    2. Upload the file to the lc_Document file column via client.files.upload.
    3. Optionally bind lc_LaunchId to an existing lc_Launch by lc_Name.

Idempotent: re-running updates summary/category and overwrites the file column.

Usage:
    python launch-control/episodes/ep-06-the-agent/upload_knowledge.py
    python launch-control/episodes/ep-06-the-agent/upload_knowledge.py --dry-run
    python launch-control/episodes/ep-06-the-agent/upload_knowledge.py --only escalation-policy.md
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import yaml

# Add project root so we can import scripts/auth.py
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402


CATEGORY_VALUES = {
    "Policy": 10600100,
    "Playbook": 10600101,
    "Spec": 10600102,
    "Postmortem": 10600103,
}

KNOWLEDGE_DIR = ROOT / "data" / "knowledge"
INDEX_FILE = KNOWLEDGE_DIR / "index.yaml"


def _find_existing(client, title):
    """Return (record_id, record) for an existing lc_KnowledgeArticle with this title, or (None, None)."""
    safe = title.replace("'", "''")
    pages = client.records.get(
        "lc_knowledgearticle",
        filter=f"lc_title eq '{safe}'",
        select=["lc_knowledgearticleid", "lc_title", "lc_category"],
        top=1,
    )
    for page in pages:
        for rec in page:
            return rec["lc_knowledgearticleid"], rec
    return None, None


def _find_launch_id(client, launch_name):
    if not launch_name:
        return None
    safe = launch_name.replace("'", "''")
    pages = client.records.get(
        "lc_launch",
        filter=f"lc_name eq '{safe}'",
        select=["lc_launchid"],
        top=1,
    )
    for page in pages:
        for rec in page:
            return rec["lc_launchid"]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument("--only", help="Process only this filename from index.yaml")
    args = parser.parse_args()

    if not INDEX_FILE.exists():
        print(f"ERROR: {INDEX_FILE} not found.")
        sys.exit(1)

    with INDEX_FILE.open("r", encoding="utf-8") as fh:
        index = yaml.safe_load(fh) or {}
    articles = index.get("articles", [])
    if args.only:
        articles = [a for a in articles if a.get("file") == args.only]
        if not articles:
            print(f"No article matches --only {args.only}")
            sys.exit(1)

    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()

    with DataverseClient(env_url, credential) as client:
        for art in articles:
            file_name = art["file"]
            file_path = KNOWLEDGE_DIR / file_name
            title = art["title"]
            summary = " ".join((art.get("summary") or "").split())
            category = art["category"]
            launch_name = art.get("launch")

            if category not in CATEGORY_VALUES:
                print(f"  SKIP {file_name}: unknown category {category}")
                continue
            if not file_path.exists():
                print(f"  SKIP {file_name}: file missing at {file_path}")
                continue

            print(f"\n{file_name}  ->  {title}")
            print(f"  category={category}, launch={launch_name or '(none)'}")

            launch_id = _find_launch_id(client, launch_name) if launch_name else None
            if launch_name and not launch_id:
                print(f"  WARN: launch '{launch_name}' not found in lc_Launch; record will be unlinked")

            payload = {
                "lc_title": title,
                "lc_summary": summary,
                "lc_category": CATEGORY_VALUES[category],
            }
            if launch_id:
                payload["lc_LaunchId@odata.bind"] = f"/lc_launchs({launch_id})"

            existing_id, _ = _find_existing(client, title)

            if args.dry_run:
                action = "UPDATE" if existing_id else "CREATE"
                print(f"  [dry-run] {action} lc_knowledgearticle {existing_id or ''}")
                print(f"  [dry-run] upload {file_path.name} -> lc_document")
                continue

            if existing_id:
                client.records.update("lc_knowledgearticle", existing_id, payload)
                print(f"  Updated record {existing_id}")
                record_id = existing_id
            else:
                record_id = client.records.create("lc_knowledgearticle", payload)
                print(f"  Created record {record_id}")

            mime, _ = mimetypes.guess_type(file_path.name)
            mime = mime or "application/octet-stream"
            client.files.upload(
                "lc_knowledgearticle",
                record_id,
                "lc_document",
                str(file_path),
                mime_type=mime,
                if_none_match=False,
            )
            print(f"  Uploaded {file_path.name} ({mime}) -> lc_document")

    print("\n=== Knowledge upload complete ===")


if __name__ == "__main__":
    main()
