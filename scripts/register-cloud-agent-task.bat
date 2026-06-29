@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "TASK_NAME=TapInShift Cloud Agent"
set "RUN_BAT=%ROOT_DIR%\scripts\start-cloud-agent.bat"

if not exist "%RUN_BAT%" (
  echo ERROR: %RUN_BAT% was not found.
  exit /b 1
)

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "\"%RUN_BAT%\"" /RL LIMITED /F
if errorlevel 1 (
  echo ERROR: Failed to register task: %TASK_NAME%
  exit /b 1
)

echo OK: Registered task: %TASK_NAME%
echo It will start TapInShift cloud polling when this Windows user logs on.
echo To run it now:
echo schtasks /Run /TN "%TASK_NAME%"

exit /b 0
