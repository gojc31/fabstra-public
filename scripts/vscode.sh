#!/usr/bin/env bash
# VSCode window whose Claude Code sessions run on the routed model.
# Usage: ./vscode.sh [folder]
# Uses a separate VSCode profile dir so it works even while your normal VSCode
# is open (a running VSCode ignores env vars from new launches otherwise).
# Extensions are shared; settings in that window start fresh.
FOLDER="${1:-.}"

ANTHROPIC_BASE_URL="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}" \
ANTHROPIC_AUTH_TOKEN="${MODEL_ROUTER_KEY:-my-proxy-key}" \
code -n --user-data-dir "${TMPDIR:-/tmp}/vscode-model-router" "$FOLDER"
