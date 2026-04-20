#!/usr/bin/env bash
# Native Agents plugin hook wrapper.
# Generated from nativeagents-sdk template — DO NOT EDIT.
#
# Contract:
#   - stdin: JSON hook event payload from Claude Code
#   - env:   HOOK_EVENT_NAME (preferred) — the event type
#   - exit:  0 (always, unless explicit block with exit 2)
#
# This wrapper NEVER blocks Claude Code. Python-level errors are logged.

set -u
# Deliberately NOT set -e: the Python handler manages its own error flow.

PLUGIN_NAME="{{PLUGIN_NAME}}"
PYTHON="{{PYTHON_EXECUTABLE}}"
MODULE="{{PYTHON_MODULE}}"

export PYTHONUNBUFFERED=1
export NATIVEAGENTS_PLUGIN_NAME="$PLUGIN_NAME"

# Forward stdin + env + args to the Python entry point.
# The Python side is responsible for reading stdin, dispatching,
# logging errors, and exiting with 0 (or 2 for explicit block).
"$PYTHON" -m "$MODULE" "$@"
rc=$?

# Policy: propagate exit code 2 (explicit block).
# Otherwise force 0 so Claude Code is never blocked by plugin bugs.
if [ "$rc" = "2" ]; then
    exit 2
fi
exit 0
