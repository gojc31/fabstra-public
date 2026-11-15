@echo off
rem geminipro shim for cmd/PowerShell: runs scripts\geminipro.py with the geminipro-lab
rem venv interpreter (GEMINIPRO_PYTHON overrides it), no bash. Same lookup as
rem bin/geminipro: next to this file first, then %MODEL_ROUTER_HOME%\scripts when
rem set, then %USERPROFILE%\model-router\scripts.
setlocal
set "GEMINIPRO_PY=%~dp0..\scripts\geminipro.py"
if not exist "%GEMINIPRO_PY%" if defined MODEL_ROUTER_HOME set "GEMINIPRO_PY=%MODEL_ROUTER_HOME%\scripts\geminipro.py"
if not exist "%GEMINIPRO_PY%" set "GEMINIPRO_PY=%USERPROFILE%\model-router\scripts\geminipro.py"
set "GEMINIPRO_EXE=%GEMINIPRO_PYTHON%"
if "%GEMINIPRO_EXE%"=="" set "GEMINIPRO_EXE=%USERPROFILE%\geminipro-lab\.venv\Scripts\python.exe"
"%GEMINIPRO_EXE%" "%GEMINIPRO_PY%" %*
exit /b %ERRORLEVEL%
