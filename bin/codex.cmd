@echo off
rem Shim for cmd/PowerShell: delegates to the bash shim so both share one routing rule
rem (model calls via the local model-router proxy; CODEX_DIRECT=1 bypasses).
"C:\Program Files\Git\usr\bin\bash.exe" "%USERPROFILE%\bin\codex" %*
exit /b %ERRORLEVEL%
