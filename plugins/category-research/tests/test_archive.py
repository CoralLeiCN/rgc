import base64
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from category_research import ArchiveError, import_document
from category_research.archive import section_presence


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aSqUAAAAASUVORK5CYII=")


def document(products=None):
    return {
        "contract_version": "1",
        "study": {"study_id": "fixture-study", "category": "tea", "market": "uk", "currency": "GBP", "scope": {"sources": ["fixture-shop"], "sale_evidence": "source reported"}},
        "products": products if products is not None else [{
            "product_id": "fixture-1", "source_url": "https://example.test/product", "source_key": "fixture-shop",
            "identity": {"name": "Source product", "brand": "Source brand", "source_variant_id": "variant-1", "gtin": None},
            "information": {"price": "GBP 2.00", "availability": False, "unfamiliar_source_field": {"anything": [1, None, "original wording"]}},
            "source_artifacts": [{"url": "https://example.test/product", "kind": "page", "content": "<html><body>Original source</body></html>"}],
            "images": [], "collection_notes": ["Ingredient text unavailable from this source."],
        }],
    }


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = self.root / "archive"

    def tearDown(self):
        self.temporary.cleanup()

    def read_capture(self, report, index=0):
        return json.loads((self.output / report["products"][index]["history_path"]).read_text())

    def test_complete_original_record_and_unknown_ingredients_are_preserved(self):
        supplied = document()
        original = deepcopy(supplied)
        report = import_document(supplied, self.output)
        capture = self.read_capture(report)
        self.assertEqual(capture["raw_record"], original["products"][0])
        self.assertEqual(capture["study"], original["study"])
        self.assertEqual(capture["collection_notes"], original["products"][0]["collection_notes"])
        self.assertEqual(capture["raw_section_presence"]["ingredients"]["status"], "unknown")
        self.assertEqual(capture["completeness"], "not_verified")
        self.assertEqual(capture["raw_section_presence"]["availability"]["status"], "source_field_present")
        self.assertEqual(supplied, original)
        artifact = capture["source_artifacts"][0]
        expected = original["products"][0]["source_artifacts"][0]["content"].encode()
        self.assertEqual((self.output / artifact["archive_relative_path"]).read_bytes(), expected)
        self.assertEqual(artifact["sha256"], hashlib.sha256(expected).hexdigest())

    def test_reruns_append_capture_history_and_keep_old_artifacts(self):
        first = import_document(document(), self.output)
        snapshot_path = self.output / first["products"][0]["history_path"]
        snapshot_bytes = snapshot_path.read_bytes()
        first_capture = self.read_capture(first)
        original_path = self.output / first_capture["source_artifacts"][0]["archive_relative_path"]
        original_bytes = original_path.read_bytes()
        second_input = document()
        second_input["products"][0]["information"]["ingredients_text"] = "Source-provided ingredients"
        second = import_document(second_input, self.output)
        current = json.loads((self.output / second["products"][0]["product_json"]).read_text())
        self.assertEqual(len(current["captures"]), 2)
        self.assertEqual(current["captures"][0], first_capture)
        self.assertEqual(snapshot_path.read_bytes(), snapshot_bytes)
        self.assertEqual(original_path.read_bytes(), original_bytes)
        self.assertEqual(current["latest_capture_id"], second["products"][0]["capture_id"])
        self.assertEqual(current["captures"][1]["raw_section_presence"]["ingredients"]["status"], "source_field_present")
        self.assertEqual(current["captures"][1]["raw_section_presence"]["ingredients"]["completeness"], "not_verified")

    def test_ingredient_presence_excludes_metadata_and_unknown_placeholders(self):
        metadata_only = {"ingredients_status": "missing", "ingredients_quality": "unknown",
                         "ingredients_notes": "Inspect the retained page.", "ingredients": [],
                         "ingredient_capture": {"status": "not captured", "source_url": "https://example.test/product"},
                         "collection_evidence": {"ingredient_evidence_interpretation": "No ingredient list was returned; retain uncertainty."},
                         "ingredients_provenance": "Listing page reviewed", "ingredients_metadata": "Follow-up needed",
                         "ingredients_text": "not available"}
        presence = section_presence(metadata_only)["ingredients"]
        self.assertEqual(presence["status"], "unknown")
        self.assertEqual(presence["paths"], [])
        for evidence in ("Cocoa, sugar", ["Cocoa", "Sugar"], {"text": "Cocoa, sugar", "status": "stated"}):
            presence = section_presence({**metadata_only, "ingredient_candidates": evidence})["ingredients"]
            self.assertEqual(presence["status"], "source_field_present")
            self.assertEqual(presence["completeness"], "not_verified")

    def test_duplicate_product_ids_append_without_losing_parallel_history(self):
        supplied = document()
        second = deepcopy(supplied["products"][0])
        second["source_key"] = "another-source"
        second["information"]["price"] = "GBP 2.50"
        supplied["products"].append(second)
        report = import_document(supplied, self.output, workers=4)
        current = json.loads((self.output / report["products"][0]["product_json"]).read_text())
        self.assertEqual(report["unique_product_ids"], 1)
        self.assertEqual(len(current["captures"]), 2)
        self.assertEqual(len(list((self.output / "tea/uk/products/fixture-1/history").glob("*.json"))), 2)

    def test_exact_compressed_bytes_errors_and_derived_text_remain_distinct(self):
        source = self.root / "blocked.html.gz"
        compressed = gzip.compress(b"<html>429 response</html>")
        source.write_bytes(compressed)
        supplied = document()
        supplied["products"][0]["source_artifacts"] = [
            {"kind": "fetch_error", "local_path": source.name, "url": "https://example.test/product", "content_encoding": "gzip", "http_status": 429, "retrieved_at": "2026-10-03T09:00:00Z"},
            {"kind": "derived_text", "content": "Text derived from another preserved source.", "derivation": "HTML-to-text extraction"},
            {"kind": "unfamiliar_kind", "content": {"original_field": "Keep this."}},
        ]
        report = import_document(supplied, self.output, input_base=self.root)
        capture = self.read_capture(report)
        error = capture["source_artifacts"][0]
        self.assertEqual(error["status"], "saved")
        self.assertEqual(error["source_retrieval_status"], "failed")
        self.assertEqual(error["retrieved_at"], "2026-10-03T09:00:00Z")
        self.assertNotEqual(error["archived_at"], error["retrieved_at"])
        self.assertEqual(error["content_encoding"], "gzip")
        self.assertTrue(error["archive_relative_path"].endswith(".html.gz"))
        self.assertEqual((self.output / error["archive_relative_path"]).read_bytes(), compressed)
        self.assertEqual(capture["source_artifacts"][1]["representation"], "derived_text")
        self.assertEqual(capture["source_artifacts"][2]["descriptor"]["content"], {"original_field": "Keep this."})
        self.assertEqual(report["status"], "partial")

    def test_shared_local_catalog_is_copied_once_with_exact_bytes(self):
        source = self.root / "catalog.json"
        body = b'{"records": [1, 2], "original_format": "retained"}\n'
        source.write_bytes(body)
        supplied = document()
        second = deepcopy(supplied["products"][0])
        second["product_id"] = "fixture-2"
        supplied["products"].append(second)
        for product in supplied["products"]:
            product["source_catalog"] = {"local_path": "catalog.json", "kind": "json", "url": "https://example.test/catalog"}
        report = import_document(supplied, self.output, input_base=self.root)
        self.assertEqual(len(report["source_catalogs"]), 1)
        shared = report["source_catalogs"][0]
        self.assertEqual((self.output / shared["archive_relative_path"]).read_bytes(), body)
        self.assertEqual(self.read_capture(report, 0)["source_catalogs"], self.read_capture(report, 1)["source_catalogs"])

    def test_images_preserve_bytes_and_network_downloads_are_deduplicated(self):
        supplied = document()
        supplied["products"][0]["images"] = [{"url": "https://example.test/original.png", "source_page_url": "https://example.test/product", "alt": "Original alt", "role": "source product gallery"}]
        second = deepcopy(supplied["products"][0])
        second["product_id"] = "fixture-2"
        supplied["products"].append(second)
        response = ({"status": "downloaded", "url": "https://example.test/original.png", "content_type": "image/png", "retrieved_at": "2026-10-03T09:00:00Z", "http_status": 200}, PNG)
        with patch("category_research.archive.get_raw", return_value=response) as fetch:
            report = import_document(supplied, self.output, download_images=True, workers=4)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(report["unique_http_transfers"], 1)
        for index in (0, 1):
            image = self.read_capture(report, index)["images"][0]
            self.assertEqual(image["descriptor"]["alt"], "Original alt")
            self.assertEqual((self.output / image["archive_relative_path"]).read_bytes(), PNG)
            self.assertEqual(image["sha256"], hashlib.sha256(PNG).hexdigest())

    def test_network_is_opt_in_and_image_limit_retains_all_references(self):
        supplied = document()
        supplied["products"][0]["images"] = [{"url": "https://example.test/image.png"}]
        supplied["products"][0]["source_artifacts"] = [{"url": "https://example.test/product", "kind": "page"}]
        with patch("category_research.archive.get_raw", side_effect=AssertionError("Unexpected network")):
            report = import_document(supplied, self.output)
            limited = import_document(supplied, self.output, download_images=True, image_limit=0)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(self.read_capture(limited)["images"][0]["reason"], "image limit")
        self.assertEqual(self.read_capture(limited)["raw_record"]["images"], supplied["products"][0]["images"])

    def test_invalid_identity_does_not_create_an_archive(self):
        supplied = document()
        supplied["products"][0]["product_id"] = "../escape"
        with self.assertRaises(ArchiveError):
            import_document(supplied, self.output)
        self.assertFalse(self.output.exists())

    def test_cli_returns_a_concise_report_without_raw_records(self):
        path = self.root / "input.json"
        path.write_text(json.dumps(document()))
        result = subprocess.run([sys.executable, "-B", str(PLUGIN_ROOT / "cli.py"), "import", "--input", str(path), "--output", str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertNotIn("products", summary)
        self.assertEqual(summary["records_received"], 1)
        self.assertEqual(summary["ingredient_fields_unknown"], 1)
        self.assertTrue((self.output / summary["report_path"]).exists())
        self.assertEqual(json.loads(result.stderr)["completed"], 1)


if __name__ == "__main__":
    unittest.main()
