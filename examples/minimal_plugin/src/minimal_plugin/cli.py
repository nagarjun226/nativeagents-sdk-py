"""CLI for minimal-plugin."""

import typer

from minimal_plugin import __version__ as plugin_version
from nativeagents_sdk import __version__ as sdk_version
from nativeagents_sdk.install import doctor

app = typer.Typer(name="minimal-plugin", help="Minimal example plugin commands.")


@app.command()
def version() -> None:
    """Print plugin and SDK versions."""
    typer.echo(f"minimal-plugin {plugin_version} (sdk {sdk_version})")


@app.command("doctor")
def doctor_cmd() -> None:
    """Run health checks for this plugin."""
    report = doctor("minimal-plugin")
    typer.echo(report.to_text())
    raise typer.Exit(0 if report.is_healthy else 1)
