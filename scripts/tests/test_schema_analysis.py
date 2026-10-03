"""Verify evidence-state frequencies and safe schema-analysis output."""

import hashlib
import importlib.util
import io
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_chocolate_schema.py"
SPEC = importlib.util.spec_from_file_location("analyze_chocolate_schema", MODULE_PATH)
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def cell(value=None, status="unknown", scope="product", qualifier=None):
    return {
        "status": status,
        "review_status": "unreviewed",
        "value": value,
        "scope": scope,
        "qualifier": qualifier,
        "method": "source",
    }


class SchemaAnalysisTests:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.profile = {
            "schema_version": "fixture-1",
            "groups": ["nutrition", "claim", "ingredients"],
            "attributes": {
                "nutrition.amount": {"type": "number", "unit": "g"},
                "nutrition.unavailable": {"type": "number", "unit": "g"},
                "claim.nut": {
                    "type": "enum",
                    "allowed_values": ["present", "absent", "other"],
                },
                "ingredients.tokens": {"type": "string_list"},
            },
        }
        self.design = {"predictors": ["nutrition.amount"]}
        self.rows = []
        for index in range(6):
            attributes = {name: cell() for name in self.profile["attributes"]}
            if index < 3:
                attributes["nutrition.amount"] = cell(0, "known", "per_100g")
                attributes["claim.nut"] = cell(
                    "present" if index < 2 else "absent", "known"
                )
                attributes["ingredients.tokens"] = cell(
                    ["milk", "milk", "egg"] if index < 2 else ["milk", "egg"], "known"
                )
            elif index == 3:
                attributes["nutrition.amount"] = cell(
                    4, "known", "per_product", "minimum"
                )
            elif index == 4:
                attributes["nutrition.amount"] = cell(status="conflict")
            else:
                attributes = {
                    name: cell(status="not_applicable") for name in attributes
                }
            self.rows.append(
                {
                    "listing_id": str(index),
                    "source_key": "a" if index < 4 else "b",
                    "attributes": attributes,
                }
            )

    def report(self):
        return analysis.analyze_schema(
            pd.DataFrame(self.rows), self.profile, self.design
        )

    def attributes(self):
        return {row["attribute"]: row for row in self.report()["attributes"]}

    def test_known_zero_and_null_states_have_separate_coverage_and_quantiles(self):
        attributes = self.attributes()
        amount = attributes["nutrition.amount"]
        assert amount["status_counts"] == {
            "known": 4,
            "unknown": 0,
            "conflict": 1,
            "not_applicable": 1,
        }
        assert amount["known_percent"] == pytest.approx(100 * 4 / 6, abs=0.0001, rel=0)
        assert amount["value_frequencies"][0]["value"] == 0
        assert type(amount["value_frequencies"][0]["value"]) is int
        assert amount["value_frequencies"][0]["count"] == 3
        assert amount["numeric_summary"]["n"] == 4
        assert amount["numeric_summary"]["median"] == 0
        assert amount["numeric_summary"]["q3"] == 1
        bases = {
            (row["scope"], row["qualifier"]): row
            for row in amount["numeric_summary_by_basis"]
        }
        assert bases["per_100g", "(none)"]["max"] == 0
        assert bases["per_product", "minimum"]["median"] == 4
        unavailable = attributes["nutrition.unavailable"]
        assert unavailable["known_percent"] == 0
        assert unavailable["value_frequencies"] == []
        assert unavailable["numeric_summary"] is None

    def test_numeric_only_profile_preserves_exact_integer_and_float_frequencies(self):
        profile = deepcopy(self.profile)
        profile["groups"] = ["nutrition"]
        profile["attributes"] = {
            name: definition
            for (name, definition) in profile["attributes"].items()
            if name.startswith("nutrition.")
        }
        rows = deepcopy(self.rows)
        for row in rows:
            row["attributes"] = {
                name: row["attributes"][name] for name in profile["attributes"]
            }
        rows[1]["attributes"]["nutrition.amount"]["value"] = 0.0
        report = analysis.analyze_schema(pd.DataFrame(rows), profile, self.design)
        amount = next(
            (
                row
                for row in report["attributes"]
                if row["attribute"] == "nutrition.amount"
            )
        )
        assert {
            (type(row["value"]), row["value"]): row["count"]
            for row in amount["value_frequencies"]
        } == {(int, 0): 2, (float, 0.0): 1, (int, 4): 1}

    def test_enum_absence_is_observed_only_when_explicitly_known(self):
        nut = self.attributes()["claim.nut"]
        assert {row["value"]: row["count"] for row in nut["value_frequencies"]} == {
            "present": 2,
            "absent": 1,
            "other": 0,
        }
        assert nut["status_counts"]["unknown"] == 2

    def test_list_frequencies_count_exact_combinations_once_per_listing(self):
        frequencies = self.attributes()["ingredients.tokens"]["value_frequencies"]
        assert [(row["value"], row["count"]) for row in frequencies] == [
            (["milk", "milk", "egg"], 2),
            (["milk", "egg"], 1),
        ]
        assert sum((row["count"] for row in frequencies)) == 3

    def test_source_coverage_retains_each_source_population(self):
        report = self.report()
        amount = next(
            (
                row
                for row in report["attributes"]
                if row["attribute"] == "nutrition.amount"
            )
        )
        assert report["source_listing_counts"] == {"a": 4, "b": 2}
        assert amount["coverage_by_source"] == {"a": [4, 0, 0, 0], "b": [0, 0, 1, 1]}
        for source, count in report["source_listing_counts"].items():
            assert sum(amount["coverage_by_source"][source]) == count

    def test_invalid_states_and_selected_values_are_rejected(self):
        for status, value in (
            ("unknown", 0),
            ("conflict", False),
            ("not_applicable", "absent"),
            ("known", None),
            ("bad", None),
        ):
            rows = deepcopy(self.rows)
            rows[0]["attributes"]["nutrition.amount"] = cell(value, status)
            with pytest.raises(ValueError):
                analysis.analyze_schema(pd.DataFrame(rows), self.profile, self.design)

    def snapshot(self, root):
        root.mkdir()
        documents = {
            "products.jsonl": "".join((json.dumps(row) + "\n" for row in self.rows)),
            "profile.json": json.dumps(self.profile),
            "model-design.json": json.dumps(self.design),
        }
        for name, body in documents.items():
            (root / name).write_text(body, encoding="utf-8")
        manifest = {
            "dataset_version": "fixture",
            "managed_files": {
                name: {"sha256": hashlib.sha256(body.encode()).hexdigest()}
                for (name, body) in documents.items()
            },
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def cli(self, root, output):
        return analysis.main(
            [
                "--silver-root",
                str(root),
                "--dataset-revision",
                "a" * 40,
                "--analysis-date",
                "2026-10-03",
                "--output",
                str(output),
            ]
        )

    def test_modified_snapshot_input_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "silver"
            self.snapshot(root)
            analysis.verified_inputs(root)
            with (root / "products.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with pytest.raises(ValueError, match="SHA-256 mismatch"):
                analysis.verified_inputs(root)

    def test_cli_protects_input_directory_and_hardlink_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "silver"
            self.snapshot(root)
            source = root / "prices.jsonl"
            original = b"Original price evidence\n"
            source.write_bytes(original)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with pytest.raises(SystemExit) as error:
                    self.cli(root, source)
            assert error.value.code == 2
            assert source.read_bytes() == original
            output = Path(directory) / "analysis.json"
            output.hardlink_to(source)
            with redirect_stdout(io.StringIO()):
                assert self.cli(root, output) == 0
            assert source.read_bytes() == original
            assert json.loads(output.read_text())["summary"]["listings"] == 6
