"""Reject inconsistent category contracts before any silver output changes."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from category_processing.pipeline import build_silver_dataset
from category_processing.profiles import load_profile
from fixture_archive import import_document


class ProfileValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.profile = self.base / "profile"
        shutil.copytree(PLUGIN_ROOT / "profiles/coffee", self.profile)

    def edit(self, filename, change):
        path = self.profile / filename
        document = json.loads(path.read_text(encoding="utf-8"))
        change(document)
        path.write_text(json.dumps(document) + "\n", encoding="utf-8")

    def value_schema(self, document, name, location):
        attribute = document["properties"]["attributes"]["properties"][name]
        if location == "nullable":
            return next(branch for branch in attribute["properties"]["value"]["anyOf"]
                        if branch["type"] != "null")
        return attribute["allOf"][0]["then"]["properties"]["value"]

    def test_bundled_profiles_load_with_consistent_contracts(self):
        for category in ("chocolate", "coffee"):
            with self.subTest(category=category):
                profile, unused_mappings, unused_design, unused_recipe, hashes = load_profile(PLUGIN_ROOT / "profiles" / category)
                self.assertEqual(profile["category"], category)
                self.assertEqual(len(hashes), 5)

    def test_new_canonical_label_requires_matching_validator_before_publication(self):
        self.edit("profile.json", lambda doc: doc["attributes"]["coffee.roast"]["allowed_values"].append("ultra"))
        self.edit("source-mappings.json", lambda doc: doc["aliases"]["coffee.roast"].update({"Ultra Roast": "ultra"}))
        archive = self.base / "collections"
        import_document({"study": {"category": "coffee", "market": "uk"}, "products": [{
            "product_id": "fixture", "source_key": "fixture-retailer",
            "source_url": "https://fixture.example/products/coffee",
            "identity": {"source_product_id": "coffee", "name": "Fixture Coffee"},
            "information": {"coffee": {"roast": "Ultra Roast"}},
        }]}, archive)
        output = self.base / "silver"
        output.mkdir()
        marker = output / "existing-snapshot.txt"
        marker.write_bytes(b"Preserve the previous snapshot.\n")
        before = {path.name: path.read_bytes() for path in output.iterdir()}
        with self.assertRaisesRegex(ValueError, "validator vocabulary differs"):
            build_silver_dataset(archive, output, self.profile)
        self.assertEqual({path.name: path.read_bytes() for path in output.iterdir()}, before)

    def test_value_type_drift_in_either_schema_branch_is_rejected(self):
        for location in ("nullable", "known"):
            with self.subTest(location=location):
                self.edit("product.schema.json", lambda doc: self.value_schema(doc, "identity.name", location).update(type="boolean"))
                with self.assertRaisesRegex(ValueError, "attribute type differs"):
                    load_profile(self.profile)
                shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/product.schema.json", self.profile / "product.schema.json")

    def test_numeric_minimum_and_maximum_drift_in_either_branch_is_rejected(self):
        for location in ("nullable", "known"):
            for constraint, value in (("minimum", 100), ("maximum", 250), ("exclusiveMinimum", 0)):
                with self.subTest(location=location, constraint=constraint):
                    self.edit("product.schema.json", lambda doc: self.value_schema(doc, "quantity.net_weight_g", location).update({constraint: value}))
                    with self.assertRaisesRegex(ValueError, "numeric bounds differ|Unsupported product validator value constraints"):
                        load_profile(self.profile)
                    shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/product.schema.json", self.profile / "product.schema.json")

    def test_numeric_profile_bound_change_requires_validator_update(self):
        self.edit("profile.json", lambda doc: doc["attributes"]["quantity.net_weight_g"].update(minimum=10))
        with self.assertRaisesRegex(ValueError, "numeric bounds differ"):
            load_profile(self.profile)

    def test_unit_drift_is_rejected(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["quantity.net_weight_g"]["properties"]["unit"].update(const="kg"))
        with self.assertRaisesRegex(ValueError, "attribute unit differs"):
            load_profile(self.profile)

    def test_list_item_vocabulary_and_type_drift_are_rejected(self):
        for location in ("nullable", "known"):
            with self.subTest(location=location):
                self.edit("product.schema.json", lambda doc: self.value_schema(doc, "origin.countries", location)["items"].update(enum=["Colombia"]))
                with self.assertRaisesRegex(ValueError, "list vocabulary differs"):
                    load_profile(self.profile)
                shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/product.schema.json", self.profile / "product.schema.json")
                self.edit("product.schema.json", lambda doc: self.value_schema(doc, "origin.countries", location)["items"].update(type="number"))
                with self.assertRaisesRegex(ValueError, "list item type differs"):
                    load_profile(self.profile)
                shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/product.schema.json", self.profile / "product.schema.json")

    def test_enum_order_does_not_change_its_contract(self):
        def reorder(document):
            for location in ("nullable", "known"):
                self.value_schema(document, "coffee.roast", location)["enum"].reverse()
        self.edit("product.schema.json", reorder)
        load_profile(self.profile)

    def test_empty_list_vocabulary_cannot_publish_unrestricted_values(self):
        self.edit("profile.json", lambda doc: doc["attributes"]["origin.countries"].update(allowed_values=[]))
        def add_empty_validator(document):
            for location in ("nullable", "known"):
                self.value_schema(document, "origin.countries", location)["items"]["enum"] = []
        self.edit("product.schema.json", add_empty_validator)
        with self.assertRaisesRegex(ValueError, "Profile list vocabulary requires"):
            load_profile(self.profile)

    def test_known_status_requires_its_own_consistent_value_contract(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["coffee.roast"]["allOf"].pop(0))
        with self.assertRaisesRegex(ValueError, "known-status value condition"):
            load_profile(self.profile)

    def test_validator_category_and_market_must_match_profile(self):
        for key in ("category", "market"):
            with self.subTest(key=key):
                self.edit("product.schema.json", lambda doc: doc["properties"][key].update(const="other"))
                with self.assertRaisesRegex(ValueError, "Product validator " + key + " differs"):
                    load_profile(self.profile)
                shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/product.schema.json", self.profile / "product.schema.json")

    def test_selected_model_vocabulary_may_be_subset_but_not_outside_profile(self):
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"].update(allowed_values=["light", "dark"]))
        load_profile(self.profile)
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"]["allowed_values"].append("ultra"))
        with self.assertRaisesRegex(ValueError, "Model predictor vocabulary exceeds"):
            load_profile(self.profile)

    def test_selected_model_type_and_unit_must_match_profile(self):
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"].update(type="numeric"))
        with self.assertRaisesRegex(ValueError, "Numeric model predictor requires"):
            load_profile(self.profile)
        shutil.copyfile(PLUGIN_ROOT / "profiles/coffee/model-design.json", self.profile / "model-design.json")
        self.edit("model-design.json", lambda doc: doc["predictors"]["quantity.net_weight_g"].update(unit="kg"))
        with self.assertRaisesRegex(ValueError, "Model predictor unit differs"):
            load_profile(self.profile)


if __name__ == "__main__":
    unittest.main()
