"""Reject inconsistent category contracts before any silver output changes."""

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.pipeline import build_silver_dataset
from category_processing.profiles import load_profile, resolve_profile
from fixture_archive import import_document

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class ProfileValidationTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.profile = self.base / "profile"
        self.packaged_coffee = resolve_profile(PLUGIN_ROOT / "profiles/coffee")
        shutil.copytree(self.packaged_coffee, self.profile, ignore=shutil.ignore_patterns("dataset-contract.json"))

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

    def test_pinned_profiles_load_with_consistent_contracts(self):
        for category in ("chocolate", "coffee"):
            profile, unused_mappings, unused_design, unused_recipe, hashes = load_profile(resolve_profile(category=category))
            assert (profile["category"]) == (category)
            assert (len(hashes)) == (5)

    def test_pinned_reference_metadata_must_match_verified_payload_meaning(self):
        names = ("profile.json", "source-mappings.json", "model-design.json", "product.schema.json", "pipeline.json")
        bodies = {name: (self.profile / name).read_bytes() for name in names}
        documents = {name: json.loads(body) for name, body in bodies.items()}
        profile, mappings, design, recipe = (documents[name] for name in
                                             ("profile.json", "source-mappings.json", "model-design.json", "pipeline.json"))
        reference = {"format_version": "rgc-dataset-contract-reference-1", "repo_id": "fixture/contracts",
                     "revision": "a" * 40, "contract_set": "category-processing/coffee",
                     "category": profile["category"], "market": profile["market"],
                     "schema_version": profile["schema_version"], "mapping_version": mappings["mapping_version"],
                     "model_design_version": design["model_design_version"], "pipeline_version": recipe["pipeline_version"],
                     "attribute_count": profile["attribute_count"],
                     "files": {name: {"path": "contracts/category-processing/coffee/" + name,
                                      "sha256": hashlib.sha256(body).hexdigest(), "size_bytes": len(body)}
                               for name, body in bodies.items()}}
        marker = self.profile / "dataset-contract.json"
        marker.write_text(json.dumps(reference) + "\n", encoding="utf-8")
        load_profile(self.profile)
        for field in ("category", "market", "schema_version", "mapping_version", "model_design_version",
                      "pipeline_version", "attribute_count"):
            changed = deepcopy(reference)
            changed[field] = reference[field] + 1 if field == "attribute_count" else "different-" + reference[field]
            if field == "category":
                changed["contract_set"] = "category-processing/" + changed[field]
                for name, metadata in changed["files"].items():
                    metadata["path"] = "contracts/" + changed["contract_set"] + "/" + name
            marker.write_text(json.dumps(changed) + "\n", encoding="utf-8")
            with pytest.raises(ValueError, match="dataset reference metadata: " + field):
                load_profile(self.profile)

    def test_model_and_recipe_require_shared_regular_consumer_price_policy(self):
        for filename, path in (("model-design.json", "target"), ("pipeline.json", "price")):
            for field, value in (("price_basis", "displayed"), ("tax_basis", "unknown"),
                             ("promotion_basis", "promotional"), ("fallback_policy", "reference"),
                             ("price_basis_contract_version", None)):
                def change(document):
                    target = document[path] if path == "target" else document["price"]["target_policy"]
                    target[field] = value
                self.edit(filename, change)
                with pytest.raises(ValueError, match=field):
                    load_profile(self.profile)
                shutil.copyfile(self.packaged_coffee / filename, self.profile / filename)

    def test_missing_recipe_price_policy_is_rejected_before_publication(self):
        self.edit("pipeline.json", lambda doc: doc["price"].pop("target_policy"))
        with pytest.raises(ValueError, match="target_policy|target policy"):
            load_profile(self.profile)

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
        with pytest.raises(ValueError, match="validator vocabulary differs"):
            build_silver_dataset(archive, output, self.profile)
        assert ({path.name: path.read_bytes() for path in output.iterdir()}) == (before)

    def test_value_type_drift_in_either_schema_branch_is_rejected(self):
        for location in ("nullable", "known"):
            self.edit("product.schema.json", lambda doc: self.value_schema(doc, "identity.name", location).update(type="boolean"))
            with pytest.raises(ValueError, match="attribute type differs"):
                load_profile(self.profile)
            shutil.copyfile(self.packaged_coffee / "product.schema.json", self.profile / "product.schema.json")

    def test_numeric_minimum_and_maximum_drift_in_either_branch_is_rejected(self):
        for location in ("nullable", "known"):
            for constraint, value in (("minimum", 100), ("maximum", 250), ("exclusiveMinimum", 0)):
                self.edit("product.schema.json", lambda doc: self.value_schema(doc, "quantity.net_weight_g", location).update({constraint: value}))
                with pytest.raises(ValueError, match="numeric bounds differ|Unsupported product validator value constraints"):
                    load_profile(self.profile)
                shutil.copyfile(self.packaged_coffee / "product.schema.json", self.profile / "product.schema.json")

    def test_numeric_profile_bound_change_requires_validator_update(self):
        self.edit("profile.json", lambda doc: doc["attributes"]["quantity.net_weight_g"].update(minimum=10))
        with pytest.raises(ValueError, match="numeric bounds differ"):
            load_profile(self.profile)

    def test_unit_drift_is_rejected(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["quantity.net_weight_g"]["properties"]["unit"].update(const="kg"))
        with pytest.raises(ValueError, match="attribute unit differs"):
            load_profile(self.profile)

    def test_list_item_vocabulary_and_type_drift_are_rejected(self):
        for location in ("nullable", "known"):
            self.edit("product.schema.json", lambda doc: self.value_schema(doc, "origin.countries", location)["items"].update(enum=["Colombia"]))
            with pytest.raises(ValueError, match="list vocabulary differs"):
                load_profile(self.profile)
            shutil.copyfile(self.packaged_coffee / "product.schema.json", self.profile / "product.schema.json")
            self.edit("product.schema.json", lambda doc: self.value_schema(doc, "origin.countries", location)["items"].update(type="number"))
            with pytest.raises(ValueError, match="list item type differs"):
                load_profile(self.profile)
            shutil.copyfile(self.packaged_coffee / "product.schema.json", self.profile / "product.schema.json")

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
        with pytest.raises(ValueError, match="Profile list vocabulary requires"):
            load_profile(self.profile)

    def test_known_status_requires_its_own_consistent_value_contract(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["coffee.roast"]["allOf"].pop(0))
        with pytest.raises(ValueError, match="known-status value condition"):
            load_profile(self.profile)

    def test_validator_category_and_market_must_match_profile(self):
        for key in ("category", "market"):
            self.edit("product.schema.json", lambda doc: doc["properties"][key].update(const="other"))
            with pytest.raises(ValueError, match="Product validator " + key + " differs"):
                load_profile(self.profile)
            shutil.copyfile(self.packaged_coffee / "product.schema.json", self.profile / "product.schema.json")

    def test_selected_model_vocabulary_may_be_subset_but_not_outside_profile(self):
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"].update(allowed_values=["light", "dark"]))
        load_profile(self.profile)
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"]["allowed_values"].append("ultra"))
        with pytest.raises(ValueError, match="Model predictor vocabulary exceeds"):
            load_profile(self.profile)

    def test_selected_model_type_and_unit_must_match_profile(self):
        self.edit("model-design.json", lambda doc: doc["predictors"]["coffee.roast"].update(type="numeric"))
        with pytest.raises(ValueError, match="Numeric model predictor requires"):
            load_profile(self.profile)
        shutil.copyfile(self.packaged_coffee / "model-design.json", self.profile / "model-design.json")
        self.edit("model-design.json", lambda doc: doc["predictors"]["quantity.net_weight_g"].update(unit="kg"))
        with pytest.raises(ValueError, match="Model predictor unit differs"):
            load_profile(self.profile)
