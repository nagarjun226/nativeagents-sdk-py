"""Exception hierarchy for the Native Agents SDK.

All SDK exceptions derive from SDKError. Callers can catch SDKError for
broad handling or the specific subclass for targeted handling.
"""


class SDKError(Exception):
    """Base exception for all Native Agents SDK errors."""


class ConfigError(SDKError):
    """Raised when config.yaml is invalid or cannot be loaded."""


class PluginManifestError(SDKError):
    """Raised when plugin.toml is invalid or cannot be loaded."""


class ManifestError(SDKError):
    """Raised when memory manifest.json is invalid or cannot be loaded."""


class FrontmatterError(SDKError):
    """Raised when a memory file's YAML frontmatter is invalid."""


class AuditStoreError(SDKError):
    """Raised when audit.db cannot be opened or written to."""


class IntegrityError(SDKError):
    """Raised when audit.db hash chain integrity check fails critically."""


class InstallError(SDKError):
    """Raised when plugin installation or registration fails."""


class DuplicatePluginError(SDKError):
    """Raised when two installed plugins declare the same name."""


class ConformanceError(SDKError):
    """Raised when a plugin fails the conformance harness."""
