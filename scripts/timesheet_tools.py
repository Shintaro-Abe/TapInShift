#!/usr/bin/env python3
"""TapInShift 検証補助ツール。

サブコマンド:
  make-copy      原本から検証用コピーを作る（原本は変更しない）
  inspect-dates  Excel の日付列(L)を確認する（実機 Excel + xlwings 必須）
  diagnose-date Excel の対象日検索を詳細診断する
  show-db        SQLite の打刻・手動編集履歴を表示する

使い方の例:
  python scripts/timesheet_tools.py make-copy --source "C:/path/原本.xlsx"
  python scripts/timesheet_tools.py inspect-dates
  python scripts/timesheet_tools.py show-db --limit 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.local.json"


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise SystemExit(f"ERROR: 設定ファイルが見つかりません: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def _resolve(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def cmd_make_copy(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"ERROR: 原本が見つかりません: {source}", file=sys.stderr)
        return 1

    config_path = Path(args.config).resolve()
    if args.dest:
        dest = Path(args.dest).expanduser().resolve()
    else:
        cfg = _load_config(config_path)
        dest = _resolve(config_path.parent, cfg["excel"]["path"])

    if dest == source:
        print("ERROR: コピー先が原本と同じです。中止します。", file=sys.stderr)
        return 1
    if dest.exists() and not args.force:
        print(
            f"ERROR: コピー先が既に存在します: {dest}\n"
            "上書きするには --force を付けてください。",
            file=sys.stderr,
        )
        return 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    print("OK: 検証用コピーを作成しました")
    print(f"  原本  : {source}")
    print(f"  コピー: {dest}")
    return 0


def cmd_inspect_dates(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)
    excel = cfg["excel"]
    path = _resolve(config_path.parent, excel["path"])
    sheet_name = str(excel["sheet_name"])
    first = int(excel.get("first_data_row", 7))
    last = int(excel.get("last_data_row", 37))
    date_col = excel.get("columns", {}).get("date", "L")
    pw_env = excel.get("password_env", "TAPINSHIFT_EXCEL_PASSWORD")

    password = os.getenv(pw_env)
    if not password:
        print(f"ERROR: 環境変数 {pw_env} が未設定です。", file=sys.stderr)
        return 1
    if not path.exists():
        print(f"ERROR: Excel が見つかりません: {path}", file=sys.stderr)
        return 1
    try:
        import xlwings as xw
    except ImportError:
        print("ERROR: xlwings が未インストールです。pip install xlwings", file=sys.stderr)
        return 1

    from datetime import date, datetime

    ok_date = 0
    ok_day_number = 0
    ok_excel_serial = 0
    blank = 0
    other = 0
    app = xw.App(visible=False, add_book=False)
    try:
        book = app.books.open(str(path), password=password)
        sheet = book.sheets[sheet_name]
        for row in range(first, last + 1):
            value = sheet.range(f"{date_col}{row}").value
            kind = _date_cell_kind(value)
            if kind == "date":
                ok_date += 1
            elif kind == "day_number":
                ok_day_number += 1
            elif kind.startswith("excel_serial:"):
                ok_excel_serial += 1
            elif kind == "blank":
                blank += 1
            else:
                other += 1
            print(f"{date_col}{row}: {value!r}  [{kind}]")
        book.close()
    finally:
        app.quit()

    print("---")
    valid = ok_date + ok_day_number + ok_excel_serial
    print(
        f"日付型: {ok_date} 件 / 日番号: {ok_day_number} 件 / "
        f"Excelシリアル: {ok_excel_serial} 件 / 空欄: {blank} 件 / それ以外: {other} 件"
    )
    if other:
        print("判定: 日付型でない値があります。excel_writer の日付検索を要確認。")
        return 2
    if blank and valid:
        print("判定: 空欄行がありますが、日付行は確認できました。続行してよい。")
        return 0
    if blank and not valid:
        print("判定: 日付行が見つかりません。設定を要確認。")
        return 2
    if ok_day_number or ok_excel_serial:
        print("判定: 日番号または Excel シリアル形式があります。現在のコードは続行可能。")
        return 0
    print("判定: すべて日付型。続行してよい。")
    return 0


def cmd_find_date(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)
    excel = cfg["excel"]
    path = _resolve(config_path.parent, excel["path"])
    sheet_name = str(excel["sheet_name"])
    first = int(excel.get("first_data_row", 7))
    last = int(excel.get("last_data_row", 37))
    date_col = excel.get("columns", {}).get("date", "L")
    date_format = excel.get("date_format", "%Y-%m-%d")
    pw_env = excel.get("password_env", "TAPINSHIFT_EXCEL_PASSWORD")
    target = date.fromisoformat(args.date)

    password = os.getenv(pw_env)
    if not password:
        print(f"ERROR: 環境変数 {pw_env} が未設定です。", file=sys.stderr)
        return 1
    if not path.exists():
        print(f"ERROR: Excel が見つかりません: {path}", file=sys.stderr)
        return 1
    try:
        import xlwings as xw
        from tapinshift.excel_writer import matches_target_date
    except ImportError as exc:
        print(f"ERROR: 必要なライブラリが未インストールです: {exc}", file=sys.stderr)
        return 1

    app = xw.App(visible=False, add_book=False)
    try:
        book = app.books.open(str(path), password=password)
        sheet = book.sheets[sheet_name]
        for row in range(first, last + 1):
            value = sheet.range(f"{date_col}{row}").value
            if matches_target_date(value, target, date_format):
                print(f"OK: {args.date} は {date_col}{row} に一致しました: {value!r} [{_date_cell_kind(value)}]")
                return 0
        print(f"ERROR: {args.date} に一致する行が見つかりません。{date_col}{first}:{date_col}{last} を確認してください。")
        return 2
    finally:
        try:
            book.close()
        except Exception:
            pass
        app.quit()


def cmd_diagnose_date(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)
    excel = cfg["excel"]
    path = _resolve(config_path.parent, excel["path"])
    sheet_name = str(excel["sheet_name"])
    first = int(excel.get("first_data_row", 7))
    last = int(excel.get("last_data_row", 37))
    columns = excel.get("columns", {})
    date_col = columns.get("date", "L")
    date_format = excel.get("date_format", "%Y-%m-%d")
    pw_env = excel.get("password_env", "TAPINSHIFT_EXCEL_PASSWORD")
    target = date.fromisoformat(args.date)

    password = os.getenv(pw_env)
    if not password:
        print(f"ERROR: 環境変数 {pw_env} が未設定です。", file=sys.stderr)
        return 1
    if not path.exists():
        print(f"ERROR: Excel が見つかりません: {path}", file=sys.stderr)
        return 1
    try:
        import xlwings as xw
        from tapinshift.excel_writer import matches_target_date
    except ImportError as exc:
        print(f"ERROR: 必要なライブラリが未インストールです: {exc}", file=sys.stderr)
        return 1

    print("# 設定")
    print(f"config: {config_path}")
    print(f"excel.path: {path}")
    print(f"sheet_name: {sheet_name}")
    print(f"date_column: {date_col}")
    print(f"data_rows: {first}..{last}")
    print(f"target_date: {args.date}")
    print()

    app = xw.App(visible=False, add_book=False)
    book = None
    try:
        book = app.books.open(str(path), password=password)
        print("# Workbook")
        print("sheets:", ", ".join(sheet.name for sheet in book.sheets))
        sheet = book.sheets[sheet_name]
        print(f"used_range: {sheet.used_range.address}")
        print()

        print(f"# {date_col}{first}:{date_col}{last} の詳細")
        exact_matches = []
        for row in range(first, last + 1):
            cell = sheet.range(f"{date_col}{row}")
            value = cell.value
            text = _safe_cell_text(cell)
            formula = _safe_cell_formula(cell)
            number_format = _safe_cell_number_format(cell)
            kind = _date_cell_kind(value)
            matched = matches_target_date(value, target, date_format) or _text_matches_target_date(text, target, date_format)
            marker = "MATCH" if matched else "-----"
            if matched:
                exact_matches.append(f"{date_col}{row}")
            print(
                f"{marker} {date_col}{row}: value={value!r} [{kind}] "
                f"text={text!r} formula={formula!r} number_format={number_format!r}"
            )
        print()

        if exact_matches:
            print("OK: date_column で一致しました:", ", ".join(exact_matches))
            return 0

        scan_columns = _neighbor_columns(date_col, span=4)
        print("# 周辺列スキャン")
        print("対象列:", ", ".join(scan_columns))
        nearby_matches = []
        for col in scan_columns:
            for row in range(first, last + 1):
                cell = sheet.range(f"{col}{row}")
                value = cell.value
                text = _safe_cell_text(cell)
                if matches_target_date(value, target, date_format) or _text_matches_target_date(text, target, date_format):
                    nearby_matches.append(f"{col}{row}: value={value!r} text={text!r}")
        if nearby_matches:
            print("WARN: date_column 以外で一致候補があります。config の excel.columns.date を見直してください。")
            for item in nearby_matches:
                print("  ", item)
            return 3

        print("ERROR: 指定日と一致する値は date_column にも周辺列にも見つかりません。")
        print("確認事項: config の excel.path / sheet_name / columns.date / first_data_row / last_data_row が実ファイルに合っているか。")
        return 2
    finally:
        if book is not None:
            try:
                book.close()
            except Exception:
                pass
        app.quit()


def _date_cell_kind(value) -> str:
    from datetime import date, datetime

    if isinstance(value, (date, datetime)):
        return "date"
    if value in (None, ""):
        return "blank"
    if isinstance(value, (int, float)) and not isinstance(value, bool) and float(value).is_integer():
        number = int(value)
        if 1 <= number <= 31:
            return "day_number"
        if number > 31:
            return f"excel_serial:{_excel_serial_to_date(number).isoformat()}"
    text = str(value).strip()
    if text.replace(".0", "", 1).isdigit():
        number = int(float(text))
        if 1 <= number <= 31:
            return "day_number"
        if number > 31:
            return f"excel_serial:{_excel_serial_to_date(number).isoformat()}"
    return type(value).__name__


def _excel_serial_to_date(serial: int) -> date:
    return date(1899, 12, 30) + timedelta(days=serial)


def _safe_cell_text(cell) -> str:
    try:
        return str(cell.api.Text)
    except Exception as exc:
        return f"<Text error: {exc}>"


def _safe_cell_formula(cell):
    try:
        return cell.formula
    except Exception as exc:
        return f"<formula error: {exc}>"


def _safe_cell_number_format(cell):
    try:
        return cell.number_format
    except Exception as exc:
        return f"<number_format error: {exc}>"


def _text_matches_target_date(text: str, target: date, date_format: str) -> bool:
    from tapinshift.excel_writer import matches_target_date

    cleaned = text.strip()
    if matches_target_date(cleaned, target, date_format):
        return True
    normalized = re.sub(r"\s+", "", cleaned)
    normalized = normalized.replace("（", "(").replace("）", ")")
    if matches_target_date(normalized, target, date_format):
        return True
    without_weekday = re.sub(r"[（(]?[月火水木金土日][）)]?", "", normalized)
    return matches_target_date(without_weekday, target, date_format)


def _neighbor_columns(center: str, span: int) -> list[str]:
    index = _column_to_index(center)
    first = max(1, index - span)
    last = index + span
    return [_index_to_column(i) for i in range(first, last + 1)]


def _column_to_index(column: str) -> int:
    value = 0
    for char in column.upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"Invalid Excel column: {column}")
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def _index_to_column(index: int) -> str:
    chars = []
    while index:
        index, rem = divmod(index - 1, 26)
        chars.append(chr(ord("A") + rem))
    return "".join(reversed(chars))


def cmd_show_db(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)
    db_path = _resolve(config_path.parent, cfg.get("database_path", "../data/tapinshift.sqlite3"))
    if not db_path.exists():
        print(f"INFO: DB がまだありません: {db_path}")
        return 0

    limit = args.limit
    with closing(sqlite3.connect(db_path)) as conn:
        print(f"# punch_events (最新 {limit} 件)")
        for r in conn.execute(
            "SELECT tapped_at, punch_type, status, error "
            "FROM punch_events ORDER BY rowid DESC LIMIT ?",
            (limit,),
        ):
            print("  ", r)
        print(f"# manual_edits (最新 {limit} 件)")
        for r in conn.execute(
            "SELECT created_at, target_date, status, error "
            "FROM manual_edits ORDER BY id DESC LIMIT ?",
            (limit,),
        ):
            print("  ", r)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TapInShift 検証補助ツール")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="設定ファイルのパス（既定: config/config.local.json）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_copy = sub.add_parser("make-copy", parents=[common], help="原本から検証用コピーを作る")
    p_copy.add_argument("--source", required=True, help="原本の勤務表パス")
    p_copy.add_argument("--dest", help="コピー先（省略時は config の excel.path）")
    p_copy.add_argument("--force", action="store_true", help="既存のコピー先を上書きする")
    p_copy.set_defaults(func=cmd_make_copy)

    p_ins = sub.add_parser("inspect-dates", parents=[common], help="Excel の日付列を確認する")
    p_ins.set_defaults(func=cmd_inspect_dates)

    p_find = sub.add_parser("find-date", parents=[common], help="指定日が Excel のどの行に一致するか確認する")
    p_find.add_argument("--date", required=True, help="確認する日付（例: 2026-06-27）")
    p_find.set_defaults(func=cmd_find_date)

    p_diag = sub.add_parser("diagnose-date", parents=[common], help="対象日検索の詳細診断を出力する")
    p_diag.add_argument("--date", required=True, help="確認する日付（例: 2026-06-27）")
    p_diag.set_defaults(func=cmd_diagnose_date)

    p_db = sub.add_parser("show-db", parents=[common], help="SQLite 履歴を表示する")
    p_db.add_argument("--limit", type=int, default=5, help="表示件数（既定: 5）")
    p_db.set_defaults(func=cmd_show_db)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
