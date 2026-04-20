"""nativeagents-sdk check-contract: run doctor on all installed plugins."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def check_contract_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run doctor checks on all discovered plugins."""
    from nativeagents_sdk.errors import DuplicatePluginError
    from nativeagents_sdk.install.doctor import doctor
    from nativeagents_sdk.plugin.discovery import discover_plugins

    try:
        plugins = discover_plugins()
    except DuplicatePluginError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if not plugins:
        console.print("No plugins discovered.")
        return

    all_healthy = True
    reports = []
    for manifest in plugins:
        report = doctor(manifest.name)
        reports.append(report)
        if not report.is_healthy:
            all_healthy = False

    if json_output:
        import json

        typer.echo(
            json.dumps(
                [
                    {
                        "plugin_name": r.plugin_name,
                        "is_healthy": r.is_healthy,
                        "checks": r.checks,
                    }
                    for r in reports
                ],
                indent=2,
            )
        )
    else:
        for report in reports:
            console.print(report.to_text())
            console.print()

        if all_healthy:
            console.print("[green]All plugins healthy.[/green]")
        else:
            console.print("[red]Some plugins have issues.[/red]")
            raise typer.Exit(1)
