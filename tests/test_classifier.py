import unittest

from tapinshift.classifier import classify_with_rules


class ClassifierTest(unittest.TestCase):
    def test_rule_classifier_extracts_expense_amount(self) -> None:
        result = classify_with_rules("交通費320円")

        self.assertEqual(result.expense_item, "交通費")
        self.assertEqual(result.amount, 320)
        self.assertFalse(result.needs_confirmation)

    def test_rule_classifier_keeps_amount_out_of_notice_and_expense(self) -> None:
        result = classify_with_rules("遅延証明あり 交通費1,200円")

        self.assertEqual(result.notice, "遅延証明あり 交通費")
        self.assertEqual(result.expense_item, "遅延証明あり 交通費")
        self.assertEqual(result.amount, 1200)

    def test_rule_classifier_marks_ambiguous_text_for_confirmation(self) -> None:
        result = classify_with_rules("あとで確認")

        self.assertTrue(result.needs_confirmation)


if __name__ == "__main__":
    unittest.main()
