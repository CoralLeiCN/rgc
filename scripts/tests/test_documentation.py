"""Exercise the documentation guard against drift in real maintained contracts."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_documentation as guard


class DocumentationMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in guard.REQUIRED:
            self.copy_file(name)
        for path in (ROOT / "schemas/chocolate").glob("*.json"):
            self.copy_file(str(path.relative_to(ROOT)))
        for path in (ROOT / "plugins/category-processing/profiles").glob("*/*.json"):
            self.copy_file(str(path.relative_to(ROOT)))
        # Preserve real local-link destinations without copying the product corpus.
        for name in guard.REQUIRED:
            for target in re.findall(r"\]\(([^)]+)\)", (ROOT / name).read_text(encoding="utf-8")):
                target = target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                source = ((ROOT / name).parent / target).resolve()
                if not source.is_relative_to(ROOT):
                    continue
                destination = self.root / source.relative_to(ROOT)
                if source.is_file():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                elif source.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)

    def copy_file(self, name):
        destination = self.root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)

    def contract(self, name, change):
        path = self.root / "schemas/chocolate" / name
        document = json.loads(path.read_text(encoding="utf-8"))
        change(document)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def assert_error(self, fragment):
        errors = guard.check(self.root)
        self.assertTrue(any(fragment.casefold() in error.casefold() for error in errors), errors)

    def test_current_maintained_documents_and_contracts_pass(self):
        self.assertEqual(guard.check(self.root), [])

    def test_missing_maintained_document_is_reported(self):
        (self.root / "docs/intention.md").unlink()
        self.assert_error("Missing maintained document: docs/intention.md")

    def test_unfilled_lifecycle_placeholder_is_rejected(self):
        path = self.root / "docs/lifecycle/plan.md"
        path.write_text(path.read_text() + "\n[Describe the implementation step]\n")
        self.assert_error("Unfilled lifecycle/documentation template")

    def test_broken_relative_link_is_reported_with_document(self):
        path = self.root / "docs/spec.md"
        path.write_text(path.read_text() + "\n[Missing contract](missing-contract.md#section)\n")
        self.assert_error("Broken local link in docs/spec.md: missing-contract.md")

    def test_existing_fragments_and_external_links_do_not_require_local_files(self):
        path = self.root / "docs/spec.md"
        path.write_text(path.read_text() + "\n[Local](intention.md#purpose) [Here](#scope) "
                        "[External](https://example.test/unavailable) [Email](mailto:example@example.test)\n")
        self.assertEqual(guard.check(self.root), [])

    def test_unreadable_category_contract_is_reported(self):
        (self.root / "schemas/chocolate/source-mappings.json").write_text("{invalid json\n")
        self.assert_error("Unreadable category contract source-mappings.json")

    def test_schema_version_drift_is_rejected(self):
        self.contract("source-mappings.json", lambda doc: doc.update(schema_version="chocolate-schema-obsolete"))
        self.assert_error("Schema version mismatch: source-mappings.json")

    def test_product_validator_version_drift_is_rejected(self):
        self.contract("product.schema.json", lambda doc: doc["properties"]["schema_version"].update(const="chocolate-schema-obsolete"))
        self.assert_error("Product validator version")

    def test_schema_guide_must_name_the_current_schema_version(self):
        path = self.root / "docs/chocolate-schema.md"
        profile = json.loads((self.root / "schemas/chocolate/profile.json").read_text())
        path.write_text(path.read_text().replace(profile["schema_version"], "obsolete-schema"))
        self.assert_error("Schema guide does not document")

    def test_schema_guide_must_name_the_current_mapping_version(self):
        self.contract("source-mappings.json", lambda doc: doc.update(mapping_version="chocolate-source-mappings-new"))
        self.assert_error("mapping version")

    def test_schema_guide_must_name_the_current_model_design_version(self):
        self.contract("model-design.json", lambda doc: doc.update(model_design_version="chocolate-pricing-design-new"))
        self.assert_error("model design version")

    def test_declared_attribute_count_must_match_the_catalog(self):
        self.contract("profile.json", lambda doc: doc.update(attribute_count=doc["attribute_count"] + 1))
        self.assert_error("count")

    def test_product_validator_must_track_the_same_catalog(self):
        self.contract("product.schema.json", lambda doc: doc["properties"]["attributes"]["properties"].pop("quantity.total_edible_weight_g"))
        self.assert_error("catalog")

    def test_vocabulary_mappings_cannot_reference_undefined_attributes(self):
        self.contract("source-mappings.json", lambda doc: doc["aliases"].update({"composition.imaginary": {"x": "x"}}))
        self.assert_error("Vocabulary mappings reference an undefined attribute: composition.imaginary")

    def test_active_model_predictors_cannot_reference_undefined_attributes(self):
        self.contract("model-design.json", lambda doc: doc["predictors"].update({"composition.imaginary": {"type": "categorical"}}))
        self.assert_error("Model design references an undefined attribute: composition.imaginary")

    def test_behavior_change_requires_documents_in_the_same_change(self):
        errors = guard.check(self.root, changed={"scripts/chocolate_standardization/values.py"})
        required = {"docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"}
        for name in required:
            self.assertTrue(any("accompanying documentation update: " + name in error for error in errors), errors)
        changed = required | {"scripts/chocolate_standardization/values.py"}
        self.assertEqual(guard.check(self.root, changed=changed), [])

    def test_silver_builder_and_cli_require_their_guides_in_the_same_change(self):
        required = {"docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"}
        for name in ("scripts/chocolate_silver.py", "scripts/build_chocolate_silver.py"):
            with self.subTest(name=name):
                self.assertEqual(guard.required_updates({name}), required)
                errors = guard.check(self.root, changed={name})
                self.assertTrue(any("accompanying documentation update: docs/chocolate-silver.md" in error for error in errors), errors)
                self.assertEqual(guard.check(self.root, changed=required | {name}), [])

    def test_missing_silver_guide_is_a_maintained_document_failure(self):
        (self.root / "docs/chocolate-silver.md").unlink()
        self.assert_error("Missing maintained document: docs/chocolate-silver.md")

    def test_shared_schema_and_cleanup_changes_require_silver_documentation(self):
        for name in ("schemas/chocolate/profile.json", "scripts/chocolate_standardization/pipeline.py",
                     "scripts/chocolate_cleanup/deduplication.py", "scripts/chocolate_model.py"):
            with self.subTest(name=name):
                self.assertIn("docs/chocolate-silver.md", guard.required_updates({name}))

    def test_tests_and_unrelated_changes_do_not_require_behavior_documentation(self):
        self.assertEqual(guard.check(self.root, changed={"scripts/tests/test_documentation.py", "unrelated.txt"}), [])

    def test_processing_behavior_requires_portable_plugin_documentation(self):
        changed = {"plugins/category-processing/category_processing/pipeline.py"}
        required = {"docs/spec.md", "docs/category-processing.md", "plugins/category-processing/README.md", "docs/lifecycle/plan.md"}
        self.assertEqual(guard.required_updates(changed), required)
        self.assertEqual(guard.check(self.root, changed=changed | required), [])
        self.assertEqual(guard.required_updates({"plugins/category-processing/tests/test_model.py"}), set())

    def test_processing_profile_version_drift_is_rejected(self):
        path = self.root / "plugins/category-processing/profiles/coffee/pipeline.json"
        recipe = json.loads(path.read_text())
        recipe["schema_version"] = "obsolete"
        path.write_text(json.dumps(recipe))
        self.assert_error("Processing profile version mismatch: coffee/pipeline.json")

    def test_processing_profile_catalog_drift_is_rejected(self):
        path = self.root / "plugins/category-processing/profiles/coffee/product.schema.json"
        schema = json.loads(path.read_text())
        schema["properties"]["attributes"]["required"].pop()
        path.write_text(json.dumps(schema))
        self.assert_error("Processing product validator catalog mismatch: coffee")

    def test_component_policies_cover_collection_cleanup_publication_and_governance(self):
        cases = (
            ({"plugins/category-research/category_research/archive.py"}, {"docs/spec.md", "plugins/category-research/README.md", "docs/lifecycle/plan.md"}),
            ({"scripts/chocolate_cleanup/adapters.py"}, {"docs/spec.md", "docs/chocolate-cleaning.md", "docs/chocolate-deduplication.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"}),
            ({"scripts/publish_collections.py"}, {"docs/spec.md", "README", "docs/lifecycle/plan.md"}),
            ({"scripts/check_documentation.py"}, {"docs/documentation-policy.md", "docs/lifecycle/plan.md"}),
        )
        for changed, expected in cases:
            with self.subTest(changed=changed):
                self.assertEqual(guard.required_updates(changed), expected)
        self.assertEqual(guard.required_updates({"plugins/category-research/tests/test_archive.py"}), set())

    def test_structural_cli_returns_success_without_git_comparison(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(guard, "ROOT", self.root), patch.object(guard, "changed_paths") as git_changes:
            with redirect_stdout(output), redirect_stderr(errors):
                status = guard.main(["--structural-only"])
        self.assertEqual(status, 0, errors.getvalue())
        git_changes.assert_not_called()
        self.assertIn("maintenance checks passed", output.getvalue())

    def test_cli_returns_failure_for_missing_same_change_docs(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(guard, "ROOT", self.root), patch.object(guard, "changed_paths", return_value={"scripts/chocolate_model.py"}):
            with redirect_stdout(output), redirect_stderr(errors):
                status = guard.main(["--base", "test-base"])
        self.assertEqual(status, 1)
        self.assertIn("accompanying documentation update", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
