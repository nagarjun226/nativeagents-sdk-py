"""nativeagents-sdk CLI entry point."""

from __future__ import annotations

import typer
from rich.console import Console


def _version_callback(value: bool) -> None:
    if value:
        from nativeagents_sdk.version import __version__

        console.print(f"nativeagents-sdk {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="nativeagents-sdk",
    help="Native Agents SDK command-line tools.",
    no_args_is_help=True,
)


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version."
    ),
) -> None:
    pass


console = Console()
err_console = Console(stderr=True)


@app.command("version")
def version_cmd() -> None:
    """Print SDK version."""
    from nativeagents_sdk.version import __version__

    console.print(f"nativeagents-sdk {__version__}")


# Import and register subcommands
from nativeagents_sdk.cli.check_contract import check_contract_cmd  # noqa: E402
from nativeagents_sdk.cli.init_plugin import init_plugin_cmd  # noqa: E402
from nativeagents_sdk.cli.validate_plugin import validate_plugin_cmd  # noqa: E402

app.command("init-plugin")(init_plugin_cmd)
app.command("validate-plugin")(validate_plugin_cmd)
app.command("check-contract")(check_contract_cmd)


if __name__ == "__main__":
    app()
