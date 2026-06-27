# Codex / Claude Code Dev Container 初期設定

この ZIP は、Windows OS 上の VS Code Dev Containers で Linux コンテナを起動し、その中で Codex CLI、Claude Code CLI、Gemini CLI を利用するための最小構成です。

## 使い方

1. ZIP を展開します。
2. 展開したファイル群を対象リポジトリのルートにコピーします。
3. VS Code で対象リポジトリを開きます。
4. Command Palette から `Dev Containers: Reopen in Container` を実行します。
5. コンテナ起動後、統合ターミナルで次を実行します。

```bash
codex
```

初回起動時にサインインが求められます。ブラウザが自動で開かない場合は、ターミナルに表示される URL を Windows 側ブラウザへコピーして認証してください。

Claude Code を使う場合は、同じく統合ターミナルで次を実行します。

```bash
claude
```

初回起動時にブラウザでのログインが求められます。Claude Pro / Max などのサブスクリプションアカウントでOAuthログインしてください。コンテナ内からブラウザが開けない場合は、表示されたURLをWindows側ブラウザへコピーし、必要に応じて表示されたコードをターミナルへ貼り付けます。APIキーは不要です。

Gemini CLI を使う場合は、同じく統合ターミナルで次を実行します。

```bash
gemini
```

初回起動時は "Login with Google" を選択してOAuthログインしてください。APIキーは不要です。

## 含まれるファイル

```text
.devcontainer/
├─ devcontainer.json
├─ Dockerfile
├─ codex.config.toml
└─ postCreateCommand.sh
AGENTS.md
CLAUDE.md
.gitattributes
.gitignore
README-CODEX-DEVCONTAINER.md
```

## 設計方針

- Codex CLI は Dev Container 内の Linux 環境にインストールします。
- Claude Code CLI は Dev Container 内の Linux 環境にインストールします。
- Gemini CLI は Dev Container 内の Linux 環境にインストールします。
- Codex の設定・認証情報は `/home/vscode/.codex` に保存します。
- `/home/vscode/.codex` は `codex-home` named volume に永続化します。
- Claude Code の設定・認証情報は `/home/vscode/.claude` に保存します。
- `/home/vscode/.claude` は `claude-home` named volume に永続化します。
- Gemini CLI の設定・認証情報は `/home/vscode/.gemini` に保存します。
- `/home/vscode/.gemini` は `gemini-home` named volume に永続化します。
- 秘密情報は Git 管理しません。
- Windows 由来の CRLF 問題を避けるため、関連ファイルは LF 改行に固定します。
- Claude Code は `CLAUDE.md` から `AGENTS.md` を読み込み、レビュー時の基本方針を共有します。

## 動作確認

```bash
codex --version
codex "このリポジトリの構成を短く説明してください"
claude --version
claude
gemini --version
gemini
```

Claude Code をレビュアーとして使う場合は、`claude` 起動後に `/code-review` を実行するか、レビュー対象を自然言語で指定してください。

非対話モードの `claude -p` / `claude --print` は、このDev Containerではハーネスでブロックします。Claude Codeを使う場合は必ず対話式の `claude` から開始してください。

## 注意

`bubblewrap` や sandbox 関連のエラーが出る場合は、まず `Dev Containers: Rebuild Container` を実行してください。それでも解消しない場合は、Docker Desktop、WSL2、または企業管理ポリシー側で user namespace や seccomp が制限されている可能性があります。
