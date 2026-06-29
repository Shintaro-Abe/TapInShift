# TapInShift ユビキタス言語定義

## 1. 目的

この文書は TapInShift のドメイン用語、UI 用語、コード上の命名を統一するための用語集である。

## 2. ドメイン用語

| 日本語 | 英語・コード表現 | 定義 |
| --- | --- | --- |
| 打刻 | punch | 出勤または退勤を記録する操作 |
| 出勤 | clock in, `clock_in` | 勤務開始時刻を記録すること |
| 退勤 | clock out, `clock_out` | 勤務終了時刻を記録すること |
| 打刻種別 | `PunchType` | 出勤か退勤かを表す区分 |
| 勤務表 | timesheet | Excel 形式の勤務記録ファイル |
| 対象日 | target date | 打刻または編集の対象となる日付 |
| 反映 | reflection | Excel 勤務表へ値を書き込むこと |
| 反映状態 | `ReflectionStatus` | Excel 反映の状態 |
| 反映済み | `reflected` | Excel への書き込みが成功した状態 |
| 反映失敗 | `failed` | Excel への書き込みに失敗した状態 |
| 保留 | `pending` | 処理途中または未反映の状態 |
| 確認待ち | `needs_confirmation` | 分類が曖昧で自動反映しない状態 |
| 任意メモ | note | `メモ反映` ボタンで対象日に反映する自由記述 |
| 届出内容 | notice | 勤務した拠点、建物名、駅名などの場所情報 |
| 経費内容 | expense item, `expense_item` | 金額に対応する内容。交通費の場合は経路のみ |
| 金額 | amount | 経費の金額。整数で扱い、届出内容・経費内容には含めない |
| 監査ログ | audit log | 打刻・編集・反映結果を追跡するための SQLite 記録 |
| クラウドキュー | cloud queue | Slack 受付イベントを Windows Agent 起動後に処理するための DynamoDB 保存領域 |
| 同期 | sync | クラウドキューのイベントをローカル Excel へ反映し、結果をクラウドへ返す処理 |
| claim | claim | 未同期イベントを特定の Windows Agent が処理対象として確保すること |
| claim token | `claim_token` | claimしたWindows Agentを識別し、反映結果更新の所有者確認に使う値 |
| 未同期 | queued | Slackで受け付け済みだが、Windows Agentがまだ処理していない状態 |
| 処理中 | claimed | Windows Agentがclaim済みで、Excel反映中または結果報告前の状態 |
| 手動編集 | manual edit | Slack の編集モーダルから対象日を上書きする操作 |
| 時刻丸め | time rounding | 打刻時刻を指定分単位へ丸める処理 |
| 丸め単位 | rounding mode, `time_rounding.mode` | 丸めなし、5分、10分、15分、20分、30分のいずれか |
| アプリ設定 | app setting | Slack UI から変更した実行時設定 |

## 3. UI 用語

| 用語 | 定義 |
| --- | --- |
| Slack App Home | Slack アプリのホーム画面。TapInShift の主入力画面 |
| 出勤ボタン | App Home 上で出勤を記録するボタン |
| 退勤ボタン | App Home 上で退勤を記録するボタン |
| 日付選択 | 編集対象日を選ぶ datepicker |
| 丸め単位選択 | App Home 上で打刻時刻の丸め単位を選ぶ select |
| 編集モーダル | 対象日の勤務データを上書きする Slack modal |
| 状態メッセージ | App Home に表示する処理結果 |

## 4. 技術用語

| 用語 | 定義 |
| --- | --- |
| Socket Mode | Slack App が WebSocket 経由でイベントを受け取る方式 |
| HTTP Request URL | Slack App がHTTP POSTでイベントや操作を送る方式 |
| Lambda Function URL | AWS Lambda をHTTPS URLとして公開する機能 |
| DynamoDB | AWS のマネージドNoSQLデータベース |
| Slack Bolt | Slack App を Python で実装するためのフレームワーク |
| Block Kit | Slack UI を構成する JSON ベースの仕組み |
| xlwings | Python から Excel アプリを操作するライブラリ |
| SQLite | ローカルファイルとして動作するデータベース |

## 5. コード上の主要名

| 名前 | 種別 | 意味 |
| --- | --- | --- |
| `PunchType` | Enum | 打刻種別 |
| `ReflectionStatus` | Enum | 反映状態 |
| `Classification` | dataclass | 任意メモ分類結果 |
| `PunchEvent` | dataclass | 打刻イベント |
| `AppConfig` | dataclass | アプリケーション全体設定 |
| `ExcelConfig` | dataclass | Excel 書き込み設定 |
| `SlackConfig` | dataclass | Slack token 設定 |
| `CloudSyncConfig` | dataclass | クラウド同期設定 |
| `CloudEvent` | dataclass | クラウドキュー上の同期イベント |
| `CloudSyncService` | class | claim と claim token 付き同期結果更新 |
| `CloudExcelSynchronizer` | class | claim 済みイベントを Excel へ反映する同期ワーカー |
| `PunchService` | class | 打刻・編集の業務サービス |
| `EventStore` | class | SQLite 永続化 |
| `RuleBasedClassifier` | class | ローカルルールによる任意メモ分類 |
| `ExcelTimesheetWriter` | class | Excel 勤務表書き込み |

## 6. 状態値

| 値 | 日本語 | 意味 |
| --- | --- | --- |
| `pending` | 保留 | 初期状態または未反映 |
| `queued` | 未同期 | クラウドで受付済み、Windows Agent未処理 |
| `claimed` | 処理中 | Windows Agentが処理対象として確保済み |
| `reflected` | 反映済み | Excel 書き込み成功 |
| `failed` | 反映失敗 | Excel 書き込みまたは入力変換失敗 |
| `needs_confirmation` | 確認待ち | 分類結果が曖昧で自動反映しない |

## 7. 設定項目名

| 設定名 | 意味 |
| --- | --- |
| `timezone` | 打刻時刻のタイムゾーン |
| `database_path` | SQLite ファイルパス |
| `excel.path` | Excel 勤務表ファイルパス |
| `excel.sheet_name` | Excel 対象シート名 |
| `excel.columns.date` | 日付列 |
| `excel.columns.clock_in` | 出勤列 |
| `excel.columns.clock_out` | 退勤列 |
| `excel.columns.notice` | 届出内容列 |
| `excel.columns.expense_item` | 経費内容列 |
| `excel.columns.amount` | 金額列 |
| `time_rounding.mode` | 丸め単位 |
| `time_rounding.direction` | 丸め方向 |
| `time_rounding.clock_in_direction` | 出勤時刻の丸め方向 |
| `time_rounding.clock_out_direction` | 退勤時刻の丸め方向 |
| `SETTING#time_rounding.mode` | クラウド運用時にSlack UIで選択した丸め単位 |
| `app_settings.time_rounding.mode` | ローカル Bolt 運用時にSlack UIで選択した丸め単位 |
| `cloud_sync.endpoint` | Lambda Function URL |
| `cloud_sync.endpoint_env` | Lambda Function URL を読む環境変数名 |
| `cloud_sync.token_env` | 同期 API token を読む環境変数名 |
| `cloud_sync.poll_interval_seconds` | Windows Agent のポーリング間隔 |

## 8. 環境変数

| 環境変数 | 意味 |
| --- | --- |
| `SLACK_BOT_TOKEN` | Slack Bot Token |
| `SLACK_SIGNING_SECRET` | Slack署名検証用secret |
| `TAPINSHIFT_CLOUD_ENDPOINT` | Lambda Function URL |
| `TAPINSHIFT_SYNC_TOKEN` | Windows Agent同期API token |
| `TAPINSHIFT_EXCEL_PASSWORD` | Excel 開封パスワード |

## 9. 表記ルール

- 日本語文書では「出勤」「退勤」「打刻」「勤務表」「反映」を使う。
- コードでは `clock_in`, `clock_out`, `punch`, `timesheet`, `reflected` を使う。
- 「届出内容」は `notice` とする。
- 「経費内容」は `expense_item` とする。
- 「確認待ち」は `needs_confirmation` とする。
