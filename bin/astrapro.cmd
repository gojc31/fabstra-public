@echo off
rem astrapro shim for cmd/PowerShell: runs scripts\astrapro.py with python directly
rem (no bash). Same lookup as bin/astrapro: next to this file first (the shareable
rem repo has bin\ and scripts\ side by side), then %USERPROFILE%\model-router\scripts.
setlocal
set "ASTRAPRO_PY=%~dp0..\scripts\astrapro.py"
if not exist "%ASTRAPRO_PY%" set "ASTRAPRO_PY=%USERPROFILE%\model-router\scripts\astrapro.py"
python "%ASTRAPRO_PY%" %*
exit /b %ERRORLEVEL%
