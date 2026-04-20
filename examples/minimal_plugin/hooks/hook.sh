#!/usr/bin/env bash
# Native Agents plugin hook wrapper — minimal-plugin.
# Generated from nativeagents-sdk template — DO NOT EDIT.

set -u

PLUGIN_NAME="minimal-plugin"
PYTHON="python3"
MODULE="minimal_plugin.hook"

export PYTHONUNBUFFERED=1
export NATIVEAGENTS_PLUGIN_NAME="$PLUGIN_NAME"

"$PYTHON" -m "$MODULE" "$@"
rc=$?

if [ "$rc" = "2" ]; then
    exit 2
fi
exit 0
