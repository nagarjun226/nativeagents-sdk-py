"""Tests for the public API contract of nativeagents_sdk."""

from __future__ import annotations


def test_version_exported() -> None:
    """__version__ is accessible at the package top level."""
    import nativeagents_sdk

    assert hasattr(nativeagents_sdk, "__version__")
    assert isinstance(nativeagents_sdk.__version__, str)
    assert nativeagents_sdk.__version__ != ""


def test_all_declared() -> None:
    """nativeagents_sdk.__all__ is declared and non-empty."""
    import nativeagents_sdk

    assert hasattr(nativeagents_sdk, "__all__")
    assert isinstance(nativeagents_sdk.__all__, list)
    assert len(nativeagents_sdk.__all__) > 0


def test_all_members_importable() -> None:
    """Every name in __all__ is actually importable from the package."""
    import nativeagents_sdk

    for name in nativeagents_sdk.__all__:
        assert hasattr(nativeagents_sdk, name), f"{name!r} is in __all__ but not on the module"


def test_no_unexpected_public_names() -> None:
    """Every name in __all__ appears in dir(nativeagents_sdk)."""
    import nativeagents_sdk

    all_set = set(nativeagents_sdk.__all__)
    dir_set = set(dir(nativeagents_sdk))
    missing = all_set - dir_set
    assert not missing, f"In __all__ but not in dir(): {missing}"


def test_version_pep440() -> None:
    """__version__ is a valid PEP 440 version string."""
    import re

    import nativeagents_sdk

    pep440_re = re.compile(
        r"^(\d+)\.(\d+)\.(\d+)"
        r"(\.?(a|b|rc)\d+)?"
        r"(\.post\d+)?"
        r"(\.dev\d+)?$"
    )
    assert pep440_re.match(nativeagents_sdk.__version__), (
        f"Not a valid PEP 440 version: {nativeagents_sdk.__version__!r}"
    )


def test_submodule_imports_do_not_pollute_top_level() -> None:
    """Importing submodules does not add unexpected names to the top-level namespace."""
    import nativeagents_sdk
    from nativeagents_sdk import audit, hooks, memory, paths  # noqa: F401

    # After importing submodules the top-level __all__ must not have grown
    assert "__version__" in nativeagents_sdk.__all__
    # Submodule imports as names are fine; __all__ should not auto-expand
    unexpected = [n for n in nativeagents_sdk.__all__ if n not in {"__version__"}]
    assert not unexpected, f"Unexpected entries appeared in __all__: {unexpected}"
