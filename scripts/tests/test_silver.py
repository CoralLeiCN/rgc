"""Verify that one raw-input command creates a self-contained chocolate silver layer."""

import hashlib
import io
import json
import math
import os
import shutil
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import chocolate_silver as silver_module
import dataset_contracts as contract_module
import pytest
from build_chocolate_silver import main as silver_main
from chocolate_archive_fixture import ChocolateArchiveFixture
from chocolate_cleanup.core import pointer_value
from chocolate_silver import build_silver_dataset
from chocolate_tables import TableBackend

ROOT = Path(__file__).resolve().parents[2]


class ChocolateSilverTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.fixture = ChocolateArchiveFixture()
        self.fixture.initialize(tmp_path)
        self.base = self.fixture.base
        self.archive = self.fixture.archive
        self.output = self.base / "silver"
        self.design = self.fixture.design
        self.schema_root = self.fixture.schema_root

    def product(self, *args, **kwargs):
        return self.fixture.product(*args, **kwargs)

    def collect(self, products):
        return self.fixture.collect(products)

    def snapshot(self, directory):
        return self.fixture.snapshot(directory)

    def build(self, reviews=None, output=None):
        return build_silver_dataset(
            self.archive, output or self.output, reviews=reviews, offline=True
        )

    def rows(self, name):
        return [
            json.loads(line)
            for line in (self.output / (name + ".jsonl"))
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    def reviews(self):
        source = self.rows("source-listings")[0]
        captures = {capture["capture_id"]: capture for capture in source["captures"]}
        latest = captures[source["latest_capture_id"]]
        capture_id = latest["capture_id"]
        common = {
            "reviewed_by": "Fixture evidence reviewer",
            "reason": "Explicit product-specific fixture declaration reviewed.",
        }
        values = latest["raw_record"]["information"]["review_fixture"]
        attributes = {}
        for name in self.design["predictors"]:
            attributes[name] = {
                **common,
                "value": values[name],
                "status": "known",
                "scope": "product",
                "evidence": [
                    {
                        "capture_id": capture_id,
                        "pointer": "/raw_record/information/review_fixture/" + name,
                    }
                ],
            }
            if name == "composition.cocoa_percentage":
                attributes[name]["qualifier"] = "exact"
        product = {
            **common,
            "variant_id": "reviewed-fixture-variant",
            "family_id": "reviewed-fixture-family",
            "in_scope": True,
            "attributes": attributes,
            "evidence": [
                {"capture_id": capture_id, "pointer": "/raw_record/identity/name"}
            ],
        }
        prices = {}
        for price in self.rows("prices"):
            ref = price["evidence"][0]
            raw = captures[ref["capture_id"]]["raw_record"]
            prices[price["observation_id"]] = {
                **common,
                "regular_price": float(raw["information"]["selected_variant"]["price"]),
                "currency": "GBP",
                "tax_basis": "consumer_tax_included",
                "available": True,
                "observed_at": raw["information"]["catalogue_collected_at"],
                "evidence": [deepcopy(ref)],
            }
        return {
            "review_format_version": "chocolate-schema-reviews-1",
            "products": {source["listing_id"]: product},
            "prices": prices,
        }

    def test_raw_input_stays_immutable_and_needs_only_one_output_folder(self):
        self.collect([self.product()])
        raw_before = self.snapshot(self.archive)
        self.build()
        assert self.snapshot(self.archive) == raw_before
        assert {path.name for path in self.base.iterdir()} == {"collections", "silver"}
        assert not (self.base / "deduplicated").exists()
        assert not (self.base / "standardized").exists()
        expected = {
            "quality-report.json",
            "manifest.json",
            "profile.json",
            "source-mappings.json",
            "model-design.json",
            "product.schema.json",
            "products.jsonl",
            "assertions.jsonl",
            "prices.jsonl",
            "training-candidates.jsonl",
            "model-inputs.jsonl",
            "review-queue.jsonl",
            "family-mappings.json",
            "family-review-packets.jsonl",
            "source-listings.jsonl",
            "listing-aliases.jsonl",
        }
        for role in ("brand", "retail", "unknown"):
            expected.update(
                {
                    role + "/products.jsonl",
                    role + "/prices.jsonl",
                    role + "/source-listings.jsonl",
                }
            )
        assert set(self.snapshot(self.output)) == expected
        assert (
            self.rows("source-listings")[0]["captures"][0]["raw_record"]
            == self.product()
        )

    def test_exact_same_seller_duplicates_merge_and_other_sellers_stay_unique(self):
        first = self.product("first-copy", "chocolate-shop")
        alias = self.product("second-copy", "chocolate-shop")
        brand = self.product("brand-listing", "montezumas")
        unknown = self.product("unknown-listing", "unresolved-shop")
        self.collect([first, alias, brand, unknown])
        self.build()
        sources = {row["listing_id"]: row for row in self.rows("source-listings")}
        assert set(sources) == {"first-copy", "brand-listing", "unknown-listing"}
        assert sources["first-copy"]["source_listing_ids"] == [
            "first-copy",
            "second-copy",
        ]
        assert len(sources["first-copy"]["captures"]) == 2
        assert {row["listing_id"] for row in self.rows("products")} == set(sources)
        aliases = {
            (row["source_listing_id"], row["listing_id"])
            for row in self.rows("listing-aliases")
        }
        assert (("second-copy", "first-copy")) in aliases
        assert len(aliases) == 4
        for role, listing in (
            ("brand", "brand-listing"),
            ("retail", "first-copy"),
            ("unknown", "unknown-listing"),
        ):
            assert [
                row["listing_id"] for row in self.rows(role + "/source-listings")
            ] == [listing]
            assert [row["listing_id"] for row in self.rows(role + "/products")] == [
                listing
            ]
        assert sources["first-copy"]["brand"] == sources["brand-listing"]["brand"]
        assert sources["first-copy"]["retailer"] != sources["brand-listing"]["retailer"]

    def test_captures_and_artifacts_resolve_from_silver_and_raw_after_build_returns(
        self,
    ):
        self.collect([self.product()])
        original_temporary_directory = silver_module.TemporaryDirectory
        scratch_paths = []

        def captured_scratch(*args, **kwargs):
            kwargs["dir"] = self.base
            temporary = original_temporary_directory(*args, **kwargs)
            scratch_paths.append(Path(temporary.name).resolve())
            return temporary

        with patch.object(
            silver_module, "TemporaryDirectory", side_effect=captured_scratch
        ):
            self.build()
        sources = self.rows("source-listings")
        captures = {
            capture["capture_id"]: capture
            for source in sources
            for capture in source["captures"]
        }
        assert captures
        for capture in captures.values():
            history = self.archive / capture["history_path"]
            assert history.is_file()
            assert json.loads(history.read_text()) == capture
            for artifact in capture["source_artifacts"]:
                path = self.archive / artifact["archive_relative_path"]
                assert path.read_text() == "Original wording: chocolat noir; café.\n"
        for assertion in self.rows("assertions"):
            for ref in assertion["evidence"]:
                pointer_value(captures[ref["capture_id"]], ref["pointer"])
        for product in self.rows("products"):
            for attribute in product["attributes"].values():
                for ref in attribute["evidence"]:
                    pointer_value(captures[ref["capture_id"]], ref["pointer"])
        for table in ("prices", "review-queue"):
            for row in self.rows(table):
                for ref in row.get("evidence", []):
                    pointer_value(captures[ref["capture_id"]], ref["pointer"])
        published = b"".join(self.snapshot(self.output).values())
        assert str(self.base).encode() not in published
        assert scratch_paths
        for scratch in scratch_paths:
            assert not scratch.exists()
            assert str(scratch).encode() not in published

    def test_parent_and_source_versions_are_consistent_and_all_outputs_hashed(self):
        self.collect([self.product()])
        report = self.build()
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert report["dataset_version"].startswith("silver-")
        assert report["source_dataset_version"].startswith("raw-snapshot-")
        assert manifest["dataset_version"] == report["dataset_version"]
        assert manifest["source_dataset_version"] == report["source_dataset_version"]
        for table in (
            "products",
            "assertions",
            "prices",
            "training-candidates",
            "model-inputs",
        ):
            for row in self.rows(table):
                assert row["dataset_version"] == report["dataset_version"]
                if "source_dataset_version" in row:
                    assert (
                        row["source_dataset_version"]
                        == report["source_dataset_version"]
                    )
        for table in ("source-listings", "listing-aliases", "retail/source-listings"):
            for row in self.rows(table):
                assert row["dataset_version"] == report["dataset_version"]
                assert row["source_dataset_version"] == report["source_dataset_version"]
        for name, metadata in manifest["managed_files"].items():
            data = (self.output / name).read_bytes()
            assert metadata["byte_length"] == len(data)
            assert metadata["sha256"] == hashlib.sha256(data).hexdigest()
        assert set(manifest["managed_files"]) == set(self.snapshot(self.output)) - {
            "manifest.json"
        }
        assert len(manifest["managed_files"]) == 24
        assert set(manifest["contract_sha256"]) == {
            "profile.json",
            "source-mappings.json",
            "model-design.json",
            "product.schema.json",
        }
        for name, checksum in manifest["contract_sha256"].items():
            copied = (self.output / name).read_bytes()
            assert copied == (self.schema_root / name).read_bytes()
            assert hashlib.sha256(copied).hexdigest() == checksum

    def test_custom_contract_directory_is_copied_exactly_and_changes_dataset_version(
        self,
    ):
        self.collect([self.product()])
        original = self.build()
        custom = self.base / "custom-contracts"
        shutil.copytree(
            self.schema_root,
            custom,
            ignore=shutil.ignore_patterns("dataset-contract.json"),
        )
        design_path = custom / "model-design.json"
        design = json.loads(design_path.read_text())
        design["purpose"] += " Custom fixture contract."
        design_path.write_text(
            json.dumps(design, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report = build_silver_dataset(
            self.archive, self.output, schema_root=custom, offline=True
        )
        assert report["dataset_version"] != original["dataset_version"]
        assert report["source_dataset_version"] == original["source_dataset_version"]
        manifest = json.loads((self.output / "manifest.json").read_text())
        for name, checksum in manifest["contract_sha256"].items():
            data = (custom / name).read_bytes()
            assert (self.output / name).read_bytes() == data
            assert hashlib.sha256(data).hexdigest() == checksum

    def test_unavailable_pinned_contract_cache_prevents_raw_processing_and_output(self):
        self.collect([self.product()])
        before = self.snapshot(self.archive)
        with patch.object(
            contract_module, "SCHEMA_CACHE", self.base / "missing-contract-cache"
        ):
            with patch.object(
                silver_module, "build_deduplicated_dataset"
            ) as deduplicate:
                with patch(
                    "category_processing.dataset_contracts._download",
                    side_effect=AssertionError(
                        "Offline builds must not fetch contracts"
                    ),
                ):
                    with pytest.raises(FileNotFoundError, match="not cached"):
                        self.build()
                deduplicate.assert_not_called()
        assert not self.output.exists()
        assert self.snapshot(self.archive) == before

    def test_corrupt_offline_cache_is_rejected_before_raw_processing(self):
        self.collect([self.product()])
        cache_root = self.base / "corrupt-contract-cache"
        reference = contract_module.load_manifest(contract_module.SCHEMA_REFERENCE)
        cached = contract_module.cache_directory(reference, cache_root)
        shutil.copytree(self.schema_root, cached)
        profile = cached / "profile.json"
        profile.write_bytes(profile.read_bytes() + b"\n")
        before = self.snapshot(self.archive)
        with patch.object(contract_module, "SCHEMA_CACHE", cache_root):
            with patch.object(
                silver_module, "build_deduplicated_dataset"
            ) as deduplicate:
                with patch(
                    "category_processing.dataset_contracts._download",
                    side_effect=AssertionError(
                        "Corrupt caches must not be silently refetched"
                    ),
                ):
                    with pytest.raises(ValueError, match="checksum/length mismatch"):
                        self.build()
                deduplicate.assert_not_called()
        assert not self.output.exists()
        assert self.snapshot(self.archive) == before

    def test_same_archive_and_reviews_rebuild_to_identical_bytes(self):
        self.collect([self.product()])
        first = self.build()
        before = self.snapshot(self.output)
        second = self.build()
        assert first == second
        assert self.snapshot(self.output) == before

    def test_pandas_and_compatibility_backends_preserve_exact_table_records(self):
        product = self.product("first-copy")
        product["identity"]["source_product_id"] = 9007199254740993
        product["identity"]["source_variant_id"] = None
        product["information"]["arbitrary_source_fields"] = {
            "integer": 9007199254740993,
            "padded_string": "00123",
            "null": None,
            "boolean": False,
            "float": 1.0,
            "list": [0, None, True],
            "wording": "Original café.\u2028Preserved\u2029source.\n",
        }
        alias = deepcopy(product)
        alias["product_id"] = "second-copy"
        alias["identity"]["source_product_id"] = "9007199254740993"
        self.collect(
            [
                product,
                alias,
                self.product("brand", "montezumas"),
                self.product("unknown", "unknown-shop"),
            ]
        )
        pandas_report = self.build()
        compatible_output = self.base / "silver-stdlib"
        standard_report = build_silver_dataset(
            self.archive, compatible_output, offline=True, table_backend="stdlib"
        )
        assert pandas_report["counts"] == standard_report["counts"]
        assert (
            pandas_report["source_dataset_version"]
            == standard_report["source_dataset_version"]
        )
        assert pandas_report["dataset_version"] != standard_report["dataset_version"]

        def records(path):
            result = []
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    for name in ("dataset_version", "source_dataset_version"):
                        row.pop(name, None)
                    result.append(
                        json.dumps(
                            row, sort_keys=True, ensure_ascii=True, allow_nan=False
                        )
                    )
            return sorted(result) if path.name == "assertions.jsonl" else result

        for path in self.output.rglob("*.jsonl"):
            assert records(path) == records(
                compatible_output / path.relative_to(self.output)
            )
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert manifest["processing_runtime"]["table_backend"] == "pandas"
        for name in (
            "pandas_version",
            "numpy_version",
            "python_version",
            "python_implementation",
        ):
            assert manifest["processing_runtime"][name]
        assert "scripts/chocolate_tables.py" in manifest["implementation_sha256"]
        assert "scripts/build_chocolate_silver.py" in manifest["implementation_sha256"]

    def test_runtime_dependency_changes_version_without_changing_source_or_observation_ids(
        self,
    ):
        self.collect([self.product()])
        original = self.build()
        original_ids = [row["observation_id"] for row in self.rows("prices")]
        original_inputs = self.snapshot(self.archive)
        changed_runtime = {
            **original["processing_runtime"],
            "numpy_version": "fixture-changed-runtime",
        }
        with patch.object(TableBackend, "runtime", return_value=changed_runtime):
            changed = self.build()
        assert changed["dataset_version"] != original["dataset_version"]
        assert changed["source_dataset_version"] == original["source_dataset_version"]
        assert [row["observation_id"] for row in self.rows("prices")] == original_ids
        assert self.snapshot(self.archive) == original_inputs
        manifest = json.loads((self.output / "manifest.json").read_text())
        assert manifest["processing_runtime"] == changed_runtime

    def test_reviews_reuse_stable_observation_ids_and_keep_source_snapshot_version(
        self,
    ):
        self.collect([self.product()])
        initial = self.build()
        ids = {row["observation_id"] for row in self.rows("prices")}
        reviewed = self.build(self.reviews())
        assert initial["dataset_version"] != reviewed["dataset_version"]
        assert initial["source_dataset_version"] == reviewed["source_dataset_version"]
        assert {row["observation_id"] for row in self.rows("prices")} == ids
        assert len(self.rows("model-inputs")) == 1
        row = self.rows("model-inputs")[0]
        assert row["target"]["regular_price_per_100g_gbp"] == 2
        assert (
            round(
                abs((row["target"]["log_regular_price_per_100g_gbp"]) - (math.log(2))),
                7,
            )
            == 0
        )
        assert len(row["predictors"]) == 11
        assert not reviewed["release_ready"]
        before = self.snapshot(self.output)
        assert self.build(self.reviews()) == reviewed
        assert self.snapshot(self.output) == before

    def test_partial_raw_input_quality_is_preserved_in_silver_report(self):
        self.collect([self.product()])
        folder = self.archive / "chocolate/uk/products/invalid"
        folder.mkdir(parents=True)
        (folder / "product.json").write_bytes(b'{"unfinished":')
        before = self.snapshot(self.archive)
        report = self.build()
        assert report["status"] == "partial"
        assert report["input_status"] == "partial"
        assert report["input_quality_counts"]["archive_errors"] == 1
        assert len(self.rows("products")) == 1
        assert not report["release_ready"]
        assert self.snapshot(self.archive) == before

    def assert_changed_source_identity_is_preserved_and_excluded(self, first, latest):
        self.collect([first])
        self.collect([latest])
        raw_index = self.archive / "chocolate/uk/products/example/product.json"
        captures = json.loads(raw_index.read_text())["captures"]
        assert len(captures) == 2
        for capture in captures:
            assert (
                json.loads((self.archive / capture["history_path"]).read_text())
                == capture
            )
        before = self.snapshot(self.archive)
        report = self.build()
        assert report["status"] == "partial"
        assert report["counts"]["archive_errors"] == 1
        assert report["counts"]["listings"] == 0
        assert self.rows("source-listings") == []
        assert self.rows("products") == []
        assert self.rows("prices") == []
        assert self.rows("model-inputs") == []
        assert report["archive_errors"][0]["listing_id"] == "example"
        assert (
            "identity changes across captures" in report["archive_errors"][0]["reason"]
        )
        assert self.snapshot(self.archive) == before
        assert {
            json.dumps(capture["raw_record"], sort_keys=True) for capture in captures
        } == {json.dumps(first, sort_keys=True), json.dumps(latest, sort_keys=True)}

    def test_one_raw_folder_cannot_reassign_historical_prices_to_a_different_seller(
        self,
    ):
        first = self.product(
            source="chocolate-shop", price="4.00", observed_at="2026-10-02T07:00:00Z"
        )
        latest = self.product(
            source="waitrose", price="3.00", observed_at="2026-10-03T07:00:00Z"
        )
        self.assert_changed_source_identity_is_preserved_and_excluded(first, latest)

    def test_one_raw_folder_cannot_mix_different_source_variant_identifiers(self):
        first = self.product(price="4.00", observed_at="2026-10-02T07:00:00Z")
        latest = self.product(price="3.00", observed_at="2026-10-03T07:00:00Z")
        latest["identity"]["source_variant_id"] = "different-source-variant"
        latest["information"]["selected_variant"]["id"] = "different-source-variant"
        self.assert_changed_source_identity_is_preserved_and_excluded(first, latest)

    def test_silver_output_cannot_overlap_raw_archive(self):
        self.collect([self.product()])
        before = self.snapshot(self.archive)
        for output in (self.archive, self.archive / "silver", self.base):
            with pytest.raises(ValueError):
                self.build(output=output)
        assert self.snapshot(self.archive) == before

    def test_raw_index_mutation_between_internal_steps_prevents_publication(self):
        self.collect([self.product()])
        original_standardizer = silver_module.build_standardized_dataset
        raw_index = self.archive / "chocolate/uk/products/example/product.json"

        def standardize_then_mutate(*args, **kwargs):
            report = original_standardizer(*args, **kwargs)
            raw_index.write_bytes(raw_index.read_bytes() + b"\n")
            return report

        with patch.object(
            silver_module,
            "build_standardized_dataset",
            side_effect=standardize_then_mutate,
        ):
            with pytest.raises(RuntimeError, match="Raw archive changed"):
                self.build()
        assert not self.output.exists()

    def test_bad_output_symlink_is_rejected_before_any_output_is_overwritten(self):
        self.collect([self.product()])
        outside = self.base / "protected-product-table.jsonl"
        original = b"Keep this existing external result unchanged.\n"
        outside.write_bytes(original)
        self.output.mkdir()
        (self.output / "products.jsonl").symlink_to(outside)
        with pytest.raises(ValueError, match="output paths"):
            self.build()
        assert outside.read_bytes() == original
        assert {path.name for path in self.output.iterdir()} == {"products.jsonl"}
        assert (self.output / "products.jsonl").is_symlink()

    def test_inside_output_partition_symlink_cannot_alias_another_partition(self):
        self.collect(
            [
                self.product("brand-listing", "montezumas"),
                self.product("retail-listing", "chocolate-shop"),
            ]
        )
        self.build()
        shutil.rmtree(self.output / "brand")
        (self.output / "brand").symlink_to("retail", target_is_directory=True)
        output_before, raw_before = (
            self.snapshot(self.output),
            self.snapshot(self.archive),
        )
        with pytest.raises(ValueError):
            self.build()
        assert self.snapshot(self.output) == output_before
        assert self.snapshot(self.archive) == raw_before
        assert (self.output / "brand").is_symlink()

    def test_legacy_temporary_hardlink_cannot_overwrite_raw_source(self):
        self.collect([self.product()])
        raw_index = self.archive / "chocolate/uk/products/example/product.json"
        self.output.mkdir()
        legacy = self.output / ".products.jsonl.tmp"
        os.link(raw_index, legacy)
        original = raw_index.read_bytes()
        try:
            self.build()
        except ValueError:
            # Refusing the preexisting hardlink and ignoring it while publishing
            # through a unique temporary file both preserve the raw archive.
            pass
        assert raw_index.read_bytes() == original
        assert legacy.read_bytes() == original
        assert legacy.stat().st_ino == raw_index.stat().st_ino

    def test_cli_builds_silver_directly_and_reports_partial_exit_status(self):
        self.collect([self.product()])
        arguments = [
            "--archive-root",
            str(self.archive),
            "--output",
            str(self.output),
            "--schema-root",
            str(self.schema_root),
            "--offline",
        ]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            assert silver_main(arguments) == 0
        result = json.loads(stdout.getvalue())
        assert result["dataset_version"].startswith("silver-")
        assert result["status"] == "complete_snapshot"
        assert result["counts"]["listings"] == 1
        assert (
            Path(result["report_path"]).resolve()
            == (self.output / "quality-report.json").resolve()
        )
        invalid = self.archive / "chocolate/uk/products/invalid"
        invalid.mkdir(parents=True)
        (invalid / "product.json").write_bytes(b'{"unfinished":')
        with redirect_stdout(io.StringIO()):
            assert silver_main(arguments) == 1
        with redirect_stderr(io.StringIO()):
            assert (
                silver_main(
                    ["--archive-root", str(self.archive), "--output", str(self.archive)]
                )
                == 2
            )
