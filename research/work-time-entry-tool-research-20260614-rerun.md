# 勤務時間入力ツール 事前調査

作成日: 2026-06-14

## 1. 結論

条件付きの第一候補は **Microsoft Teams + Power Automate Desktop + ローカルExcel** です。

理由は、今回の条件が「モバイルで打刻」「自宅PCローカルのExcelへ入力」「Excelを開く時にパスワードが必要」という組み合わせであり、クラウドAPIだけでは完結しにくいためです。Power Automate Desktopは、ローカルPC上のExcelやデスクトップ操作を自動化できるため、有力候補です。

ただし、会社のMicrosoft 365 / Teamsテナントを使えること、クラウドフローからデスクトップフローを起動するためのマシン登録、Power Automate Premium等の有償ライセンス要否を確認できることが前提です。これらが満たせない場合は、**Slack + Pythonローカルエージェント + xlwings** を同等の有力候補として扱います。

ただし、勤務表の相対パス、Excel形式、パスワード方式、入力列の仕様が未確定です。実装前に勤務表の実ファイルで検証が必要です。

## 2. Thought / Action / Observation

| 区分 | 内容 |
|---|---|
| Thought | 要件は「チャットUI」「AI分類」「ローカルのパスワード付きExcel更新」の3領域に分かれる。最も難しいのは、クラウドやモバイルから自宅PCローカルExcelへ安全に書き込む部分。 |
| Action | Gemini Skillで調査を実施し、Slack、LINE、Teams、Discord、Excel自動化、生成AIの構造化出力を公式情報で確認した。 |
| Observation | Slack/Teams/Discordはボタンと入力フォームを作りやすい。LINEはLIFFを使えば柔軟な画面を作れる。Excel更新はMicrosoft Graphよりも、ローカルPC上で動くPower Automate DesktopまたはPythonエージェントが適している。 |

## 3. Gemini Skill利用状況

| 項目 | 結果 |
|---|---|
| 使用Skill | `.codex/skills/gemini/scripts/gemini-ask.sh` |
| モデル | `pro` |
| 実行結果 | Codex通常サンドボックスではネットワーク制限により認証プロンプト検出で停止。ネットワーク許可付きで再実行し、調査結果を取得。 |
| 扱い | Gemini出力は助言として扱い、重要な事実は公式Webで確認した。 |
| 注意 | Gemini出力内にURLの誤記と、根拠が弱い市場表現があったため、本文では採用しない。 |

## 4. 前提条件と未確定事項

| 項目 | 状況 | 実装前の確認 |
|---|---|---|
| 勤務表パス | `<勤務表の相対パス>` のまま未指定 | 実ファイルの相対パスが必要 |
| Excel形式 | Excel形式のみ指定 | `.xlsx` / `.xlsm` / `.xls` の確認が必要 |
| パスワード | 「開くためのパスワード」あり | ファイル暗号化か、シート保護かを確認 |
| 入力列 | 届出内容、経費内容、金額、出勤、退勤など | 列名、行の探し方、日付形式の確認が必要 |
| 丸め | 5/10/15/20/30分刻みを選択可能 | 切り上げ、切り捨て、四捨五入のルール確認が必要 |
| 編集 | 日付送信で編集画面を返す | 編集画面の範囲、承認フロー、履歴保存の確認が必要 |

## 5. 公式情報ベースの調査結果

### 5.1 コミュニケーションツール

| ツール | ボタン | テキスト入力 | 編集画面 | 評価 |
|---|---:|---:|---:|---|
| Slack | 可能。Block Kitのbutton elementを利用 | 可能。Modalやinput系要素を利用 | 可能。Modalやメッセージ更新で実装 | 実装しやすい |
| LINE | 可能。Flex Messageやアクションを利用 | Messaging APIだけでは弱い。LIFFを使うと実装しやすい | LIFFで実装可能 | 日本の個人利用では強い |
| Microsoft Teams | 可能。Adaptive Cards / card actionsを利用 | 可能。Adaptive CardsのInput.Textを利用 | 可能。Adaptive CardsやBotで実装 | Microsoft環境と相性がよい |
| Discord | 可能。Componentsのbuttonを利用 | 可能。Modalとtext inputを利用 | 可能。Interactionで実装 | 個人・小規模向け |

### 5.2 Excel更新方式

| 方式 | ローカルExcel | パスワード付きExcel | メリット | 注意点 |
|---|---:|---:|---|---|
| Power Automate Desktop | 強い | UI操作で対応しやすい | Excelやデスクトップ操作を自動化できる | Windows PC前提。安定化には実機検証が必要 |
| Python + xlwings / pywin32 | 強い | Excelアプリ経由なら対応しやすい | 細かい制御が可能 | Windows + Excelインストール前提 |
| Python + msoffcrypto-tool + openpyxl | 低 | 復号は可能 | Excelを起動せず読める可能性 | msoffcrypto-toolは主に復号用途。openpyxlは開封パスワード付き保存やExcel固有機能の保持に弱く、書き戻し要件を満たしにくい |
| Microsoft Graph Excel API | 弱い | 条件と合いにくい | クラウド保存のExcelには強い | OneDrive for Business / SharePoint等の保存先が前提。ローカルPC直置きには不向き |
| RPA製品 | 強い | UI操作で対応可能 | 既存Excelを壊しにくい | コスト、保守、実行環境の管理が重い |

### 5.3 生成AIによる仕分け

| 方式 | 内容 | 評価 |
|---|---|---|
| OpenAI Structured Outputs | JSON Schemaに沿って、届出内容、経費内容、金額などを構造化する | 推奨 |
| Gemini structured output | Google系でまとめる場合の候補 | 有力 |
| ルール + AI | 金額抽出は正規表現、分類はAIに分担 | 実務向き |

生成AIは補助に留め、最終的には次のような構造に正規化してからExcelへ書き込むのが安全です。

```json
{
  "notice": "交通遅延",
  "expense_item": "電車代",
  "amount": 320,
  "confidence": 0.92,
  "needs_confirmation": false
}
```

## 6. 市場・競合の見方

| 分類 | 例 | 今回要件との関係 |
|---|---|---|
| 勤怠管理SaaS | KING OF TIME、ジョブカン勤怠管理、freee人事労務など | 打刻、集計、申請は強い。ただし既存の自宅PCローカルExcelへ直接入力する要件とはズレる |
| チャット連携 | Slack、Teams、LINE、DiscordのBot | ワンタップ打刻の入口として使える |
| 自動化基盤 | Power Automate、n8n、Zapier、Makeなど | チャットと処理基盤をつなげる候補 |
| RPA | Power Automate Desktop、UiPath等 | パスワード付きExcelやローカルPC操作に強い |
| 独自開発 | Python/Node.js + Bot API + ローカル常駐エージェント | 条件に最も合わせやすいが、保守責任が大きい |

市場には勤怠SaaSや打刻アプリは多いですが、「任意のチャットからワンタップし、自宅PCローカルのパスワード付きExcelへ自動入力する」条件は標準機能よりも個別開発向きです。

## 7. 選択肢5案

| # | 選択肢 | 推奨度 | 理由 |
|---:|---|---:|---|
| 1 | Teams + Power Automate Desktop + ローカルExcel | 4 | Microsoft系でまとまり、ローカルExcel操作に強い。ただしテナント、マシン登録、有償ライセンス確認が前提 |
| 2 | Slack + Pythonローカルエージェント + xlwings | 4 | チャットUIが作りやすく、Excel制御も柔軟 |
| 3 | LINE + LIFF + Pythonローカルエージェント | 3 | モバイル操作は良いが、LIFF画面の作成が必要 |
| 4 | Discord + Pythonローカルエージェント | 3 | 個人・小規模では作りやすいが、業務利用の統制は弱い |
| 5 | n8n / Zapier / Make + ローカル実行部品 | 2 | ノーコード寄りだが、ローカルExcelとパスワード対応が難所 |

### 7.1 案1: Teams + Power Automate Desktop + ローカルExcel

| 項目 | 内容 |
|---|---|
| 推奨度 | 4 |
| サービス | Microsoft Teams、Power Automate Desktop |
| 言語 | 低コード中心。必要に応じてPowerShellまたはPython |
| 実行環境 | 自宅Windows PC |
| コミュニケーションツール | Teams |
| 勤務表保管先 | 自宅PCローカル |
| メリット | ローカルPC上のExcel操作に向く。Microsoft環境で統一しやすい。 |
| デメリット | Teams BotやPower Automateの権限設計が必要。Windows PCが起動している必要がある。クラウドからデスクトップフローを起動するには、マシン登録、接続設定、Premiumライセンスが必要となる可能性が高い。 |

### 7.2 案2: Slack + Pythonローカルエージェント + xlwings

| 項目 | 内容 |
|---|---|
| 推奨度 | 4 |
| サービス | Slack、OpenAIまたはGemini API |
| 言語 | Python |
| 実行環境 | 自宅Windows PC + 外部から到達できる中継API |
| コミュニケーションツール | Slack |
| 勤務表保管先 | 自宅PCローカル |
| メリット | Slackのボタン、Modal、日付指定編集が実装しやすい。PythonでExcel処理を細かく制御できる。 |
| デメリット | 外部から自宅PCへ安全に届ける仕組みが必要。Bot運用と秘密情報管理が必要。 |

### 7.3 案3: LINE + LIFF + Pythonローカルエージェント

| 項目 | 内容 |
|---|---|
| 推奨度 | 3 |
| サービス | LINE Messaging API、LIFF、OpenAIまたはGemini API |
| 言語 | TypeScript、Python |
| 実行環境 | LIFF用Webホスティング + 自宅Windows PC |
| コミュニケーションツール | LINE |
| 勤務表保管先 | 自宅PCローカル |
| メリット | スマートフォンで使いやすい。個人利用に合う。 |
| デメリット | 「ボタン横にテキストボックス」はMessaging API単体では作りにくく、LIFFが必要になりやすい。 |

### 7.4 案4: Discord + Pythonローカルエージェント

| 項目 | 内容 |
|---|---|
| 推奨度 | 3 |
| サービス | Discord Bot、OpenAIまたはGemini API |
| 言語 | PythonまたはTypeScript |
| 実行環境 | 自宅Windows PC + Bot実行環境 |
| コミュニケーションツール | Discord |
| 勤務表保管先 | 自宅PCローカル |
| メリット | Components、Modal、Interactionで必要UIを作れる。個人開発では始めやすい。 |
| デメリット | 会社業務の正式ツールとしては採用しにくい場合がある。 |

### 7.5 案5: n8n / Zapier / Make + ローカル実行部品

| 項目 | 内容 |
|---|---|
| 推奨度 | 2 |
| サービス | n8n、Zapier、Make、Power Automate等 |
| 言語 | 低コード。必要に応じてJavaScript/Python |
| 実行環境 | クラウド自動化サービス + 自宅Windows PC |
| コミュニケーションツール | Slack、Teams、LINE、Discordのいずれか |
| 勤務表保管先 | 自宅PCローカル |
| メリット | 連携の試作が早い。運用画面がある。 |
| デメリット | ローカルPCのパスワード付きExcel更新は結局カスタム部品が必要になりやすい。 |

## 8. 比較表

| 観点 | 案1 Teams | 案2 Slack | 案3 LINE | 案4 Discord | 案5 自動化基盤 |
|---|---|---|---|---|---|
| 初期実装のしやすさ | 中 | 中 | 中 | 高 | 中 |
| モバイル操作 | 高 | 高 | 高 | 高 | 利用ツール次第 |
| ボタン + テキスト入力 | 高 | 高 | 中 | 高 | 利用ツール次第 |
| 日付指定編集 | 高 | 高 | 高 | 高 | 利用ツール次第 |
| ローカルExcel対応 | 高 | 高 | 高 | 高 | 中 |
| パスワード付きExcel対応 | 中〜高 | 中〜高 | 中〜高 | 中〜高 | 中 |
| 業務利用のしやすさ | 高。ただし会社テナント前提 | 高 | 中 | 低〜中 | 中 |
| 保守性 | 高 | 中 | 中 | 中 | 中 |

## 9. 推奨アーキテクチャ

```mermaid
flowchart LR
    U[スマートフォン] --> C[Teams / Slack / LINE / Discord]
    C --> B[Bot / Webhook]
    B --> Q[打刻キュー]
    Q --> A[自宅PCローカルエージェント]
    A --> AI[生成AI分類]
    A --> X[パスワード付きExcel勤務表]
    X --> A
    A --> C
```

ローカルPCが停止している場合に備え、チャットから受けた打刻は一度キューへ保存する構成が必要です。Excelへの反映は、自宅PCのローカルエージェントが起動している時に処理します。

## 10. 業務・運用リスク

| リスク | 内容 | 対応 |
|---|---|---|
| 社内規程 | 勤怠表の自動入力、パスワード解除、自宅PC保管が許可されるか不明 | 実装前に会社規程と承認者を確認する |
| 監査証跡 | 勤怠記録は後から説明できる必要がある | 打刻時刻、反映時刻、編集者、編集前後の値をログに残す |
| 改ざん耐性 | Excelへ直接書くと変更履歴が弱くなりやすい | 元入力イベントとExcel反映結果を別DBまたはログに保存する |
| 排他制御 | ユーザーがExcelを開いている時に自動書き込みすると失敗や競合が起きる | ファイルロック検知、リトライ、失敗通知を実装する |
| PC停止・スリープ | 自宅PCが停止中だとExcelへ反映できない | キューへ保存し、PC起動時に再処理する |
| パスワード管理 | パスワード変更時に自動化が停止する | OS資格情報ストア等に保管し、更新手順を決める |
| ライセンス | Power Automate Desktopをクラウドから起動する場合、有償ライセンスが必要となる可能性がある | Microsoftの最新ライセンスを確認してから採用判断する |

## 11. 実装前に決める事項

| 項目 | 決める内容 |
|---|---|
| 勤務表ファイル | 相対パス、拡張子、シート名 |
| パスワード | 保管方法、入力方法、ローテーション方法 |
| 日付判定 | どの列・行を対象日として扱うか |
| 時刻丸め | 切り上げ、切り捨て、四捨五入 |
| AI分類 | 低信頼度時に確認画面を出すか |
| 編集履歴 | 誰が、いつ、何を変更したかを残すか |
| PC停止時 | キューに貯めるか、失敗通知するか |
| Excel排他制御 | Excelをユーザーが開いている時のリトライ、通知、手動反映方法 |
| 利用主体 | 会社のM365/Teamsテナントを使うのか、個人利用なのか |
| ライセンス | Power Automate Premium、RPA、Bot運用費用の上限 |

## 12. ソース

### 公式ドキュメント

| 分類 | ソース |
|---|---|
| Slack Button element | https://docs.slack.dev/reference/block-kit/block-elements/button-element/ |
| Slack Interactivity | https://docs.slack.dev/interactivity/handling-user-interaction/ |
| LINE Flex Message | https://developers.line.biz/en/docs/messaging-api/using-flex-messages/ |
| LINE LIFF | https://developers.line.biz/en/docs/liff/overview/ |
| Teams Card types / Adaptive Cards | https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-reference |
| Adaptive Cards input validation | https://learn.microsoft.com/en-us/adaptive-cards/authoring-cards/input-validation |
| Discord Components | https://docs.discord.com/developers/components/reference |
| Discord Interactions | https://docs.discord.com/developers/interactions/receiving-and-responding |
| Power Automate Desktop | https://learn.microsoft.com/en-us/power-automate/desktop-flows/introduction |
| Power Automate machine management | https://learn.microsoft.com/en-us/power-automate/desktop-flows/manage-machines |
| Microsoft Graph Excel | https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0 |
| xlwings | https://docs.xlwings.org/en/stable/ |
| msoffcrypto-tool | https://msoffcrypto-tool.readthedocs.io/en/latest/ |
| OpenAI Structured Outputs | https://developers.openai.com/api/docs/guides/structured-outputs |
| Gemini API structured output | https://ai.google.dev/gemini-api/docs/structured-output |
| n8n integrations | https://docs.n8n.io/integrations/ |

### 競合・市場調査で参照した分類

| 分類 | 補足 |
|---|---|
| 勤怠管理SaaS | 既存製品は勤怠管理そのものには強いが、今回の「自宅PCローカルExcel直接入力」とは要件が異なる。 |
| チャットBot | Slack、Teams、LINE、Discordはいずれも打刻の入口には使える。 |
| 自動化/RPA | ローカルExcelや既存業務ファイルを扱う場合は、Power Automate Desktopなどのデスクトップ自動化が候補になる。 |

## 13. Claude Codeレビュー

対話式の `claude` でレビューを試行したが、この端末実行ではTUI出力を回収できず、レビュー結果を取得できなかった。

その後、対話式 Claude Code（レビュアー設定）による事後レビュー結果が追記されたため、主要指摘を本文へ反映した。`claude -p` は非対話式実行であり、この環境では従量課金化リスクを避けるため使用していない。

## 14. レビュー指摘と反映状況（2026-06-14 追記）

対話式 Claude Code（レビュアー設定）による事後レビュー結果を追記する。本レビューの主要指摘は本文へ反映済み。

### 14.1 総合判定

**問題あり**（致命的なハルシネーションは無し / 推奨度の過大評価と実装リスク記載不足が主）。

- ハルシネーション（捏造URL・捏造仕様）: **検出されず**。疑わしかった4件のURL（Discord / OpenAI / Gemini / Teams）は実在を確認済み。
- 一方、推奨度5の根拠の弱さ、実装・運用リスクの欠落、比較表の整合性に複数の指摘あり。

### 14.2 反映状況

| 指摘 | 反映 |
|---|---|
| 案1の推奨度5が過大 | 推奨度を4へ変更し、会社M365テナント、マシン登録、Premiumライセンス確認を前提化 |
| 業務・コンプライアンスリスク不足 | 「業務・運用リスク」章を追加 |
| msoffcrypto-tool + openpyxlの過小評価 | 評価を低へ変更し、書き戻し要件を満たしにくい旨を明記 |
| 比較表のパスワード対応評価 | 「中〜高」に修正し、実機検証前提を残した |
| Gemini構造化出力の参照先 | Gemini APIの公式Structured outputページへ差し替え |
| Teams参照先がlegacy寄り | Teamsカード種別/Adaptive Cardsの現行説明ページへ差し替え |

### 14.3 指摘事項（重大度順）

| ID | 重大度 | 該当箇所 | 問題 | 期待・安全側の対応 |
|---|---|---|---|---|
| H-1 | High | 9, 99, 116行目 | 案1（Teams + PAD）推奨度5に、モバイル→自宅PCの起動経路とライセンス費用が未反映。モバイル/Teamsイベントからクラウドフロー経由でデスクトップフローを起動するにはマシン登録（マシンランタイム/オンプレミスゲートウェイ）とPower Automate Premium（有償）が必要になる可能性が高い。 | デメリットに起動経路と費用を明記し、推奨度を再評価。 |
| H-2 | High | 文書全体 | 業務・コンプライアンス上のリスク（自動化・パスワード解除の社内許可可否、勤怠記録の正確性・改ざん耐性・監査証跡）が未記載。 | 専用節または「実装前に決める事項」へ追加。 |
| M-1 | Medium | 59行目 | 方式3（msoffcrypto-tool + openpyxl）の「再暗号化」を過小評価。msoffcrypto-toolは復号専用で再暗号化機能なし、openpyxlは暗号化保存不可かつ書式・図・ピボットを失う。実質ブロッカーの可能性。 | 「書き戻しにはExcel/COM併用が事実上必要」と踏み込む。 |
| M-2 | Medium | 179行目 | 比較表のパスワード対応評価の根拠薄弱。案1（PAD）「高」と案2（xlwings）「中」の差の根拠なし。ローカルExcel対応が案1〜4すべて「高」で差別化要素が消失。 | 評価差の根拠を明記、または評価を揃える。 |
| M-3 | Medium | 230行目 | Gemini構造化出力のソースが「Gemini Enterprise Agent Platform」（エンタープライズ製品）で、案で想定する一般「Gemini API」と不一致。 | `https://ai.google.dev/gemini-api/docs/structured-output` 等へ差し替え。 |
| M-4 | Medium | 9章・10章 | 運用リスクの欠落（ユーザーがExcelを開いている間のファイルロック/排他制御、PCスリープ時の挙動、パスワードローテーション時の破綻）。 | 「実装前に決める事項」へ排他制御・スリープ対策を追加。 |
| L-1 | Low | 221行目 | Teamsカードアクションの引用先が公式に「legacy」と明記されたページ。 | Adaptive Cards公式ハブ等の現行ページへ更新。 |
| L-2 | Low | 5〜9章 vs 全体 | 文脈（自宅PC・モバイル打刻・個人利用寄り）と推奨（Teams=5）の整合性に懸念。M365テナント前提を最上位にするのは過大評価の可能性。 | 利用主体（会社テナント有無）を前提条件に明記し、推奨を条件付きに。 |
| L-3 | Low | 229行目 | OpenAI構造化出力URL。新ポータル `developers.openai.com/api/docs` は実在確認済みだが、末尾サブパスの厳密一致は未確認。 | リンク切れ確認。 |

### 14.4 修正すべき文言

| 箇所 | before | after |
|---|---|---|
| 9行目 | 最初の実装候補として最も現実的です。 | 最も現実的な候補の一つだが、モバイル起点でPADを起動する経路（クラウドフロー＋マシン登録）とPremiumライセンス費用の確認を前提とする。 |
| 59行目 | 復号は可能 / 書式、マクロ、再暗号化、互換性の検証が必要 | 復号のみ可能（再暗号化機能なし）。openpyxlは書式・図・ピボットを失い、開封パスワード再設定も困難なため、書き戻し要件を満たしにくい。 |
| 116行目（案1デメリット） | Teams BotやPower Automateの権限設計が必要。Windows PCが起動している必要がある。 | （上記に加え）モバイル起点の起動にはクラウド→デスクトップ連携（マシンランタイム/ゲートウェイ）とPremiumライセンスが必要となる可能性が高い。 |
| 7行目 | 推奨は Microsoft Teams + Power Automate Desktop + ローカルExcel です。 | 同上に加え、利用主体（会社M365テナントの有無）を条件として併記する。 |

### 14.5 追加確認が必要な点

1. 利用主体: 会社のM365/Teamsテナントを使えるのか、個人利用か（推奨順位が変わる）。
2. PADのライセンス: クラウド→デスクトップ起動に必要なライセンス階層と月額。
3. 勤務表の自動入力可否: 社内規程上、パスワード解除・自動書き込みが許容されるか。
4. パスワード種別: 「開封パスワード（暗号化）」か「シート/ブック保護」か（4章でも未確定）。
5. 未検証ソース: Slack / LINE / xlwings / msoffcrypto / Graph / n8n / Power Automate の各URLは標準的だが個別未検証。

### 14.6 検証ギャップ

- ソースURLは疑わしかったURLを中心に実地確認した。残りの市場分類は実装判断前に追加確認する。
- PADのパスワード開封対応は実ファイルで未検証。クラウドからデスクトップフローを起動する場合のPremium要件はMicrosoft Learnの機械管理ドキュメントで確認したが、最終費用は最新の契約条件で確認する。
- 本文書はコードではないため、テスト/lint/型チェックは対象外。
