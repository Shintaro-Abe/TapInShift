---
description: Update project memory or persistent docs
allowed-tools: Read, Glob, Grep, Edit, Write
argument-hint: [内容または更新対象]
---

このプロジェクトの記憶または永続ドキュメントを更新してください。

対象:
- プロジェクト運用ルール: `AGENTS.md`
- Claude Code レビュー方針: `CLAUDE.md`
- 永続ドキュメント: `docs/product-requirements.md`, `docs/functional-design.md`, `docs/architecture.md`, `docs/repository-structure.md`, `docs/development-guidelines.md`, `docs/glossary.md`
- 作業単位の記録: `.steering/YYYYMMDD-development-title/{requirements.md,design.md,tasklist.md}`

判断ルール:
- アプリ全体の「何を作るか」「どう作るか」は `docs/` を更新する。
- 開発プロセス、ドキュメント運用、ステアリング運用は `AGENTS.md` を更新する。
- レビュー時の振る舞い、出力形式、レビュー観点は `CLAUDE.md` を更新する。
- 今回だけの作業内容、設計、タスクは `.steering/` を更新する。
- 秘密情報、token、API key、Excel password、個人データは保存しない。
- `$ARGUMENTS` が空の場合は、現在の記憶ファイルを確認し、更新候補だけを提示して、ファイル編集は行わない。
- `$ARGUMENTS` がある場合は、内容から更新対象を選び、必要最小限の編集を行う。

更新後に必ず出力する内容:

```text
更新対象
- path

更新内容
- 変更点

未対応
- あれば記載
```

