# Start CLIProxyAPI in the background if it is not already listening.
# Set $env:CLIPROXY_DIR to where you installed cli-proxy-api (default: ~\cli-proxy-api).
$dir = if ($env:CLIPROXY_DIR) { $env:CLIPROXY_DIR } else { Join-Path $HOME "cli-proxy-api" }
$url = if ($env:MODEL_ROUTER_URL) { $env:MODEL_ROUTER_URL } else { "http://127.0.0.1:8317" }
$port = ([uri]$url).Port

$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "proxy already running at $url"
} else {
    Start-Process -FilePath (Join-Path $dir "cli-proxy-api.exe") `
        -ArgumentList "-config", (Join-Path $dir "config.yaml") -WindowStyle Hidden
    Start-Sleep -Seconds 2
    Write-Host "proxy started at $url"
}
