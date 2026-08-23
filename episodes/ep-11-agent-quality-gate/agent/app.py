from __future__ import annotations

import asyncio
import os
from pathlib import Path

from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    MemoryStorage,
    TurnContext,
    TurnState,
)
from dotenv import load_dotenv

from .config import Config
from .dataverse import DataverseClient
from .identity import AgentTokenProvider
from .start_server import start_server
from .teams import TeamsNotifier
from .worker import run_once

EPISODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EPISODE_ROOT.parents[1]
load_dotenv(REPO_ROOT / ".env")
load_dotenv(EPISODE_ROOT / ".env", override=True)

SDK_CONFIG = load_configuration_from_env({
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID": os.environ.get(
        "A365_BLUEPRINT_CLIENT_ID", ""
    ),
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET": os.environ.get(
        "A365_BLUEPRINT_CLIENT_SECRET", ""
    ),
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID": os.environ.get(
        "TENANT_ID", ""
    ),
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE": "CLIENT_SECRET",
})
CONNECTION_MANAGER = MsalConnectionManager(**SDK_CONFIG)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)

APP = AgentApplication[TurnState](
    storage=MemoryStorage(),
    adapter=ADAPTER,
    connection_manager=CONNECTION_MANAGER,
)


@APP.activity("message")
async def on_message(context: TurnContext, _state: TurnState) -> None:
    text = (context.activity.text or "").strip().lower()
    if text in {"run", "run quality gate", "check"}:
        config = Config.load()
        provider = AgentTokenProvider(config)
        client = DataverseClient(config, provider)
        teams = (
            TeamsNotifier(
                config,
                provider,
                os.environ.get("A365_AGENT_USER_ID", ""),
            )
            if config.teams_recipient and config.launch_control_app_id
            else None
        )
        count = await asyncio.to_thread(
            run_once, client, config, None, teams
        )
        await context.send_activity(
            f"Processed {count} pending Quality Gate assignment(s)."
        )
        return
    if text == "status":
        config = Config.load()
        provider = AgentTokenProvider(config)
        client = DataverseClient(config, provider)
        assignments = await asyncio.to_thread(client.pending_assignments)
        await context.send_activity(
            f"{len(assignments)} pending Quality Gate assignment(s). "
            f"Identity mode: {provider.mode}."
        )
        return
    await context.send_activity(
        "Quality Gate agent ready. Send 'status' or 'run quality gate'."
    )


if __name__ == "__main__":
    start_server(
        APP, CONNECTION_MANAGER.get_default_connection_configuration()
    )
