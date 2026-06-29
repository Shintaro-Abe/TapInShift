# TapInShift 機能設計書

## 1. 目的

この文書は TapInShift の機能構成、データ構造、画面、処理フローを定義する。

TapInShift は Slack App Home を入力画面とし、AWS Lambda Function URL が Slack 操作を DynamoDB に保存し、Windows Agent が未同期イベントをローカル Excel 勤務表へ反映する。

## 2. システム構成

```mermaid
graph TD
    U[ユーザー] --> S[Slack App Home]
    S --> L[Lambda Function URL]
    L --> CL[RuleBasedClassifier]
    L --> DDB[(DynamoDB)]
    A[tapinshift-agent] --> L
    A --> DB[(SQLite)]
    A --> XW[ExcelTimesheetWriter]
    XW --> XL[ローカルExcel勤務表]
```

## 3. 機能一覧

| 機能 | 概要 | 主な実装 |
| --- | --- | --- |
| App Home 表示 | Slack App Home に入力 UI を表示する | `cloud/lambda_app.py`, `slack_app.py` |
| 出勤打刻 | 出勤ボタンで時刻を記録し同期キューへ保存する | `cloud/lambda_app.py`, `cloud/business.py` |
| 退勤打刻 | 退勤ボタンで時刻を記録し同期キューへ保存する | `cloud/lambda_app.py`, `cloud/business.py` |
| 任意メモ分類 | メモから届出・経費・金額を分類する | `classifier.py` |
| 日別編集 | 日付選択から編集モーダルを開き、対象日編集を同期キューへ保存する | `cloud/lambda_app.py`, `cloud/business.py` |
| クラウド同期 | 未同期イベントを claim して Excel へ反映する | `cloud/worker.py`, `cloud/client.py` |
| 監査ログ | Excel 反映試行を SQLite に保存する | `storage.py` |
| 丸め単位変更 | App Home で選択した丸め単位を保存し、以降の打刻へ適用する | `cloud/lambda_app.py`, `cloud/business.py` |
| 設定診断 | 起動前に環境変数、Excel、依存関係を確認する | `app.py` |

## 4. ユースケース

```mermaid
flowchart LR
    User[ユーザー]
    User --> UC1[出勤を記録する]
    User --> UC2[退勤を記録する]
    User --> UC3[任意メモを分類して反映する]
    User --> UC4[対象日を編集する]
    User --> UC5[反映失敗を確認する]
    User --> UC6[丸め単位を変更する]
```

## 5. 主要フロー

### 5.1 出勤・退勤フロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Slack as Slack App Home
    participant Cloud as Lambda
    participant Queue as DynamoDB
    participant Agent as Windows Agent
    participant Excel as Excel

    User->>Slack: 出勤/退勤ボタン押下
    Slack->>Cloud: action payload
    Cloud-->>Slack: ack
    Cloud->>Queue: queued保存
    Agent->>Cloud: claim
    Cloud->>Queue: claimed更新
    Agent->>Excel: write_punch
    alt Excel 反映成功
        Agent->>Cloud: reflected報告
    else Excel 反映失敗
        Agent->>Cloud: failed報告
    end
```

### 5.2 丸め単位変更フロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Slack as Slack App Home
    participant Cloud as Lambda
    participant Store as DynamoDB

    User->>Slack: 丸め単位を選択
    Slack->>Cloud: static_select payload
    Cloud-->>Slack: ack
    Cloud->>Store: SETTING#time_rounding.mode保存
    Cloud->>Slack: App Home 状態更新
```

### 5.3 日別編集フロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Slack as Slack
    participant Agent as tapinshift-agent
    participant Service as PunchService
    participant Store as SQLite
    participant Excel as Excel

    User->>Slack: 日付選択
    Slack->>Agent: selected_date
    Agent->>Service: get_day_events
    Service->>Store: SELECT punch_events
    Agent->>Slack: 編集モーダル表示
    User->>Slack: 編集内容を保存
    Slack->>Agent: view submission
    Agent->>Service: update_day
    Service->>Excel: update_day
    Service->>Store: record_manual_edit
    Agent->>Slack: App Home 状態更新
```

## 6. コンポーネント設計

### 6.1 `app.py`

- CLI エントリポイント。
- `.env.local` を読み込む。
- JSON 設定を `AppConfig` に変換する。
- `--check-config` で起動前診断を行う。
- `--sync-now` でクラウド未同期イベントを1回同期する。
- `--poll-cloud` でクラウド未同期イベントを定期同期する。

### 6.2 `config.py`

- JSON 設定ファイルを読み込む。
- Excel、Slack、時刻丸め、SQLite、クラウド同期の設定を dataclass で保持する。
- `time_rounding.mode` は設定ファイル上の初期値として扱う。クラウド運用時は Slack UI で変更された丸め単位を DynamoDB の `SETTING#time_rounding.mode` に保存し、ローカル Bolt 運用時は SQLite の `app_settings` を優先する。
- 秘密情報は環境変数名だけを設定ファイルに持ち、値は実行時に環境変数から取得する。

### 6.3 `slack_app.py`

- Slack Bolt App を構築する。
- App Home、ボタンアクション、日付選択、編集モーダル送信を処理する。
- 丸め単位の `static_select` を表示し、選択変更を `PunchService` に委譲する。
- 出勤・退勤ボタンは任意メモ欄を送信せず、メモ分類は `メモ反映` ボタンでのみ実行する。
- Slack UI は Block Kit のみで構成する。
- ビジネスロジックは `PunchService` に委譲する。

### 6.4 `service.py`

- 打刻と編集のアプリケーションサービス。
- 打刻では現在時刻取得、時刻丸め、Excel 書き込み、SQLite 保存を統合する。
- 任意メモ分類は、後追いメモ反映時にだけ実行する。
- 丸め単位は `EventStore.get_setting("time_rounding.mode")` を優先し、未設定時は `AppConfig.time_rounding.mode` を使う。
- Excel 反映失敗時も SQLite に状態とエラーを保存する。

### 6.5 `classifier.py`

- 任意メモの分類を担当する。
- キーワードと正規表現によるローカルルール分類を行う。

### 6.6 `excel_writer.py`

- xlwings で Excel アプリを起動し、指定ファイルを開く。
- 対象日付の行を検索する。
- 打刻時は既存の出勤・退勤セルを上書きしない。
- 手動編集時は指定された値で上書きする。

### 6.7 `storage.py`

- SQLite の初期化と読み書きを担当する。
- 打刻イベントは `slack_event_id` を主キーとして upsert する。
- 手動編集は追記履歴として保存する。
- UI で変更したアプリ設定は `app_settings` に key-value で保存する。

### 6.8 `tapinshift.cloud`

- `lambda_app.py` は Slack HTTP Request URL、Slack署名検証、同期APIを処理する。
- `business.py` はクラウド受付イベントの作成、丸め、分類、二重打刻検出を担当する。
- `events.py` は DynamoDB 単一テーブルのイベント表現を担当する。
- `dynamodb_store.py` は DynamoDB 永続化を担当し、claim と結果更新では条件付き `UpdateItem` を使う。
- `worker.py` は Windows Agent 側で claim 済みイベントを Excel へ反映する。
- `client.py` は Windows Agent から Lambda Function URL へ同期APIを呼び出す。

## 7. データモデル

### 7.1 ドメインモデル

| モデル | 内容 |
| --- | --- |
| `PunchType` | `clock_in`, `clock_out` |
| `ReflectionStatus` | `pending`, `reflected`, `failed`, `needs_confirmation` |
| `Classification` | 届出内容、経費内容、金額、信頼度、確認要否 |
| `PunchEvent` | Slack イベント、ユーザー、打刻種別、時刻、分類、状態、エラー |

### 7.2 ER 図

```mermaid
erDiagram
    punch_events {
        text slack_event_id PK
        text slack_user_id
        text punch_type
        text tapped_at
        text reflected_at
        text note
        text notice
        text expense_item
        integer amount
        real confidence
        integer needs_confirmation
        text status
        text error
        text created_at
        text updated_at
    }

    manual_edits {
        integer id PK
        text slack_user_id
        text target_date
        text clock_in
        text clock_out
        text notice
        text expense_item
        integer amount
        text status
        text error
        text created_at
    }

    app_settings {
        text key PK
        text value
        text updated_at
    }
```

## 8. Slack 画面設計

### 8.1 App Home

```text
+----------------------------------+
| 状態メッセージ                    |
+----------------------------------+
| 任意メモ                          |
| [渋谷オフィス 新宿駅-渋谷駅 1200円] |
+----------------------------------+
| [出勤] [退勤] [メモ反映]           |
+----------------------------------+
| 表示・編集する日付                 |
| [yyyy-mm-dd]                      |
+----------------------------------+
| 丸め単位                          |
| [丸めなし / 5分 / 10分 / ...]      |
+----------------------------------+
```

任意メモは、届出内容と経費内容が同じ文に含まれる場合も分類結果を分離する。届出内容は勤務した拠点、建物名、駅名などの場所情報として扱う。経費内容は金額に対応する内容として扱い、交通費の場合は経路のみを入れる。例: `渋谷オフィス 新宿駅-渋谷駅 1200円` は `notice=渋谷オフィス`, `expense_item=新宿駅-渋谷駅`, `amount=1200` とする。

### 8.2 編集モーダル

```text
+----------------------------------+
| 勤務データ                        |
+----------------------------------+
| 対象日と記録済みイベント           |
| 出勤 [09:00]                      |
| 退勤 [18:00]                      |
| 届出内容 [渋谷オフィス]            |
| 経費内容 [新宿駅-渋谷駅]           |
| 金額 [320]                        |
| [保存] [閉じる]                   |
+----------------------------------+
```

金額表現は金額欄にのみ反映し、届出内容・経費内容からは除去する。

## 9. Excel 反映設計

### 9.1 行検索

- 設定の `excel.columns.date` 列を対象にする。
- `first_data_row` から `last_data_row` までを検索する。
- セル値を `date_format` で正規化し、対象日と一致する行を使う。

### 9.2 打刻時の書き込み

- 出勤は `clock_in` 列へ書く。
- 退勤は `clock_out` 列へ書く。
- 対象セルに既存値がある場合は上書きせず失敗にする。
- 任意メモ分類は行わず、届出内容、経費内容、金額は変更しない。

### 9.3 手動編集時の書き込み

- 出勤、退勤、届出内容、経費内容、金額を上書きする。
- 空欄は `None` として扱い、Excel 側の既存値を保持する。セルを消す操作は Excel 上で直接行う。
- 金額は整数へ変換する。変換できない場合は失敗として保存する。

## 10. API 設計

クラウドキュー同期では Lambda Function URL が HTTP API を持つ。

Slack 向け:

- `POST /slack/events`: `app_home_opened` と URL verification を処理する。
- `POST /slack/actions`: ボタン、select、datepicker、modal submission を処理する。

Windows Agent 向け:

- `POST /sync/claim`: `queued` または期限切れ `claimed` イベントを条件付き更新で `claimed` にして返す。成功したイベントだけを返し、`claim_token` を保存する。
- `POST /sync/reflected`: Excel 反映成功を記録する。対象イベントが `claimed` かつ `claim_token` が一致する場合だけ `reflected` に更新する。
- `POST /sync/failed`: Excel 反映失敗と retryable を記録する。対象イベントが `claimed` かつ `claim_token` が一致する場合だけ `failed` に更新する。

## 11. エラー処理

| エラー | 処理 |
| --- | --- |
| Slack token 未設定 | 起動失敗、または `--check-config` で MISSING |
| Excel パスワード未設定 | `--check-config` で MISSING |
| Excel 対象日なし | 打刻または編集を failed として保存 |
| 既存セルあり | 打刻を failed として保存 |
| 空メモ | クラウド受付時点で failed として保存 |
| メモ分類が曖昧 | Excel 反映せず needs_confirmation として保存 |
| 金額入力不正 | 日別編集を failed として保存し、Slackリクエスト自体は正常応答する |
| sync API の malformed JSON | 400 を返す |
