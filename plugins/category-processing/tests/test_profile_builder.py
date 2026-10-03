"""Exercise category-neutral contract authoring and a relocated nonfood pipeline."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.adapters import extract_capture
from category_processing.profile_builder import init_profile
from category_processing.profiles import CONTRACT_FILES, load_profile
from category_processing.values import standardize_value
from fixture_archive import import_document

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def stationery_definition():
    """Explicit policy; no bundled profile provides attributes or conventions."""
    return {
        "definition_format_version": "category-processing-definition-1",
        "category": "stationery", "market": "us",
        "versions": {"schema": "stationery-schema-1", "mapping": "stationery-mappings-1",
                     "pipeline": "stationery-pipeline-1", "model_design": "stationery-pricing-1"},
        "attributes": {
            "product.name": {"type": "string", "unit": None, "scope": "product", "standardization_rule": "text"},
            "product.group": {"type": "enum", "unit": None, "scope": "product", "standardization_rule": "vocabulary",
                              "allowed_values": ["pen", "pencil"]},
            "quantity.items": {"type": "integer", "unit": "item", "scope": "product", "standardization_rule": "quantity", "minimum": 1},
            "technical.material": {"type": "enum", "unit": None, "scope": "product", "standardization_rule": "vocabulary",
                                   "allowed_values": ["polymer", "metal"]},
            "technical.length": {"type": "number", "unit": "m", "scope": "product", "standardization_rule": "quantity", "minimum": 0},
            "technical.ink_volume": {"type": "number", "unit": "l", "scope": "product", "standardization_rule": "quantity", "minimum": 0},
            "technical.warranty": {"type": "number", "unit": "s", "scope": "product", "standardization_rule": "quantity", "minimum": 0},
            "technical.refillable": {"type": "boolean", "unit": None, "scope": "product", "standardization_rule": "boolean"},
            "technical.colors": {"type": "string_list", "unit": None, "scope": "product", "standardization_rule": "vocabulary",
                                 "allowed_values": ["blue", "black"]},
        },
        "standardization_rules": {"text": "Canonical source text.", "vocabulary": "Explicit aliases to declared labels.",
                                  "quantity": "Typed numbers in explicit units.", "boolean": "Typed source boolean."},
        "mappings": {"aliases": {"product.group": {"ballpoint": "pen"}, "technical.material": {"plastic": "polymer"}},
                     "unit_conversions": {"m": {"mm": 0.001}, "l": {"ml": 0.001}, "s": {"hour": 3600}}},
        "pipeline": {
            "fields": [{"attribute": "product.name", "pointer": "/raw_record/identity/name"},
                       {"attribute": "product.group", "pointer": "/raw_record/information/group"},
                       {"attribute": "quantity.items", "pointer": "/raw_record/information/item_count", "unit": "item"},
                       {"attribute": "technical.length", "pointer": "/raw_record/information/length_mm", "unit": "mm"},
                       {"attribute": "technical.ink_volume", "pointer": "/raw_record/information/ink_ml", "unit": "ml"},
                       {"attribute": "technical.warranty", "pointer": "/raw_record/information/warranty_hours", "unit": "hour"}],
            "sections": {"/raw_record/information/technical": "technical"},
            "group_attribute": "product.group",
            "price": {"amount_pointer": "/raw_record/information/price/amount",
                      "regular_price_pointer": "/raw_record/information/price/regular_amount",
                      "currency_pointer": "/raw_record/information/price/currency",
                      "observed_at_pointer": "/raw_record/information/price/observed_at",
                      "available_pointer": "/raw_record/information/price/available",
                      "tax_basis_pointer": "/raw_record/information/price/tax_basis", "price_unit": "major"},
            "quantity": {"attribute": "quantity.items", "unit": "item", "base_quantity": 1},
            "source_roles": {"fixture-stationer": {"source_role": "retail", "retailer": "Fixture Stationer"}},
        },
        "model_design": {
            "target": {"name": "log_regular_unit_price", "currency": "USD", "unit": "USD_per_item",
                       "quantity_attribute": "quantity.items", "base_quantity": 1,
                       "price_basis": "regular", "tax_basis": "consumer_tax_excluded"},
            "eligibility": {"allowed_tax_bases": ["consumer_tax_excluded"]},
            "predictors": {"technical.material": {"type": "categorical", "required": True, "missing_policy": "reject",
                                                  "transform": "identity", "reference": "training_mode",
                                                  "allowed_values": ["polymer", "metal"]}},
        },
    }


class ProfileBuilderTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.output = self.base / "profiles/stationery-1"

    def test_generates_all_six_attribute_types_and_five_aligned_contracts(self):
        definition = stationery_definition()
        original = deepcopy(definition)
        result = init_profile(definition, self.output)
        assert (definition) == (original)
        assert (set(path.name for path in self.output.iterdir())) == (set(CONTRACT_FILES))
        profile, mappings, design, recipe, fingerprints = load_profile(self.output)
        assert (result["contract_sha256"]) == (fingerprints)
        assert (profile["attributes"]) == (definition["attributes"])
        assert (design["target"]) == (definition["model_design"]["target"])
        assert (recipe["group_attribute"]) == ("product.group")
        assert (recipe["adapter"]) == ("structured")
        assert (mappings["unit_conversions"]) == (definition["mappings"]["unit_conversions"])
        validator = json.loads((self.output / "product.schema.json").read_text())
        assert ({"category", "market"} <= set(validator["required"]))
        for name, attribute in profile["attributes"].items():
            envelope = validator["properties"]["attributes"]["properties"][name]
            assert (envelope["properties"]["unit"]["const"]) == (attribute["unit"])
            assert (envelope["properties"]["value"]["anyOf"][1]) == (envelope["allOf"][0]["then"]["properties"]["value"])
        assert (design["status"]) == ("specified_not_trained")

    def test_arbitrary_units_are_normalized_only_by_explicit_conversion_tables(self):
        init_profile(stationery_definition(), self.output)
        profile, mappings, unused_design, unused_recipe, unused_hashes = load_profile(self.output)
        for name, raw, unit, expected in (("technical.length", 140, "mm", 0.14),
                                           ("technical.ink_volume", 2, "ml", 0.002),
                                           ("technical.warranty", 24, "hour", 86400)):
            assert round(abs((standardize_value(name, raw, profile, mappings, unit)) - (expected)), 7) == 0
        with pytest.raises(ValueError, match="Unsupported unit conversion"):
            standardize_value("technical.length", 6, profile, mappings, "inch")

    def test_reference_definition_is_complete_and_missing_count_is_not_inferred(self):
        reference = PLUGIN_ROOT / "skills/category-processing/references/profile-definition.md"
        example = re.search(r"```json\n(.*?)\n```", reference.read_text(), flags=re.DOTALL).group(1)
        init_profile(json.loads(example), self.output)
        unused_profile, unused_mappings, unused_design, recipe, unused_hashes = load_profile(self.output)
        extracted = extract_capture({"raw_record": {"information": {"price": {"amount": 4, "currency": "USD"}}}}, recipe)
        assert (extracted["quantities"]) == ([])
        assert not (any(attribute["attribute"] == "quantity.items" for attribute in extracted["attributes"]))

    def test_explicit_currency_precision_and_tax_policy_are_preserved(self):
        definition = stationery_definition()
        definition["model_design"]["target"].update(currency="JPY", unit="JPY_per_item", tax_basis="consumer_tax_included")
        definition["model_design"].pop("eligibility")
        definition["pipeline"]["price"].update(price_unit="minor", minor_unit_factor=1)
        init_profile(definition, self.output)
        unused_profile, unused_mappings, design, recipe, unused_hashes = load_profile(self.output)
        assert (design["target"]["currency"]) == ("JPY")
        assert (design["eligibility"]) == ({"allowed_tax_bases": ["consumer_tax_included"]})
        assert (recipe["price"]["minor_unit_factor"]) == (1)

    def test_invalid_or_unknown_controls_fail_before_publishing(self):
        mutations = (
            lambda d: d.update(definition_format_version="unsupported"),
            lambda d: d.update(category="../stationery"),
            lambda d: d.update(adapter="arbitrary.module"),
            lambda d: d["pipeline"].update(adapter="arbitrary.module"),
            lambda d: d["pipeline"].update(group_attribute="missing.group"),
            lambda d: d["pipeline"]["price"].update(amount_pointr="/typo"),
            lambda d: d["pipeline"]["price"].update(price_unit="minor"),
            lambda d: d["model_design"]["target"].update(base_quantity=100),
            lambda d: d["model_design"]["target"].update(currency=""),
            lambda d: d["model_design"]["eligibility"].update(allowed_tax_bases=["consumer_tax_excluded", "consumer_tax_included"]),
            lambda d: d["model_design"]["predictors"]["technical.material"].update(transform="log"),
            lambda d: d["model_design"].update(interpretation={"regression_fitted": True}),
            lambda d: d["mappings"]["aliases"]["product.group"].update(ballpoint="food"),
        )
        for mutation in mutations:
            definition = stationery_definition()
            mutation(definition)
            with pytest.raises(ValueError):
                init_profile(definition, self.output)
            assert not (self.output.exists())

    def test_output_collision_preserves_contract_bytes_and_empty_directory(self):
        init_profile(stationery_definition(), self.output)
        before = {path.name: path.read_bytes() for path in self.output.iterdir()}
        changed = stationery_definition()
        changed["versions"]["schema"] = "stationery-schema-2"
        with pytest.raises(ValueError, match="already exists"):
            init_profile(changed, self.output)
        assert ({path.name: path.read_bytes() for path in self.output.iterdir()}) == (before)
        empty = self.base / "empty"
        empty.mkdir()
        with pytest.raises(ValueError, match="already exists"):
            init_profile(changed, empty)
        assert (list(empty.iterdir())) == ([])

    def test_copied_cli_authors_processes_and_prepares_nonfood_without_bundled_profiles(self):
        copied = self.base / "portable"
        shutil.copytree(PLUGIN_ROOT / "category_processing", copied / "category_processing", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(PLUGIN_ROOT / "cli.py", copied / "cli.py")
        definition = self.base / "stationery-definition.json"
        definition.write_text(json.dumps(stationery_definition()))

        def run(*arguments):
            completed = subprocess.run([sys.executable, "-I", "-B", str(copied / "cli.py"), *map(str, arguments)],
                                       cwd=self.base, capture_output=True, text=True)
            assert (completed.returncode) == (0), (completed.stderr)
            return json.loads(completed.stdout)

        assert (run("init-profile", "--input", definition, "--output", self.output)["status"]) == ("profile_initialized")
        archive, silver = self.base / "collections", self.base / "silver"
        products = []
        for suffix, amount in (("a", 4), ("b", 6)):
            products.append({"product_id": "pens-" + suffix, "source_key": "fixture-stationer",
                             "source_url": "https://stationer.example.test/products/pens-" + suffix,
                             "identity": {"name": "Fixture pens " + suffix, "brand": "Fixture Maker",
                                          "source_product_id": "pens-" + suffix, "source_variant_id": "pens-" + suffix},
                             "information": {"group": "ballpoint", "item_count": 2, "length_mm": 140, "ink_ml": 2,
                                             "warranty_hours": 24, "technical": {"material": "plastic", "refillable": False,
                                                                                 "colors": ["blue", "black"]},
                                             "price": {"amount": amount, "regular_amount": amount, "currency": "USD",
                                                       "observed_at": "2026-10-03T10:00:00Z", "available": True,
                                                       "tax_basis": "consumer_tax_excluded"}},
                             "source_artifacts": [{"kind": "page", "content": "Preuve originale: stylos bleus.\n"}], "images": []})
        import_document({"study": {"category": "stationery", "market": "us"}, "products": products}, archive)
        before = {path.relative_to(archive).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in archive.rglob("*") if path.is_file()}
        assert (run("process", "--archive-root", archive, "--profile", self.output, "--output", silver)["status"]) == ("complete_snapshot")
        def rows(name):
            return [json.loads(line) for line in (silver / (name + ".jsonl")).read_text().splitlines()]
        listings, prices = rows("products"), rows("prices")
        for listing in listings:
            attributes = listing["attributes"]
            assert (attributes["quantity.items"]["value"]) == (2)
            assert round(abs((attributes["technical.length"]["value"]) - (0.14)), 7) == 0
            assert round(abs((attributes["technical.ink_volume"]["value"]) - (0.002)), 7) == 0
            assert (attributes["technical.warranty"]["value"]) == (86400)
            assert (attributes["technical.refillable"]["value"]) is (False)
            assert (attributes["technical.colors"]["value"]) == (["black", "blue"])
        assert (rows("model-inputs")) == ([])
        common = {"reviewed_by": "Fixture reviewer", "reason": "The saved source establishes these fixture facts."}
        reviews = {"review_format_version": "category-processing-reviews-1", "products": {}, "prices": {}}
        for listing in listings:
            attributes = listing["attributes"]
            reviews["products"][listing["seller_uid"]] = {
                **common, "variant_id": "variant-" + listing["listing_id"], "family_id": "family-" + listing["listing_id"],
                "in_scope": True, "evidence": deepcopy(attributes["product.name"]["evidence"]),
                "attributes": {name: {**common, "status": "known", "value": attributes[name]["value"],
                                      "unit": attributes[name]["unit"], "scope": "product",
                                      "evidence": deepcopy(attributes[name]["evidence"])}
                               for name in ("product.group", "quantity.items", "technical.material")},
            }
        for price in prices:
            reviews["prices"][price["observation_id"]] = {
                **common, "regular_price": price["regular_price"], "currency": "USD",
                "tax_basis": "consumer_tax_excluded", "available": True, "observed_at": "2026-10-03T10:00:00Z",
                "evidence": deepcopy(price["evidence"]),
            }
        review_path = self.base / "reviews.json"
        review_path.write_text(json.dumps(reviews))
        run("process", "--archive-root", archive, "--profile", self.output, "--output", silver, "--reviews", review_path)
        eligible = rows("model-inputs")
        assert (sorted(row["target"]["regular_unit_price"] for row in eligible)) == ([2, 3])
        assert ({row["seller_uid"] for row in rows("products")}) == ({row["seller_uid"] for row in listings})
        prepared = self.base / "prepared"
        report = run("prepare-model", "--silver-root", silver, "--output", prepared)
        assert (report["target_definition"]["unit"]) == ("USD_per_item")
        assert (report["split"]["training_observations"]) == (1)
        assert (report["split"]["validation_observations"]) == (1)
        assert (report["regression_fitted"]) is (False)
        after = {path.relative_to(archive).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in archive.rglob("*") if path.is_file()}
        assert (after) == (before)
