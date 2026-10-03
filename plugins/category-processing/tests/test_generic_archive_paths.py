"""Check generic study labels against portable collector archive directories."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.archive import load_raw_archive, seller_uid
from category_processing.pipeline import build_silver_dataset
from category_processing.profile_builder import init_profile
from fixture_archive import import_document

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


CATEGORY = "Home_Furniture"
MARKET = "US.Markets"


def definition():
    return {
        "definition_format_version": "category-processing-definition-1",
        "category": CATEGORY, "market": MARKET,
        "versions": {"schema": "furniture-schema-1", "mapping": "furniture-mappings-1",
                     "pipeline": "furniture-pipeline-1", "model_design": "furniture-pricing-1"},
        "attributes": {
            "product.name": {"type": "string", "unit": None, "scope": "product", "standardization_rule": "text"},
            "product.group": {"type": "enum", "unit": None, "scope": "product", "standardization_rule": "vocabulary",
                              "allowed_values": ["chair", "table"]},
            "quantity.items": {"type": "integer", "unit": "item", "scope": "product", "standardization_rule": "quantity", "minimum": 1},
        },
        "standardization_rules": {"text": "Source text.", "vocabulary": "Declared product group.", "quantity": "Explicit item count."},
        "mappings": {"aliases": {}},
        "pipeline": {
            "fields": [{"attribute": "product.name", "pointer": "/raw_record/identity/name"},
                       {"attribute": "product.group", "pointer": "/raw_record/information/group"},
                       {"attribute": "quantity.items", "pointer": "/raw_record/information/count", "unit": "item"}],
            "sections": {}, "group_attribute": "product.group",
            "price": {"amount_pointer": "/raw_record/information/price", "currency": "USD", "price_unit": "major"},
            "quantity": {"attribute": "quantity.items", "unit": "item", "base_quantity": 1},
            "source_roles": {"fixture-shop": {"source_role": "retail", "retailer": "Fixture Shop"}},
        },
        "model_design": {
            "target": {"name": "log_regular_unit_price", "currency": "USD", "unit": "USD_per_item",
                       "quantity_attribute": "quantity.items", "base_quantity": 1,
                       "price_basis": "regular", "tax_basis": "consumer_tax_excluded"},
            "predictors": {"product.group": {"type": "categorical", "required": True, "missing_policy": "reject",
                                              "transform": "identity", "reference": "training_mode", "allowed_values": ["chair", "table"]}},
        },
    }


def product(listing="fixture-chair"):
    return {"product_id": listing, "source_key": "fixture-shop",
            "source_url": "https://fixture.example.test/products/chair",
            "identity": {"name": "Fixture chair", "source_product_id": "chair", "source_variant_id": "oak"},
            "information": {"group": "chair", "count": 1, "price": 240}, "source_artifacts": [], "images": []}


class GenericArchivePathTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.archive = self.base / "collections"

    def normalized_fixture(self):
        # Match collector slugs while retaining the original envelope identifiers.
        import_document({"study": {"category": "home-furniture", "market": "us-markets"},
                         "products": [product()]}, self.archive)
        index = self.archive / "home-furniture/us-markets/products/fixture-chair/product.json"
        document = json.loads(index.read_text())
        document.update(category=CATEGORY, market=MARKET)
        index.write_text(json.dumps(document))
        return index

    def test_normalized_archive_survives_relocation_and_repeated_builds_with_stable_uid(self):
        self.normalized_fixture()
        profile = self.base / "profile"
        init_profile(definition(), profile)
        first_output = self.base / "first-silver"
        build_silver_dataset(self.archive, first_output, profile)
        first = json.loads((first_output / "products.jsonl").read_text())
        relocated = self.base / "relocated/collections"
        shutil.copytree(self.archive, relocated)
        relocated_output = self.base / "relocated-silver"
        first_report = build_silver_dataset(relocated, relocated_output, profile)
        before = {path.relative_to(relocated_output): path.read_bytes() for path in relocated_output.rglob("*") if path.is_file()}
        second_report = build_silver_dataset(relocated, relocated_output, profile)
        after = {path.relative_to(relocated_output): path.read_bytes() for path in relocated_output.rglob("*") if path.is_file()}
        second = json.loads((relocated_output / "products.jsonl").read_text())
        assert (first["seller_uid"]) == (seller_uid(product(), CATEGORY, MARKET, "fixture-chair"))
        assert (first["seller_uid"]) == (second["seller_uid"])
        assert (second["category"]) == (CATEGORY)
        assert (second["market"]) == (MARKET)
        assert (first_report["dataset_version"]) == (second_report["dataset_version"])
        assert (before) == (after)

    def test_exact_safe_directory_identifiers_remain_supported(self):
        import_document({"study": {"category": CATEGORY, "market": MARKET}, "products": [product()]}, self.archive)
        archive = load_raw_archive(self.archive, CATEGORY, MARKET)
        assert (set(archive["listings"])) == ({"fixture-chair"})
        assert (archive["errors"]) == ([])

    def test_normalized_directory_is_preferred_when_both_producers_exist(self):
        self.normalized_fixture()
        import_document({"study": {"category": CATEGORY, "market": MARKET}, "products": [product("legacy-chair")]}, self.archive)
        archive = load_raw_archive(self.archive, CATEGORY, MARKET)
        assert (set(archive["listings"])) == ({"fixture-chair"})
        assert (archive["errors"]) == ([])

    def test_normalized_directory_does_not_relax_exact_envelope_identity(self):
        index = self.normalized_fixture()
        original = json.loads(index.read_text())
        for name, value in (("category", "home-furniture"), ("market", "us-markets")):
            changed = deepcopy(original)
            changed[name] = value
            index.write_text(json.dumps(changed))
            archive = load_raw_archive(self.archive, CATEGORY, MARKET)
            assert (archive["listings"]) == ({})
            assert (archive["errors"][0]["code"]) == ("invalid_archive_record")
            assert ("Product envelope does not match") in (archive["errors"][0]["reason"])

    def test_exact_fallback_cannot_traverse_outside_the_archive(self):
        import_document({"study": {"category": "outside", "market": "us-markets"},
                         "products": [product()]}, self.base)
        with pytest.raises(ValueError, match="Expected outside/us-markets/products"):
            load_raw_archive(self.archive, "../outside", "us-markets")
        for identifier in (".", ".."):
            with pytest.raises(ValueError, match="nonempty directory name"):
                load_raw_archive(self.archive, identifier, "us-markets")
