@echo off
rem Shim for cmd/PowerShell: delegates to the bash wrapper (bin/lanew needs
rem bash builtins - mkdir-based locking, `timeout`, stdin redirection - that
rem cmd.exe does not have). Same pattern as bin/codex.cmd, not bin/jev.cmd
rem (jev.cmd calls python directly because jev.py needs no shell mechanics).
"C:\Program Files\Git\usr\bin\bash.exe" "%USERPROFILE%\bin\lanew" %*
exit /b %ERRORLEVEL%
