"""Pinned contract download, cache integrity, and publication boundary tests."""

import hashlib
import json
from pathlib import Path

import pytest
from dataset_contracts import (
    cache_directory,
    load_manifest,
    resolve_contracts,
    verify_contract_directory,
)
from publish_contracts import build_contract_bundle, update_dataset_card

ROOT = Path(__file__).resolve().parents[2]


class DatasetContractTests:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.body = b'{"schema_version": "example-1"}\n'
        self.manifest = {
            "format_version": "rgc-dataset-contract-reference-1",
            "repo_id": "example/contracts",
            "revision": "a" * 40,
            "contract_set": "example",
            "category": "example",
            "market": "uk",
            "schema_version": "example-1",
            "mapping_version": "example-mappings-1",
            "model_design_version": "example-design-1",
            "attribute_count": 1,
            "files": {
                "profile.json": {
                    "path": "contracts/example/profile.json",
                    "sha256": hashlib.sha256(self.body).hexdigest(),
                    "size_bytes": len(self.body),
                }
            },
        }
        self.reference = self.root / "dataset-contract.json"
        self.save()

    def save(self):
        self.reference.write_text(json.dumps(self.manifest))

    def test_fetch_pins_revision_and_offline_reuses_verified_bytes(self):
        calls = []

        def fetch(url):
            calls.append(url)
            return self.body

        resolved = resolve_contracts(
            self.reference, self.root / "cache", download=fetch
        )
        assert calls == [
            "https://huggingface.co/datasets/example/contracts/resolve/"
            + "a" * 40
            + "/contracts/example/profile.json"
        ]
        assert (resolved / "profile.json").read_bytes() == self.body
        assert (
            resolve_contracts(
                self.reference,
                self.root / "cache",
                offline=True,
                download=lambda _: pytest.fail("Offline cache must not fetch"),
            )
            == resolved
        )

    def test_cold_offline_cache_does_not_call_network(self):
        with pytest.raises(FileNotFoundError, match="fetch them before offline use"):
            resolve_contracts(
                self.reference,
                self.root / "cache",
                offline=True,
                download=lambda _: pytest.fail("Offline must not fetch"),
            )

    def test_bad_download_never_becomes_a_cached_contract(self):
        with pytest.raises(ValueError, match="checksum/length mismatch"):
            resolve_contracts(
                self.reference, self.root / "cache", download=lambda _: b"{}"
            )
        directory = cache_directory(self.manifest, self.root / "cache")
        assert not (directory / "profile.json").exists()
        assert not (directory / "dataset-contract.json").exists()

    def test_corrupt_existing_cache_is_rejected_without_repair(self):
        directory = resolve_contracts(
            self.reference, self.root / "cache", download=lambda _: self.body
        )
        (directory / "profile.json").write_bytes(self.body + b" ")
        with pytest.raises(ValueError, match="checksum/length mismatch"):
            resolve_contracts(
                self.reference,
                self.root / "cache",
                download=lambda _: pytest.fail("Corruption must not silently fetch"),
            )

    def test_cache_marker_must_agree_with_tracked_pin(self):
        directory = resolve_contracts(
            self.reference, self.root / "cache", download=lambda _: self.body
        )
        marker = load_manifest(directory / "dataset-contract.json")
        marker["mapping_version"] = "changed"
        (directory / "dataset-contract.json").write_text(json.dumps(marker))
        with pytest.raises(ValueError, match="differs from the pinned reference"):
            verify_contract_directory(self.manifest, directory)

    def test_mutable_revision_and_traversal_are_rejected(self):
        for key, value in [("revision", "main"), ("contract_set", "../example")]:
            original = self.manifest[key]
            self.manifest[key] = value
            self.save()
            with pytest.raises(ValueError):
                load_manifest(self.reference)
            self.manifest[key] = original

    def test_remote_path_must_match_declared_set_and_filename(self):
        self.manifest["files"]["profile.json"]["path"] = "products.jsonl"
        self.save()
        with pytest.raises(ValueError, match="remote dataset contract path"):
            load_manifest(self.reference)

    def test_cached_symlink_is_rejected(self):
        directory = cache_directory(self.manifest, self.root / "cache")
        directory.mkdir(parents=True)
        source = self.root / "source.json"
        source.write_bytes(self.body)
        (directory / "profile.json").symlink_to(source)
        with pytest.raises(ValueError, match="symlink"):
            resolve_contracts(self.reference, self.root / "cache", offline=True)

    def test_dataset_card_update_preserves_raw_card_and_is_idempotent(self):
        body = b"---\nconfigs: []\n---\n\n# Raw evidence\n\nOriginal evidence description.\n"
        updated = update_dataset_card(body)
        assert updated.startswith(body.rstrip())
        assert b"contracts/category-processing/coffee/" in updated
        assert update_dataset_card(updated) == updated

    def test_dataset_card_update_preserves_sections_after_contracts(self):
        body = b"# Dataset\n\n## Analytical contracts\n\nOlder description.\n\n## Silver snapshots\n\nExisting silver links.\n"
        updated = update_dataset_card(body)
        assert b"## Silver snapshots\n\nExisting silver links." in updated
        assert b"Older description." not in updated
        assert update_dataset_card(updated) == updated

    def test_publication_inventory_excludes_unrelated_files_and_preserves_bytes(self):
        for group in [
            "chocolate",
            "category-processing/chocolate",
            "category-processing/coffee",
        ]:
            category = group.split("/")[-1]
            directory = self.root / "contracts" / group
            directory.mkdir(parents=True)
            version = category + "-schema-1"
            documents = {
                "profile.json": {
                    "schema_version": version,
                    "category": category,
                    "market": "uk",
                    "attribute_count": 1,
                    "attributes": {"example": {}},
                },
                "source-mappings.json": {
                    "schema_version": version,
                    "mapping_version": category + "-mappings-1",
                },
                "model-design.json": {
                    "schema_version": version,
                    "model_design_version": category + "-design-1",
                },
                "product.schema.json": {
                    "properties": {"schema_version": {"const": version}}
                },
            }
            if group.startswith("category-processing/"):
                documents["pipeline.json"] = {
                    "schema_version": version,
                    "pipeline_version": category + "-pipeline-1",
                }
            for filename, value in documents.items():
                (directory / filename).write_text(json.dumps(value) + "\n")
            (directory / "unrelated.json").write_text('{"do_not_publish": true}\n')
        payloads, references = build_contract_bundle(self.root)
        assert len(payloads) == 15
        assert len(references) == 3
        assert not any(path.endswith("unrelated.json") for path in payloads)
        for path, body in payloads.items():
            if path != "contracts/manifest.json":
                assert body == (self.root / path).read_bytes()

    def test_publication_rejects_version_drift_before_upload(self):
        self.test_publication_inventory_excludes_unrelated_files_and_preserves_bytes()
        path = self.root / "contracts/chocolate/model-design.json"
        document = json.loads(path.read_text())
        document["schema_version"] = "wrong-schema"
        path.write_text(json.dumps(document))
        with pytest.raises(ValueError, match="Contract versions differ"):
            build_contract_bundle(self.root)
