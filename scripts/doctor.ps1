# doctor.ps1 - Windows wrapper: runs doctor.sh under Git Bash so there is one set of checks.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
$bash = @("C:\Program Files\Git\bin\bash.exe", "C:\Program Files\Git\usr\bin\bash.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $bash) { Write-Host "Git for Windows not found (needs bash.exe under C:\Program Files\Git). Install from git-scm.com."; exit 1 }
$sh = Join-Path $PSScriptRoot "doctor.sh"
& $bash $sh
exit $LASTEXITCODE
