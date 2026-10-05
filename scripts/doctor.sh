#!/usr/bin/env bash
# doctor.sh - check a machine is ready for FabStra / FabSol / fable-mode.
# Run from anywhere: bash "$MODEL_ROUTER_HOME/scripts/doctor.sh"
# Prints one line per check; exits 1 if any REQUIRED check fails.

here="$(cd "$(dirname "$0")/.." && pwd -P)"
url="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}"
fail=0
ok()   { printf '  ok    %s\n' "$1"; }
warn() { printf '  warn  %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }

echo "FabStra doctor - $(date +%F)"

# 1. env
if [ -n "${MODEL_ROUTER_HOME:-}" ]; then ok "MODEL_ROUTER_HOME=$MODEL_ROUTER_HOME"; else warn "MODEL_ROUTER_HOME not set (skills use it to find scripts/); this repo is at $here"; fi
cpd="${CLIPROXY_DIR:-$HOME/cli-proxy-api}"
if [ -f "$cpd/config.yaml" ]; then ok "proxy config: $cpd/config.yaml"; else bad "no proxy config at $cpd/config.yaml (set CLIPROXY_DIR or install CLIProxyAPI)"; fi

# 2. tools
for t in claude python node curl; do
  if command -v "$t" >/dev/null 2>&1; then ok "$t on PATH"; else bad "$t not on PATH"; fi
done

# 3. shims
for s in codex codex-pro codex-fast proxy-key proxy-pin; do
  if command -v "$s" >/dev/null 2>&1; then ok "shim $s on PATH ($(command -v "$s"))"; else bad "shim $s not on PATH - copy bin/ to ~/bin"; fi
done

# 4. proxy key + proxy up + models
key="$("$here/bin/proxy-key" 2>/dev/null)"
if [ -n "$key" ]; then ok "proxy-key resolves"; else bad "proxy-key cannot find a key (MODEL_ROUTER_KEY or api-keys: in config.yaml)"; fi
models="$(curl -s -m 5 "$url/v1/models" -H "Authorization: Bearer $key" 2>/dev/null)"
if [ -n "$models" ]; then
  ok "proxy answering at $url"
  for m in gpt-6-astra gpt-5.6-sol gpt-5.6-terra gpt-5.6-luna; do
    if printf '%s' "$models" | grep -q "\"$m\""; then ok "model served: $m"; else
      if [ "$m" = gpt-6-astra ]; then warn "model not served: $m (needs a Pro plan; skills fall back to Sol)"; else bad "model not served: $m"; fi
    fi
  done
else
  bad "nothing answering at $url - run scripts/start-proxy.sh (or .ps1)"
fi

# 5. codex CLI + agents + Pro home
if CODEX_DIRECT=1 codex --version >/dev/null 2>&1; then ok "codex CLI runs ($(CODEX_DIRECT=1 codex --version 2>/dev/null | head -1))"; else bad "codex CLI does not run (install the Codex app or npm package, or set CODEX_BIN)"; fi
for a in sol terra luna; do
  if [ -f "$HOME/.codex/agents/$a.toml" ]; then ok "codex agent $a"; else bad "missing ~/.codex/agents/$a.toml - copy from codex/agents/"; fi
done
if grep -q "model_providers.router" "$HOME/.codex/config.toml" 2>/dev/null; then ok "router provider in ~/.codex/config.toml"; else bad "no [model_providers.router] in ~/.codex/config.toml - merge codex/config.example.toml"; fi
pro="${CODEX_PRO_HOME:-$HOME/.codex-pro}"
if [ -f "$pro/auth.json" ]; then ok "Pro home logged in: $pro"; else warn "no login at $pro (only needed for native Astra; run: codex-pro login)"; fi
if [ -f "$pro/agents/spark.toml" ]; then ok "codex agent spark in Pro home"; else warn "no $pro/agents/spark.toml (Pro-only fast mechanic; copy from codex/agents/ - Astra uses luna without it)"; fi
if [ -f "$pro/cua-headless.mjs" ]; then ok "cua-headless.mjs in Pro home"; else warn "no $pro/cua-headless.mjs (only for 'use computer use' runs; copy from codex/)"; fi

# 6. Codex plugin companion (the Codex transport the skills call)
comp="$(ls -d "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | sort -V | tail -1)"
if [ -n "$comp" ]; then ok "codex-companion.mjs: $comp"; else bad "OpenAI Codex plugin for Claude Code not installed (/plugin install codex@openai-codex)"; fi

# 7. plugin / skills visible to Claude Code
if ls -d "$HOME"/.claude/plugins/cache/*/model-router/* >/dev/null 2>&1 || [ -d "$HOME/.claude/skills/fabstra" ]; then ok "model-router plugin or fabstra skill installed"; else warn "plugin not installed yet (/plugin marketplace add gojc31/fabstra-public, /plugin install model-router@gojc31)"; fi

echo
if [ "$fail" = 0 ]; then echo "All required checks passed."; else echo "Some required checks FAILED - see SETUP.md."; exit 1; fi
