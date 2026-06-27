Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    python -m venv .venv
}

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    throw "Windows 用の仮想環境を作成できませんでした。既存の .venv が Linux/macOS 用の場合は、手動で .venv を退避または削除してから再実行してください。"
}

& .\.venv\Scripts\Activate.ps1
pip install -e .

Write-Host "OK: Python 環境を作成しました"
Write-Host "次に実機では必要に応じて実行してください: pip install xlwings"
Write-Host "確認: tapinshift-agent --help"
