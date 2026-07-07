"""Small MCP clients used by the Episode 9 verification and demo scripts.

Two transports, because the Launch Control demo talks to two MCP servers:

``DataverseMcp``
    Streamable-HTTP JSON-RPC client for the **Dataverse MCP server**
    (``<env>/api/mcp``). This is the unified read/write endpoint an agent uses
    for the ``lc_*`` launch tables (and, read-only, the ``mserp_*`` F&O virtual
    entities). Authentication is a Dataverse bearer token from ``scripts/auth``.

``StdioMcp``
    stdio JSON-RPC client for a locally hosted MCP server, used to drive the
    **F&O (ERP) MCP server** that the unified CLI hosts with
    ``dataverse mcp <fno-operations-url>``. The ERP MCP is not a remote HTTP
    endpoint; the CLI runs it as a child process and routes to Finance &
    Operations based on the URL host, so the only way to reach it from a script
    is to speak MCP over the process's stdin/stdout.

Both expose the same three helpers: ``initialize()``, ``list_tools()`` and
``call(name, arguments)``.
"""

import json
import subprocess
import threading
import time

import requests


class McpError(RuntimeError):
    """Raised when an MCP tool call returns an error result."""


def _extract_text(result):
    """Join the text parts of an MCP tool-call result content array."""
    return "".join(
        c.get("text", "")
        for c in (result or {}).get("content", [])
        if c.get("type") == "text"
    )


class DataverseMcp:
    """Streamable-HTTP JSON-RPC client for the Dataverse MCP server."""

    def __init__(self, base_url, token):
        self.url = f"{base_url.rstrip('/')}/api/mcp"
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self._id = 0

    @staticmethod
    def _parse(resp):
        if "text/event-stream" in resp.headers.get("Content-Type", ""):
            payload = None
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        pass
            return payload
        return resp.json()

    def _rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._id += 1
            body["id"] = self._id
        if params is not None:
            body["params"] = params
        resp = self.session.post(
            self.url, headers=self.headers, data=json.dumps(body), timeout=180
        )
        resp.raise_for_status()
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.headers["Mcp-Session-Id"] = sid
        return None if notify else self._parse(resp)

    def initialize(self, client_name="launchcontrol-demo"):
        res = self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "1.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)
        return (res or {}).get("result", {}).get("serverInfo", {})

    def list_tools(self):
        res = self._rpc("tools/list")
        return [t["name"] for t in (res or {}).get("result", {}).get("tools", [])]

    def call(self, name, arguments):
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        result = (res or {}).get("result")
        if result is None:
            raise McpError(json.dumps(res)[:400])
        if result.get("isError"):
            raise McpError(_extract_text(result) or json.dumps(result)[:400])
        return _extract_text(result)

    def read_query(self, sql):
        text = self.call("read_query", {"querytext": sql})
        return json.loads(text) if text.strip() else []

    def create_record(self, tablename, item):
        return self.call("create_record", {"tablename": tablename, "item": json.dumps(item)})


class StdioMcp:
    """stdio JSON-RPC client that spawns and drives a local MCP server process.

    Used for the F&O (ERP) MCP server hosted by
    ``dataverse mcp <fno-operations-url>``. The child inherits the environment,
    so it authenticates through the current unified-CLI auth profile
    (``dataverse auth create --environment <dataverse-url>``); there is no way to
    inject a bearer token over stdio.
    """

    def __init__(self, args):
        self.args = args
        self.proc = None
        self._id = 0
        self._stderr_lines = []

    def __enter__(self):
        self.proc = subprocess.Popen(
            self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        def drain():
            for line in self.proc.stderr:
                self._stderr_lines.append(line.rstrip("\n"))

        threading.Thread(target=drain, daemon=True).start()
        return self

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    @property
    def stderr(self):
        return "\n".join(self._stderr_lines)

    def _send(self, method, params=None, notify=False, timeout=120):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._id += 1
            body["id"] = self._id
        if params is not None:
            body["params"] = params
        self.proc.stdin.write(json.dumps(body) + "\n")
        self.proc.stdin.flush()
        if notify:
            return None

        want_id = body.get("id")
        deadline = time.monotonic() + timeout
        noise = []

        def read_line(sink):
            sink["line"] = self.proc.stdout.readline()

        # The CLI-hosted ERP MCP server interleaves human-readable banners and log
        # lines with the JSON-RPC frames on stdout, so read line by line and skip
        # anything that is not the JSON-RPC response for this request. A dedicated
        # thread bounds each read so a server blocked on interactive auth cannot
        # hang the caller forever.
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise McpError(
                    f"no JSON-RPC response to '{method}' from ERP MCP server "
                    f"within {timeout}s (likely awaiting interactive auth). "
                    f"non-JSON stdout:\n{chr(10).join(noise[-10:])}\n"
                    f"stderr:\n{self.stderr[-1500:]}"
                )
            sink = {}
            t = threading.Thread(target=read_line, args=(sink,), daemon=True)
            t.start()
            t.join(remaining)
            if "line" not in sink:
                raise McpError(
                    f"no response to '{method}' from ERP MCP server within "
                    f"{timeout}s (likely awaiting interactive auth). "
                    f"stderr:\n{self.stderr[-1500:]}"
                )
            raw = sink["line"]
            if raw == "":
                raise McpError(
                    f"ERP MCP server closed stdout before answering '{method}'. "
                    f"non-JSON stdout:\n{chr(10).join(noise[-10:])}\n"
                    f"stderr:\n{self.stderr[-1500:]}"
                )
            line = raw.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                noise.append(line)
                continue
            if not isinstance(msg, dict):
                noise.append(line)
                continue
            if want_id is not None and msg.get("id") == want_id:
                return msg
            if want_id is None and "id" not in msg:
                return msg
            # A notification or a response to a different request: keep reading.
            noise.append(line)

    def initialize(self, client_name="launchcontrol-demo", timeout=120):
        res = self._send(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "1.0"},
            },
            timeout=timeout,
        )
        self._send("notifications/initialized", notify=True)
        return (res or {}).get("result", {}).get("serverInfo", {})

    def list_tools(self, timeout=60):
        res = self._send("tools/list", timeout=timeout)
        return [t["name"] for t in (res or {}).get("result", {}).get("tools", [])]

    def call(self, name, arguments, timeout=180):
        res = self._send(
            "tools/call", {"name": name, "arguments": arguments}, timeout=timeout
        )
        result = (res or {}).get("result")
        if result is None:
            raise McpError(json.dumps(res)[:400])
        if result.get("isError"):
            raise McpError(_extract_text(result) or json.dumps(result)[:400])
        return _extract_text(result)

    def read_query(self, sql, timeout=180):
        text = self.call("read_query", {"querytext": sql}, timeout=timeout)
        return json.loads(text) if text.strip() else []

    def create_record(self, tablename, item, timeout=180):
        return self.call(
            "create_record",
            {"tablename": tablename, "item": json.dumps(item)},
            timeout=timeout,
        )
