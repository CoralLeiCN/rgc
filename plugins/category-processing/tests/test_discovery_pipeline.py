"""Exercise raw-field discovery through portable snapshots and local review packets."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from category_processing.archive import pointer_value
from category_processing.cli import summarize
from category_processing.pipeline import build_silver_dataset
from category_processing.profile_builder import init_profile
from category_processing.profiles import CONTRACT_FILES
from fixture_archive import import_document
from test_profile_builder import stationery_definition

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class DiscoveryPipelineTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path
        self.archive = self.base / "collections"
        self.profile = self.base / "stationery-profile"
        self.output = self.base / "silver"

    def product(self):
        return {
            "product_id": "fixture-pens", "source_key": "fixture-stationer",
            "source_url": "https://fixture.example.test/products/pens",
            "identity": {"name": "Fixture pens", "brand": "Fixture Maker",
                         "source_product_id": "pens", "source_variant_id": "blue"},
            "information": {
                "group": "ballpoint", "item_count": 2, "length_mm": 140,
                "ink_ml": 2, "warranty_hours": 24,
                "technical": {"material": "plastic", "refillable": False, "colors": ["blue", "black"]},
                "price": {"amount": 4, "regular_amount": 4, "currency": "USD",
                          "observed_at": "2026-10-03T10:00:00Z", "available": True,
                          "tax_basis": "consumer_tax_excluded"},
            },
            "source_artifacts": [{"kind": "page", "content": "Original product evidence.\n"}],
            "images": [], "collection_notes": ["Source acquisition context"],
        }

    def initialize(self, products=None, definition=None):
        init_profile(definition or stationery_definition(), self.profile)
        import_document({"study": {"category": "stationery", "market": "us"},
                         "products": products or [self.product()]}, self.archive)

    def rows(self, name, root=None):
        return [json.loads(line) for line in ((root or self.output) / (name + ".jsonl")).read_text().splitlines()]

    def snapshot(self, root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def build(self):
        return build_silver_dataset(self.archive, self.output, self.profile)

    def pipeline(self):
        return json.loads((self.profile / "pipeline.json").read_text())

    def write_pipeline(self, recipe):
        (self.profile / "pipeline.json").write_text(json.dumps(recipe, ensure_ascii=False) + "\n")

    def use_older_manifest(self):
        manifest_path = self.output / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for name in ("discovered-fields.jsonl", "schema-extension-review.md"):
            manifest["managed_files"].pop(name)
            (self.output / name).unlink()
        manifest_path.write_text(json.dumps(manifest) + "\n")

    def test_fields_outside_sections_and_identity_top_level_are_evidenced_without_new_model_facts(self):
        product = self.product()
        nested = {"source_measure": 0, "source_flag": False, "unit": "Source unit", "basis": None,
                  "components": [{"source_text": "Bois massif", "qualifier": None}, None]}
        product["information"]["unconfigured"] = nested
        product["information"]["price"]["new_context"] = "Source-specific offer basis"
        product["identity"]["batch/identifier~raw"] = "Original batch designation"
        product["new_entity_record"] = {"metadata": {"status": "Business evidence"}}
        self.initialize([product])
        raw_before, contracts_before = self.snapshot(self.archive), self.snapshot(self.profile)
        report = self.build()
        discovered = {row["field_pointer"]: row for row in self.rows("discovered-fields")}
        expected = {
            "/raw_record/information/unconfigured": nested,
            "/raw_record/information/price/new_context": "Source-specific offer basis",
            "/raw_record/identity/batch~1identifier~0raw": "Original batch designation",
            "/raw_record/new_entity_record": {"metadata": {"status": "Business evidence"}},
        }
        for pointer, value in expected.items():
            assert (discovered[pointer]["raw_value"]) == (value)
            assert discovered[pointer]["scope"] is None
            assert discovered[pointer]["unit"] is None
            assert (discovered[pointer]["reason"]) == ("unconfigured_source_field")
        assert (discovered["/raw_record/information/unconfigured"]["value_type"]) == ("object")
        captures = {capture["capture_id"]: capture for row in self.rows("source-listings") for capture in row["captures"]}
        for row in discovered.values():
            assert (pointer_value(captures[row["capture_id"]], row["field_pointer"])) == (row["raw_value"])
            assert (row["evidence"]) == ([{"capture_id": row["capture_id"], "pointer": row["field_pointer"]}])
        batches = [row for row in self.rows("mapping-review-batches") if row["reason"] == "unconfigured_source_field"]
        assert (any(row["value"] == nested for row in batches))
        review = (self.output / "schema-extension-review.md").read_text()
        assert (discovered["/raw_record/information/unconfigured"]["field_id"]) in (review)
        assert ("Meaning, unit, qualifier and semantic scope remain unresolved") in (review)
        assert ("Working hypothesis and triage: pending") in (review)
        profile = json.loads((self.profile / "profile.json").read_text())
        design = json.loads((self.profile / "model-design.json").read_text())
        assert (set(self.rows("products")[0]["attributes"])) == (set(profile["attributes"]))
        assert (set(self.rows("training-candidates")[0]["predictors"])) == (set(design["predictors"]))
        assert (self.rows("model-inputs")) == ([])
        assert (report["release_ready"]) is (False)
        assert (self.snapshot(self.archive)) == (raw_before)
        assert (self.snapshot(self.profile)) == (contracts_before)

    def test_declared_sections_skipped_fields_and_price_context_do_not_double_report(self):
        product = self.product()
        product["information"]["technical"]["new_source_claim"] = {"original_value": 12, "unit": "source unit"}
        product["information"]["technical"]["material"] = "Unrecognized proprietary material"
        product["information"]["variant_label"] = "Default Title"
        definition = stationery_definition()
        definition["pipeline"]["fields"].append({"attribute": "product.name",
                                                "pointer": "/raw_record/information/variant_label",
                                                "skip_values": ["Default Title"]})
        self.initialize([product], definition)
        self.build()
        discovered = self.rows("discovered-fields")
        pointers = {row["field_pointer"] for row in discovered}
        assert not (any(pointer.startswith("/raw_record/information/technical") for pointer in pointers))
        assert ("/raw_record/information/variant_label") not in (pointers)
        assert not (any(pointer.startswith("/raw_record/information/price") for pointer in pointers))
        batches = self.rows("mapping-review-batches")
        new_claim = [row for row in batches if row["attribute"] == "technical.new_source_claim"]
        assert (len(new_claim)) == (1)
        assert (new_claim[0]["value"]) == (product["information"]["technical"]["new_source_claim"])
        failed_material = [row for row in batches if row["attribute"] == "technical.material"]
        assert (len(failed_material)) == (1)
        assert (failed_material[0]["reason"]) == ("standardization_failed")

    def test_failed_extraction_still_discovers_unconfigured_evidence(self):
        product = self.product()
        product["information"]["technical"] = ["Unexpected section format"]
        product["information"]["new_unconfigured_source"] = {"fact": "Original source", "value": 0}
        self.initialize([product])
        raw_before = self.snapshot(self.archive)
        report = self.build()
        assert (report["status"]) == ("partial")
        assert (report["counts"]["extraction_errors"]) > (0)
        fields = {row["field_pointer"]: row for row in self.rows("discovered-fields")}
        assert (fields["/raw_record/information/new_unconfigured_source"]["raw_value"]) == (product["information"]["new_unconfigured_source"])
        assert (fields["/raw_record/information/technical"]["raw_value"]) == (product["information"]["technical"])
        assert (any(row["reason"] == "extraction_failed" for row in self.rows("review-queue")))
        assert (self.rows("processing-ledger")[0]["state"]) == ("failed")
        assert (self.snapshot(self.archive)) == (raw_before)
        assert (self.rows("model-inputs")) == ([])

    def test_repeated_build_is_identical_and_recapture_keeps_seller_field_identity(self):
        product = self.product()
        product["information"]["unconfigured"] = {"original_text": "Source value", "measurement": 0}
        self.initialize([product])
        first = self.build()
        before = self.snapshot(self.output)
        uid = self.rows("products")[0]["seller_uid"]
        field_id = next(row["field_id"] for row in self.rows("discovered-fields")
                        if row["field_pointer"] == "/raw_record/information/unconfigured")
        assert (self.build()) == (first)
        assert (self.snapshot(self.output)) == (before)
        second = deepcopy(product)
        second["information"]["unconfigured"] = {"original_text": "New source value", "measurement": False}
        import_document({"study": {"category": "stationery", "market": "us"}, "products": [second]}, self.archive)
        self.build()
        assert (self.rows("products")[0]["seller_uid"]) == (uid)
        occurrences = [row for row in self.rows("discovered-fields") if row["field_id"] == field_id]
        assert (len(occurrences)) == (2)
        assert ({row["capture_id"] for row in occurrences}) == ({row["capture_id"] for row in self.rows("processing-ledger")})
        assert ([row["field_id"] for row in occurrences]) == ([field_id, field_id])

    def test_discovery_policy_changes_fingerprint_preserving_field_ids_and_effective_control_exclusions(self):
        product = self.product()
        product["information"]["new_section"] = {"candidate": "Original evidence", "ignored": "Context"}
        product["outside"] = "Another source field"
        self.initialize([product])
        first = self.build()
        initial = {row["field_pointer"]: row["field_id"] for row in self.rows("discovered-fields")}
        uid = self.rows("products")[0]["seller_uid"]
        recipe = self.pipeline()
        recipe["pipeline_version"] = "stationery-pipeline-2"
        recipe["discovery"] = {"roots": ["/raw_record/information/new_section"],
                               "ignore_pointers": ["/raw_record/information/new_section/ignored"]}
        self.write_pipeline(recipe)
        narrowed = self.build()
        rows = self.rows("discovered-fields")
        assert ([row["field_pointer"] for row in rows]) == (["/raw_record/information/new_section/candidate"])
        assert (narrowed["processing_fingerprint"]) != (first["processing_fingerprint"])
        assert ("/raw_record/source_artifacts") in (narrowed["field_discovery"]["policy"]["ignore_pointers"])
        assert (self.rows("products")[0]["seller_uid"]) == (uid)
        recipe["discovery"] = {"enabled": False}
        self.write_pipeline(recipe)
        disabled = self.build()
        assert (self.rows("discovered-fields")) == ([])
        assert (disabled["field_discovery"]["policy"]["enabled"]) is (False)
        assert (disabled["processing_fingerprint"]) != (narrowed["processing_fingerprint"])
        recipe.pop("discovery")
        self.write_pipeline(recipe)
        self.build()
        assert ({row["field_pointer"]: row["field_id"] for row in self.rows("discovered-fields")}) == (initial)

    def test_invalid_discovery_controls_fail_before_existing_output_changes(self):
        product = self.product()
        product["information"]["new_field"] = "Original evidence"
        self.initialize([product])
        self.build()
        before = self.snapshot(self.output)
        base_recipe = self.pipeline()
        invalid = [None, [], {"enabled": 1}, {"enabled": "false"}, {"roots": []},
                   {"roots": "/raw_record"}, {"roots": ["/capture_id"]},
                   {"roots": ["/raw_record_bad"]}, {"roots": ["/raw_record/information/~2"]},
                   {"ignore_pointers": "metadata"}, {"ignore_pointers": ["/images"]},
                   {"ignore_pointers": [True]}, {"unknown_control": True}]
        for discovery in invalid:
            recipe = deepcopy(base_recipe)
            recipe["discovery"] = discovery
            self.write_pipeline(recipe)
            with pytest.raises(ValueError):
                self.build()
            assert (self.snapshot(self.output)) == (before)

    def test_summarize_reproduces_review_artifacts_and_refuses_tampered_discovery(self):
        product = self.product()
        product["information"]["new_field"] = {"source_text": "Original wording", "value": False}
        self.initialize([product])
        self.build()
        packet = self.base / "review-packet"
        result = summarize(self.output, packet)
        assert (result["status"]) == ("review_packet_prepared")
        assert (result["discovered_field_count"]) > (0)
        for name in ("mapping-review-batches.jsonl", "mapping-review-summary.md", "discovered-fields.jsonl",
                     "schema-extension-review.md"):
            assert ((packet / name).read_bytes()) == ((self.output / name).read_bytes())
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert ({"discovered-fields.jsonl", "schema-extension-review.md"} <= set(manifest["managed_files"]))
        assert (set(manifest["contract_sha256"])) == (set(CONTRACT_FILES))
        (self.output / "discovered-fields.jsonl").write_text("{}\n")
        rejected = self.base / "rejected-packet"
        with pytest.raises(ValueError, match="differs from its manifest"):
            summarize(self.output, rejected)
        assert not (rejected.exists())

    def test_chocolate_unknown_fallbacks_do_not_hide_new_fields_or_repeat_handled_statements(self):
        self.profile = PLUGIN_ROOT / "profiles/chocolate"
        product = {
            "product_id": "chocolate-fixture", "source_key": "chocolate-shop",
            "source_url": "https://fixture.example.test/products/chocolate",
            "identity": {"name": "Dark Chocolate Bar 100g", "brand": "Fixture Maker",
                         "source_product_id": "chocolate", "source_variant_id": "100g"},
            "information": {
                "selected_variant": {"price": "4.00", "title": "Default Title", "available": True},
                "catalogue_retrieval_currency": "GBP", "catalogue_collected_at": "2026-10-03T10:00:00Z",
                "product_page_information": {"ingredients_source_statement": "Ingredients: cocoa, sugar."},
                "new_source_field": {"source_fact": "Original unfamiliar statement", "value": False},
            },
            "source_artifacts": [], "images": [],
        }
        import_document({"study": {"category": "chocolate", "market": "uk"}, "products": [product]}, self.archive)
        self.build()
        fields = {row["field_pointer"]: row for row in self.rows("discovered-fields")}
        assert (fields["/raw_record/information/new_source_field"]["raw_value"]) == (product["information"]["new_source_field"])
        statement_pointer = "/raw_record/information/product_page_information/ingredients_source_statement"
        assert (statement_pointer) not in (fields)
        assert ("/raw_record/information/catalogue_retrieval_currency") not in (fields)
        assert (self.rows("products")[0]["attributes"]["composition.ingredients_text"]["value"]) == (product["information"]["product_page_information"]["ingredients_source_statement"])
        assert (self.rows("products")[0]["attributes"]["dietary.vegan_claim"]["status"]) == ("unknown")

    def test_chocolate_provisional_group_ancestor_pointer_does_not_hide_new_fields(self):
        self.profile = PLUGIN_ROOT / "profiles/chocolate"
        product = {
            "product_id": "chocolate-fixture", "source_key": "chocolate-shop",
            "source_url": "https://fixture.example.test/products/chocolate",
            "identity": {"source_product_id": "chocolate", "source_variant_id": "100g"},
            "information": {"product_type": "Bar", "new_source_field": {"source_value": 12}},
            "source_artifacts": [], "images": [],
        }
        import_document({"study": {"category": "chocolate", "market": "uk"}, "products": [product]}, self.archive)
        self.build()
        fields = self.rows("discovered-fields")
        assert (any(row["field_pointer"] == "/raw_record/information"
                            and row["raw_value"] == product["information"] for row in fields))
        assert (self.rows("products")[0]["attributes"]["identity.product_group"]["value"]) == ("bar")
        assert (self.rows("model-inputs")) == ([])

    def test_older_manifest_summarizes_without_consuming_unmanaged_discovery_files(self):
        self.initialize()
        self.build()
        self.use_older_manifest()
        # An unrelated leftover is neither verified nor consumed as discovery
        # evidence when an older snapshot's manifest does not declare it.
        (self.output / "discovered-fields.jsonl").write_text("Unmanaged invalid JSON must remain unread.\n")
        packet = self.base / "older-review-packet"
        result = summarize(self.output, packet)
        assert (result["status"]) == ("review_packet_prepared")
        assert (result["discovered_field_count"]) == (0)
        assert not ((packet / "discovered-fields.jsonl").exists())
        assert not ((packet / "schema-extension-review.md").exists())
        for name in ("mapping-review-batches.jsonl", "mapping-review-summary.md"):
            assert ((packet / name).read_bytes()) == ((self.output / name).read_bytes())

    def test_older_snapshot_removes_only_obsolete_discovery_outputs_from_reused_packet(self):
        product = self.product()
        product["information"]["new_source_field"] = "Original unfamiliar evidence"
        self.initialize([product])
        self.build()
        packet = self.base / "reused-review-packet"
        summarize(self.output, packet)
        assert ((packet / "discovered-fields.jsonl").exists())
        assert ((packet / "schema-extension-review.md").exists())
        proposal = packet / "proposals" / "decision.md"
        proposal.parent.mkdir()
        proposal.write_bytes(b"Retain the durable reviewed decision.\n")
        notes = packet / "local-notes.txt"
        notes.write_bytes(b"Retain other local files.\n")
        self.use_older_manifest()
        result = summarize(self.output, packet)
        assert (result["discovered_field_count"]) == (0)
        assert not ((packet / "discovered-fields.jsonl").exists())
        assert not ((packet / "schema-extension-review.md").exists())
        assert (proposal.read_bytes()) == (b"Retain the durable reviewed decision.\n")
        assert (notes.read_bytes()) == (b"Retain other local files.\n")
        assert ((packet / "mapping-review-batches.jsonl").exists())
        assert ((packet / "mapping-review-summary.md").exists())

    def test_unsafe_obsolete_output_is_rejected_before_any_packet_mutation(self):
        self.initialize()
        self.build()
        self.use_older_manifest()
        external = self.base / "external-source.txt"
        external.write_bytes(b"Preserve the external target.\n")
        for name in ("discovered-fields.jsonl", "schema-extension-review.md"):
            for kind in ("symlink", "directory"):
                packet = self.base / (name.replace(".", "-") + "-" + kind)
                packet.mkdir()
                previous = packet / "mapping-review-summary.md"
                previous.write_bytes(b"Preserve the previous packet summary.\n")
                obsolete = packet / name
                if kind == "symlink":
                    obsolete.symlink_to(external)
                else:
                    obsolete.mkdir()
                with pytest.raises(ValueError):
                    summarize(self.output, packet)
                assert (previous.read_bytes()) == (b"Preserve the previous packet summary.\n")
                assert not ((packet / "mapping-review-batches.jsonl").exists())
                assert (obsolete.exists())
                assert (external.read_bytes()) == (b"Preserve the external target.\n")
