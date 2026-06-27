from datetime import date, datetime
import unittest
from zoneinfo import ZoneInfo

from tapinshift.config import ExcelColumns, ExcelConfig, ExcelDefaults
from tapinshift.excel_writer import ExcelTimesheetWriter, _apply_day_values, _excel_time_text, matches_target_date


class FakeCell:
    def __init__(self, value="existing") -> None:
        self.value = value


class FakeSheet:
    def __init__(self) -> None:
        self.cells: dict[str, FakeCell] = {}

    def range(self, address: str) -> FakeCell:
        self.cells.setdefault(address, FakeCell())
        return self.cells[address]


class ExcelWriterHelperTest(unittest.TestCase):
    def test_excel_time_text_drops_seconds_and_microseconds(self) -> None:
        value = datetime(2026, 6, 21, 9, 8, 10, 123456, tzinfo=ZoneInfo("Asia/Tokyo"))

        self.assertEqual(_excel_time_text(value), "09:08")

    def test_apply_day_values_preserves_blank_modal_fields(self) -> None:
        sheet = FakeSheet()
        columns = ExcelColumns(
            table="B",
            attendance="C",
            late="D",
            early="E",
            date="L",
            clock_in="F",
            clock_out="G",
            notice="W",
            expense_item="Y",
            amount="AB",
        )
        sheet.range("F7").value = "keep clock in"
        sheet.range("G7").value = "keep clock out"
        sheet.range("W7").value = "keep notice"
        sheet.range("Y7").value = "keep expense"
        sheet.range("AB7").value = 999

        _apply_day_values(
            sheet,
            columns,
            7,
            clock_in=None,
            clock_out="18:30",
            notice=None,
            expense_item="交通費",
            amount=None,
        )

        self.assertEqual(sheet.range("F7").value, "keep clock in")
        self.assertEqual(sheet.range("G7").value, "18:30")
        self.assertEqual(sheet.range("W7").value, "keep notice")
        self.assertEqual(sheet.range("Y7").value, "交通費")
        self.assertEqual(sheet.range("AB7").value, 999)

    def test_find_row_accepts_day_number_date_cells(self) -> None:
        sheet = FakeSheet()
        sheet.cells = {
            "L7": FakeCell(25),
            "L8": FakeCell(26.0),
            "L9": FakeCell(27),
        }

        writer = ExcelTimesheetWriter(_excel_config())

        self.assertEqual(writer._find_row(sheet, date(2026, 6, 27)), 9)

    def test_find_row_accepts_month_day_text_cells(self) -> None:
        sheet = FakeSheet()
        sheet.cells = {
            "L7": FakeCell("6/25"),
            "L8": FakeCell("6月26日"),
            "L9": FakeCell("2026-06-27"),
        }

        writer = ExcelTimesheetWriter(_excel_config())

        self.assertEqual(writer._find_row(sheet, date(2026, 6, 25)), 7)
        self.assertEqual(writer._find_row(sheet, date(2026, 6, 26)), 8)
        self.assertEqual(writer._find_row(sheet, date(2026, 6, 27)), 9)

    def test_matches_target_date_accepts_excel_serial_and_weekday_text(self) -> None:
        target = date(2026, 6, 27)
        excel_serial = (target - date(1899, 12, 30)).days

        self.assertTrue(matches_target_date(excel_serial, target, "%Y-%m-%d"))
        self.assertTrue(matches_target_date("27(土)", target, "%Y-%m-%d"))
        self.assertTrue(matches_target_date("6月27日(土)", target, "%Y-%m-%d"))


def _excel_config() -> ExcelConfig:
    return ExcelConfig(
        path="dummy.xlsx",
        sheet_name="6",
        password_env="TAPINSHIFT_EXCEL_PASSWORD",
        columns=ExcelColumns(
            table="B",
            attendance="C",
            late="D",
            early="E",
            date="L",
            clock_in="F",
            clock_out="G",
            notice="W",
            expense_item="Y",
            amount="AB",
        ),
        first_data_row=7,
        last_data_row=9,
        date_format="%Y-%m-%d",
        defaults=ExcelDefaults(table=1, attendance=1, late=0, early=0),
    )


if __name__ == "__main__":
    unittest.main()
