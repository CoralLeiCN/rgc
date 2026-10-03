import base64
import gzip
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from category_research import ArchiveError, import_document
from category_research.archive import section_presence

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


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


class ArchiveTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.output = self.root / "archive"

    def read_capture(self, report, index=0):
        return json.loads((self.output / report["products"][index]["history_path"]).read_text())

    def test_complete_original_record_and_generic_sections_are_preserved(self):
        supplied = document()
        original = deepcopy(supplied)
        report = import_document(supplied, self.output)
        capture = self.read_capture(report)
        assert (capture["raw_record"]) == (original["products"][0])
        assert (capture["study"]) == (original["study"])
        assert (capture["collection_notes"]) == (original["products"][0]["collection_notes"])
        assert (set(capture["raw_section_presence"])) == ({"description", "prices", "availability"})
        assert (capture["section_presence_contract_version"]) == ("category-research-sections-2")
        assert ("ingredient_field_status") not in (report["products"][0])
        assert (capture["completeness"]) == ("not_verified")
        assert (capture["raw_section_presence"]["availability"]["status"]) == ("source_field_present")
        assert (supplied) == (original)
        artifact = capture["source_artifacts"][0]
        expected = original["products"][0]["source_artifacts"][0]["content"].encode()
        assert ((self.output / artifact["archive_relative_path"]).read_bytes()) == (expected)
        assert (artifact["sha256"]) == (hashlib.sha256(expected).hexdigest())

    def test_reruns_append_capture_history_and_keep_old_artifacts(self):
        first = import_document(document(), self.output)
        snapshot_path = self.output / first["products"][0]["history_path"]
        snapshot_bytes = snapshot_path.read_bytes()
        first_capture = self.read_capture(first)
        original_path = self.output / first_capture["source_artifacts"][0]["archive_relative_path"]
        original_bytes = original_path.read_bytes()
        second_input = document()
        second_input["collection_sections"] = {"ingredients": ["ingredient"]}
        second_input["products"][0]["information"]["ingredients_text"] = "Source-provided ingredients"
        second = import_document(second_input, self.output)
        current = json.loads((self.output / second["products"][0]["product_json"]).read_text())
        assert (len(current["captures"])) == (2)
        assert (current["captures"][0]) == (first_capture)
        assert (snapshot_path.read_bytes()) == (snapshot_bytes)
        assert (original_path.read_bytes()) == (original_bytes)
        assert (current["latest_capture_id"]) == (second["products"][0]["capture_id"])
        assert (current["captures"][1]["raw_section_presence"]["ingredients"]["status"]) == ("source_field_present")
        assert (current["captures"][1]["raw_section_presence"]["ingredients"]["completeness"]) == ("not_verified")

    def test_non_food_sections_are_caller_selected_and_preserve_mixed_records(self):
        supplied = document()
        supplied["study"]["category"] = "consumer-products"
        supplied["collection_sections"] = {"materials": ["material"], "power": ["Battery Capacity"], "warranty": ["warranty"]}
        supplied["products"][0]["information"] = {"materials": ["Steel", "Wood"], "warranty": None, "original_text": "Bois massif"}
        second = deepcopy(supplied["products"][0])
        second["product_id"] = "fixture-2"
        second["information"] = {"battery_capacity_wh": 0, "warranty": False, "source_name": "Portable lamp"}
        supplied["products"].append(second)
        original = deepcopy(supplied)
        report = import_document(supplied, self.output)
        furniture, lamp = self.read_capture(report, 0), self.read_capture(report, 1)
        assert (furniture["raw_section_presence"]["materials"]["status"]) == ("source_field_present")
        assert (furniture["raw_section_presence"]["power"]["status"]) == ("unknown")
        assert (lamp["raw_section_presence"]["power"]["paths"]) == (["$.information.battery_capacity_wh"])
        assert (lamp["raw_section_presence"]["warranty"]["status"]) == ("source_field_present")
        assert (report["collection_sections"]) == (original["collection_sections"])
        assert ([furniture["raw_record"], lamp["raw_record"]]) == (original["products"])
        assert ("ingredients") not in (lamp["raw_section_presence"])
        assert (supplied) == (original)

    def test_empty_section_configuration_disables_field_heuristics(self):
        supplied = document()
        supplied["collection_sections"] = {}
        report = import_document(supplied, self.output)
        assert (self.read_capture(report)["raw_section_presence"]) == ({})
        assert (report["products"][0]["section_field_statuses"]) == ({})

    def test_unicode_source_markers_match_without_rewriting_original_evidence(self):
        supplied = document()
        supplied["study"]["category"] = "furniture"
        supplied["collection_sections"] = {"materials": ["材料"], "capacity": ["Capacity (mAh)"]}
        supplied["products"][0]["information"] = {"材料说明": "实木", "ＣＡＰＡＣＩＴＹ＿ｍＡｈ": 2400}
        original = deepcopy(supplied)
        report = import_document(supplied, self.output)
        capture = self.read_capture(report)
        assert (capture["raw_section_presence"]["materials"]["paths"]) == (["$.information.材料说明"])
        assert (capture["raw_section_presence"]["capacity"]["paths"]) == (["$.information.ＣＡＰＡＣＩＴＹ＿ｍＡｈ"])
        assert (capture["collection_sections"]) == (original["collection_sections"])
        assert (capture["raw_record"]) == (original["products"][0])
        assert (supplied) == (original)

    def test_existing_legacy_capture_remains_unchanged_when_generic_capture_is_added(self):
        supplied = document()
        product = supplied["products"][0]
        folder = self.output / "tea/uk/products/fixture-1"
        history = folder / "history/legacy.json"
        history.parent.mkdir(parents=True)
        legacy = {"capture_id": "legacy", "raw_record": deepcopy(product),
                  "raw_section_presence": section_presence(product["information"]), "completeness": "not_verified"}
        history.write_text(json.dumps(legacy))
        legacy_bytes = history.read_bytes()
        (folder / "product.json").write_text(json.dumps({"archive_format_version": "category-research-raw-1",
            "product_id": product["product_id"], "category": "tea", "market": "uk", "captures": [legacy]}))
        report = import_document(supplied, self.output)
        current = json.loads((self.output / report["products"][0]["product_json"]).read_text())
        assert (current["captures"][0]) == (legacy)
        assert (history.read_bytes()) == (legacy_bytes)
        assert (current["archive_format_version"]) == ("category-research-raw-1")
        assert ("ingredients") not in (current["captures"][1]["raw_section_presence"])

    def test_invalid_section_configuration_does_not_create_an_archive(self):
        for configuration in (["materials"], {"materials": []}, {"materials": "material"}, {"materials": [None]}, {"materials": ["!!!"]}):
            supplied = document()
            supplied["collection_sections"] = configuration
            with pytest.raises(ArchiveError):
                import_document(supplied, self.output)
            assert not (self.output.exists())

    def test_ingredient_presence_excludes_metadata_and_unknown_placeholders(self):
        metadata_only = {"ingredients_status": "missing", "ingredients_quality": "unknown",
                         "ingredients_notes": "Inspect the retained page.", "ingredients": [],
                         "ingredient_capture": {"status": "not captured", "source_url": "https://example.test/product"},
                         "collection_evidence": {"ingredient_evidence_interpretation": "No ingredient list was returned; retain uncertainty."},
                         "ingredients_provenance": "Listing page reviewed", "ingredients_metadata": "Follow-up needed",
                         "ingredients_text": "not available"}
        presence = section_presence(metadata_only)["ingredients"]
        assert (presence["status"]) == ("unknown")
        assert (presence["paths"]) == ([])
        for evidence in ("Cocoa, sugar", ["Cocoa", "Sugar"], {"text": "Cocoa, sugar", "status": "stated"}):
            presence = section_presence({**metadata_only, "ingredient_candidates": evidence})["ingredients"]
            assert (presence["status"]) == ("source_field_present")
            assert (presence["completeness"]) == ("not_verified")

    def test_duplicate_product_ids_append_without_losing_parallel_history(self):
        supplied = document()
        second = deepcopy(supplied["products"][0])
        second["source_key"] = "another-source"
        second["information"]["price"] = "GBP 2.50"
        supplied["products"].append(second)
        report = import_document(supplied, self.output, workers=4)
        current = json.loads((self.output / report["products"][0]["product_json"]).read_text())
        assert (report["unique_product_ids"]) == (1)
        assert (len(current["captures"])) == (2)
        assert (len(list((self.output / "tea/uk/products/fixture-1/history").glob("*.json")))) == (2)

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
        assert (error["status"]) == ("saved")
        assert (error["source_retrieval_status"]) == ("failed")
        assert (error["retrieved_at"]) == ("2026-10-03T09:00:00Z")
        assert (error["archived_at"]) != (error["retrieved_at"])
        assert (error["content_encoding"]) == ("gzip")
        assert (error["archive_relative_path"].endswith(".html.gz"))
        assert ((self.output / error["archive_relative_path"]).read_bytes()) == (compressed)
        assert (capture["source_artifacts"][1]["representation"]) == ("derived_text")
        assert (capture["source_artifacts"][2]["descriptor"]["content"]) == ({"original_field": "Keep this."})
        assert (report["status"]) == ("partial")

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
        assert (len(report["source_catalogs"])) == (1)
        shared = report["source_catalogs"][0]
        assert ((self.output / shared["archive_relative_path"]).read_bytes()) == (body)
        assert (self.read_capture(report, 0)["source_catalogs"]) == (self.read_capture(report, 1)["source_catalogs"])

    def test_images_preserve_bytes_and_network_downloads_are_deduplicated(self):
        supplied = document()
        supplied["products"][0]["images"] = [{"url": "https://example.test/original.png", "source_page_url": "https://example.test/product", "alt": "Original alt", "role": "source product gallery"}]
        second = deepcopy(supplied["products"][0])
        second["product_id"] = "fixture-2"
        supplied["products"].append(second)
        response = ({"status": "downloaded", "url": "https://example.test/original.png", "content_type": "image/png", "retrieved_at": "2026-10-03T09:00:00Z", "http_status": 200}, PNG)
        with patch("category_research.archive.get_raw", return_value=response) as fetch:
            report = import_document(supplied, self.output, download_images=True, workers=4)
        assert (fetch.call_count) == (1)
        assert (report["unique_http_transfers"]) == (1)
        for index in (0, 1):
            image = self.read_capture(report, index)["images"][0]
            assert (image["descriptor"]["alt"]) == ("Original alt")
            assert ((self.output / image["archive_relative_path"]).read_bytes()) == (PNG)
            assert (image["sha256"]) == (hashlib.sha256(PNG).hexdigest())

    def test_network_is_opt_in_and_image_limit_retains_all_references(self):
        supplied = document()
        supplied["products"][0]["images"] = [{"url": "https://example.test/image.png"}]
        supplied["products"][0]["source_artifacts"] = [{"url": "https://example.test/product", "kind": "page"}]
        with patch("category_research.archive.get_raw", side_effect=AssertionError("Unexpected network")):
            report = import_document(supplied, self.output)
            limited = import_document(supplied, self.output, download_images=True, image_limit=0)
        assert (report["status"]) == ("partial")
        assert (self.read_capture(limited)["images"][0]["reason"]) == ("image limit")
        assert (self.read_capture(limited)["raw_record"]["images"]) == (supplied["products"][0]["images"])

    def test_invalid_identity_does_not_create_an_archive(self):
        supplied = document()
        supplied["products"][0]["product_id"] = "../escape"
        with pytest.raises(ArchiveError):
            import_document(supplied, self.output)
        assert not (self.output.exists())

    def test_cli_returns_a_concise_report_without_raw_records(self):
        path = self.root / "input.json"
        path.write_text(json.dumps(document()))
        result = subprocess.run([sys.executable, "-B", str(PLUGIN_ROOT / "cli.py"), "import", "--input", str(path), "--output", str(self.output)], capture_output=True, text=True)
        assert (result.returncode) == (0), result.stderr
        summary = json.loads(result.stdout)
        assert ("products") not in (summary)
        assert (summary["records_received"]) == (1)
        assert (summary["section_fields_unknown"]) == ({"description": 1, "prices": 0, "availability": 0})
        assert ("ingredient_fields_unknown") not in (summary)
        assert ((self.output / summary["report_path"]).exists())
        assert (json.loads(result.stderr)["completed"]) == (1)

    def test_cli_emits_legacy_ingredient_counter_only_for_an_explicit_section(self):
        supplied = document()
        supplied["collection_sections"] = {"ingredients": ["ingredient"], "materials": ["material"]}
        supplied["products"][0]["information"]["materials"] = ["Glass"]
        path = self.root / "input.json"
        path.write_text(json.dumps(supplied))
        result = subprocess.run([sys.executable, "-B", str(PLUGIN_ROOT / "cli.py"), "import", "--input", str(path), "--output", str(self.output)], capture_output=True, text=True)
        assert (result.returncode) == (0), result.stderr
        summary = json.loads(result.stdout)
        assert (summary["section_fields_unknown"]) == ({"ingredients": 1, "materials": 0})
        assert (summary["ingredient_fields_unknown"]) == (1)
        report = json.loads((self.output / summary["report_path"]).read_text())
        assert (report["products"][0]["ingredient_field_status"]) == ("unknown")
