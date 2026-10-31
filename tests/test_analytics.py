from datetime import date
from pathlib import Path
import sqlite3
import tempfile
import unittest

from analytics import validate_report, analyze_report
from domain import ValidationError
from server import Store


def report(product_id="test-product", **changes):
    data=dict(product_id=product_id,listing_id="123456789",source="TEST FIXTURE, not shop data",period_start="2026-01-01",period_end="2026-01-31",currency="USD",visits=200,orders=0)
    return {**data, **changes}


class AnalyticsTests(unittest.TestCase):
    def test_unknown_is_not_zero_and_zero_conversion_is_measured(self):
        data=validate_report(report())
        self.assertIsNone(data["ad_spend"])
        result=analyze_report(data,today=date(2026,2,1))
        self.assertEqual(result["conversion_pct"],0)
        self.assertIsNone(result["ad_roas"])
        self.assertIn("ad_spend",result["missing_fields"])
        self.assertFalse(result["external_verified"])

    def test_unknown_orders_cannot_be_treated_as_no_sales(self):
        result=analyze_report(validate_report(report(orders="")))
        self.assertIsNone(result["conversion_pct"])
        codes=[r["code"] for r in result["recommendations"]]
        self.assertIn("missing_conversion",codes)
        self.assertNotIn("visits_without_orders",codes)

    def test_roas_uses_attributed_revenue_not_total(self):
        result=analyze_report(validate_report(report(revenue=1000,ad_spend=20,ad_revenue=60)))
        self.assertEqual(result["ad_roas"],3)
        self.assertIsNone(result["profit"])

    def test_low_sample_and_old_data_are_explicit(self):
        result=analyze_report(validate_report(report(visits=10)),today=date(2026,4,1))
        self.assertTrue(result["stale"])
        codes=[r["code"] for r in result["recommendations"]]
        self.assertIn("small_sample",codes)
        self.assertIn("stale",codes)
        self.assertNotIn("visits_without_orders",codes)
        self.assertTrue(all(not r["applied"] for r in result["recommendations"]))

    def test_zero_visits_cannot_produce_division_or_fake_conversion(self):
        result=analyze_report(validate_report(report(visits=0,orders=1)))
        self.assertIsNone(result["conversion_pct"])
        self.assertIn("inconsistent",[r["code"] for r in result["recommendations"]])

    def test_invalid_dates_fractional_counts_and_empty_report_rejected(self):
        for changes in ({"period_end":"9999-01-01"},{"period_end":"2025-01-01"},{"visits":2.5},{"orders":-1},{"visits":"","orders":""}):
            with self.assertRaises(ValidationError):
                validate_report(report(**changes))

    def test_duplicate_period_and_cross_product_listing_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/"test.sqlite3")
            one=store.product(dict(title="Analytics fixture",sku="AN-001",kind="seamless",notes="test"))
            two=store.product(dict(title="Other fixture",sku="AN-002",kind="seamless",notes="test"))
            store.add_performance_report(report(one["id"]))
            with self.assertRaises(sqlite3.IntegrityError):
                store.add_performance_report(report(one["id"]))
            with self.assertRaises(ValidationError):
                store.add_performance_report(report(two["id"],period_end="2026-02-01"))
            self.assertEqual(len(store.snapshot()["performance_reports"]),1)


if __name__=="__main__":
    unittest.main()
