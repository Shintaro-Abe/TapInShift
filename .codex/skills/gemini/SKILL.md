---
name: gemini
description: Gemini CLI consultation skill for Codex. Use when the user asks to use Gemini, says "Geminiで調べて", invokes "$gemini", requests sourced web research, a second opinion, summaries, translations, or brainstorming via Gemini. OAuth-only operation is supported for human-operated interactive terminal use; Codex non-interactive execution must fail fast rather than opening browser authentication prompts.
---

# Gemini 相談窓口

Gemini CLIを読み取り専用の相談窓口として使う。

## 前提

- 認証はOAuthのみ。APIキーは使わない。
- コード変更はしない。
- リポジトリのファイルをGeminiに渡さない。
- Gemini CLI本体は `gemini` があればそれを使い、無ければ `npx --yes @google/gemini-cli` を使う。
- Codexの非対話実行では `timeout` と認証プロンプト検出でハングを防ぐ。
- 既定タイムアウトは30分。必要に応じて `GEMINI_ASK_TIMEOUT_SECONDS` で変更する。
- Gemini CLIのheadless実行にはネットワークアクセスが必要。Codexの通常サンドボックスでネットワークが制限されている場合は、ネットワーク許可付きで実行する。

## 重要な制約

Gemini CLIのOAuth認証は、人がVS Code統合ターミナルで操作する対話利用が基本。`gemini --prompt` のheadless実行は可能だが、アクセストークン更新やGemini API呼び出しにはネットワークアクセスが必要。

Codexの通常サンドボックスでネットワークが制限されていると、期限切れOAuthトークンのrefreshに失敗し、Gemini CLIがブラウザ認証確認へ落ちる場合がある。そのため、このCodex用Skillのヘルパーは `timeout` を付けてheadless実行を試し、認証プロンプトを検出したら即時失敗として扱う。

## 使い方

CodexからGemini調査が必要な場合は、次のヘルパーへプロンプトをstdinで渡す。

```bash
cat <<'PROMPT' | .codex/skills/gemini/scripts/gemini-ask.sh flash
あなたは該当分野の専門家です。次の問いに、Web検索で裏取りして回答してください。
- 結論を先に1〜3行で。続けて要点を箇条書き。各主張に出典URLを併記。
- 不確実な点は「不確実」と明言。

問い：<ここに問い>
PROMPT
```

モデルは引数で指定する。`flash` は通常調査、`pro` は深掘りに使う。

Codexから実行する場合、ネットワーク制限で失敗したら同じコマンドをネットワーク許可付きで再実行する。

## Authentication

OAuthのみ。初回はVS Code統合ターミナルで `gemini` を起動し、"Login with Google" を完了する。

`~/.gemini/oauth_creds.json` が生成されれば認証済み。

## Safety Rules

- `--approval-mode plan`、`--skip-trust`、隔離cwdで起動する。
- 認証プロンプトが出た場合は失敗として扱い、ブラウザ認証待ちを継続しない。
- ネットワーク制限によりOAuth token refreshやAPI呼び出しが失敗する場合がある。必要時はユーザー承認を得てネットワーク許可付きで再実行する。
- リポジトリのファイルはGeminiに渡さない。
- PII、資格情報、秘密情報をプロンプトに含めない。
- Gemini出力は助言として扱い、重要な事実は一次情報で確認する。
