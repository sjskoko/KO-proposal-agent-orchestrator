"""CLI entry point — `agent run`, `agent repl`, `agent replay`."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(name="agent", help="Gemma 4 local agent system")
console = Console()


@app.command()
def run(
    goal: str = typer.Argument(..., help="Goal or task for the agent"),
    agent: str = typer.Option("main_agent", "--agent", "-a", help="Agent ID to use"),
    config_dir: Path = typer.Option(Path("config"), "--config", "-c"),
):
    """Run the agent with a single goal and exit."""
    from apps.cli.runner import run_agent
    result = run_agent(goal=goal, agent_id=agent, config_dir=config_dir)
    console.print(Panel(str(result), title="[bold green]Result", expand=False))


@app.command()
def repl(
    agent: str = typer.Option("main_agent", "--agent", "-a"),
    config_dir: Path = typer.Option(Path("config"), "--config", "-c"),
):
    """Start an interactive REPL session."""
    from apps.cli.repl import start_repl
    start_repl(agent_id=agent, config_dir=config_dir)


@app.command()
def replay(
    trace_file: Path = typer.Argument(..., help="Path to a .jsonl trace file"),
):
    """Load and display a recorded execution trace."""
    from core.events.trace import TraceWriter
    records = TraceWriter.replay(trace_file)
    for i, record in enumerate(records, 1):
        console.print(f"[dim]{i:03d}[/] [bold]{record.get('_type', '?')}[/]  {record}")


if __name__ == "__main__":
    app()
