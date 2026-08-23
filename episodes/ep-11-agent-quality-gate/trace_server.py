from __future__ import annotations

import argparse
import json
from pathlib import Path

from aiohttp import web

from agent.config import Config
from agent.trace_log import reset_trace

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "trace-viewer" / "index.html"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    config = Config.load(require_agent_user=False)
    if args.reset:
        reset_trace(config.evidence_dir)

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(INDEX)

    async def events(_request: web.Request) -> web.Response:
        path = config.evidence_dir / "live-trace.json"
        payload = []
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        return web.json_response(payload)

    async def evidence(request: web.Request) -> web.FileResponse:
        name = Path(request.match_info["name"]).name
        path = (config.evidence_dir / name).resolve()
        if path.parent != config.evidence_dir.resolve() or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/events", events)
    app.router.add_get("/evidence/{name}", evidence)
    web.run_app(app, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
