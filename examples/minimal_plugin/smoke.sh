#!/usr/bin/env bash
# Smoke test for minimal-plugin.
# Replays synthetic hook JSON through the dispatcher and asserts audit rows exist.
#
# Usage:
#   bash examples/minimal_plugin/smoke.sh
#
# Prerequisites: nativeagents-sdk must be installed in the active virtualenv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$SCRIPT_DIR"
SESSION_ID="smoke-$(date +%s)"

echo "==> Smoke test: minimal-plugin (session=$SESSION_ID)"

# --------------------------------------------------------------------------- #
# Step 1: install the plugin into an isolated home
# --------------------------------------------------------------------------- #
SMOKE_HOME="$(mktemp -d)"
trap 'rm -rf "$SMOKE_HOME"' EXIT

export NATIVEAGENTS_HOME="$SMOKE_HOME"
export HOME="$SMOKE_HOME"   # isolate ~/.claude writes too
mkdir -p "$SMOKE_HOME/.claude"

echo "--- Installing plugin into $SMOKE_HOME ---"
pip install -q -e "$PLUGIN_DIR"
python -m nativeagents_sdk.cli.main install "$PLUGIN_DIR" 2>/dev/null || true

# --------------------------------------------------------------------------- #
# Step 2: replay a PreToolUse + PostToolUse pair directly through the hook module
# --------------------------------------------------------------------------- #
PRE_JSON=$(cat <<EOF
{
  "hook_event_name": "PreToolUse",
  "session_id": "$SESSION_ID",
  "cwd": "/tmp",
  "tool_name": "Read",
  "tool_input": {"file_path": "/tmp/test.txt"}
}
EOF
)

POST_JSON=$(cat <<EOF
{
  "hook_event_name": "PostToolUse",
  "session_id": "$SESSION_ID",
  "cwd": "/tmp",
  "tool_name": "Read",
  "tool_input": {"file_path": "/tmp/test.txt"},
  "tool_result": "file contents"
}
EOF
)

echo "--- Firing PreToolUse ---"
echo "$PRE_JSON" | python -m minimal_plugin.hook
echo "--- Firing PostToolUse ---"
echo "$POST_JSON" | python -m minimal_plugin.hook

# --------------------------------------------------------------------------- #
# Step 3: assert two audit rows were written
# --------------------------------------------------------------------------- #
DB="$SMOKE_HOME/audit.db"
if [ ! -f "$DB" ]; then
  echo "FAIL: audit.db not found at $DB" >&2
  exit 1
fi

ROW_COUNT=$(python3 - <<PYEOF
import sqlite3, sys
conn = sqlite3.connect("$DB")
count = conn.execute(
    "SELECT COUNT(*) FROM events WHERE session_id=? AND plugin_name='minimal-plugin'",
    ("$SESSION_ID",)
).fetchone()[0]
conn.close()
print(count)
PYEOF
)

echo "--- Audit rows for session $SESSION_ID: $ROW_COUNT ---"
if [ "$ROW_COUNT" -lt 2 ]; then
  echo "FAIL: expected >= 2 audit rows, got $ROW_COUNT" >&2
  exit 1
fi

echo "==> PASS: minimal-plugin smoke test complete"
