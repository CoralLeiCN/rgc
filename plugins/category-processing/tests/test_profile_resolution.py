"""Check portable pinned-profile routing without category payload fixtures."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from category_processing.profiles import CONTRACT_FILES, resolve_profile

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class ProfileResolutionTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.base = tmp_path.resolve()
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
            assert (resolve_profile(self.profile, cache_root=self.cache, offline=True)) == (self.profile)
        download.assert_not_called()

    def test_materialized_profile_reverifies_marker_and_payloads_without_download(self):
        reference = self.reference()
        self.materialize()
        manifest = self.manifest()
        with patch("category_processing.dataset_contracts.load_manifest", return_value=manifest) as load, \
                patch("category_processing.dataset_contracts.verify_contract_directory") as verify, \
                patch("category_processing.dataset_contracts.resolve_contracts") as download:
            assert (resolve_profile(self.profile, cache_root=self.cache)) == (self.profile)
        load.assert_called_once_with(reference)
        verify.assert_called_once_with(manifest, self.profile, required_files=set(manifest["files"]))
        download.assert_not_called()

    def test_corrupt_or_partial_materialized_profile_never_falls_back_to_download(self):
        for filenames in (CONTRACT_FILES, CONTRACT_FILES[:1]):
            for file in self.profile.iterdir():
                file.unlink()
            self.reference()
            self.materialize(filenames)
            with patch("category_processing.dataset_contracts.load_manifest", return_value=self.manifest()), \
                    patch("category_processing.dataset_contracts.verify_contract_directory",
                          side_effect=ValueError("Contract cache verification failed.")), \
                    patch("category_processing.dataset_contracts.resolve_contracts") as download:
                with pytest.raises(ValueError, match="verification failed"):
                    resolve_profile(self.profile, cache_root=self.cache)
            download.assert_not_called()

    def test_packaged_selector_rejects_another_category_reference_before_downloading(self):
        plugin = self.base / "detached-plugin"
        category = plugin / "profiles/coffee"
        category.mkdir(parents=True)
        (category / "dataset-contract.json").write_text(json.dumps(self.manifest("chocolate")) + "\n",
                                                       encoding="utf-8")
        with patch("category_processing.profiles.PLUGIN_ROOT", plugin), \
                patch("category_processing.dataset_contracts.resolve_contracts") as download:
            with pytest.raises(ValueError, match="Packaged category differs"):
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
        documents.append((partial, "missing required contracts"))
        for manifest, error in documents:
            self.reference(manifest)
            with patch("category_processing.dataset_contracts.resolve_contracts") as download:
                with pytest.raises(ValueError, match=error):
                    resolve_profile(self.profile, cache_root=self.cache)
            download.assert_not_called()

    def test_selection_is_explicit_and_category_cannot_escape_plugin(self):
        for kwargs in ({}, {"profile_root": self.profile, "category": "coffee"},
                       {"category": "../coffee"}, {"category": "unknown-fixture-category"}):
            with pytest.raises(ValueError):
                resolve_profile(**kwargs)
