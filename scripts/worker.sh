#!/usr/bin/env bash
# One-shot headless run on a routed model.
# Usage: ./worker.sh "task" [model] [effort]
TASK="${1:?usage: worker.sh \"task\" [model] [effort]}"
MODEL="${2:-${MODEL_ROUTER_MODEL:-gpt-5.6-sol}}"
EFFORT="${3:-${MODEL_ROUTER_EFFORT:-low}}"

ANTHROPIC_BASE_URL="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}" \
ANTHROPIC_AUTH_TOKEN="${MODEL_ROUTER_KEY:-my-proxy-key}" \
claude -p "$TASK" --model "$MODEL" --effort "$EFFORT" \
  --bare --max-turns 20 --permission-mode acceptEdits
