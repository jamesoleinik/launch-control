from __future__ import annotations

import os

from aiohttp.web import Application, Request, Response, run_app
from microsoft_agents.hosting.aiohttp import (
    jwt_authorization_middleware,
    start_agent_process,
)


def start_server(agent_application, auth_configuration=None) -> None:
    async def entry_point(request: Request) -> Response:
        return await start_agent_process(
            request, request.app["agent_app"], request.app["adapter"]
        )

    app = Application(middlewares=[jwt_authorization_middleware])
    app.router.add_post("/api/messages", entry_point)
    app["agent_configuration"] = auth_configuration
    app["agent_app"] = agent_application
    app["adapter"] = agent_application.adapter
    run_app(app, host="127.0.0.1", port=int(os.environ.get("PORT", "3978")))
