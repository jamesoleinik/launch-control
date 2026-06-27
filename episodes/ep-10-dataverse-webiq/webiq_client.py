"""Minimal Web IQ MCP client (stdlib only).

Wraps the Web IQ MCP server (Streamable HTTP, JSON-RPC 2.0) so the rest of the
episode can call `web` / `news` / `browse` without pulling in an MCP SDK.

Auth: reads WEBIQ_API_KEY (and optional WEBIQ_MCP_URL) from the environment.
Use scripts/auth.load_env so a per-episode .env (selected with LC_ENV) is picked
up. Never hardcode or commit the key; request one from your Microsoft
representative. Public docs: https://www.microsoft.com/webiq

Example:
    from webiq_client import WebIqClient
    client = WebIqClient()
    for hit in client.web("CSP frame-ancestors SharePoint embedding", max_results=3):
        print(hit["title"], hit["url"])
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

# Allow importing scripts/auth.py for the shared .env loader.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
try:
    import auth as _auth
except Exception:  # pragma: no cover - auth is optional for pure env usage
    _auth = None

DEFAULT_ENDPOINT = "https://api.microsoft.ai/v3/mcp"


class WebIqError(RuntimeError):
    pass


class WebIqClient:
    """Tiny JSON-RPC client for the Web IQ MCP server."""

    def __init__(self, api_key=None, endpoint=None, env_name=None, timeout=60):
        if _auth is not None:
            _auth.load_env(env_name)
        self.endpoint = (endpoint or os.environ.get("WEBIQ_MCP_URL")
                         or DEFAULT_ENDPOINT)
        self.api_key = api_key or os.environ.get("WEBIQ_API_KEY")
        self.timeout = timeout
        self._id = 0
        if not self.api_key:
            raise WebIqError(
                "WEBIQ_API_KEY is not set. Copy episodes/ep-10-dataverse-webiq/"
                ".env.example to .env, add your key, and select it with "
                "LC_ENV=ep-10-dataverse-webiq.")

    def _rpc(self, method, params=None):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=data, method="POST",
            headers={
                "x-apikey": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            })
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
        message = _extract_json(raw)
        if "error" in message:
            raise WebIqError(f"{method} failed: {message['error']}")
        return message.get("result", {})

    def initialize(self):
        return self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "launch-control-webiq", "version": "1.0"},
        })

    def list_tools(self):
        return self._rpc("tools/list").get("tools", [])

    def tool_names(self):
        return [t.get("name") for t in self.list_tools()]

    def call(self, name, arguments):
        """Call a tool and return the parsed JSON payload from its text content."""
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        blocks = result.get("content", [])
        for block in blocks:
            text = block.get("text")
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
        return result

    def web(self, query, max_results=3, **kwargs):
        args = {"query": query, "maxResults": max_results}
        args.update(kwargs)
        payload = self.call("web", args)
        return payload.get("webResults", payload.get("results", []))

    def news(self, query, max_results=3, **kwargs):
        args = {"query": query, "maxResults": max_results}
        args.update(kwargs)
        payload = self.call("news", args)
        return payload.get("newsResults", payload.get("value", payload.get("results", [])))


def _extract_json(raw):
    """Parse a JSON-RPC response that may arrive as JSON or as an SSE stream."""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    # Server-Sent Events: pull the last `data:` line.
    last = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            last = line[len("data:"):].strip()
    if last:
        return json.loads(last)
    raise WebIqError(f"Could not parse Web IQ response: {raw[:200]}")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Popular cat breeds in America"
    c = WebIqClient()
    info = c.initialize().get("serverInfo", {})
    print(f"Connected: {info.get('name')} {info.get('version')}")
    print(f"Tools: {', '.join(c.tool_names())}")
    print(f"\nweb('{q}'):")
    for hit in c.web(q, max_results=3):
        print(f"  - {hit.get('title')}\n    {hit.get('url')}")
