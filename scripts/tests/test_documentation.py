"""Exercise offline dataset pins, optional cached contracts and documentation drift."""

import hashlib
import io
import json
import re
import shutil
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import check_documentation as guard
import pytest

ROOT = Path(__file__).resolve().parents[2]


REFERENCES = (
    "schemas/chocolate/dataset-contract.json",
    "plugins/category-processing/profiles/chocolate/dataset-contract.json",
    "plugins/category-processing/profiles/coffee/dataset-contract.json",
)


class DocumentationMaintenanceTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        for name in guard.REQUIRED + REFERENCES:
            self.copy_file(name)
        # Preserve local documentation/link destinations without copying caches/corpus.
        for name in guard.REQUIRED:
            for target in re.findall(
                r"\]\(([^)]+)\)", (ROOT / name).read_text(encoding="utf-8")
            ):
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

    def reference(self, name, change):
        path = self.root / name
        document = json.loads(path.read_text(encoding="utf-8"))
        change(document)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def cached_contracts(self, category="chocolate", portable=False):
        """Build minimal temporary fixtures, never copy authoritative schema bodies."""
        name = (
            "plugins/category-processing/profiles/"
            + category
            + "/dataset-contract.json"
            if portable
            else REFERENCES[0]
        )
        manifest = json.loads((self.root / name).read_text(encoding="utf-8"))
        manifest["attribute_count"] = 1
        attributes = {
            "quantity.total_edible_weight_g": {"type": "numeric", "unit": "g"}
        }
        documents = {
            "profile.json": {
                "schema_version": manifest["schema_version"],
                "category": category,
                "market": "uk",
                "attribute_count": 1,
                "attributes": attributes,
            },
            "source-mappings.json": {
                "schema_version": manifest["schema_version"],
                "mapping_version": manifest["mapping_version"],
                "aliases": {},
            },
            "model-design.json": {
                "schema_version": manifest["schema_version"],
                "model_design_version": manifest["model_design_version"],
                "predictors": {},
            },
            "product.schema.json": {
                "properties": {
                    "schema_version": {"const": manifest["schema_version"]},
                    "attributes": {
                        "properties": attributes,
                        "required": list(attributes),
                    },
                }
            },
        }
        if portable:
            documents["pipeline.json"] = {
                "schema_version": manifest["schema_version"],
                "pipeline_version": manifest["pipeline_version"],
                "fields": [],
            }
        cache_root = (
            self.root / "plugins/category-processing/.contract-cache"
            if portable
            else self.root / "data/contract-cache"
        )
        directory = guard.cache_directory(manifest, cache_root)
        directory.mkdir(parents=True)
        for filename, document in documents.items():
            payload = (json.dumps(document, sort_keys=True) + "\n").encode("utf-8")
            (directory / filename).write_bytes(payload)
            manifest["files"][filename]["sha256"] = hashlib.sha256(payload).hexdigest()
            manifest["files"][filename]["size_bytes"] = len(payload)
        (self.root / name).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return name, directory

    def cached_change(self, reference, directory, filename, change):
        path = directory / filename
        document = json.loads(path.read_text(encoding="utf-8"))
        change(document)
        payload = (json.dumps(document, sort_keys=True) + "\n").encode("utf-8")
        path.write_bytes(payload)
        self.reference(
            reference,
            lambda manifest: manifest["files"][filename].update(
                sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload)
            ),
        )

    def assert_error(self, fragment):
        errors = guard.check(self.root)
        assert any(fragment.casefold() in error.casefold() for error in errors), errors

    def test_clean_clone_passes_without_cached_contracts(self):
        with patch.object(guard, "verify_contract_directory") as verify:
            assert guard.check(self.root) == []
            verify.assert_not_called()
        assert not (self.root / "data/contract-cache").exists()
        assert not (self.root / "plugins/category-processing/.contract-cache").exists()

    def test_missing_maintained_document_is_reported(self):
        (self.root / "docs/intention.md").unlink()
        self.assert_error("Missing maintained document: docs/intention.md")

    def test_unfilled_lifecycle_placeholder_is_rejected(self):
        path = self.root / "docs/lifecycle/plan.md"
        path.write_text(path.read_text() + "\n[Describe the implementation step]\n")
        self.assert_error("Unfilled lifecycle/documentation template")

    def test_broken_relative_link_is_reported_with_document(self):
        path = self.root / "docs/spec.md"
        path.write_text(
            path.read_text() + "\n[Missing contract](missing-contract.md#section)\n"
        )
        self.assert_error("Broken local link in docs/spec.md: missing-contract.md")

    def test_existing_fragments_and_external_links_do_not_require_local_files(self):
        path = self.root / "docs/spec.md"
        path.write_text(
            path.read_text() + "\n[Local](intention.md#purpose) [Here](#scope) "
            "[External](https://example.test/unavailable) [Email](mailto:example@example.test)\n"
        )
        assert guard.check(self.root) == []

    def test_missing_dataset_reference_is_reported(self):
        (self.root / REFERENCES[0]).unlink()
        self.assert_error("Unreadable dataset contract reference")

    def test_mutable_dataset_revision_is_rejected(self):
        self.reference(REFERENCES[0], lambda doc: doc.update(revision="main"))
        self.assert_error("Unreadable dataset contract reference")

    def test_malformed_file_hash_is_rejected(self):
        self.reference(
            REFERENCES[0], lambda doc: doc["files"]["profile.json"].update(sha256="bad")
        )
        self.assert_error("Unreadable dataset contract reference")

    def test_dataset_file_set_drift_is_rejected(self):
        self.reference(REFERENCES[0], lambda doc: doc["files"].pop("model-design.json"))
        self.assert_error("file set")

    def test_unexpected_dataset_repository_is_rejected(self):
        self.reference(
            REFERENCES[0], lambda doc: doc.update(repo_id="OtherOwner/dataset")
        )
        self.assert_error("repository")

    def test_schema_guide_must_name_pinned_versions_without_cache(self):
        for field in ("schema_version", "mapping_version", "model_design_version"):
            original = (self.root / REFERENCES[0]).read_text()
            self.reference(
                REFERENCES[0], lambda doc: doc.update({field: "undocumented-version"})
            )
            self.assert_error("Contract guide does not document chocolate " + field)
            (self.root / REFERENCES[0]).write_text(original)

    def test_processing_guide_must_name_pinned_recipe_version_without_cache(self):
        self.reference(
            REFERENCES[2],
            lambda doc: doc.update(pipeline_version="undocumented-recipe"),
        )
        self.assert_error("Contract guide does not document coffee pipeline_version")

    def test_matching_cached_contracts_pass(self):
        self.cached_contracts()
        self.cached_contracts("coffee", portable=True)
        assert guard.check(self.root) == []

    def test_cache_hash_drift_is_rejected(self):
        _, directory = self.cached_contracts()
        (directory / "profile.json").write_text("{}\n")
        self.assert_error("Invalid cached dataset contracts")

    def test_partial_verified_cache_does_not_require_downloads(self):
        _, directory = self.cached_contracts()
        (directory / "model-design.json").unlink()
        assert guard.check(self.root) == []

    def test_cache_marker_must_match_the_pinned_reference(self):
        reference, directory = self.cached_contracts()
        marker = json.loads((self.root / reference).read_text())
        marker["revision"] = "a" * 40
        (directory / "dataset-contract.json").write_text(json.dumps(marker))
        self.assert_error("Invalid cached dataset contracts")

    def test_cached_schema_version_drift_is_rejected(self):
        reference, directory = self.cached_contracts()
        self.cached_change(
            reference,
            directory,
            "source-mappings.json",
            lambda doc: doc.update(schema_version="obsolete"),
        )
        self.assert_error("Cached schema version mismatch")

    def test_cached_attribute_catalog_shape_is_reported_without_crashing(self):
        reference, directory = self.cached_contracts()
        self.cached_change(
            reference, directory, "profile.json", lambda doc: doc.update(attributes=[])
        )
        self.assert_error("Cached profile attributes must be an object")

    def test_cached_validator_catalog_drift_is_rejected(self):
        reference, directory = self.cached_contracts("coffee", portable=True)
        self.cached_change(
            reference,
            directory,
            "product.schema.json",
            lambda doc: doc["properties"]["attributes"]["required"].clear(),
        )
        self.assert_error("Cached product validator attribute catalog")

    def test_cached_predictors_cannot_reference_undefined_attributes(self):
        reference, directory = self.cached_contracts()
        self.cached_change(
            reference,
            directory,
            "model-design.json",
            lambda doc: doc["predictors"].update({"composition.imaginary": {}}),
        )
        self.assert_error("undefined attribute")

    def test_cached_recipe_cannot_reference_undefined_attributes(self):
        reference, directory = self.cached_contracts("coffee", portable=True)
        self.cached_change(
            reference,
            directory,
            "pipeline.json",
            lambda doc: doc["fields"].append({"attribute": "composition.imaginary"}),
        )
        self.assert_error("Cached processing recipe references an undefined attribute")

    def test_behavior_change_requires_documents_in_the_same_change(self):
        changed = {"scripts/chocolate_standardization/values.py"}
        required = {
            "docs/spec.md",
            "docs/chocolate-schema.md",
            "docs/chocolate-silver.md",
            "docs/lifecycle/plan.md",
        }
        errors = guard.check(self.root, changed=changed)
        for name in required:
            assert any(
                "accompanying documentation update: " + name in error
                for error in errors
            ), errors
        assert guard.check(self.root, changed=required | changed) == []

    def test_dataset_resolver_and_manifest_changes_require_guides(self):
        for name in ("scripts/dataset_contracts.py", REFERENCES[0]):
            assert "docs/chocolate-silver.md" in guard.required_updates({name})
            assert "docs/lifecycle/plan.md" in guard.required_updates({name})

    def test_silver_builder_and_cli_require_their_guides_in_the_same_change(self):
        required = {
            "docs/spec.md",
            "docs/chocolate-schema.md",
            "docs/chocolate-silver.md",
            "docs/lifecycle/plan.md",
        }
        for name in (
            "scripts/chocolate_silver.py",
            "scripts/build_chocolate_silver.py",
        ):
            assert guard.required_updates({name}) == required
            assert guard.check(self.root, changed=required | {name}) == []

    def test_shared_schema_and_cleanup_changes_require_silver_documentation(self):
        for name in (
            REFERENCES[0],
            "scripts/chocolate_standardization/pipeline.py",
            "scripts/chocolate_cleanup/deduplication.py",
            "scripts/chocolate_model.py",
        ):
            assert "docs/chocolate-silver.md" in guard.required_updates({name})

    def test_tests_and_unrelated_changes_do_not_require_behavior_documentation(self):
        assert (
            guard.check(
                self.root,
                changed={"scripts/tests/test_documentation.py", "unrelated.txt"},
            )
            == []
        )

    def test_processing_behavior_requires_portable_plugin_documentation(self):
        changed = {"plugins/category-processing/category_processing/pipeline.py"}
        required = {
            "docs/spec.md",
            "docs/category-processing.md",
            "plugins/category-processing/README.md",
            "docs/lifecycle/plan.md",
        }
        assert guard.required_updates(changed) == required
        assert guard.check(self.root, changed=changed | required) == []
        assert (
            guard.required_updates({"plugins/category-processing/tests/test_model.py"})
            == set()
        )

    def test_component_policies_cover_collection_cleanup_publication_and_governance(
        self,
    ):
        cases = (
            (
                {"plugins/category-research/category_research/archive.py"},
                {
                    "docs/spec.md",
                    "plugins/category-research/README.md",
                    "docs/lifecycle/plan.md",
                },
            ),
            (
                {"scripts/chocolate_cleanup/adapters.py"},
                {
                    "docs/spec.md",
                    "docs/chocolate-cleaning.md",
                    "docs/chocolate-deduplication.md",
                    "docs/chocolate-silver.md",
                    "docs/lifecycle/plan.md",
                },
            ),
            (
                {"scripts/publish_collections.py"},
                {"docs/spec.md", "README", "docs/lifecycle/plan.md"},
            ),
            (
                {"scripts/check_documentation.py"},
                {"docs/documentation-policy.md", "docs/lifecycle/plan.md"},
            ),
        )
        for changed, expected in cases:
            assert guard.required_updates(changed) == expected

    def test_structural_cli_returns_success_without_git_comparison(self):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(guard, "ROOT", self.root),
            patch.object(guard, "changed_paths") as git_changes,
        ):
            with redirect_stdout(output), redirect_stderr(errors):
                status = guard.main(["--structural-only"])
        assert status == 0, errors.getvalue()
        git_changes.assert_not_called()
        assert "maintenance checks passed" in output.getvalue()

    def test_cli_returns_failure_for_missing_same_change_docs(self):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(guard, "ROOT", self.root),
            patch.object(
                guard, "changed_paths", return_value={"scripts/chocolate_model.py"}
            ),
        ):
            with redirect_stdout(output), redirect_stderr(errors):
                status = guard.main(["--base", "test-base"])
        assert status == 1
        assert "accompanying documentation update" in errors.getvalue()
