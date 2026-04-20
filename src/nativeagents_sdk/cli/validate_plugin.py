"""nativeagents-sdk validate-plugin: run the conformance harness."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def validate_plugin_cmd(
    plugin_path: Annotated[
        Path | None,
        typer.Argument(help="Path to the plugin directory (default: current directory)"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON"),
    ] = False,
) -> None:
    """Run conformance checks against a plugin directory."""
    from nativeagents_sdk.conformance.harness import run_conformance

    target = plugin_path or Path.cwd()

    if not target.exists():
        err_console.print(f"[red]Error:[/red] Path does not exist: {target}")
        raise typer.Exit(1)

    report = run_conformance(target)

    if json_output:
        import json
        import sys

        sys.stdout.write(
            json.dumps(
                {
                    "plugin_dir": str(report.plugin_dir),
                    "passed": report.passed,
                    "checks": report.checks,
                },
                indent=2,
            )
        )
        sys.stdout.write("\n")
    else:
        console.print(f"Validating plugin at: [bold]{target}[/bold]")
        for check in report.checks:
            status = "[green]PASS[/green]" if check.get("passed") else "[red]FAIL[/red]"
            console.print(f"  [{status}] {check['name']}: {check['message']}")

        if report.passed:
            console.print("\n[green]All conformance checks passed.[/green]")
        else:
            console.print("\n[red]Conformance checks failed.[/red]")
            raise typer.Exit(3)
