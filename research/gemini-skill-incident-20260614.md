# Gemini Skill インシデント記録

日付: 2026-06-14

## 概要

Gemini Skillを使った調査で、Gemini CLIがブラウザ認証確認を表示したまま戻らず、調査処理が停止した。

## 影響

| 項目 | 内容 |
|---|---|
| 影響範囲 | Gemini Skillを使う非対話調査 |
| 直接影響 | Geminiから調査結果を取得できなかった |
| 追加リスク | 認証待ちで処理が止まり、作業が進まない |

## 原因

当初はGemini CLIのheadless modeとOAuthのみの相性問題と見ていたが、追加調査で主因はCodex通常サンドボックスのネットワーク制限だった。

`~/.gemini/oauth_creds.json` は存在していたが、access tokenは期限切れだった。通常であればrefresh tokenで更新されるが、Codexの通常コマンド実行ではネットワークが制限されるため更新に失敗し、Gemini CLIがブラウザ認証フローへ落ちた。

## 是正内容

| 対応 | 内容 |
|---|---|
| 失敗方式の変更 | `timeout` を付けてheadless実行を試し、認証プロンプトを検出したらexit 3で停止する |
| 認証判定 | `~/.gemini/oauth_creds.json` 等のOAuth状態を確認し、未認証ならexit 3で案内する |
| 起動方式 | `-p` ではなく明示的に `--prompt` を使用する |
| タイムアウト | pro調査を想定し、既定タイムアウトを30分にする |
| ドキュメント | Codex Skillと元Gemini Skillに、OAuthは対話ターミナル専用であることを明記した |
| 同期 | `/home/vscode/.codex/skills/gemini` にも修正版を配置した |
| 追加修正 | ネットワーク許可付きでheadless実行すればOAuth refresh後に成功することを確認した |

## 検証

| 検証 | 結果 |
|---|---|
| `bash -n .codex/skills/gemini/scripts/gemini-ask.sh` | OK |
| `bash -n gemini/scripts/gemini-ask.sh` | OK |
| `bash -n /home/vscode/.codex/skills/gemini/scripts/gemini-ask.sh` | OK |
| OAuthのみ、通常サンドボックスで `.codex/skills/gemini/scripts/gemini-ask.sh flash` | 認証プロンプト検出によりexit 3 |
| OAuthのみ、ネットワーク許可付きで `.codex/skills/gemini/scripts/gemini-ask.sh flash` | 成功 |

## 残る制約

OAuthのみでも、ネットワーク許可付きならCodexからGemini Skillをheadless実行できる。ただし通常サンドボックスではネットワーク制限により失敗する場合がある。

候補:

| 方法 | 備考 |
|---|---|
| OAuth + ネットワーク許可 | APIキー不要。Codex実行時にネットワーク許可が必要 |
| `GEMINI_API_KEY` | Google AI StudioのAPI keyを使う。秘密情報管理が必要 |
| `GOOGLE_API_KEY` | Google API keyを使う。秘密情報管理が必要 |
| Vertex AI | `GOOGLE_GENAI_USE_VERTEXAI=true`、`GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION` 等を使う |
| 手動OAuth | VS Code統合ターミナルで人が `gemini` を操作する場合に有効 |

## 参照

- Gemini CLI authentication setup  
  https://geminicli.com/docs/get-started/authentication/
- Gemini CLI help output  
  `gemini --help`
