"""Verify all-row Gold selection, immutable migration and actual input failures."""

import json
import shutil
from unittest.mock import patch

import pytest
from build_chocolate_gold import main
from chocolate_gold import (
    build_gold_dataset,
    build_legacy_gold_dataset,
    checksum,
    json_bytes,
    mark_gold_reviewed,
    mark_legacy_gold_reviewed,
    parquet_bytes,
    read_json,
    read_parquet,
    rows,
    verified_gold,
)
from chocolate_gold_eligibility import mark_gold_eligible
from chocolate_gold_population import TABLE, population_rows, population_schema
from test_gold import GoldFixture
from test_training_run import TrainingRunTests as TrainingFixture
from train_chocolate_model import build_model_run


class TestGoldPopulation(GoldFixture):
    def test_new_gold_has_one_table_without_selection_columns_and_keeps_every_row(self):
        candidates = [self.observation(1), self.observation(2, eligible=True)]
        self.snapshot(candidates)
        original = self.tree_bytes(self.silver)
        report, gold = build_gold_dataset(self.silver, self.output)
        design = read_json(original["model-design.json"])
        schema = population_schema(design)
        values = read_parquet((gold / TABLE).read_bytes(), schema)
        assert values == population_rows(candidates)
        assert "model_eligible" not in schema.names
        assert "exclusion_reasons" not in schema.names
        assert set(read_json((gold / "manifest.json").read_bytes())["tables"]) == {TABLE}
        assert not (gold / "model-inputs.parquet").exists()
        assert report["counts"] == {"training_rows": 2}
        assert "exclusion_counts" not in report and "eligibility_preserved" not in report
        assert self.tree_bytes(self.silver) == original
        assert values[0]["target"]["regular_price_per_100g_gbp"] is None
        assert (gold / "inputs/source-training-candidates.jsonl").read_bytes() == original["training-candidates.jsonl"]
        shutil.rmtree(self.silver)
        inputs = verified_gold(gold)[2]
        assert rows(inputs["model-inputs.jsonl"]) == values
        assert inputs["model-inputs.jsonl"] == inputs["training-candidates.jsonl"]

    @pytest.mark.parametrize("kind", ["original", "reviewed", "override", "population"])
    def test_migration_and_loading_consider_every_row_from_each_supported_snapshot(self, kind):
        candidates = [self.observation(1), self.observation(2, eligible=True)]
        self.snapshot(candidates)
        _, parent = build_gold_dataset(self.silver, self.output) if kind == "population" else build_legacy_gold_dataset(
            self.silver, self.output)
        if kind == "reviewed":
            _, parent = mark_legacy_gold_reviewed(parent, self.output, "User", "Review Gold")
        if kind == "override":
            _, parent = mark_gold_eligible(parent, self.output, "User", "Select all rows")
        before = self.tree_bytes(parent)
        assert rows(verified_gold(parent)[2]["model-inputs.jsonl"]) == population_rows(candidates)
        assert main(["--gold-root", str(parent), "--output", str(self.output)]) == 0
        migrated = next(p for p in self.output.iterdir() if p.is_dir() and
                        (p / "inputs/parent-gold/manifest.json").exists() and
                        (p / "inputs/parent-gold/manifest.json").read_bytes() == before["manifest.json"])
        assert self.tree_bytes(parent) == before
        shutil.rmtree(parent)
        shutil.rmtree(self.silver)
        assert rows(verified_gold(migrated)[2]["model-inputs.jsonl"]) == population_rows(candidates)

    def test_recomputed_table_hashes_cannot_hide_omitted_or_changed_source_rows(self):
        self.snapshot([self.observation(1), self.observation(2)])
        _, gold = build_gold_dataset(self.silver, self.output)
        original = self.tree_bytes(gold)
        design = read_json(original["inputs/model-design.json"])
        for change in (lambda values: values.pop(),
                       lambda values: values[0]["predictors"].update({"composition.cocoa_percentage": 99.0}),
                       lambda values: values.reverse()):
            values = read_parquet(original[TABLE], population_schema(design))
            change(values)
            data, _ = parquet_bytes(values, population_schema(design))
            self.change_manifest(gold, TABLE, data)
            manifest = read_json((gold / "manifest.json").read_bytes())
            from chocolate_gold_population import table_metadata
            manifest["tables"][TABLE] = table_metadata(values)
            (gold / "manifest.json").write_bytes(json_bytes(manifest))
            with pytest.raises(ValueError, match="changed analytical source values or omitted rows"):
                verified_gold(gold)
            for name, data in original.items():
                (gold / name).write_bytes(data)

    def test_review_annotation_never_adds_selection_columns(self):
        self.snapshot([self.observation(1)])
        _, gold = build_gold_dataset(self.silver, self.output)
        _, reviewed = mark_gold_reviewed(gold, self.output, "User", "Review all")
        assert verified_gold(reviewed) == verified_gold(gold)
        assert set(rows(verified_gold(reviewed)[2]["model-inputs.jsonl"])[0]).isdisjoint(
            {"model_eligible", "exclusion_reasons", "review_status", "review_basis"})


@pytest.mark.parametrize("current_price", [False, True])
def test_gold_training_needs_no_row_or_price_eligibility_flag(tmp_path, current_price):
    fixture = TrainingFixture()
    fixture.root, fixture.silver, fixture.output = tmp_path, tmp_path / "silver", tmp_path / "models"
    fixture.silver.mkdir()
    candidates = [fixture.observation(i) for i in range(1, 31)]
    for row in candidates:
        row.update(model_eligible=False, exclusion_reasons=["administrative_exclusion"])
    fixture.snapshot(candidates=candidates)
    # Price flags are also absent. Their actual context remains source evidence.
    prices = [json.loads(line) for line in (fixture.silver / "prices.jsonl").read_bytes().splitlines()]
    for price in prices:
        price.pop("model_eligible")
    fixture.replace_prices(prices)
    _, gold = build_gold_dataset(fixture.silver, tmp_path / "gold")
    report, run = build_model_run(None, fixture.output, "bar", gold_root=gold, current_price_target=current_price)
    assert report["regression_fitted"]
    assert report["counts"]["training_rows"] == 30
    assert report["population_selection"] == "all_gold_rows"
    assert "exclusion_counts" not in report
    selected = rows((run / "selected-inputs.jsonl").read_bytes())
    assert len(selected) == 30
    assert all("model_eligible" not in row and "exclusion_reasons" not in row for row in selected)


def test_empty_population_and_report_corruption_are_verified(tmp_path):
    fixture = GoldFixture()
    fixture.root, fixture.silver, fixture.output = tmp_path, tmp_path / "silver", tmp_path / "gold"
    fixture.silver.mkdir()
    fixture.snapshot()
    report, gold = build_gold_dataset(fixture.silver, fixture.output)
    assert report["counts"] == {"training_rows": 0}
    assert verified_gold(gold)[2]["model-inputs.jsonl"] == b""
    assert build_gold_dataset(fixture.silver, fixture.output) == (report, gold)
    report["counts"]["training_rows"] = 1
    data = json_bytes(report)
    fixture.change_manifest(gold, "report.json", data)
    assert checksum(data) == read_json((gold / "manifest.json").read_bytes())["managed_files"]["report.json"]["sha256"]
    with pytest.raises(ValueError, match="report disagrees"):
        verified_gold(gold)


@pytest.mark.parametrize("current_price", [False, True])
def test_gold_actual_price_failure_saves_readiness_without_attempting_fit(tmp_path, current_price):
    fixture = TrainingFixture()
    fixture.root, fixture.silver, fixture.output = tmp_path, tmp_path / "silver", tmp_path / "models"
    fixture.silver.mkdir()
    fixture.snapshot([fixture.observation(i) for i in range(1, 31)])
    prices = [json.loads(line) for line in (fixture.silver / "prices.jsonl").read_bytes().splitlines()]
    prices[0].update(displayed_price=None) if current_price else prices[0].update(review_status="unreviewed")
    fixture.replace_prices(prices)
    _, gold = build_gold_dataset(fixture.silver, tmp_path / "gold")
    with patch("chocolate_regression.fit_regression", side_effect=AssertionError("must not fit invalid targets")):
        report, run = build_model_run(None, fixture.output, "bar", gold_root=gold, current_price_target=current_price)
    assert report["counts"]["training_rows"] == 30
    assert report["counts"]["selected_observations"] == 30
    assert report["blockers"]
    assert not report["regression_fitted"] and not (run / "model.json").exists()
