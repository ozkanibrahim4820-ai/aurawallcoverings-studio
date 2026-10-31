from datetime import date
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from domain import ValidationError, pricing, quality
from server import Store, handler_factory


def scenario():
    return dict(supplier="Printmarkt", variation="100 × 100 cm / test material", currency="USD", source="test fixture: not supplier data", source_date=date.today().isoformat(),
                production=20, bulk_shipping=3, domestic_shipping=5, customs_tax=2, other_costs=0,
                listing_fee=.2, payment_fixed=.3, ads_fixed=1, price=100, shipping_charged=10,
                buyer_tax=8, discount_pct=20, transaction_pct=6.5, payment_pct=3, ads_pct=0,
                target_margin_pct=35, payment_on_tax=True, transaction_on_tax=False, ads_on_tax=False)


class CalculationTests(unittest.TestCase):
    def test_discount_shipping_tax_and_distinct_fee_bases(self):
        r = pricing(scenario())
        self.assertEqual(r["revenue"], 90)
        self.assertEqual(r["transaction_fee"], 5.85)
        self.assertEqual(r["payment_fee"], 2.94)
        self.assertEqual(r["total_cost"], 40.29)
        self.assertEqual(r["profit"], 49.71)
        self.assertEqual(r["evidence"], "estimate")

    def test_missing_cost_never_defaults_to_zero(self):
        data = scenario()
        del data["customs_tax"]
        with self.assertRaises(ValidationError):
            pricing(data)

    def test_supplier_cannot_be_substituted(self):
        data = scenario()
        data["supplier"] = "Lumaprints"
        with self.assertRaises(ValidationError):
            pricing(data)

    def test_nonfinite_and_negative_cost_rejected(self):
        for invalid in ["NaN", "Infinity", -1, True]:
            data = scenario()
            data["production"] = invalid
            with self.assertRaises(ValidationError):
                pricing(data)

    def test_full_discount_and_no_revenue(self):
        data = scenario()
        data.update(discount_pct=100, shipping_charged=0)
        result = pricing(data)
        self.assertIsNone(result["margin_pct"])
        self.assertIsNone(result["target_price"])
        self.assertLess(result["profit"], 0)

    def test_impossible_target_is_explicit(self):
        data = scenario()
        data.update(target_margin_pct=95)
        self.assertIsNone(pricing(data)["target_price"])

    def test_suggested_price_reaches_target_after_discount(self):
        data = scenario()
        result = pricing(data)
        data["price"] = result["target_price"]
        self.assertGreaterEqual(pricing(data)["margin_pct"], 35)

    def test_300dpi_requires_real_pixels(self):
        data = dict(kind="seamless_source", width_px=11811, height_px=11811, width_cm=100, height_cm=100)
        result = quality(data)
        self.assertEqual(result["required_width_px"], 11812)
        self.assertFalse(result["resolution_ok"])
        self.assertFalse(result["print_ready"])
        data.update(width_px=11812, height_px=11812)
        self.assertTrue(quality(data)["resolution_ok"])
        self.assertFalse(quality(data)["print_ready"])

    def test_mural_and_mockup_ratios_are_distinct(self):
        data = dict(kind="mural_source", width_px=6000, height_px=4000, width_cm=50.8, height_cm=33)
        self.assertTrue(quality(data)["ratio_ok"])
        data["kind"] = "mural_mockup"
        self.assertFalse(quality(data)["ratio_ok"])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.sqlite3")
        self.product = dict(title="TEST ONLY", sku="TEST-001", kind="seamless", notes="test fixture")

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_sku_does_not_create_second_plan(self):
        self.store.product(self.product)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.product({**self.product, "sku":"test-001"})
        self.assertEqual(len(self.store.snapshot()["products"]), 1)

    def test_stale_update_is_rejected_and_previous_value_preserved(self):
        p = self.store.product(self.product)
        self.store.product({**self.product, "version":1, "title":"Updated"}, p["id"])
        with self.assertRaises(FileExistsError):
            self.store.product({**self.product, "version":1, "title":"Stale edit"}, p["id"])
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["products"][0]["title"], "Updated")
        self.assertEqual(len(snapshot["audits"]), 2)
        self.assertEqual(json.loads(snapshot["audits"][0]["before_json"])["title"], "TEST ONLY")

    def test_duplicate_calculation_reuses_record(self):
        p = self.store.product(self.product)
        data = {"product_id":p["id"], "inputs":scenario()}
        first = self.store.evaluate(data, "pricing")
        second = self.store.evaluate(data, "pricing")
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(second["reused"])
        self.assertEqual(len(self.store.snapshot()["evaluations"]), 1)

    def test_external_steps_cannot_be_marked_reviewed(self):
        p = self.store.product(self.product)
        for step in ("etsy", "drive"):
            with self.assertRaises(ValidationError):
                self.store.pilot_check(dict(product_id=p["id"], step=step, status="reviewed", evidence="not connected"))
        self.assertEqual(self.store.snapshot()["pilot_checks"], [])

    def test_pilot_review_requires_evidence_and_rejects_stale_edits(self):
        p = self.store.product(self.product)
        data = dict(product_id=p["id"], step="research", status="in_progress", evidence="")
        with self.assertRaises(ValidationError):
            self.store.pilot_check(data)
        data["evidence"] = "Test fixture; awaiting real sources"
        first = self.store.pilot_check(data)
        with self.assertRaises(FileExistsError):
            self.store.pilot_check(data)
        data.update(expected_updated_at=first["updated_at"], status="blocked")
        self.store.pilot_check(data)
        self.assertEqual(self.store.snapshot()["pilot_checks"][0]["status"], "blocked")

    def test_schema_reopen_preserves_user_data(self):
        self.store.product(self.product)
        reopened = Store(self.store.filename)
        self.assertEqual(reopened.snapshot()["products"][0]["sku"], self.product["sku"])

    def test_output_import_is_manual_and_does_not_verify_pilot(self):
        p = self.store.product(self.product)
        data = dict(product_id=p["id"], role="mockup", reference="https://example.com/test-mockup.png", alt_text="Test mockup fixture", notes="Not a real Printmarkt output")
        result = self.store.add_output(data)
        self.assertFalse(result["payload"]["externally_verified"])
        self.assertEqual(result["payload"]["evidence"], "manual_import")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.add_output(data)
        self.assertEqual(self.store.snapshot()["pilot_checks"], [])

    def test_seo_import_preserves_description_and_rejects_invalid_tags(self):
        p = self.store.product(self.product)
        data = dict(product_id=p["id"], role="seo", reference="https://example.com/test-seo", title="Fixture title", description="Fixed seller text\nAI disclosure to be reviewed", tags=["wallpaper", "Wallpaper"])
        with self.assertRaises(ValidationError):
            self.store.add_output(data)
        data["tags"] = ["wallpaper", "sage decor"]
        result = self.store.add_output(data)
        self.assertEqual(result["payload"]["description"], data["description"])
        self.assertEqual(len(self.store.snapshot()["outputs"]), 1)

    def test_research_cannot_store_javascript_or_duplicate(self):
        data = dict(title="Test", source="javascript:alert(1)", observed_on=date.today().isoformat(), evidence="estimate", notes="Test fixture")
        with self.assertRaises(ValidationError):
            self.store.add_research(data)
        data["source"] = "https://example.com/test"
        self.store.add_research(data)
        with self.assertRaises(FileExistsError):
            self.store.add_research(data)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(Store(Path(cls.temp.name) / "http.sqlite3")))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, method="GET", data=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        body = json.dumps(data) if data else None
        conn.request(method, path, body=body, headers=headers or {"Content-Type":"application/json"})
        res = conn.getresponse()
        content = res.read()
        status = res.status
        conn.close()
        return status, content

    def test_real_http_create_read_and_conflict(self):
        item = dict(title="HTTP fixture", sku="HTTP-001", kind="mural", notes="not real product")
        self.assertEqual(self.request("/api/products", "POST", item)[0], 200)
        self.assertEqual(self.request("/api/products", "POST", item)[0], 409)
        status, body = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["products"][0]["sku"], "HTTP-001")

    def test_cross_origin_write_is_denied(self):
        status, _ = self.request("/api/products", "POST", {"title":"blocked"}, {"Content-Type":"application/json", "Origin":"https://example.com"})
        self.assertEqual(status, 403)

    def test_no_external_write_route_and_no_path_traversal(self):
        self.assertEqual(self.request("/api/etsy/publish", "POST", {"id":"anything"})[0], 404)
        self.assertEqual(self.request("/../server.py")[0], 404)
        self.assertEqual(self.request("/data/studio.sqlite3")[0], 404)

    def test_html_and_script_are_served(self):
        for path, expected in [("/", b"AuraWallCoverings"), ("/app.js", b"use strict")]:
            status, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertIn(expected, body)


if __name__ == "__main__":
    unittest.main()
