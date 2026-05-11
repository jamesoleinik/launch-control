"""Launch Coordinator (Python edition) - the code-first agent.

Architecture:

    [ user prompt ]
          |
          v
    +--------------------------------------------+
    |  GitHubCopilotAgent (Microsoft Agent FW)   |  <- LLM brain
    |  github-copilot-sdk + Claude/GPT model     |
    +--------------------------------------------+
          |
          v
    +--------------------------------------------+
    |  Local skills cache (./.skills/*.md)       |  <- the "brain"
    |  pulled from Dataverse on every run        |     (editable in
    +--------------------------------------------+      Dataverse)
          |
          v
    +--------------------------------------------+
    |  Dataverse MCP server (stdio)              |  <- tool surface
    |  npx @microsoft/dataverse mcp <orgUrl>     |
    +--------------------------------------------+
          |
          v
       [ Dataverse: data + Custom APIs ]

The same business skills (Launch Readiness Checklist, Escalation
Policy, ...) drive Copilot Studio (Ep 6), the Sentinel autonomous
flow (Ep 7), and this Python agent (Ep 8). Three runtimes, one brain.

Run:
    python agents/launch-coordinator-py/agent.py
    python agents/launch-coordinator-py/agent.py --launch "Q3 Widget Launch"
    python agents/launch-coordinator-py/agent.py --plain   # no rich UI
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Make `from scripts.auth import load_env` work regardless of where we are run from.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_framework.github import GitHubCopilotAgent  # noqa: E402
from copilot.session import PermissionHandler  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.rule import Rule  # noqa: E402
from rich.syntax import Syntax  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from scripts.auth import load_env  # noqa: E402

# Local sibling module - pulls skills from Dataverse at startup.
from sync_skills import sync as sync_skills_from_dataverse  # noqa: E402

SKILLS_DIR = Path(__file__).resolve().parent / ".skills"

console = Console()


INSTRUCTIONS = """\
You are the Launch Coordinator. You help product teams determine whether
a launch is ready to ship.

# How you work

You do **not** answer from general knowledge. The actual go/no-go logic
lives as a business skill in Dataverse. At startup we pulled the latest
copy of every skill from Dataverse and wrote it to `./.skills/`. On
every request:

1. **Step 0 - Load the skill.** Open
   `./.skills/launch-readiness-checklist.md` and follow the steps it
   contains verbatim. The file was synced from Dataverse moments ago -
   that is the source of truth. If the file is missing, stop and say
   so; do not improvise the gate logic.
2. Use the Dataverse MCP tools (`read_query`, `Search`,
   `describe_table`) to gather the data the skill asks for. The MCP
   server is registered with this agent under the name `dataverse`.
3. Produce the verdict the skill template specifies. Do not invent
   additional gates or change the wording.

# Output format

End your response with a single line:

    VERDICT: GO | NO-GO | CONDITIONAL - <one-sentence reason>
"""


def build_mcp_servers(dataverse_url: str) -> dict:
    is_windows = os.name == "nt"
    return {
        "dataverse": {
            "type": "stdio",
            "command": "npx.cmd" if is_windows else "npx",
            "args": [
                "-y",
                "@microsoft/dataverse",
                "mcp",
                dataverse_url,
            ],
            "tools": ["*"],
        },
    }


def auto_approve(request: object, context: dict) -> object:
    return PermissionHandler.approve_all(request, context)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# Recording-friendly rendering
# ----------------------------------------------------------------------

def render_banner(dataverse_url: str) -> None:
    """The opening shot: who am I, what am I made of."""
    body = Group(
        Text("Three runtimes, one brain.", style="bold cyan"),
        Text(""),
        Text("LLM brain      ", style="dim") + Text("github-copilot-sdk + agent-framework"),
        Text("Editable brain ", style="dim") + Text("Dataverse skills (pulled on every run)"),
        Text("Tool surface   ", style="dim") + Text("Dataverse MCP server (stdio)"),
        Text("Environment    ", style="dim") + Text(dataverse_url, style="green"),
    )
    console.print(Panel(body, title="[bold]Launch Coordinator (Python)[/bold]",
                        subtitle="[dim]Episode 8 - the code-first agent[/dim]",
                        border_style="cyan"))


def render_brain_sync(skills: list[dict]) -> None:
    """Show the skills as they land from Dataverse."""
    tbl = Table(title="\U0001F9E0  Skills synced from Dataverse",
                title_style="bold magenta",
                border_style="magenta",
                show_lines=False)
    tbl.add_column("Skill", style="bold")
    tbl.add_column("Unique name", style="dim")
    tbl.add_column("Lines", justify="right")
    tbl.add_column("Description")
    for s in skills:
        tbl.add_row(s["name"], s["uniquename"], str(s["lines"]),
                    Text(s["description"][:80], style="italic"))
    console.print(tbl)
    console.print(f"[dim]   -> wrote {len(skills)} files to {SKILLS_DIR}[/dim]\n")


def _shorten(text: str, n: int = 220) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "\u2026"


def _format_args(args) -> str:
    if args is None:
        return ""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return _shorten(args, 120)
    try:
        return _shorten(json.dumps(args, separators=(",", ":")), 120)
    except Exception:
        return _shorten(str(args), 120)


async def stream_agent(agent, prompt: str) -> str:
    """Run the agent in streaming mode, printing tool calls and assistant text live."""
    import time
    console.print(Rule(style="dim"))
    console.print(f"[bold]Prompt:[/bold] {prompt}\n")
    console.print(Rule("[bold cyan]Agent run[/bold cyan]", style="cyan"))

    full_text_parts: list[str] = []
    tool_call_names: dict[str, str] = {}
    saw_first_token = False
    start = time.monotonic()

    # Animated spinner so the user can see we are alive while Copilot
    # spawns the MCP subprocess + reasons. Stops on first token.
    status = console.status(
        "[dim italic]starting Dataverse MCP server, model warming up...[/dim italic]",
        spinner="dots",
    )
    status.start()

    def first_token():
        nonlocal saw_first_token
        if not saw_first_token:
            elapsed = time.monotonic() - start
            status.stop()
            console.print(f"[dim](first token after {elapsed:.1f}s)[/dim]\n")
            saw_first_token = True

    try:
        async for update in agent.run(prompt, stream=True):
            for content in getattr(update, "contents", []) or []:
                ctype = type(content).__name__

                if ctype == "FunctionCallContent":
                    first_token()
                    name = getattr(content, "name", "?")
                    call_id = getattr(content, "call_id", "") or ""
                    tool_call_names[call_id] = name
                    args = _format_args(getattr(content, "arguments", None))
                    console.print(
                        Text("\n\u2192 ", style="bold yellow")
                        + Text(name, style="bold")
                        + Text(f"  {args}", style="dim")
                    )

                elif ctype == "FunctionResultContent":
                    call_id = getattr(content, "call_id", "") or ""
                    name = tool_call_names.get(call_id, "tool")
                    result = getattr(content, "result", "")
                    exc = getattr(content, "exception", None)
                    if exc:
                        console.print(Text(f"  \u00d7 {name} failed: {exc}", style="red"))
                    else:
                        console.print(Text(f"  \u2190 {_shorten(str(result), 240)}", style="green"))

                else:
                    # Assistant text delta - print live, no buffering.
                    txt = getattr(content, "text", None)
                    if txt:
                        first_token()
                        full_text_parts.append(txt)
                        console.file.write(txt)
                        console.file.flush()
    finally:
        if not saw_first_token:
            status.stop()

    console.print()  # final newline
    return "".join(full_text_parts)


def render_verdict(final_text: str) -> None:
    """Pull the verdict line out and put it in its own panel."""
    import re
    verdict_line = None
    for ln in reversed(final_text.splitlines()):
        s = ln.strip().strip("*").strip()
        if re.match(r"(?i)^verdict\s*[:\-]", s):
            verdict_line = s
            break
    console.print(Rule(style="dim"))
    if verdict_line:
        upper = verdict_line.upper()
        if "NO-GO" in upper or "NO GO" in upper:
            style = "red"
        elif "CONDITIONAL" in upper:
            style = "yellow"
        elif "GO" in upper:
            style = "green"
        else:
            style = "cyan"
        console.print(Panel(Text(verdict_line, style=f"bold {style}"),
                            title="[bold]Verdict[/bold]",
                            border_style=style))
    else:
        console.print(Panel("(no Verdict line found in response)",
                            title="[bold]Verdict[/bold]", border_style="yellow"))


# ----------------------------------------------------------------------
# Main flow
# ----------------------------------------------------------------------

async def run_once(prompt: str, *, plain: bool) -> str:
    load_env()
    dataverse_url = os.environ["DATAVERSE_URL"].rstrip("/")

    if not plain:
        render_banner(dataverse_url)

    # Hydrate ./.skills/ from Dataverse before the agent runs. This is
    # the on-camera moment: the local cache is *just* a cache, the
    # editable brain lives in Dataverse.
    if not plain:
        with console.status("[magenta]Pulling skills from Dataverse...[/magenta]",
                            spinner="dots"):
            skills = sync_skills_from_dataverse(SKILLS_DIR)
        render_brain_sync(skills)
    else:
        skills = sync_skills_from_dataverse(SKILLS_DIR)
        print(f"[skills] synced {len(skills)} skills from Dataverse to {SKILLS_DIR}")

    agent = GitHubCopilotAgent(
        default_options={
            "instructions": INSTRUCTIONS,
            "mcp_servers": build_mcp_servers(dataverse_url),
            "on_permission_request": auto_approve,
            "timeout": 300,
        },
        name="launch-coordinator-py",
    )

    async with agent:
        if plain:
            return str(await agent.run(prompt))
        final_text = await stream_agent(agent, prompt)
        render_verdict(final_text)
        return final_text


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--launch", default="Q3 Widget Launch",
                   help="Name of the launch to evaluate (default: Q3 Widget Launch)")
    p.add_argument("--prompt", help="Override the default prompt entirely")
    p.add_argument("--plain", action="store_true",
                   help="Disable rich rendering (use for piping/CI)")
    args = p.parse_args()

    prompt = args.prompt or (
        f"Run the launch readiness checklist for the launch named "
        f"'{args.launch}'. Use Dataverse for the data and the "
        f"'Launch Readiness Checklist' skill for the gate logic."
    )

    if args.plain:
        print(f"--- prompt ---\n{prompt}\n--- response ---")
        print(asyncio.run(run_once(prompt, plain=True)))
    else:
        asyncio.run(run_once(prompt, plain=False))


if __name__ == "__main__":
    main()
