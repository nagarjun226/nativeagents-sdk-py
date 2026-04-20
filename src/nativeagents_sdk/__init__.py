"""Native Agents SDK — shared contract and primitives for the plugin ecosystem.

Only __version__ is exported at the top level. Import submodules explicitly:

    from nativeagents_sdk.paths import home, plugin_dir
    from nativeagents_sdk.audit import open_store, write_event
    from nativeagents_sdk.hooks import HookDispatcher
"""

from nativeagents_sdk.version import __version__

__all__ = ["__version__"]
