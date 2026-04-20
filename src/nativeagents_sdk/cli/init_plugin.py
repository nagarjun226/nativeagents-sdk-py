"""nativeagents-sdk init-plugin: scaffold a new plugin directory."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def init_plugin_cmd(
    name: Annotated[str, typer.Argument(help="Plugin name (e.g., my-plugin)")],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Directory to create the plugin in"),
    ] = None,
) -> None:
    """Scaffold a new SDK-conformant plugin directory."""
    from nativeagents_sdk.paths import validate_plugin_name

    try:
        validate_plugin_name(name)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    target = (output_dir or Path.cwd()) / name
    if target.exists():
        err_console.print(f"[red]Error:[/red] Directory already exists: {target}")
        raise typer.Exit(1)

    _scaffold_plugin(name, target)
    console.print(f"[green]Created plugin scaffold at:[/green] {target}")
    console.print("\nNext steps:")
    console.print(f"  cd {target}")
    console.print("  pip install -e '.[dev]'")
    console.print("  pytest")


def _scaffold_plugin(name: str, target: Path) -> None:
    """Create all scaffold files for a new plugin."""
    module_name = name.replace("-", "_")

    # Directory structure
    src_dir = target / "src" / module_name
    hooks_dir = target / "hooks"
    tests_dir = target / "tests"

    for d in [src_dir, hooks_dir, tests_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # plugin.toml
    (target / "plugin.toml").write_text(
        f"""schema_version = 1

[plugin]
name = "{name}"
version = "0.1.0"
description = "A Native Agents plugin"
hooks = ["PreToolUse"]
writes_audit_events = true
owns_paths = ["plugins/{name}/"]
hook_module = "{module_name}.hook"
cli_entry = "{module_name}.cli:app"
min_sdk_version = "0.1.0"
""",
        encoding="utf-8",
    )

    # pyproject.toml
    (target / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "A Native Agents plugin"
requires-python = ">=3.11"
dependencies = ["nativeagents-sdk>=0.1"]

[project.scripts]
{name} = "{module_name}.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/{module_name}"]

[dependency-groups]
dev = ["pytest>=7", "nativeagents-sdk[dev]>=0.1"]
""",
        encoding="utf-8",
    )

    # src/<module>/__init__.py
    (src_dir / "__init__.py").write_text(
        f'"""{name} — a Native Agents plugin."""\n\n__version__ = "0.1.0"\n',
        encoding="utf-8",
    )

    # src/<module>/hook.py
    (src_dir / "hook.py").write_text(
        f"""\"\"\"Hook handler for {name}.\"\"\"

from nativeagents_sdk.hooks import HookDecision, HookDispatcher, PreToolUseInput

dispatcher = HookDispatcher(plugin_name="{name}")


@dispatcher.on("PreToolUse")
def on_pre_tool_use(event: PreToolUseInput, ctx) -> HookDecision:
    \"\"\"Log pre-tool-use events and write an audit entry.\"\"\"
    ctx.log.info("Tool: %s", event.tool_name)
    ctx.write_audit(
        event_type="{name}.pre_tool_use",
        payload={{"tool_name": event.tool_name}},
        session_id=event.session_id,
    )
    return HookDecision.ok()


if __name__ == "__main__":
    dispatcher.run()
""",
        encoding="utf-8",
    )

    # src/<module>/cli.py
    (src_dir / "cli.py").write_text(
        f"""\"\"\"CLI for {name}.\"\"\"

import typer
from nativeagents_sdk import __version__ as sdk_version
from nativeagents_sdk.install import doctor

from {module_name} import __version__ as plugin_version

app = typer.Typer(name="{name}", help="{name} plugin commands.")


@app.command()
def version() -> None:
    \"\"\"Print plugin and SDK versions.\"\"\"
    typer.echo(f"{name} {{plugin_version}} (sdk {{sdk_version}})")


@app.command("doctor")
def doctor_cmd() -> None:
    \"\"\"Run health checks for this plugin.\"\"\"
    report = doctor("{name}")
    typer.echo(report.to_text())
    raise typer.Exit(0 if report.is_healthy else 1)
""",
        encoding="utf-8",
    )

    # hooks/hook.sh (from template)
    hook_sh = _render_hook_template(name, module_name)
    hook_sh_path = hooks_dir / "hook.sh"
    hook_sh_path.write_text(hook_sh, encoding="utf-8")
    hook_sh_path.chmod(0o755)

    # tests/test_smoke.py
    (tests_dir / "test_smoke.py").write_text(
        f"""\"\"\"Smoke tests for {name}.\"\"\"

import {module_name}


def test_version() -> None:
    assert {module_name}.__version__
""",
        encoding="utf-8",
    )


def _render_hook_template(plugin_name: str, module_name: str) -> str:
    """Render the hook.sh template for a plugin."""
    import sys
    from pathlib import Path as _Path

    template_text = _DEFAULT_TEMPLATE
    try:
        tmpl_path = _Path(__file__).parent.parent / "hooks" / "template.sh"
        if tmpl_path.exists():
            template_text = tmpl_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    python_exe = sys.executable
    return (
        template_text.replace("{{PLUGIN_NAME}}", plugin_name)
        .replace("{{PYTHON_EXECUTABLE}}", python_exe)
        .replace("{{PYTHON_MODULE}}", f"{module_name}.hook")
    )


_DEFAULT_TEMPLATE = """#!/usr/bin/env bash
set -u
PLUGIN_NAME="{{PLUGIN_NAME}}"
PYTHON="{{PYTHON_EXECUTABLE}}"
MODULE="{{PYTHON_MODULE}}"
export PYTHONUNBUFFERED=1
export NATIVEAGENTS_PLUGIN_NAME="$PLUGIN_NAME"
"$PYTHON" -m "$MODULE" "$@"
rc=$?
if [ "$rc" = "2" ]; then exit 2; fi
exit 0
"""
