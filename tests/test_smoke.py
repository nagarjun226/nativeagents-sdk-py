"""Smoke tests: verify the package imports and exposes __version__."""

import nativeagents_sdk


def test_version_exists() -> None:
    assert hasattr(nativeagents_sdk, "__version__")
    assert isinstance(nativeagents_sdk.__version__, str)
    assert nativeagents_sdk.__version__ == "0.2.0"


def test_import_paths() -> None:
    from nativeagents_sdk import paths  # noqa: F401


def test_import_config() -> None:
    from nativeagents_sdk import config  # noqa: F401


def test_import_schema() -> None:
    from nativeagents_sdk.schema import audit, events, frontmatter, manifest, plugin  # noqa: F401


def test_import_audit() -> None:
    from nativeagents_sdk import audit  # noqa: F401


def test_import_memory() -> None:
    from nativeagents_sdk import memory  # noqa: F401


def test_import_hooks() -> None:
    from nativeagents_sdk import hooks  # noqa: F401


def test_import_spool() -> None:
    from nativeagents_sdk import spool  # noqa: F401


def test_import_install() -> None:
    from nativeagents_sdk import install  # noqa: F401


def test_import_plugin() -> None:
    from nativeagents_sdk import plugin  # noqa: F401
