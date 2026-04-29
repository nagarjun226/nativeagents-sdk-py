"""Path resolution for the Native Agents ecosystem.

This is the ONLY module that reads NATIVEAGENTS_HOME and CLAUDE_HOME env vars.
No other module (and no plugin) should read ~/.nativeagents or ~/.claude directly.

Design constraints:
- Path functions NEVER create directories as a side effect.
- Call ensure_dir() explicitly when you need a directory to exist.
- atomic_write() is the only sanctioned way to write files safely.
"""

import contextlib
import os
import re as _re
import secrets
import tempfile
import warnings
from pathlib import Path
from typing import IO

# Reserved plugin names — these are SDK-owned subdirectory names.
RESERVED_PLUGIN_NAMES: frozenset[str] = frozenset(
    [
        "audit",
        "memory",
        "wiki",
        "policies",
        "plugins",
        "spool",
        "bin",
        "sidecar",
        "config",
        "meta",
        "system",
    ]
)

# Reserved plugin name prefixes (spec §15.5)
_RESERVED_PLUGIN_PREFIXES: tuple[str, ...] = ("native-", "sdk-", "system-")

# Plugin name regex: lowercase alphanumeric + hyphen, starting with letter, 1-40 chars.
_PLUGIN_NAME_RE = _re.compile(r"^[a-z][a-z0-9\-]{0,39}$")


def home() -> Path:
    """Return the Native Agents home directory.

    Resolves NATIVEAGENTS_HOME env var; defaults to ~/.nativeagents.
    Never creates the directory.
    """
    env_val = os.environ.get("NATIVEAGENTS_HOME")
    if env_val:
        return Path(env_val)
    return Path.home() / ".nativeagents"


def claude_home() -> Path:
    """Return the Claude Code home directory.

    Resolves CLAUDE_HOME env var; defaults to ~/.claude.
    Never creates the directory.
    """
    env_val = os.environ.get("CLAUDE_HOME")
    if env_val:
        return Path(env_val)
    return Path.home() / ".claude"


def plugin_dir(plugin_name: str) -> Path:
    """Return the state directory for a named plugin.

    Does NOT create the directory. Does NOT validate the plugin name —
    callers that accept user input should call validate_plugin_name() first.
    """
    return home() / "plugins" / plugin_name


def audit_db_path() -> Path:
    """Return the path to the shared SQLite audit database."""
    return home() / "audit.db"


def memory_dir() -> Path:
    """Return the memory plugin namespace directory."""
    return home() / "memory"


def wiki_dir() -> Path:
    """Return the wiki plugin namespace directory."""
    return home() / "wiki"


def wiki_inbox_dir() -> Path:
    """Return the wiki raw-inbox drop zone directory."""
    return home() / "wiki" / "raw-inbox"


def policies_dir() -> Path:
    """Return the policies directory (SDK-owned structure, plugin-populated files)."""
    return home() / "policies"


def spool_dir() -> Path:
    """Return the spool root directory."""
    return home() / "spool"


def bin_dir() -> Path:
    """Return the managed bin directory."""
    return home() / "bin"


def config_path() -> Path:
    """Return the path to config.yaml."""
    return home() / "config.yaml"


def ensure_layout() -> None:
    """Create the full ~/.nativeagents/ tree idempotently with mode 0o700.

    Call once at process startup (or from `nativeagents-sdk init-plugin`).
    Safe to call multiple times; does nothing if all directories already exist.
    """
    _root = home()
    for _dir in [
        _root,
        _root / "plugins",
        memory_dir(),
        wiki_dir(),
        policies_dir(),
        spool_dir(),
        bin_dir(),
    ]:
        _dir.mkdir(mode=0o700, parents=True, exist_ok=True)


def ensure_dir(path: Path) -> None:
    """Create directory and all parents if they don't exist (explicit mkdir -p).

    Uses mode 0o700 for new directories, matching the SDK's ownership rules.
    """
    path.mkdir(mode=0o700, parents=True, exist_ok=True)


def atomic_write(path: Path, data: bytes) -> None:
    """Write data to path atomically: write to tmp, fsync, then os.replace.

    Creates parent directories if necessary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a sibling temp file (same filesystem = same device for os.replace)
    suffix = f".tmp.{os.getpid()}.{secrets.token_hex(4)}"
    tmp_path = path.with_suffix(suffix)
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure, but don't swallow the original error.
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


def validate_plugin_name(name: str) -> str:
    """Validate and return the plugin name, raising ValueError if invalid.

    Rules:
    - Must match ^[a-z][a-z0-9-]{0,39}$
    - Must not be in RESERVED_PLUGIN_NAMES
    """
    if not _PLUGIN_NAME_RE.match(name):
        raise ValueError(
            f"Invalid plugin name {name!r}. "
            "Plugin names must match ^[a-z][a-z0-9-]{{0,39}}$ "
            "(lowercase, alphanumeric + hyphen, 1-40 chars, start with letter)."
        )
    if name in RESERVED_PLUGIN_NAMES:
        raise ValueError(
            f"Plugin name {name!r} is reserved. Reserved names: {sorted(RESERVED_PLUGIN_NAMES)}"
        )
    for prefix in _RESERVED_PLUGIN_PREFIXES:
        if name.startswith(prefix):
            raise ValueError(
                f"Plugin name {name!r} uses a reserved prefix {prefix!r}. "
                f"Reserved prefixes: {list(_RESERVED_PLUGIN_PREFIXES)}"
            )
    return name


def deprecated_env_path(
    legacy_var: str,
    default: Path,
    removal_version: str = "0.3.0",
) -> Path:
    """Return a path from a legacy env var, falling back to ``default``.

    Plugins that previously used their own home-dir env vars (e.g.
    ``AGENTAUDIT_HOME``, ``AGENTMEMORY_HOME``) should call this during
    migration to honour existing installs while steering users toward
    ``NATIVEAGENTS_HOME``.

    Emits a ``DeprecationWarning`` whenever the legacy var is present,
    directing users to unset it and rely on ``NATIVEAGENTS_HOME`` instead.
    The warning is raised at the caller's stack frame (``stacklevel=2``).

    Args:
        legacy_var: Name of the deprecated environment variable.
        default: The SDK-canonical path to use when the var is absent.
        removal_version: SDK version at which the legacy var will be ignored.

    Returns:
        ``Path(os.environ[legacy_var])`` if set, else ``default``.

    Example (in a plugin's config.py)::

        from nativeagents_sdk.paths import deprecated_env_path, plugin_dir

        def get_audit_home() -> Path:
            return deprecated_env_path(
                "AGENTAUDIT_HOME",
                default=plugin_dir("agentaudit"),
            )
    """
    val = os.environ.get(legacy_var)
    if val:
        warnings.warn(
            f"{legacy_var} is deprecated and will be ignored in SDK v{removal_version}. "
            f"Unset it and let NATIVEAGENTS_HOME control the layout instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Path(val)
    return default


def _make_temp_file(directory: Path) -> tuple[Path, IO[bytes]]:
    """Internal helper: create a named temp file in directory."""
    # Exposed for testing only; not part of public API.
    f = tempfile.NamedTemporaryFile(  # noqa: SIM115
        dir=directory,
        delete=False,
        prefix=".tmp.",
        suffix=f".{os.getpid()}",
    )
    return Path(f.name), f
