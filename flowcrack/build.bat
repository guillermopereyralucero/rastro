@echo off
REM FlowCrack - regenera decisiones.js desde decisiones.yaml. Doble-click amigable.
setlocal
pushd "%~dp0"
python "%~dp0build.py" %*
set EXITCODE=%ERRORLEVEL%
popd
if %EXITCODE% NEQ 0 pause
exit /b %EXITCODE%
