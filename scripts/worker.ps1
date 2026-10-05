# One-shot headless run on a routed model.
# Usage: .\worker.ps1 "task" [model] [effort]
param(
    [Parameter(Mandatory=$true)][string]$Task,
    [string]$Model = $(if ($env:MODEL_ROUTER_MODEL) { $env:MODEL_ROUTER_MODEL } else { "gpt-5.6-sol" }),
    [string]$Effort = $(if ($env:MODEL_ROUTER_EFFORT) { $env:MODEL_ROUTER_EFFORT } else { "low" })
)

$saved = @{
    ANTHROPIC_BASE_URL   = $env:ANTHROPIC_BASE_URL
    ANTHROPIC_AUTH_TOKEN = $env:ANTHROPIC_AUTH_TOKEN
}
$env:ANTHROPIC_BASE_URL   = if ($env:MODEL_ROUTER_URL) { $env:MODEL_ROUTER_URL } else { "http://127.0.0.1:8317" }
$env:ANTHROPIC_AUTH_TOKEN = if ($env:MODEL_ROUTER_KEY) { $env:MODEL_ROUTER_KEY } else { "my-proxy-key" }
try {
    claude -p $Task --model $Model --effort $Effort --bare --max-turns 20 --permission-mode acceptEdits
} finally {
    $env:ANTHROPIC_BASE_URL   = $saved.ANTHROPIC_BASE_URL
    $env:ANTHROPIC_AUTH_TOKEN = $saved.ANTHROPIC_AUTH_TOKEN
}
