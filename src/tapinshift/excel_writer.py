from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re

from .config import ExcelConfig
from .models import Classification, PunchType


@dataclass(frozen=True)
class ExcelWriteResult:
    reflected_at: datetime
    row: int


class ExcelTimesheetWriter:
    def __init__(self, config: ExcelConfig) -> None:
        self.config = config

    def write_punch(
        self,
        target_date: date,
        punch_type: PunchType,
        reflected_time: datetime,
        classification: Classification | None,
    ) -> ExcelWriteResult:
        try:
            import xlwings as xw
        except ImportError as exc:
            raise RuntimeError("xlwings package is not installed") from exc

        password = self.config.password
        app = xw.App(visible=False, add_book=False)
        try:
            book = app.books.open(str(self.config.path), password=password)
            sheet = book.sheets[self.config.sheet_name]
            row = self._find_row(sheet, target_date)
            columns = self.config.columns
            self._write_defaults(sheet, row)

            if punch_type == PunchType.CLOCK_IN:
                _write_if_empty(sheet, f"{columns.clock_in}{row}", _excel_time_text(reflected_time))
            else:
                _write_if_empty(sheet, f"{columns.clock_out}{row}", _excel_time_text(reflected_time))

            if classification:
                if classification.notice:
                    sheet.range(f"{columns.notice}{row}").value = classification.notice
                if classification.expense_item:
                    sheet.range(f"{columns.expense_item}{row}").value = classification.expense_item
                if classification.amount is not None:
                    sheet.range(f"{columns.amount}{row}").value = classification.amount

            book.save()
            book.close()
            return ExcelWriteResult(reflected_at=datetime.now(reflected_time.tzinfo), row=row)
        finally:
            app.quit()

    def update_day(
        self,
        target_date: date,
        *,
        clock_in: str | None,
        clock_out: str | None,
        notice: str | None,
        expense_item: str | None,
        amount: int | None,
    ) -> ExcelWriteResult:
        try:
            import xlwings as xw
        except ImportError as exc:
            raise RuntimeError("xlwings package is not installed") from exc

        password = self.config.password
        app = xw.App(visible=False, add_book=False)
        try:
            book = app.books.open(str(self.config.path), password=password)
            sheet = book.sheets[self.config.sheet_name]
            row = self._find_row(sheet, target_date)
            columns = self.config.columns
            self._write_defaults(sheet, row)

            _apply_day_values(
                sheet,
                columns,
                row,
                clock_in=clock_in,
                clock_out=clock_out,
                notice=notice,
                expense_item=expense_item,
                amount=amount,
            )

            book.save()
            book.close()
            return ExcelWriteResult(reflected_at=datetime.now(), row=row)
        finally:
            app.quit()

    def _find_row(self, sheet, target_date: date) -> int:
        columns = self.config.columns
        last_row = self.config.last_data_row or sheet.used_range.last_cell.row
        samples: list[str] = []

        for row in range(self.config.first_data_row, last_row + 1):
            cell = sheet.range(f"{columns.date}{row}")
            value = cell.value
            if len(samples) < 8 or row in (target_date.day + self.config.first_data_row - 1, last_row):
                samples.append(f"{columns.date}{row}={_describe_value(value)}")
            if matches_target_date(value, target_date, self.config.date_format):
                return row
        target_text = target_date.strftime(self.config.date_format)
        sample_text = "; ".join(samples)
        raise ValueError(
            f"Target date is outside this timesheet period: {target_text}. "
            f"Checked {columns.date}{self.config.first_data_row}:{columns.date}{last_row}. "
            f"Samples: {sample_text}"
        )

    def _write_defaults(self, sheet, row: int) -> None:
        columns = self.config.columns
        defaults = self.config.defaults
        pairs = [
            (columns.table, defaults.table),
            (columns.attendance, defaults.attendance),
            (columns.late, defaults.late),
            (columns.early, defaults.early),
        ]
        for column, value in pairs:
            if column and value is not None:
                cell = sheet.range(f"{column}{row}")
                if cell.value in (None, ""):
                    cell.value = value


def _write_if_empty(sheet, address: str, value: str) -> None:
    cell = sheet.range(address)
    if cell.value not in (None, ""):
        raise ValueError(f"Cell already has a value: {address}")
    cell.value = value


def _apply_day_values(
    sheet,
    columns,
    row: int,
    *,
    clock_in: str | None,
    clock_out: str | None,
    notice: str | None,
    expense_item: str | None,
    amount: int | None,
) -> None:
    """Overwrite only the fields that were provided.

    ``None`` means the field was left blank in the edit modal, so the existing
    cell value is preserved instead of being cleared. Clearing a cell must be
    done directly in Excel to avoid accidental data loss.
    """
    if clock_in is not None:
        sheet.range(f"{columns.clock_in}{row}").value = _parse_time_text(clock_in)
    if clock_out is not None:
        sheet.range(f"{columns.clock_out}{row}").value = _parse_time_text(clock_out)
    if notice is not None:
        sheet.range(f"{columns.notice}{row}").value = notice
    if expense_item is not None:
        sheet.range(f"{columns.expense_item}{row}").value = expense_item
    if amount is not None:
        sheet.range(f"{columns.amount}{row}").value = amount


def matches_target_date(value, target_date: date, date_format: str) -> bool:
    if isinstance(value, datetime):
        return value.date() == target_date
    if isinstance(value, date):
        return value == target_date
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _matches_number(value, target_date)

    text = str(value).strip()
    if not text:
        return False
    if text == target_date.strftime(date_format):
        return True
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return _matches_number(float(text), target_date)

    for fmt in (date_format, "%Y-%m-%d", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        return parsed == target_date

    for fmt in ("%m/%d", "%m-%d"):
        try:
            parsed = datetime.strptime(f"{target_date.year}/{text}", f"%Y/{fmt}").date()
        except ValueError:
            continue
        return parsed.month == target_date.month and parsed.day == target_date.day

    jp_match = re.fullmatch(r"(?:(\d{1,2})月)?(\d{1,2})日", text)
    if jp_match:
        month = int(jp_match.group(1)) if jp_match.group(1) else target_date.month
        day = int(jp_match.group(2))
        return month == target_date.month and day == target_date.day

    weekday_text_match = re.fullmatch(r"(?:(\d{1,2})月)?(\d{1,2})(?:日)?[（(]?[月火水木金土日][）)]?", text)
    if weekday_text_match:
        month = int(weekday_text_match.group(1)) if weekday_text_match.group(1) else target_date.month
        day = int(weekday_text_match.group(2))
        return month == target_date.month and day == target_date.day

    return False


def _matches_number(value: int | float, target_date: date) -> bool:
    if float(value).is_integer():
        number = int(value)
        if 1 <= number <= 31:
            return number == target_date.day
        if number > 31:
            return _excel_serial_to_date(number) == target_date
    return False


def _excel_serial_to_date(serial: int) -> date:
    return date(1899, 12, 30) + timedelta(days=serial)


def _describe_value(value) -> str:
    return f"{value!r}({type(value).__name__})"


def _excel_time_text(value: datetime) -> str:
    """Return HH:MM text to avoid COM VARIANT conversion issues with datetime.time."""
    return value.strftime("%H:%M")


def _parse_time_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return datetime.strptime(text, "%H:%M").strftime("%H:%M")
