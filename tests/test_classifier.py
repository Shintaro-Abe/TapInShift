import unittest

from tapinshift.classifier import classify_with_rules


class ClassifierTest(unittest.TestCase):
    def test_rule_classifier_extracts_expense_route_and_amount(self) -> None:
        result = classify_with_rules("新宿駅-渋谷駅 320円")

        self.assertIsNone(result.notice)
        self.assertEqual(result.expense_item, "新宿駅-渋谷駅")
        self.assertEqual(result.amount, 320)
        self.assertFalse(result.needs_confirmation)

    def test_rule_classifier_omits_expense_label_without_route(self) -> None:
        result = classify_with_rules("交通費320円")

        self.assertIsNone(result.notice)
        self.assertIsNone(result.expense_item)
        self.assertEqual(result.amount, 320)
        self.assertTrue(result.needs_confirmation)

    def test_rule_classifier_extracts_notice_location_without_amount(self) -> None:
        result = classify_with_rules("渋谷オフィス")

        self.assertEqual(result.notice, "渋谷オフィス")
        self.assertIsNone(result.expense_item)
        self.assertIsNone(result.amount)
        self.assertFalse(result.needs_confirmation)

    def test_rule_classifier_splits_location_and_expense_route(self) -> None:
        result = classify_with_rules("渋谷オフィス 新宿駅-渋谷駅 1,200円")

        self.assertEqual(result.notice, "渋谷オフィス")
        self.assertEqual(result.expense_item, "新宿駅-渋谷駅")
        self.assertEqual(result.amount, 1200)

    def test_rule_classifier_splits_location_and_route_with_japanese_commas(self) -> None:
        result = classify_with_rules("アレア品川、南平⇔市ヶ谷、1134")

        self.assertEqual(result.notice, "アレア品川")
        self.assertEqual(result.expense_item, "南平⇔市ヶ谷")
        self.assertEqual(result.amount, 1134)

    def test_rule_classifier_marks_ambiguous_text_for_confirmation(self) -> None:
        result = classify_with_rules("あとで確認")

        self.assertTrue(result.needs_confirmation)


if __name__ == "__main__":
    unittest.main()
