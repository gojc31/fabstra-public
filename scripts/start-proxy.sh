#!/usr/bin/env bash
# Start CLIProxyAPI in the background if it is not already listening.
# Set CLIPROXY_DIR to where you installed cli-proxy-api (default: ~/cli-proxy-api).
DIR="${CLIPROXY_DIR:-$HOME/cli-proxy-api}"
URL="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}"
KEY="${MODEL_ROUTER_KEY:-my-proxy-key}"

if curl -s -o /dev/null --max-time 2 "$URL/v1/models" -H "Authorization: Bearer $KEY"; then
  echo "proxy already running at $URL"
else
  nohup "$DIR/cli-proxy-api" -config "$DIR/config.yaml" >/dev/null 2>&1 &
  sleep 2
  echo "proxy started at $URL"
fi
