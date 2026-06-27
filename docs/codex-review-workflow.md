# Codex レビュー方式

## 1. 目的

TapInShift の変更を Codex でレビューするときの標準手順を定義する。

レビューでは、見た目や文体よりも、バグ、回帰、セキュリティ、テスト不足、実機検証漏れ、ドキュメント齟齬を優先する。

## 2. 推奨手順

### 2.1 ローカルの未コミット差分レビュー

作業中またはコミット前は、まず現在の未コミット差分を Codex にレビューさせる。

```text
今回の未コミット差分をレビューしてください。バグ、回帰、セキュリティ、テスト不足を優先し、重要度順に指摘してください。
```

TapInShift では特に次を確認する。

- `config/config.local.json`、`data/`、実 Excel、SQLite、token、API key、Excel password が差分に含まれていない。
- Slack UI 変更には `tests/test_slack_app.py` がある。
- SQLite 保存内容の変更には保存確認テストと `show-db` の確認手段がある。
- Excel 書き込み変更には `tests/test_excel_writer.py` がある。
- `.steering/.../tasklist.md` が、自動テスト済み、実機確認済み、運用判断待ちを区別している。

### 2.2 Review pane

Codex App を使う場合は Review pane で差分を確認する。

用途:

- 未コミット差分、ブランチ差分、直近ターン差分を確認する。
- 行単位でコメントを付け、Codex に修正を依頼する。
- ステージ、アンステージ、revert を使ってコミット対象を調整する。

### 2.3 GitHub PR 上の Codex review

PR を使う場合は、PR コメントで Codex review を依頼する。

```text
@codex review
```

一回限りの観点を足す場合:

```text
@codex review for security regressions and missing tests
```

GitHub 側の Codex review は重大な問題に絞られるため、細かいドキュメント表現や運用メモの確認はローカルレビューで先に行う。

### 2.4 Codex Security plugin

秘密情報、認証、ファイル操作、外部通信、入力処理のリスクがある変更では、Codex Security plugin を使う。

```text
Use $codex-security:security-diff-scan to review my current uncommitted changes for security regressions.
```

TapInShift では、Slack token、OpenAI API key、Excel password、SQLite、実 Excel ファイルを扱うため、リリース前や大きめの変更では security diff scan を推奨する。

## 3. レビュー後の処理

1. 指摘がある場合は、重要度の高いものから修正する。
2. 修正後に関連テストを実行する。
3. `docs/` と `.steering/` に齟齬がないか確認する。
4. 秘密情報や実データが Git に入っていないことを確認する。
5. コミット前に `git diff --cached --name-status` を確認する。

## 4. 今回の自動レビュー結果

2026-06-27 時点のレビューでは、`scripts/timesheet_tools.py show-db` が古い SQLite スキーマで `app_settings` テーブル未作成の場合に失敗し得る点を修正した。

対応:

- `app_settings` テーブルがない場合も `show-db` が落ちないようにした。
- `tests/test_timesheet_tools.py` を追加し、古い DB と新しい DB の両方を検証した。
- 全テストは `34` 件 PASS。

## 5. 参照

- Codex Review pane: `https://developers.openai.com/codex/app/review`
- Codex code review in GitHub: `https://developers.openai.com/codex/integrations/github`
- Codex Security plugin change review: `https://developers.openai.com/codex/security/plugin/code-changes`
- Codex Skills: `https://developers.openai.com/codex/skills`
- Codex Plugins: `https://developers.openai.com/codex/plugins`
