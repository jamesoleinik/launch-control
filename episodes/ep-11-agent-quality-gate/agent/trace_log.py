from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def reset_trace(evidence_dir: Path) -> None:
    _write(evidence_dir, [])


def trace_event(
    evidence_dir: Path,
    *,
    status: str,
    title: str,
    detail: str = "",
    attachment: str = "",
) -> None:
    path = _path(evidence_dir)
    events = []
    if path.exists():
        events = json.loads(path.read_text(encoding="utf-8"))
    events.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "title": title,
        "detail": detail,
        "attachment": attachment,
    })
    _write(evidence_dir, events[-50:])


def _path(evidence_dir: Path) -> Path:
    return evidence_dir / "live-trace.json"


def _write(evidence_dir: Path, events: list[dict[str, str]]) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = _path(evidence_dir)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(events, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
