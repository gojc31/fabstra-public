# VSCode window whose Claude Code sessions run on the routed model.
# Usage: .\vscode.ps1 [folder]
# Uses a separate VSCode profile dir so it works even while your normal VSCode
# is open (a running VSCode ignores env vars from new launches otherwise).
# Extensions are shared; settings in that window start fresh.
param([string]$Folder = ".")

$saved = @{
    ANTHROPIC_BASE_URL   = $env:ANTHROPIC_BASE_URL
    ANTHROPIC_AUTH_TOKEN = $env:ANTHROPIC_AUTH_TOKEN
}
$env:ANTHROPIC_BASE_URL   = if ($env:MODEL_ROUTER_URL) { $env:MODEL_ROUTER_URL } else { "http://127.0.0.1:8317" }
$env:ANTHROPIC_AUTH_TOKEN = if ($env:MODEL_ROUTER_KEY) { $env:MODEL_ROUTER_KEY } else { "my-proxy-key" }
try {
    code -n --user-data-dir (Join-Path $env:TEMP "vscode-model-router") $Folder
} finally {
    $env:ANTHROPIC_BASE_URL   = $saved.ANTHROPIC_BASE_URL
    $env:ANTHROPIC_AUTH_TOKEN = $saved.ANTHROPIC_AUTH_TOKEN
}
