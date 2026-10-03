"""Keep legacy chocolate profile changes consistent with its persisted validator."""

import json
import shutil
from pathlib import Path

import dataset_contracts as contract_module
import pytest
from chocolate_standardization.pipeline import load_contract
from dataset_contracts import resolve_contract_root

ROOT = Path(__file__).resolve().parents[2]


class ChocolateContractConsistencyTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path / "contracts"
        shutil.copytree(
            resolve_contract_root(offline=True),
            self.root,
            ignore=shutil.ignore_patterns("dataset-contract.json"),
        )

    def edit(self, name, change):
        path = self.root / name
        document = json.loads(path.read_text())
        change(document)
        path.write_text(json.dumps(document))

    def test_new_category_label_requires_validator_expansion(self):
        self.edit(
            "profile.json",
            lambda doc: doc["attributes"]["composition.chocolate_type"][
                "allowed_values"
            ].append("new_type"),
        )
        with pytest.raises(ValueError, match="validator vocabulary differs"):
            load_contract(self.root)

    def test_unit_drift_is_rejected(self):
        self.edit(
            "product.schema.json",
            lambda doc: doc["properties"]["attributes"]["properties"][
                "quantity.total_edible_weight_g"
            ]["properties"]["unit"].update(const="kg"),
        )
        with pytest.raises(ValueError, match="attribute unit differs"):
            load_contract(self.root)

    def test_bound_drift_in_known_condition_is_rejected(self):
        self.edit(
            "product.schema.json",
            lambda doc: doc["properties"]["attributes"]["properties"][
                "composition.cocoa_percentage"
            ]["allOf"][0]["then"]["properties"]["value"].update(maximum=95),
        )
        with pytest.raises(ValueError, match="numeric bounds differ"):
            load_contract(self.root)

    def test_pinned_reference_metadata_must_agree_with_verified_payloads(self):
        original = contract_module.load_manifest(contract_module.SCHEMA_REFERENCE)
        for field, changed in (
            ("category", "coffee"),
            ("market", "us"),
            ("schema_version", "other-schema-1"),
            ("attribute_count", original["attribute_count"] + 1),
            ("mapping_version", "other-mappings-1"),
            ("model_design_version", "other-design-1"),
        ):
            reference = dict(original, **{field: changed})
            (self.root / "dataset-contract.json").write_text(json.dumps(reference))
            with pytest.raises(
                ValueError, match="dataset reference metadata: " + field
            ):
                load_contract(self.root, offline=True)
