# Created by Harsh (@harsh-91) | Made in India
import unittest
from datetime import date
from decimal import Decimal

from statement_importer.parsers import date_value, fingerprint, money


class ParserPrimitiveTests(unittest.TestCase):
    def test_money_is_exact_and_locale_tolerant(self):
        self.assertEqual(money("₹1,234.50"), Decimal("1234.50"))
        self.assertEqual(money("100.00 DR"), Decimal("-100.00"))
        self.assertIsNone(money(""))

    def test_supported_dates_are_unambiguous(self):
        self.assertEqual(date_value("21/09/2026", "%d/%m/%Y"), date(2026, 9, 21))
        self.assertEqual(date_value("2026-09-21", "%Y-%m-%d"), date(2026, 9, 21))

    def test_fingerprint_is_stable(self):
        parts = ("ACCOUNT", date(2026, 9, 21), "Coffee", Decimal("125.00"), Decimal("875.00"))
        self.assertEqual(fingerprint("sample_bank", *parts), fingerprint("sample_bank", *parts))
        self.assertNotEqual(fingerprint("sample_bank", *parts), fingerprint("another_bank", *parts))


if __name__ == "__main__":
    unittest.main()
