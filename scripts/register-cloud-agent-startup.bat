@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "RUN_BAT=%ROOT_DIR%\scripts\start-cloud-agent.bat"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_BAT=%STARTUP_DIR%\TapInShift Cloud Agent.bat"

if not exist "%RUN_BAT%" (
  echo ERROR: %RUN_BAT% was not found.
  exit /b 1
)

if not exist "%STARTUP_DIR%" (
  echo ERROR: Startup folder was not found: %STARTUP_DIR%
  exit /b 1
)

(
  echo @echo off
  echo call "%RUN_BAT%"
) > "%STARTUP_BAT%"

if errorlevel 1 (
  echo ERROR: Failed to create startup launcher: %STARTUP_BAT%
  exit /b 1
)

echo OK: Registered startup launcher:
echo %STARTUP_BAT%
echo It will start TapInShift cloud polling when this Windows user logs on.

exit /b 0
