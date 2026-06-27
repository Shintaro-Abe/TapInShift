#!/usr/bin/env python3
"""ランブックの Markdown を、コピー可能なコードブロック付き HTML へ変換する。

依存ライブラリなしで動く軽量変換。対応記法は次のとおり。
  見出し(#, ##, ###) / 箇条書き(-) / 番号付き(1.) / 表 / 引用(>) /
  コードフェンス(```) / 水平線(---) / 強調(**) / インラインコード(`)

使い方:
  python scripts/render_runbook_html.py
  python scripts/render_runbook_html.py --src <md> --out <html>
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = REPO_ROOT / ".steering" / "20260621-real-excel-validation" / "validation-runbook.md"
DEFAULT_OUT = REPO_ROOT / ".steering" / "20260621-real-excel-validation" / "validation-runbook.html"


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"  $", "<br>", text)
    return text


def _render_table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = cells(rows[0])
    body = rows[2:]
    out = ["<table>", "<thead>", "<tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out += ["</tr>", "</thead>", "<tbody>"]
    for line in body:
        out.append("<tr>")
        out += [f"<td>{_inline(c)}</td>" for c in cells(line)]
        out.append("</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def convert(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    code_id = 0
    list_mode: str | None = None  # "ul" or "ol"

    def close_list() -> None:
        nonlocal list_mode
        if list_mode == "ul":
            out.append("</ul>")
        elif list_mode == "ol":
            out.append("</ol>")
        list_mode = None

    while i < n:
        line = lines[i]

        if line.startswith("```"):
            close_list()
            lang = line[3:].strip()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code_id += 1
            escaped = html.escape("\n".join(buf))
            label = f" data-lang=\"{html.escape(lang)}\"" if lang else ""
            out.append(
                "<div class=\"code-wrap\">"
                f"<button class=\"copy-btn\" type=\"button\" data-target=\"code-{code_id}\">コピー</button>"
                f"<pre><code id=\"code-{code_id}\"{label}>{escaped}</code></pre>"
                "</div>"
            )
            continue

        if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            close_list()
            tbl = [line]
            i += 1
            tbl.append(lines[i])
            i += 1
            while i < n and "|" in lines[i] and lines[i].strip():
                tbl.append(lines[i])
                i += 1
            out.append(_render_table(tbl))
            continue

        if line.strip() == "---":
            close_list()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if line.startswith(">"):
            close_list()
            out.append(f"<blockquote>{_inline(line.lstrip('> ').rstrip())}</blockquote>")
            i += 1
            continue

        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if list_mode != "ol":
                close_list()
                out.append("<ol>")
                list_mode = "ol"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\s*-\s+(.*)$", line)
        if m:
            if list_mode != "ul":
                close_list()
                out.append("<ul>")
                list_mode = "ul"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        if not line.strip():
            close_list()
            i += 1
            continue

        close_list()
        out.append(f"<p>{_inline(line.rstrip())}</p>")
        i += 1

    close_list()
    return "\n".join(out)


PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans JP", Meiryo, sans-serif;
    line-height: 1.7; max-width: 880px; margin: 0 auto; padding: 24px 16px 80px;
    color: #1f2328; background: #ffffff;
  }}
  h1 {{ font-size: 1.7rem; border-bottom: 2px solid #d0d7de; padding-bottom: .3em; }}
  h2 {{ font-size: 1.35rem; margin-top: 2em; border-bottom: 1px solid #d0d7de; padding-bottom: .2em; }}
  h3 {{ font-size: 1.1rem; margin-top: 1.6em; }}
  hr {{ border: none; border-top: 1px solid #d0d7de; margin: 2em 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f6f8fa; }}
  blockquote {{ margin: 1em 0; padding: .4em 1em; border-left: 4px solid #d0d7de; background: #f6f8fa; }}
  code {{ font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; font-size: .9em; }}
  p code, li code, td code {{ background: #eff1f3; padding: .1em .35em; border-radius: 4px; }}
  .code-wrap {{ position: relative; margin: 1em 0; }}
  .code-wrap pre {{
    background: #0d1117; color: #e6edf3; padding: 14px 14px; border-radius: 8px;
    overflow-x: auto; margin: 0;
  }}
  .code-wrap pre code {{ background: transparent; padding: 0; color: inherit; }}
  .copy-btn {{
    position: absolute; top: 8px; right: 8px; padding: 4px 10px; font-size: .8rem;
    border: 1px solid #30363d; border-radius: 6px; background: #21262d; color: #e6edf3;
    cursor: pointer;
  }}
  .copy-btn:hover {{ background: #30363d; }}
  .copy-btn.copied {{ background: #238636; border-color: #238636; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e6edf3; background: #0d1117; }}
    th {{ background: #161b22; }}
    th, td {{ border-color: #30363d; }}
    blockquote {{ background: #161b22; border-left-color: #30363d; }}
    p code, li code, td code {{ background: #161b22; }}
    h1, h2 {{ border-color: #30363d; }}
  }}
</style>
</head>
<body>
{body}
<script>
function copyText(text) {{
  if (navigator.clipboard && window.isSecureContext) {{
    return navigator.clipboard.writeText(text);
  }}
  var area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.focus();
  area.select();
  try {{
    document.execCommand("copy");
    return Promise.resolve();
  }} finally {{
    document.body.removeChild(area);
  }}
}}
document.querySelectorAll(".copy-btn").forEach(function (btn) {{
  btn.addEventListener("click", function () {{
    var code = document.getElementById(btn.dataset.target);
    if (!code) return;
    var text = code.innerText;
    copyText(text).then(function () {{
      var original = btn.textContent;
      btn.textContent = "コピーしました";
      btn.classList.add("copied");
      setTimeout(function () {{
        btn.textContent = original;
        btn.classList.remove("copied");
      }}, 1500);
    }});
  }});
}});
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="ランブック Markdown を HTML へ変換")
    parser.add_argument("--src", default=str(DEFAULT_SRC), help="入力 Markdown")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="出力 HTML")
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    md = src.read_text(encoding="utf-8")

    title_match = re.search(r"^#\s+(.*)$", md, re.MULTILINE)
    title = title_match.group(1) if title_match else src.stem

    body = convert(md)
    out.write_text(PAGE.format(title=html.escape(title), body=body), encoding="utf-8")
    print(f"OK: HTML を出力しました: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
