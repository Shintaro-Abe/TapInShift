@echo off
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

if not exist ".venv\Scripts\tapinshift-agent.exe" (
  echo ERROR: .venv\Scripts\tapinshift-agent.exe was not found.
  echo Run scripts\setup-local.ps1 first.
  exit /b 1
)

if not exist ".env.local" (
  echo ERROR: .env.local was not found.
  echo Create .env.local in the repository root.
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%ROOT_DIR%'; .\scripts\load-env-local.ps1; if (-not $env:TAPINSHIFT_EXCEL_PASSWORD) { throw 'TAPINSHIFT_EXCEL_PASSWORD is not set. Add it to .env.local or Windows user environment.' }; .\.venv\Scripts\tapinshift-agent.exe --config config\config.local.json --poll-cloud }"

exit /b %ERRORLEVEL%
