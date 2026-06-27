# モバイル打刻・勤務表自動入力ツール 事前調査

調査日: 2026-06-14

## 0. 前提

| 項目 | 内容 |
|---|---|
| 目的 | モバイル上のコミュニケーションツールから出勤・退勤をワンタップ送信し、自宅PCローカルのExcel勤務表へ自動入力する |
| 勤務表 | Excel形式。開くときにパスワード入力が必要 |
| 勤務表の相対パス | 未指定。実装前に確認が必要 |
| 入力UI | 出勤ボタン、退勤ボタン、任意入力テキストボックス |
| AI分類 | 任意入力文を「届出内容」「経費内容」「金額」に仕分ける |
| 時刻丸め | そのまま、5分、10分、15分、20分、30分刻みを選択可能にする |
| 編集 | 日付を送ると、その日の入力済み内容を表示し編集画面を返す |
| 指定Skill | GeminiのSkill指定あり。ただし、この環境ではGemini Skillが利用可能Skill一覧に存在しないため未使用 |

## 1. Thought / Action / Observation

| ステップ | 内容 |
|---|---|
| Thought | ワンタップ打刻は、Slack/Teams/DiscordのボタンUIなら実現しやすい。LINEは個人利用では強いが、リッチな入力画面や編集画面は工夫が必要。 |
| Action | 各コミュニケーションツールの公式ドキュメントで、ボタン、入力欄、モーダル、Webhook/APIの可否を確認した。 |
| Observation | 「ボタンの隣にテキストボックス」というUIは、Slack/Teams/Discordではモーダルやカード入力として実現しやすい。LINEはクイックリプライやポストバック中心で、同時入力はLIFFや別画面が必要になりやすい。 |
| Thought | 勤務表が自宅PCローカルかつパスワード付きExcelであるため、クラウド上のExcel APIだけでは条件に合わない可能性が高い。 |
| Action | Microsoft Graph Excel API、Office Scripts、Power Automate Desktop、Python Excelライブラリ、xlwingsを確認した。 |
| Observation | ローカルPC上のパスワード付きExcelを扱うなら、Windows上でExcel本体を操作するPower Automate DesktopまたはPython + Excel COM/xlwingsが現実的。Microsoft GraphやOffice ScriptsはOneDrive/SharePoint前提が強い。 |
| Thought | 任意入力文の分類は、生成AIの構造化出力を使うと列への反映が安定しやすい。 |
| Action | OpenAI Structured Outputs、Google Gemini/Vertex AIの構造化出力を確認した。 |
| Observation | JSON Schemaなどで「届出内容」「経費内容」「金額」を固定出力にすると、Excel転記前の検証がしやすい。 |

## 2. 公式情報の調査結果

### 2.1 コミュニケーションツール

| ツール | ボタン | テキスト入力 | 編集画面 | 実装しやすさ | コメント |
|---|---:|---:|---:|---:|---|
| Slack | 高 | 高 | 高 | 高 | Block Kit、ボタン、モーダル、インタラクションWebhookが揃っている。3秒以内の応答が必要。 |
| Microsoft Teams | 高 | 高 | 高 | 高 | Adaptive Cardsでボタンと入力を扱える。Microsoft 365環境との親和性が高い。 |
| Discord | 高 | 中 | 中 | 中 | ボタンとモーダル入力は可能。業務利用・管理面ではSlack/Teamsより弱い場合がある。 |
| LINE | 中 | 低〜中 | 中 | 中 | クイックリプライやポストバックは強い。自由入力とボタンを同一画面で扱うにはLIFFなどが必要になりやすい。 |

### 2.2 Excel・ローカルPC連携

| 方法 | ローカルExcel | パスワード付きExcel | 自宅PC常駐 | 実装難易度 | コメント |
|---|---:|---:|---:|---:|---|
| Power Automate Desktop | 高 | 高 | 高 | 中 | Windows上のExcel操作に向く。UI自動化も可能。Microsoft製で業務向き。 |
| Python + xlwings / Excel COM | 高 | 高 | 高 | 中 | Excel本体を開いて編集できる。柔軟だがWindows/Excel依存。 |
| Python + msoffcrypto-tool + openpyxl | 中 | 中 | 中 | 中〜高 | 暗号化解除後に編集する構成。書式・マクロ・保護の扱いは要検証。 |
| Microsoft Graph Excel API | 低 | 低 | 低 | 中 | OneDrive for Business/SharePoint上のExcel向け。ローカルPC条件とはズレる。 |
| Office Scripts + Power Automate | 低 | 低 | 低 | 中 | OneDrive for Business前提が強い。ローカル勤務表には不向き。 |

### 2.3 生成AI分類

| 方法 | 構造化出力 | 運用しやすさ | コメント |
|---|---:|---:|---|
| OpenAI Structured Outputs | 高 | 高 | JSON Schemaで列に対応した出力を固定しやすい。 |
| Google Gemini / Vertex AI Structured Output | 高 | 中 | Google Cloud環境に寄せる場合に有力。 |
| ルールベース分類 | 中 | 高 | 金額抽出など単純処理は安定。届出内容の判定は限界がある。 |
| AI + ルール併用 | 高 | 高 | 金額は正規表現、分類はAIのように分担すると堅い。 |

## 3. 市場調査

注意: 市場調査は、公式ドキュメントだけでは比較情報が不足するため、公開記事と公開百科情報も補助的に使用した。公式一次情報ではない情報は、実装判断前に必要に応じて再確認する。

| 観点 | 調査結果 |
|---|---|
| 勤怠管理市場 | 既存の勤怠管理SaaSは、モバイル打刻、GPS、承認、給与連携を重視している。 |
| 競争軸 | 「正確な打刻」「スマホ対応」「給与/会計連携」「法令対応」「管理者承認」が主要な差別化要素。 |
| 今回の独自性 | 既存SaaS置き換えではなく、既存のパスワード付きExcel勤務表へ自動入力する点が特徴。 |
| リスク | ローカルPC常駐、Excelパスワード、個人情報、AI分類結果の誤記入が運用リスクになる。 |
| 利用者体験 | Slack/LINE/Teams/Discordから打刻できるため、専用勤怠アプリを開かない点は強み。 |

## 4. 競合調査

| 分類 | 例 | 強み | 今回ツールとの差 |
|---|---|---|---|
| 勤怠管理SaaS | TimeClock Plus、Deputy、Rippling、Replicon、TimeTracker、Remoteなど | 打刻、承認、給与連携、管理画面が成熟 | 既存Excel勤務表への直接入力や個人ローカルPC運用は主目的ではない |
| 時間管理ツール | Toggl Track、TimeCamp、ManicTime、RescueTimeなど | 作業時間の可視化、プロジェクト別集計 | 出勤/退勤と会社指定勤務表への転記には別処理が必要 |
| 自動化ツール | Power Automate、n8n、Zapier、Makeなど | 各サービス連携が豊富 | パスワード付きローカルExcelの安定操作は設計が必要 |
| チャットBot | Slack Bot、Teams Bot、Discord Bot、LINE Bot | モバイルから自然に入力できる | Excel転記、AI分類、ローカルPC常駐を別途作る必要がある |

## 5. 選択肢 5案

### 比較表

| 順位 | 案 | サービス | 言語 | 実行環境 | コミュニケーションツール | 勤務表保管先 | 概要 |
|---:|---|---|---|---|---|---|---|
| 1 | Slack Bot + 自宅PC常駐Python | Slack API、OpenAI API、Windows Excel | Python | 自宅Windows PC | Slack | ローカルExcel | Slackのボタン/モーダルで受け、PC常駐アプリがExcelへ入力 |
| 2 | Teams Bot + Power Automate Desktop | Teams、Power Automate Desktop、AI BuilderまたはOpenAI | Power Automate / TypeScript | 自宅Windows PC + Microsoft 365 | Teams | ローカルExcel | Microsoft製品中心で構成 |
| 3 | LINE Bot + LIFF + 自宅PC常駐Python | LINE Messaging API、LIFF、OpenAI API | Python / TypeScript | 自宅Windows PC + Webhookサーバ | LINE | ローカルExcel | 日本の個人利用に強いLINEを入口にする |
| 4 | Discord Bot + 自宅PC常駐Python | Discord API、OpenAI API | Python / TypeScript | 自宅Windows PC | Discord | ローカルExcel | 個人・小規模向けに作りやすい |
| 5 | n8n等 + ローカル実行エージェント | n8n等、OpenAI API、Excel操作 | JavaScript / Python | クラウドまたは自宅PC + 自宅Windows PC | 複数対応 | ローカルExcel | ノーコード寄りで複数チャネル対応 |

### 案1: Slack Bot + 自宅PC常駐Python

| 項目 | 内容 |
|---|---|
| 推奨度 | 5/5 |
| 理由 | ボタン、入力、編集画面、Webhookの公式機能が揃っており、今回条件に最も合わせやすい。 |
| メリット | UIが作りやすい。モーダルで日付編集画面を返せる。業務用途として自然。 |
| デメリット | Slackワークスペースとアプリ設定が必要。個人LINEだけで完結したい場合は向かない。 |
| 注意点 | Slackインタラクションは短時間で応答が必要なため、Excel更新は非同期処理にする。 |

### 案2: Teams Bot + Power Automate Desktop

| 項目 | 内容 |
|---|---|
| 推奨度 | 4/5 |
| 理由 | Excel、Windows、Power Automate Desktopとの相性が高い。Microsoft 365を使っている場合は有力。 |
| メリット | Excel操作とWindows常駐処理をMicrosoft製品でまとめやすい。管理・監査に向く。 |
| デメリット | Microsoft 365ライセンスやBot/Power Automateの設定が重い。個人用途では過剰になりやすい。 |
| 注意点 | Office ScriptsやGraphはローカルExcelではなくOneDrive/SharePoint寄りなので、ローカル勤務表はDesktop Flowで扱う。 |

### 案3: LINE Bot + LIFF + 自宅PC常駐Python

| 項目 | 内容 |
|---|---|
| 推奨度 | 4/5 |
| 理由 | 日本のスマホ利用ではLINEが強く、個人の打刻導線として使いやすい。 |
| メリット | 普段使うLINEから打刻できる。通知・確認メッセージも自然。 |
| デメリット | ボタン横テキストボックスや編集画面はMessaging APIだけでは弱く、LIFFなどのWeb画面が必要。 |
| 注意点 | Webhookを受ける公開URLが必要。自宅PCへ直接到達させる場合はセキュリティ設計が重要。 |

### 案4: Discord Bot + 自宅PC常駐Python

| 項目 | 内容 |
|---|---|
| 推奨度 | 3/5 |
| 理由 | ボタンとモーダルは作れるが、業務勤怠の入口としてはSlack/Teams/LINEより優先度が下がる。 |
| メリット | Bot開発が比較的軽い。個人サーバーで試しやすい。 |
| デメリット | 会社・事務用途では採用しにくい場合がある。権限管理や監査の印象が弱い。 |
| 注意点 | 本番用途ではユーザー認証、操作ログ、誤操作防止を明確にする。 |

### 案5: n8n等 + ローカル実行エージェント

| 項目 | 内容 |
|---|---|
| 推奨度 | 3/5 |
| 理由 | 複数サービス連携は楽だが、パスワード付きローカルExcelの操作は結局ローカル実行部品が必要。 |
| メリット | Slack/Teams/LINEなど複数チャネルへ広げやすい。管理画面でフローを見やすい。 |
| デメリット | 月額費用、外部サービス依存、ローカルPC連携の複雑さが増える。 |
| 注意点 | 個人情報と勤務情報を外部自動化サービスへ流す範囲を確認する。 |

## 6. 推奨構成

最初の実装は「Slack Bot + 自宅PC常駐Python」を推奨する。

| レイヤー | 推奨 |
|---|---|
| モバイル入口 | Slack Bot |
| UI | Slack Block Kitのボタン、モーダル、日付入力 |
| Webhook受信 | FastAPI |
| キュー | SQLiteまたはローカルJSONキュー |
| AI分類 | OpenAI Structured Outputs、またはGemini Structured Output |
| Excel操作 | Python + xlwings / Excel COM |
| 実行場所 | 自宅Windows PC |
| 勤務表 | ローカルExcel。パスワードはOSの資格情報ストア等で管理 |
| 監査ログ | ローカルSQLiteに送信時刻、反映時刻、元テキスト、AI分類結果、編集履歴を保存 |

## 7. 実装時の注意点

| 注意点 | 内容 |
|---|---|
| Excelパスワード | ソースコードやログに書かない。Windows資格情報マネージャーや環境変数などで管理する。 |
| AI分類 | AI結果をそのまま信頼せず、金額は数値検証、分類は許可値チェックを行う。 |
| 時刻丸め | 「そのまま」「5/10/15/20/30分」をユーザー設定として保存する。丸め方向は切り捨て、切り上げ、四捨五入の確認が必要。 |
| 二重打刻 | 同一日の出勤/退勤が既にある場合は、上書き前に確認画面を返す。 |
| 編集 | 日付を受け取ったら、その日のレコードを読み出してモーダルに初期値を入れる。 |
| オフライン | 自宅PCが停止中の場合、Webhook受信側に一時保存し、PC起動後に同期する設計が必要。 |
| セキュリティ | Webhook署名検証、ユーザーID許可リスト、操作ログを必須にする。 |

## 8. 未決事項

| 項目 | 確認内容 |
|---|---|
| 勤務表パス | 相対パスが未指定。実ファイル位置が必要。 |
| Excel形式 | `.xlsx` か `.xlsm` か。マクロ・数式・保護シートの有無。 |
| パスワード種類 | ファイルを開くパスワードか、シート保護パスワードか、両方か。 |
| 入力先列 | 出勤、退勤、届出内容、経費内容、金額の列位置。 |
| 日付判定 | 日付行の検索方法。月別シートか、1シートに全期間か。 |
| 丸め方向 | 最寄り、切り上げ、切り捨てのどれにするか。 |
| 利用ツール | Slack/LINE/Teams/Discordのどれを第一候補にするか。 |
| AI利用 | OpenAI、Gemini、ローカルLLM、ルールベースのどれを許可するか。 |

## 9. ソース

### Slack

- Slack Developer Docs: Handling user interaction in your Slack apps  
  https://docs.slack.dev/interactivity/handling-user-interaction/
- Slack Developer Docs: Block Kit block elements  
  https://docs.slack.dev/reference/block-kit/block-elements/

### LINE

- LINE Developers: Use quick replies  
  https://developers.line.biz/en/docs/messaging-api/using-quick-reply/
- LINE Developers: Actions  
  https://developers.line.biz/en/docs/messaging-api/actions/
- LINE Developers: LIFF overview  
  https://developers.line.biz/en/docs/liff/overview/

### Microsoft Teams / Adaptive Cards

- Microsoft Learn: Add card actions in a bot  
  https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-actions
- Microsoft Learn: Adaptive Cards input validation  
  https://learn.microsoft.com/en-us/adaptive-cards/authoring-cards/input-validation

### Discord

- Discord Developer Docs: Component Reference  
  https://docs.discord.com/developers/components/reference
- Discord Developer Docs: Receiving and Responding to Interactions  
  https://docs.discord.com/developers/interactions/receiving-and-responding

### Excel / 自動化

- Microsoft Learn: Working with Excel in Microsoft Graph  
  https://learn.microsoft.com/en-us/graph/api/resources/excel
- Microsoft Learn: Platform limits and requirements with Office Scripts  
  https://learn.microsoft.com/en-us/office/dev/scripts/testing/platform-limits
- Microsoft Learn: Run Office Scripts with Power Automate  
  https://learn.microsoft.com/en-us/office/dev/scripts/develop/power-automate-integration
- Microsoft Learn: Introduction to desktop flows  
  https://learn.microsoft.com/en-us/power-automate/desktop-flows/introduction
- Microsoft Learn: Overview of AI Builder  
  https://learn.microsoft.com/en-us/ai-builder/overview
- openpyxl documentation: Protection  
  https://openpyxl.readthedocs.io/en/stable/protection.html
- msoffcrypto-tool documentation  
  https://msoffcrypto-tool.readthedocs.io/en/latest/
- xlwings documentation  
  https://docs.xlwings.org/en/stable/

### 生成AI

- OpenAI API Docs: Structured model outputs  
  https://developers.openai.com/api/docs/guides/structured-outputs
- Google Cloud: Structured output for Gemini  
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/control-generated-output

### 市場・競合

- TechRadar: Best time and attendance system of 2025  
  https://www.techradar.com/best/best-time-and-attendance-systems
- TechRadar: Best time management app of 2026  
  https://www.techradar.com/best/best-time-management-solution
- TechRadar: Best Microsoft Teams app of 2026  
  https://www.techradar.com/best/best-microsoft-teams-apps
- Wikipedia: Time and attendance  
  https://en.wikipedia.org/wiki/Time_and_attendance
- Wikipedia: Comparison of time-tracking software  
  https://en.wikipedia.org/wiki/Comparison_of_time-tracking_software
- Wikipedia: TimeClock Plus  
  https://en.wikipedia.org/wiki/TimeClock_Plus
- Wikipedia: Discord  
  https://en.wikipedia.org/wiki/Discord
- Wikipedia: Microsoft Teams  
  https://en.wikipedia.org/wiki/Microsoft_Teams
- Wikipedia: Line  
  https://en.wikipedia.org/wiki/Line_%28software%29
- Wikipedia: Slack  
  https://en.wikipedia.org/wiki/Slack_%28software%29
- n8n Docs: Integrations  
  https://docs.n8n.io/integrations/

## 10. Claude Codeレビュー

| 項目 | 結果 |
|---|---|
| レビュー依頼 | `claude "research/work-time-entry-tool-research.md をレビューしてください..."` をTTY付きで実行 |
| `claude -p` | 使用していない |
| 結果 | この実行環境ではClaude Codeの対話TUI出力を取得できず、レビュー結果を文書へ反映できなかった |
| 対応 | Claude Codeレビューは未完了。VS Codeの統合ターミナルで対話式 `claude` を開き、同じレビュー依頼を実行する必要がある |
