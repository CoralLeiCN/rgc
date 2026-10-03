"""Verify bulk eligibility, preservation, and rejection of altered Gold inputs."""

import pytest
from chocolate_gold import (
    build_legacy_gold_dataset as build_gold_dataset,
)
from chocolate_gold import (
    checksum,
    json_bytes,
    parquet_bytes,
    read_json,
    read_parquet,
    row_bytes,
    rows,
    training_schema,
)
from chocolate_gold import (
    mark_legacy_gold_reviewed as mark_gold_reviewed,
)
from chocolate_gold import (
    verified_gold_storage as verified_gold,
)
from chocolate_gold_eligibility import mark_gold_eligible
from chocolate_model import ModelContractError, validate_candidates
from test_gold import GoldFixture


class GoldEligibilityTests(GoldFixture):
    def source(self, candidates):
        self.snapshot(candidates)
        return build_gold_dataset(self.silver, self.output)[1]

    def mark(self, source):
        return mark_gold_eligible(source, self.output, "Fixture User", "Make every Gold entity eligible.")

    @pytest.mark.parametrize("reviewed", [False, True])
    def test_promotes_both_views_preserves_parent_and_actual_values(self, reviewed):
        candidates = [self.observation(1), self.observation(2, eligible=True)]
        source = self.source(candidates)
        if reviewed:
            source = mark_gold_reviewed(source, self.output, "Fixture User", "Review all.")[1]
        parent_before = self.tree_bytes(source)
        silver_before = self.tree_bytes(self.silver)
        report, destination = self.mark(source)
        assert self.tree_bytes(source) == parent_before
        assert self.tree_bytes(destination / "inputs/parent-gold") == parent_before
        assert self.tree_bytes(self.silver) == silver_before
        promoted = [{**row, "model_eligible": True, "exclusion_reasons": []} for row in candidates]
        inputs = verified_gold(destination)[2]
        assert rows(inputs["training-candidates.jsonl"]) == promoted
        assert rows(inputs["model-inputs.jsonl"]) == promoted
        assert report["counts"] == {"training_candidates": 2, "eligible_model_inputs": 2}
        assert report["source_counts"]["eligible_model_inputs"] == 1
        assert not report["eligibility_preserved"]
        assert report["analytical_values_preserved"]
        assert not report["eligibility_provenance"]["evidence_validation_performed"]
        with pytest.raises(ModelContractError):
            validate_candidates(promoted, read_json(inputs["model-design.json"]))

    def test_empty_views_and_replay_are_supported(self):
        source = self.source([])
        first = self.mark(source)
        assert self.mark(source) == first
        assert first[0]["counts"] == {"training_candidates": 0, "eligible_model_inputs": 0}
        assert verified_gold(first[1])[2]["model-inputs.jsonl"] == b""
        (first[1] / "report.json").write_bytes(b"damaged")
        with pytest.raises(ValueError, match="refusing to overwrite"):
            self.mark(source)

    def test_authorization_is_required_before_source_access(self):
        for authorized_by, reason in (("", "request"), ("user", " "), (None, "request")):
            with pytest.raises(ValueError, match="explicit user instruction"):
                mark_gold_eligible(self.root / "missing", self.output, authorized_by, reason)

    @pytest.mark.parametrize("mutation", ["target", "eligibility", "ordering"])
    def test_rehashed_table_changes_cannot_escape_parent_comparison(self, mutation):
        _, destination = self.mark(self.source([self.observation(1), self.observation(2)]))
        inputs = verified_gold(destination)[2]
        schema = training_schema(read_json(inputs["model-design.json"]))
        name = "model-inputs.parquet"
        values = read_parquet((destination / name).read_bytes(), schema)
        if mutation == "target":
            values[0]["target"]["regular_price_per_100g_gbp"] = 123.0
        elif mutation == "eligibility":
            values[0]["model_eligible"] = False
        else:
            values.reverse()
        data, _ = parquet_bytes(values, schema)
        self.change_manifest(destination, name, data)
        manifest = read_json((destination / "manifest.json").read_bytes())
        manifest["tables"][name]["logical_sha256"] = checksum(row_bytes(values))
        (destination / "manifest.json").write_bytes(json_bytes(manifest))
        with pytest.raises(ValueError, match="analytical values"):
            verified_gold(destination)

    def test_parent_damage_and_false_report_are_rejected(self):
        _, destination = self.mark(self.source([self.observation(1)]))
        report = read_json((destination / "report.json").read_bytes())
        report["release_ready"] = True
        self.change_manifest(destination, "report.json", json_bytes(report))
        with pytest.raises(ValueError, match="report disagrees"):
            verified_gold(destination)
        report["release_ready"] = False
        self.change_manifest(destination, "report.json", json_bytes(report))
        (destination / "inputs/parent-gold/training-data.parquet").write_bytes(b"damaged")
        with pytest.raises(ValueError, match="checksum mismatch"):
            verified_gold(destination)
