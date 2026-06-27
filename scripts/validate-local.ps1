param(
    [string]$Source,
    [string]$Config = "config/config.local.json",
    [switch]$Force,
    [switch]$SkipCopy,
    [switch]$SkipInstall,
    [switch]$StartAgent,
    [switch]$ShowDb,
    [int]$DbLimit = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    Write-Host @"
TapInShift 実機検証を一括実行する。

使い方:
  .\scripts\validate-local.ps1 -Source "<原本のパス>.xlsx"

主なオプション:
  -Source PATH       原本の勤務表パス。検証用コピー作成に使う
  -Force            検証用コピーが既にある場合に上書きする
  -SkipCopy         検証用コピー作成を省略する
  -Config PATH      設定ファイル。既定: config/config.local.json
  -SkipInstall      pip install を省略する
  -StartAgent       チェック完了後に tapinshift-agent を起動する
  -ShowDb           SQLite の最新履歴を表示する
  -DbLimit N        -ShowDb の表示件数。既定: 5

事前に環境変数を設定する:
  `$env:TAPINSHIFT_EXCEL_PASSWORD="Excelのパスワード"
  `$env:SLACK_BOT_TOKEN="xoxb-..."
  `$env:SLACK_APP_TOKEN="xapp-..."
"@
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath が終了コード $LASTEXITCODE で失敗しました。"
    }
}

function Start-Step {
    param([string]$Name)
    Write-Host ""
    Write-Host "==> $Name"
}

Set-Location (Join-Path $PSScriptRoot "..")

if (-not $SkipCopy -and [string]::IsNullOrWhiteSpace($Source)) {
    Show-Usage
    throw "--Source を指定するか -SkipCopy を付けてください。"
}

if (-not (Test-Path $Config)) {
    throw "設定ファイルが見つかりません: $Config。config/config.example.json から config/config.local.json を作成してください。"
}

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    Start-Step ".venv を作成"
    Invoke-Native "python" @("-m", "venv", ".venv")
}

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    throw "Windows 用の仮想環境を作成できませんでした。既存の .venv が Linux/macOS 用の場合は、手動で .venv を退避または削除してから再実行してください。"
}

& .\.venv\Scripts\Activate.ps1

if (-not $SkipInstall) {
    Start-Step "Python 依存関係をインストール"
    Invoke-Native "python" @("-m", "pip", "install", "-e", ".")
    Invoke-Native "python" @("-m", "pip", "install", "xlwings")
}

if (-not $SkipCopy) {
    Start-Step "検証用コピーを作成"
    $copyArgs = @("scripts\timesheet_tools.py", "make-copy", "--config", $Config, "--source", $Source)
    if ($Force) {
        $copyArgs += "--force"
    }
    Invoke-Native "python" $copyArgs
}

Start-Step "単体テストを実行"
Invoke-Native "python" @("-m", "unittest", "discover", "-s", "tests")

Start-Step "設定チェックを実行"
Invoke-Native "tapinshift-agent" @("--config", $Config, "--check-config")

Start-Step "Excel の日付列を確認"
Invoke-Native "python" @("scripts\timesheet_tools.py", "inspect-dates", "--config", $Config)

if ($ShowDb) {
    Start-Step "SQLite の最新履歴を表示"
    Invoke-Native "python" @("scripts\timesheet_tools.py", "show-db", "--config", $Config, "--limit", "$DbLimit")
}

if ($StartAgent) {
    Start-Step "tapinshift-agent を起動"
    Write-Host "OK: チェック完了。tapinshift-agent を起動します。終了するまでこのターミナルを閉じないでください。"
    tapinshift-agent --config $Config
    exit $LASTEXITCODE
}

Write-Host "OK: 自動チェックが完了しました。Slack UI 検証へ進んでください。"
