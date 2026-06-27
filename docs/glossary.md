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
| 任意メモ | note | 打刻時に入力できる自由記述 |
| 届出内容 | notice | 遅延、休暇、早退など勤務表へ記載する届出 |
| 経費内容 | expense item, `expense_item` | 交通費など経費欄へ記載する内容 |
| 金額 | amount | 経費の金額。整数で扱い、届出内容・経費内容には含めない |
| 監査ログ | audit log | 打刻・編集・反映結果を追跡するための SQLite 記録 |
| 手動編集 | manual edit | Slack の編集モーダルから対象日を上書きする操作 |
| 時刻丸め | time rounding | 打刻時刻を指定分単位へ丸める処理 |

## 3. UI 用語

| 用語 | 定義 |
| --- | --- |
| Slack App Home | Slack アプリのホーム画面。TapInShift の主入力画面 |
| 出勤ボタン | App Home 上で出勤を記録するボタン |
| 退勤ボタン | App Home 上で退勤を記録するボタン |
| 日付選択 | 編集対象日を選ぶ datepicker |
| 編集モーダル | 対象日の勤務データを上書きする Slack modal |
| 状態メッセージ | App Home に表示する処理結果 |

## 4. 技術用語

| 用語 | 定義 |
| --- | --- |
| Socket Mode | Slack App が WebSocket 経由でイベントを受け取る方式 |
| Slack Bolt | Slack App を Python で実装するためのフレームワーク |
| Block Kit | Slack UI を構成する JSON ベースの仕組み |
| xlwings | Python から Excel アプリを操作するライブラリ |
| SQLite | ローカルファイルとして動作するデータベース |
| OpenAI Responses API | 任意メモ分類に使う OpenAI API |
| JSON Schema | OpenAI 分類結果を固定構造で受け取るための schema |

## 5. コード上の主要名

| 名前 | 種別 | 意味 |
| --- | --- | --- |
| `PunchType` | Enum | 打刻種別 |
| `ReflectionStatus` | Enum | 反映状態 |
| `Classification` | dataclass | 任意メモ分類結果 |
| `PunchEvent` | dataclass | 打刻イベント |
| `AppConfig` | dataclass | アプリケーション全体設定 |
| `ExcelConfig` | dataclass | Excel 書き込み設定 |
| `OpenAIConfig` | dataclass | OpenAI 分類設定 |
| `SlackConfig` | dataclass | Slack token 設定 |
| `PunchService` | class | 打刻・編集の業務サービス |
| `EventStore` | class | SQLite 永続化 |
| `OpenAIClassifier` | class | 任意メモ分類 |
| `ExcelTimesheetWriter` | class | Excel 勤務表書き込み |

## 6. 状態値

| 値 | 日本語 | 意味 |
| --- | --- | --- |
| `pending` | 保留 | 初期状態または未反映 |
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
| `openai.primary_model` | 主要分類モデル |
| `openai.fallback_model` | フォールバック分類モデル |
| `openai.confidence_threshold` | 確認待ち判定の信頼度しきい値 |

## 8. 環境変数

| 環境変数 | 意味 |
| --- | --- |
| `SLACK_BOT_TOKEN` | Slack Bot Token |
| `SLACK_APP_TOKEN` | Slack App Token |
| `OPENAI_API_KEY` | OpenAI API Key |
| `TAPINSHIFT_EXCEL_PASSWORD` | Excel 開封パスワード |

## 9. 表記ルール

- 日本語文書では「出勤」「退勤」「打刻」「勤務表」「反映」を使う。
- コードでは `clock_in`, `clock_out`, `punch`, `timesheet`, `reflected` を使う。
- 「届出内容」は `notice` とする。
- 「経費内容」は `expense_item` とする。
- 「確認待ち」は `needs_confirmation` とする。
