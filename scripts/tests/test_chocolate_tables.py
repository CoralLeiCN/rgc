"""Protect seller identity and raw evidence at the pandas table boundary."""

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from chocolate_cleanup.deduplication import source_identity
from chocolate_silver import table_bytes
from chocolate_tables import get_table_backend


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


class ChocolateTableBackendTests:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.standard = get_table_backend("stdlib")
        self.pandas = get_table_backend("pandas")

    def test_nullable_variants_and_unresolved_identities_keep_seller_boundaries(self):
        key = ("seller", "shop.example", "9007199254740993", None)
        identities = [
            ("z-copy", key),
            ("a-copy", key),
            ("variant", (*key[:3], "None")),
            ("leading-zero", (*key[:2], "09007199254740993", None)),
            ("other-seller", ("other-seller", *key[1:])),
            ("other-host", (key[0], "other.example", *key[2:])),
            ("unresolved-one", None),
            ("unresolved-two", None),
        ]
        expected = [
            ["a-copy", "z-copy"],
            ["variant"],
            ["leading-zero"],
            ["other-seller"],
            ["other-host"],
            ["unresolved-one"],
            ["unresolved-two"],
        ]
        assert self.standard.identity_groups(identities) == expected
        assert self.pandas.identity_groups(identities) == expected
        assert self.pandas.identity_groups([]) == []

    def test_validated_integer_identifiers_keep_precision_and_original_strings(self):
        raw = {
            "source_key": "seller",
            "source_url": "https://shop.example/product",
            "identity": {
                "source_product_id": 9007199254740993,
                "source_variant_id": None,
            },
        }
        string_id = deepcopy(raw)
        string_id["identity"]["source_product_id"] = "9007199254740993"
        padded_id = deepcopy(raw)
        padded_id["identity"]["source_product_id"] = "09007199254740993"
        invalid_id = deepcopy(raw)
        invalid_id["identity"]["source_product_id"] = True
        rows = [
            ("integer", source_identity(raw)),
            ("string", source_identity(string_id)),
            ("padded", source_identity(padded_id)),
            ("invalid", source_identity(invalid_id)),
        ]
        assert self.pandas.identity_groups(rows) == [
            ["integer", "string"],
            ["padded"],
            ["invalid"],
        ]
        assert (
            canonical(raw["identity"])
            == '{"source_product_id": 9007199254740993, "source_variant_id": null}'
        )

    def test_opaque_nested_rows_keep_types_nulls_unicode_and_missing_keys(self):
        nested = {
            "large_integer": 9007199254740993,
            "padded_id": "00123",
            "price": "04.00",
            "none": None,
            "boolean": False,
            "zero": 0,
            "float": 1.0,
            "source_text": "Ingrédients: café.\u2028Original\u2029wording.\n",
            "list": [None, True, 0, 1.0, {"empty": []}],
        }
        rows = [
            {
                "listing_id": "first",
                "dataset_version": "old",
                "layer_version": "old-layer",
                "capture": nested,
            },
            {"listing_id": "second", "capture": {}},
        ]
        before = canonical(rows)
        standard = list(
            self.standard.envelopes(rows, "silver-test", "raw-test", "layer-test")
        )
        actual = list(
            self.pandas.envelopes(rows, "silver-test", "raw-test", "layer-test")
        )
        assert canonical(actual) == canonical(standard)
        assert canonical(rows) == before
        assert actual[0]["capture"] is nested
        assert actual[0] is not rows[0]
        assert "layer_version" not in actual[1]
        assert list(self.pandas.envelopes([], "silver", "raw", "layer")) == []

    def test_metadata_aggregates_partitions_and_empty_tables_preserve_semantics(self):
        rows = [
            {
                "listing_id": "b",
                "source_role": "brand",
                "model_eligible": False,
                "exclusion_reasons": ["quantity", "review"],
                "reason": "unknown",
                "attributes": {
                    "cocoa": {"status": "known"},
                    "mass": {"status": "unknown"},
                },
            },
            {
                "listing_id": "r",
                "source_role": "retail",
                "model_eligible": True,
                "exclusion_reasons": [],
                "reason": "unknown",
                "attributes": {
                    "cocoa": {"status": "conflict"},
                    "mass": {"status": "known"},
                },
            },
            {
                "listing_id": "u",
                "source_role": "unknown",
                "model_eligible": False,
                "exclusion_reasons": ["review"],
                "reason": "conflict",
                "attributes": {
                    "cocoa": {"status": "unknown"},
                    "mass": {"status": "known"},
                },
            },
        ]
        for records in (rows, []):
            for method, args in (
                ("counts", (records, "source_role")),
                ("counts", (records, "reason")),
                ("attribute_counts", (records,)),
                ("exclusion_counts", (records,)),
                ("select", (records, "model_eligible", True)),
                ("partitions", (records,)),
            ):
                assert canonical(getattr(self.pandas, method)(*args)) == canonical(
                    getattr(self.standard, method)(*args)
                )
        assert self.pandas.exclusion_counts(rows) == {"quantity": 1, "review": 2}
        assert self.pandas.partitions(rows)["retail"][0] is rows[1]
        assert self.pandas.select(rows, "model_eligible", True)[0] is rows[1]

    def test_jsonl_envelopes_match_across_batches_and_empty_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.jsonl"
            rows = [
                {
                    "listing_id": str(i),
                    "nested": {
                        "integer": 9007199254740993,
                        "price": "001.50",
                        "none": None,
                        "unicode": "café\u2028\u2029",
                    },
                }
                for i in range(1001)
            ]
            path.write_text(
                "".join((json.dumps(row, ensure_ascii=False) + "\n" for row in rows)),
                encoding="utf-8",
            )
            args = (path, "silver-test", "raw-test")
            assert table_bytes(*args, table_backend=self.pandas) == table_bytes(
                *args, table_backend=self.standard
            )
            path.write_bytes(b"")
            assert table_bytes(*args, table_backend=self.pandas) == b""

    def test_compatibility_backend_does_not_import_pandas_and_failure_is_explicit(self):
        with patch(
            "chocolate_tables.importlib.import_module",
            side_effect=ImportError("Unavailable"),
        ):
            standard = get_table_backend("stdlib")
            assert standard.counts([], "reason") == {}
            assert "pandas_version" not in standard.runtime()
            with pytest.raises(RuntimeError, match="pandas==2.2.3"):
                get_table_backend("pandas")
