---
description: List project memory and documentation files
allowed-tools: Read, Glob, Grep, LS
argument-hint: [filter]
---

このプロジェクトの記憶・ドキュメント状態を確認してください。

対象:
- `AGENTS.md`
- `CLAUDE.md`
- `docs/*.md`
- `.steering/*/{requirements.md,design.md,tasklist.md}`

手順:
1. `$ARGUMENTS` が指定されている場合は、その文字列に関連する記憶・ドキュメントだけを優先して確認する。
2. 対象ファイルの有無を一覧化する。
3. 各ファイルについて、目的、現在の要点、未整備または古そうな箇所を短くまとめる。
4. 秘密情報、token、API key、Excel password、個人データは出力しない。
5. 出力は日本語で、事務的に簡潔にする。

出力形式:

```text
記憶ファイル
- path: 状態 / 要点

不足・古い可能性
- path: 内容

次に更新すべき候補
- path: 理由
```

