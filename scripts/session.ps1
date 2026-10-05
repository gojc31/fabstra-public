# Full interactive Claude Code session on a routed model.
# Usage: .\session.ps1 [model]
# Do NOT use this to route a Claude subscription login - see README "Play it safe".
param(
    [string]$Model = $(if ($env:MODEL_ROUTER_MODEL) { $env:MODEL_ROUTER_MODEL } else { "gpt-5.6-sol" })
)

$saved = @{
    ANTHROPIC_BASE_URL   = $env:ANTHROPIC_BASE_URL
    ANTHROPIC_AUTH_TOKEN = $env:ANTHROPIC_AUTH_TOKEN
}
$env:ANTHROPIC_BASE_URL   = if ($env:MODEL_ROUTER_URL) { $env:MODEL_ROUTER_URL } else { "http://127.0.0.1:8317" }
$env:ANTHROPIC_AUTH_TOKEN = if ($env:MODEL_ROUTER_KEY) { $env:MODEL_ROUTER_KEY } else { "my-proxy-key" }
try {
    claude --model $Model
} finally {
    $env:ANTHROPIC_BASE_URL   = $saved.ANTHROPIC_BASE_URL
    $env:ANTHROPIC_AUTH_TOKEN = $saved.ANTHROPIC_AUTH_TOKEN
}
