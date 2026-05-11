"""Hydrate the local `.skills/` cache from Dataverse.

Called at agent startup. Pulls every business skill record from
`/api/data/v9.2/skills` and writes its `body` (markdown) to a local
file named after the skill's display name. The agent then reads from
disk - simple, deterministic, and the local files are *just a cache*:
edit the skill in Dataverse, re-run the agent, behavior changes.

This is the cleanest way to demonstrate the "three runtimes, one
editable brain" narrative without depending on whether the GitHub
Copilot CLI's MCP integration auto-discovers skills.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

import requests  # noqa: E402


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def sync(target_dir: Path) -> list[dict]:
    """Pull all skills from Dataverse, write to `target_dir/<slug>.md`.

    Returns one dict per skill with keys: name, uniquename, description,
    path, lines. Idempotent.
    """
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    cred = get_credential()
    token = cred.get_token(
        "https://" + env_url.split("://", 1)[1] + "/.default"
    ).token

    base = f"{env_url}/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }

    r = requests.get(
        f"{base}/skills?$select=name,uniquename,description,body",
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    skills = r.json().get("value", [])

    target_dir.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []

    index_lines = [
        "# Skills cache (auto-generated)",
        "",
        "These markdown files were pulled from Dataverse at agent startup.",
        "Edit them in Dataverse - not here. Local edits will be overwritten.",
        "",
        "| Skill | Unique name | File |",
        "| --- | --- | --- |",
    ]

    for skill in skills:
        name = skill.get("name") or skill.get("uniquename") or "unnamed"
        body = skill.get("body") or ""
        if not body.strip():
            continue
        slug = _slug(name)
        path = target_dir / f"{slug}.md"
        path.write_text(body, encoding="utf-8")
        out.append({
            "name": name,
            "uniquename": skill.get("uniquename", ""),
            "description": skill.get("description", "") or "",
            "path": path,
            "lines": body.count("\n") + 1,
        })
        index_lines.append(
            f"| {name} | `{skill.get('uniquename', '')}` | `{path.name}` |"
        )

    (target_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    here = Path(__file__).resolve().parent
    target = here / ".skills"
    written = sync(target)
    print(f"Synced {len(written)} skills -> {target}")
    for s in written:
        print(f"  - {s['name']} ({s['lines']} lines) - {s['description'][:60]}")


if __name__ == "__main__":
    main()
