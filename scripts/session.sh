#!/usr/bin/env bash
# Full interactive Claude Code session on a routed model.
# Usage: ./session.sh [model]
# Do NOT use this to route a Claude subscription login - see README "Play it safe".
MODEL="${1:-${MODEL_ROUTER_MODEL:-gpt-5.6-sol}}"

ANTHROPIC_BASE_URL="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}" \
ANTHROPIC_AUTH_TOKEN="${MODEL_ROUTER_KEY:-my-proxy-key}" \
claude --model "$MODEL"
