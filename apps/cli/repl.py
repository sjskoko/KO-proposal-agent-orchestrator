"""Interactive REPL for the agent system."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def start_repl(agent_id: str, config_dir: Path) -> None:
    from apps.cli.runner import build_system, run_agent

    console.print(f"[bold cyan]Gemma Agent REPL[/]  (agent: {agent_id})  — type [italic]/quit[/] to exit")
    console.print("[dim]Commands: /quit, /status, /trace <file>[/]\n")

    while True:
        try:
            goal = Prompt.ask("[bold]>[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/]")
            break

        if not goal:
            continue
        if goal in ("/quit", "/exit", "exit", "quit"):
            console.print("[dim]Bye.[/]")
            break

        try:
            result = run_agent(goal=goal, agent_id=agent_id, config_dir=config_dir)
            console.print(f"\n[green]{result}[/]\n")
        except Exception as exc:
            console.print(f"\n[red]Error:[/] {exc}\n")
