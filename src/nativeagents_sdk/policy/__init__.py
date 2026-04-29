"""Policy DSL matcher primitives (v0.2).

The SDK owns the *matcher* — four match modes (contains, regex, glob, shell)
used in plugin policy rules.  Policy *definitions* (YAML detector files,
rule evaluation, violation projection) stay in plugins.

Example::

    from nativeagents_sdk.policy import Matcher, MatchMode

    spec = {"regex": r"rm\\s+-rf", "why": "destructive rm"}
    reason = Matcher.match_spec(spec, field="command", value="rm -rf /")
    # reason == "destructive rm"
"""

from nativeagents_sdk.policy.matcher import Matcher, MatchMode

__all__ = ["Matcher", "MatchMode"]
