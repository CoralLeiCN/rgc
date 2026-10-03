"""Test the additive inferred Gold wrapper and its trainer-compatible child."""

import importlib.util
import json

import pytest
from chocolate_gold import checksum, json_bytes
from chocolate_gold_inferred import build_gold_inferred_dataset, verified_gold_inferred
from test_gold import GoldFixture


@pytest.mark.skipif(importlib.util.find_spec("pyarrow") is None, reason="optional PyArrow gold dependency unavailable")
class InferredGoldTests(GoldFixture):

    def prepare(self, decisions_mutation=None, eligible=False):
        candidate = self.observation(1, eligible=eligible)
        self.snapshot([candidate], [candidate] if eligible else [])
        profile = json.loads((self.silver / "profile.json").read_bytes())
        capture_id = "fixture-capture"
        listing_id = candidate["listing_id"]
        source_text = "70% cocoa; Hazelnut; 2 bars; SKU FIXTURE-1"
        pointer = "/raw_record/information/source_sections/0/value"
        product = {
            "schema_version": "chocolate-schema-1",
            "dataset_version": "silver-fixture",
            "source_dataset_version": "raw-fixture",
            "listing_id": listing_id,
            "source_listing_ids": ["fixture-source-listing"],
            "source_role": "retail",
            "source_key": "fixture",
            "brand": "Fixture Brand",
            "retailer": "Fixture Shop",
            "attributes": {},
            "unmapped_claims": [],
            "review_status": "reviewed",
        }
        for name, specification in profile["attributes"].items():
            product["attributes"][name] = {
                "value": None,
                "status": "unknown",
                "unit": specification.get("unit"),
                "scope": specification.get("scope", "product"),
                "qualifier": None,
                "review_status": "unreviewed",
                "method": "not_established_by_available_evidence",
                "evidence": [],
            }
        values = {
            "composition.cocoa_percentage": (70.0, "70% cocoa"),
            "composition.nut_types": (["hazelnut"], "Hazelnut"),
            "quantity.pack_count": (2, "2 bars"),
            "identity.sku": ("SKU-FIXTURE-1", "SKU FIXTURE-1"),
        }
        if "origin.cocoa_countries" in product["attributes"]:
            product["attributes"]["origin.cocoa_countries"].update(
                status="conflict", review_status="needs_review", method="conflicting_evidence"
            )
        decisions = []
        for attribute, (value, quote) in values.items():
            cell = product["attributes"][attribute]
            cell.update(value=value, status="known", review_status="reviewed", method="evidence_backed_review",
                        evidence=[{"capture_id": capture_id, "pointer": pointer}])
            decisions.append({
                "listing_id": listing_id,
                "capture_id": capture_id,
                "attribute": attribute,
                "value": value,
                "unit": cell["unit"],
                "scope": cell["scope"],
                "qualifier": cell["qualifier"],
                "evidence": [{"pointer": pointer, "quote": quote}],
            })
        if decisions_mutation:
            decisions_mutation(decisions)
        source_listing = {
            "listing_id": listing_id,
            "captures": [{
                "capture_id": capture_id,
                "raw_record": {"information": {"source_sections": [{"value": source_text}]}},
            }],
        }
        self.change_manifest(self.silver, "products.jsonl", (json.dumps(product) + "\n").encode())
        self.change_manifest(self.silver, "source-listings.jsonl", (json.dumps(source_listing) + "\n").encode())
        self.decisions = self.root / "accepted-decisions.jsonl"
        self.decisions.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in decisions))
        manifest = json.loads((self.silver / "manifest.json").read_bytes())
        provenance = {
            "source_silver_manifest_sha256": checksum((self.silver / "manifest.json").read_bytes()),
            "source_silver_dataset_version": manifest["dataset_version"],
            "inputs_sha256": {"adoption/accepted-decisions.jsonl": checksum(self.decisions.read_bytes())},
        }
        self.provenance = self.root / "provenance.json"
        self.provenance.write_bytes(json_bytes(provenance))
        return product, decisions

    def build(self):
        return build_gold_inferred_dataset(
            self.silver, self.output, self.decisions, self.provenance
        )

    def test_roundtrip_preserves_unknown_lists_integers_conflicts_and_trainer_child(self):
        product, decisions = self.prepare()
        report, destination = self.build()
        manifest, products, training_root = verified_gold_inferred(destination, self.silver)
        assert products == [product]
        assert report["counts"] == {
            "products": 1,
            "attributes_per_product": 103,
            "accepted_inference_decisions": 4,
            "training_candidates": 1,
            "eligible_model_inputs": 0,
            "price_observations": 1,
        }
        assert manifest["accepted_inference_decision_count"] == len(decisions)
        assert products[0]["attributes"]["composition.cocoa_percentage"]["value"] == 70.0
        assert products[0]["attributes"]["composition.nut_types"]["value"] == ["hazelnut"]
        assert products[0]["attributes"]["quantity.pack_count"]["value"] == 2
        assert products[0]["attributes"]["origin.cocoa_countries"]["status"] == "conflict"
        assert products[0]["attributes"]["composition.ingredients_text"]["status"] == "unknown"
        assert products[0]["attributes"]["composition.ingredients_text"]["value"] is None
        training_inputs = verified_gold_inferred(destination)[2]
        assert training_inputs == training_root
        from chocolate_gold import verified_gold_storage as verified_gold
        _, _, child_inputs = verified_gold(training_root)
        assert child_inputs["model-inputs.jsonl"] == b""
        assert child_inputs["prices.jsonl"] == (self.silver / "prices.jsonl").read_bytes()
        from train_chocolate_model import build_model_run
        training_report, _ = build_model_run(None, self.root / "models", "bar", gold_root=training_root)
        assert training_report["status"] == "unavailable"
        assert training_report["input_kind"] == "gold"
        assert not training_report["regression_fitted"]

    def test_decision_must_match_reviewed_cell_and_source_quote(self):
        def mutate(decisions):
            decisions[0]["value"] = 71.0
        self.prepare(mutate)
        with pytest.raises(ValueError, match="disagrees with reviewed Silver cell"):
            self.build()

    def test_duplicate_decision_pair_is_rejected(self):
        def mutate(decisions):
            decisions.append(dict(decisions[0]))
        self.prepare(mutate)
        with pytest.raises(ValueError, match="duplicate listing/attribute"):
            self.build()

    def test_source_eligibility_is_preserved_when_present(self):
        self.prepare(eligible=True)
        report, destination = self.build()
        assert report["counts"]["eligible_model_inputs"] == 1
        _, _, training_root = verified_gold_inferred(destination)
        from chocolate_gold import verified_gold_storage as verified_gold
        _, _, child_inputs = verified_gold(training_root)
        assert len(child_inputs["model-inputs.jsonl"].splitlines()) == 1

    def test_bad_source_quote_is_rejected(self):
        product, decisions = self.prepare()
        decisions[0]["evidence"][0]["quote"] = "unrelated source text"
        self.decisions.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in decisions))
        provenance = json.loads(self.provenance.read_bytes())
        provenance["inputs_sha256"]["adoption/accepted-decisions.jsonl"] = checksum(self.decisions.read_bytes())
        self.provenance.write_bytes(json_bytes(provenance))
        with pytest.raises(ValueError, match="not in its cited Silver source capture"):
            self.build()

    def test_decision_and_provenance_symlinks_are_rejected(self):
        self.prepare()
        link = self.root / "decisions-link.jsonl"
        link.symlink_to(self.decisions)
        with pytest.raises(ValueError, match="symlinked paths"):
            build_gold_inferred_dataset(self.silver, self.output, link, self.provenance)

    def test_immutable_replay_and_tampered_bundle_refusal(self):
        self.prepare()
        first_report, first = self.build()
        second_report, second = self.build()
        assert (first_report, first) == (second_report, second)
        products = first / "products.parquet"
        products.write_bytes(b"corrupt")
        with pytest.raises(ValueError, match="refusing to overwrite"):
            self.build()

    def test_product_logical_hash_rejects_coordinated_parquet_and_manifest_edit(self):
        self.prepare()
        _, destination = self.build()
        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet_path = destination / "products.parquet"
        table = pq.read_table(parquet_path)
        rows = table.to_pylist()
        record = json.loads(rows[0]["record_json"])
        record["attributes"]["composition.cocoa_percentage"]["value"] = 71.0
        rows[0]["composition.cocoa_percentage"] = 71.0
        rows[0]["record_json"] = json.dumps(
            record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        sink = pa.BufferOutputStream()
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), sink, **{
            "compression": "zstd", "version": "2.6", "data_page_version": "1.0",
            "use_dictionary": True, "write_statistics": True,
        })
        parquet_bytes = sink.getvalue().to_pybytes()
        parquet_path.write_bytes(parquet_bytes)
        manifest_path = destination / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["managed_files"]["products.parquet"] = {
            "sha256": checksum(parquet_bytes), "byte_length": len(parquet_bytes),
        }
        manifest_path.write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match="product logical checksum mismatch"):
            verified_gold_inferred(destination)
