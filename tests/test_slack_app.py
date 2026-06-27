import unittest

from tapinshift.slack_app import (
    APPLY_NOTE_ACTION,
    DATE_ACTION,
    DATE_BLOCK_ID,
    ROUNDING_BLOCK_ID,
    ROUNDING_MODE_ACTION,
    _event_message,
    _extract_selected_date,
    _home_view,
)
from tapinshift.models import ReflectionStatus


class SlackAppViewTest(unittest.TestCase):
    def test_home_view_uses_dispatching_datepicker_with_initial_date(self) -> None:
        view = _home_view(initial_date="2026-06-21")

        date_block = next(block for block in view["blocks"] if block.get("block_id") == DATE_BLOCK_ID)

        self.assertTrue(date_block["dispatch_action"])
        self.assertEqual(date_block["element"]["type"], "datepicker")
        self.assertEqual(date_block["element"]["action_id"], DATE_ACTION)
        self.assertEqual(date_block["element"]["initial_date"], "2026-06-21")

    def test_home_view_has_apply_note_button(self) -> None:
        view = _home_view(initial_date="2026-06-21")

        action_ids = [
            element["action_id"]
            for block in view["blocks"]
            if block["type"] == "actions"
            for element in block["elements"]
        ]

        self.assertIn(APPLY_NOTE_ACTION, action_ids)

    def test_home_view_has_rounding_mode_select(self) -> None:
        view = _home_view(initial_date="2026-06-21", rounding_mode="15m")

        rounding_block = next(block for block in view["blocks"] if block.get("block_id") == ROUNDING_BLOCK_ID)
        select = rounding_block["accessory"]

        self.assertEqual(select["type"], "static_select")
        self.assertEqual(select["action_id"], ROUNDING_MODE_ACTION)
        self.assertEqual(select["initial_option"]["value"], "15m")
        self.assertEqual([option["value"] for option in select["options"]], ["none", "5m", "10m", "15m", "20m", "30m"])

    def test_extract_selected_date_from_home_state(self) -> None:
        body = {
            "view": {
                "state": {
                    "values": {
                        DATE_BLOCK_ID: {
                            DATE_ACTION: {
                                "selected_date": "2026-06-27",
                            }
                        }
                    }
                }
            }
        }

        self.assertEqual(_extract_selected_date(body), "2026-06-27")

    def test_failed_event_message_mentions_sqlite_and_error(self) -> None:
        message = _event_message(ReflectionStatus.FAILED, "Cell already has a value: F13")

        self.assertIn("勤務表への反映に失敗しました", message)
        self.assertIn("SQLite", message)
        self.assertIn("Cell already has a value: F13", message)


if __name__ == "__main__":
    unittest.main()
