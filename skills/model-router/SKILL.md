---
description: How to run Claude Code sessions, one-shot workers, and subagents on any model through the local proxy - model IDs, env config, and the three usage modes
---

# Model Router - routing knowledge

This skill teaches the three ways to run work on a routed model (any model your
proxy serves), and how to switch models. The proxy is CLIProxyAPI running
locally; it holds the user's OTHER subscription logins (ChatGPT/Codex, Gemini,
Grok, Kimi). The main Claude session always stays on its normal direct login.

## Configuration (shared by everything in this plugin)

| Env var | Default | Meaning |
|---|---|---|
| `MODEL_ROUTER_URL` | `http://127.0.0.1:8317` | proxy address |
| `MODEL_ROUTER_KEY` | `my-proxy-key` | an `api-keys` entry from the proxy's config.yaml |
| `MODEL_ROUTER_MODEL` | `gpt-5.6-sol` | default routed model |
| `MODEL_ROUTER_EFFORT` | `low` | default worker effort |

## Mode 1 - orchestrator + worker (the flagship): `/fabsol <brief>`

Your main model plans and verifies; the routed model does 100% of the building
via headless calls. Cheapest way to ship real builds - see the fabsol command.

## Mode 2 - one-shot worker run (any model, one task)

```bash
ANTHROPIC_BASE_URL="${MODEL_ROUTER_URL:-http://127.0.0.1:8317}" \
ANTHROPIC_AUTH_TOKEN="${MODEL_ROUTER_KEY:-my-proxy-key}" \
claude -p "the task" \
  --model "${MODEL_ROUTER_MODEL:-gpt-5.6-sol}" \
  --effort "${MODEL_ROUTER_EFFORT:-low}" \
  --bare --max-turns 20 --permission-mode acceptEdits
```

Or use the wrapper: `scripts/worker.sh "the task" [model] [effort]`
(`scripts/worker.ps1` on Windows).

## Mode 3 - full session on a routed model (terminal or VSCode)

`scripts/session.sh [model]` (or `session.ps1`) launches a whole Claude Code
terminal session on the routed model. `scripts/vscode.sh [folder]` (or
`vscode.ps1`) does the same for a VSCode window - it uses a separate VSCode
profile dir because an already-running VSCode ignores new env vars. In such a
session, the plugin's `worker` subagent also resolves, so subagents can run on
routed models too.

## Switching models

Any ID the proxy serves works everywhere a model is named. Discover what your
proxy serves:

```bash
curl -s "${MODEL_ROUTER_URL:-http://127.0.0.1:8317}/v1/models" \
  -H "Authorization: Bearer ${MODEL_ROUTER_KEY:-my-proxy-key}"
```

Only logged-in providers appear. Set `MODEL_ROUTER_MODEL` to switch the default
everywhere at once, or pass a model per call. See the README's model table for
provider login commands.

## Hard rule

NEVER set `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` on the main session's
environment or route a Claude subscription login through the proxy - Anthropic's
terms ban subscription OAuth in third-party tools. Routed env vars belong on
individual headless calls (or a deliberate scripts/session launch for
non-Claude models) only.
