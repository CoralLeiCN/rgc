"""Keep legacy chocolate profile changes consistent with its persisted validator."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from chocolate_standardization.pipeline import load_contract


class ChocolateContractConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "contracts"
        shutil.copytree(ROOT / "schemas/chocolate", self.root)

    def edit(self, name, change):
        path = self.root / name
        document = json.loads(path.read_text())
        change(document)
        path.write_text(json.dumps(document))

    def test_new_category_label_requires_validator_expansion(self):
        self.edit("profile.json", lambda doc: doc["attributes"]["composition.chocolate_type"]["allowed_values"].append("new_type"))
        with self.assertRaisesRegex(ValueError, "validator vocabulary differs"):
            load_contract(self.root)

    def test_unit_drift_is_rejected(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["quantity.total_edible_weight_g"]["properties"]["unit"].update(const="kg"))
        with self.assertRaisesRegex(ValueError, "attribute unit differs"):
            load_contract(self.root)

    def test_bound_drift_in_known_condition_is_rejected(self):
        self.edit("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"]["composition.cocoa_percentage"]["allOf"][0]["then"]["properties"]["value"].update(maximum=95))
        with self.assertRaisesRegex(ValueError, "numeric bounds differ"):
            load_contract(self.root)


if __name__ == "__main__":
    unittest.main()
