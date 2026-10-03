"""Check portable pinned-profile routing without category payload fixtures."""

from contextlib import redirect_stdout
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from category_processing.cli import main
from category_processing.profiles import CONTRACT_FILES, resolve_profile


class ProfileResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.profile = self.base / "profile"
        self.profile.mkdir()
        self.cache = self.base / "cache"

    def materialize(self, filenames=CONTRACT_FILES):
        for name in filenames:
            (self.profile / name).write_text("{}\n", encoding="utf-8")

    def manifest(self, category="coffee"):
        body = b"{}\n"
        return {"format_version": "rgc-dataset-contract-reference-1", "repo_id": "fixture/contracts",
                "revision": "a" * 40, "contract_set": "category-processing/" + category,
                "category": category, "market": "uk", "schema_version": "fixture-schema-1",
                "mapping_version": "fixture-mapping-1", "model_design_version": "fixture-model-1",
                "pipeline_version": "fixture-pipeline-1", "attribute_count": 1,
                "files": {name: {"path": "contracts/category-processing/" + category + "/" + name,
                                  "sha256": hashlib.sha256(body).hexdigest(), "size_bytes": len(body)}
                          for name in CONTRACT_FILES}}

    def reference(self, manifest=None):
        path = self.profile / "dataset-contract.json"
        path.write_text(json.dumps(manifest or self.manifest()) + "\n", encoding="utf-8")
        return path

    def test_custom_profile_directory_remains_local_and_explicit(self):
        self.materialize()
        with patch("category_processing.dataset_contracts.resolve_contracts") as download:
            self.assertEqual(resolve_profile(self.profile, cache_root=self.cache, offline=True), self.profile)
        download.assert_not_called()

    def test_reference_uses_selected_cache_and_offline_policy(self):
        reference = self.reference()
        destination = self.cache / "resolved"
        with patch("category_processing.dataset_contracts.resolve_contracts", return_value=destination) as download:
            self.assertEqual(resolve_profile(self.profile, cache_root=self.cache, offline=True), destination)
        download.assert_called_once_with(reference, self.cache, offline=True)

    def test_materialized_profile_reverifies_marker_and_payloads_without_download(self):
        reference = self.reference()
        self.materialize()
        manifest = self.manifest()
        with patch("category_processing.dataset_contracts.load_manifest", return_value=manifest) as load, \
                patch("category_processing.dataset_contracts.verify_contract_directory") as verify, \
                patch("category_processing.dataset_contracts.resolve_contracts") as download:
            self.assertEqual(resolve_profile(self.profile, cache_root=self.cache), self.profile)
        load.assert_called_once_with(reference)
        verify.assert_called_once_with(manifest, self.profile)
        download.assert_not_called()

    def test_corrupt_or_partial_materialized_profile_never_falls_back_to_download(self):
        for filenames in (CONTRACT_FILES, CONTRACT_FILES[:1]):
            with self.subTest(filenames=filenames):
                for file in self.profile.iterdir():
                    file.unlink()
                self.reference()
                self.materialize(filenames)
                with patch("category_processing.dataset_contracts.load_manifest", return_value=self.manifest()), \
                        patch("category_processing.dataset_contracts.verify_contract_directory",
                              side_effect=ValueError("Contract cache verification failed.")), \
                        patch("category_processing.dataset_contracts.resolve_contracts") as download:
                    with self.assertRaisesRegex(ValueError, "verification failed"):
                        resolve_profile(self.profile, cache_root=self.cache)
                download.assert_not_called()

    def test_packaged_category_resolves_from_detached_plugin_root(self):
        plugin = self.base / "detached-plugin"
        category = plugin / "profiles/coffee"
        category.mkdir(parents=True)
        reference = category / "dataset-contract.json"
        reference.write_text(json.dumps(self.manifest()) + "\n", encoding="utf-8")
        destination = self.cache / "coffee"
        with patch("category_processing.profiles.PLUGIN_ROOT", plugin), \
                patch("category_processing.dataset_contracts.resolve_contracts", return_value=destination) as download:
            self.assertEqual(resolve_profile(category="coffee", cache_root=self.cache, offline=True), destination)
        download.assert_called_once_with(reference, self.cache, offline=True)

    def test_packaged_selector_rejects_another_category_reference_before_downloading(self):
        plugin = self.base / "detached-plugin"
        category = plugin / "profiles/coffee"
        category.mkdir(parents=True)
        (category / "dataset-contract.json").write_text(json.dumps(self.manifest("chocolate")) + "\n",
                                                       encoding="utf-8")
        with patch("category_processing.profiles.PLUGIN_ROOT", plugin), \
                patch("category_processing.dataset_contracts.resolve_contracts") as download:
            with self.assertRaisesRegex(ValueError, "Packaged category differs"):
                resolve_profile(category="coffee", cache_root=self.cache)
        download.assert_not_called()

    def test_profile_rejects_mismatched_contract_set_and_partial_reference(self):
        documents = []
        mismatch = self.manifest()
        mismatch["contract_set"] = "category-processing/chocolate"
        for name, metadata in mismatch["files"].items():
            metadata["path"] = "contracts/category-processing/chocolate/" + name
        documents.append((mismatch, "category and contract set disagree"))
        partial = self.manifest()
        del partial["files"]["pipeline.json"]
        documents.append((partial, "requires all five contracts"))
        for manifest, error in documents:
            with self.subTest(error=error):
                self.reference(manifest)
                with patch("category_processing.dataset_contracts.resolve_contracts") as download:
                    with self.assertRaisesRegex(ValueError, error):
                        resolve_profile(self.profile, cache_root=self.cache)
                download.assert_not_called()

    def test_selection_is_explicit_and_category_cannot_escape_plugin(self):
        for kwargs in ({}, {"profile_root": self.profile, "category": "coffee"},
                       {"category": "../coffee"}, {"category": "unknown-fixture-category"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                resolve_profile(**kwargs)

    def test_cli_category_passes_cache_and_offline_policy_before_processing(self):
        output = self.base / "silver"
        with patch("category_processing.cli.resolve_profile", return_value=self.profile) as resolve, \
                patch("category_processing.pipeline.build_silver_dataset",
                      return_value={"status": "complete_snapshot"}) as build, \
                patch("category_processing.cli._read_rows", return_value=[]), redirect_stdout(io.StringIO()):
            status = main(["process", "--archive-root", str(self.base / "raw"), "--category", "coffee",
                           "--contracts-cache", str(self.cache), "--offline", "--output", str(output)])
        self.assertEqual(status, 0)
        resolve.assert_called_once_with(None, category="coffee", cache_root=self.cache, offline=True)
        build.assert_called_once_with(self.base / "raw", output, self.profile, reviews=None)


if __name__ == "__main__":
    unittest.main()
