#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["huggingface_hub==2.1.1"]
# ///
"""Publish analytical contracts separately from unchanged raw evidence exports."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SETS = {
    "chocolate": ROOT / "schemas/chocolate/dataset-contract.json",
    "category-processing/chocolate": ROOT / "plugins/category-processing/profiles/chocolate/dataset-contract.json",
    "category-processing/coffee": ROOT / "plugins/category-processing/profiles/coffee/dataset-contract.json",
}
BASE_FILES = ("profile.json", "source-mappings.json", "product.schema.json", "model-design.json")
REFERENCE_FORMAT = "rgc-dataset-contract-reference-1"


def json_bytes(document):
    return (json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def build_contract_bundle(source_root):
    """Return a strict upload inventory; arbitrary source-directory files are excluded."""
    source_root = Path(source_root).expanduser().absolute()
    if source_root.is_symlink():
        raise ValueError("Contract source root cannot be a symlink.")
    source_root = source_root.resolve()
    payloads = {}
    references = {}
    for contract_set in CONTRACT_SETS:
        directory = source_root / "contracts" / contract_set
        names = BASE_FILES + (("pipeline.json",) if contract_set.startswith("category-processing/") else ())
        documents = {}
        files = {}
        for name in names:
            path = directory / name
            if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
                raise ValueError("Contract source cannot contain symlinks: " + str(path))
            body = path.read_bytes()
            documents[name] = json.loads(body)
            remote_path = "contracts/" + contract_set + "/" + name
            payloads[remote_path] = body
            files[name] = {"path": remote_path, "sha256": hashlib.sha256(body).hexdigest(), "size_bytes": len(body)}
        profile = documents["profile.json"]
        version = profile["schema_version"]
        for name in ("source-mappings.json", "model-design.json"):
            if documents[name]["schema_version"] != version:
                raise ValueError("Contract versions differ: " + contract_set + "/" + name)
        if documents["product.schema.json"].get("properties", {}).get("schema_version", {}).get("const") != version:
            raise ValueError("Product validator schema version differs: " + contract_set)
        if profile["attribute_count"] != len(profile["attributes"]):
            raise ValueError("Contract attribute count differs: " + contract_set)
        if profile["category"] != contract_set.split("/")[-1]:
            raise ValueError("Contract category differs from its destination: " + contract_set)
        reference = {
            "format_version": REFERENCE_FORMAT, "contract_set": contract_set,
            "category": profile["category"], "market": profile["market"],
            "schema_version": version, "mapping_version": documents["source-mappings.json"]["mapping_version"],
            "model_design_version": documents["model-design.json"]["model_design_version"],
            "attribute_count": profile["attribute_count"], "files": files,
        }
        if "pipeline.json" in documents:
            if documents["pipeline.json"]["schema_version"] != version:
                raise ValueError("Pipeline schema version differs: " + contract_set)
            reference["pipeline_version"] = documents["pipeline.json"]["pipeline_version"]
        references[contract_set] = reference
    payloads["contracts/manifest.json"] = json_bytes({
        "format_version": "rgc-dataset-contract-index-1", "contract_sets": references,
    })
    return payloads, references


def update_dataset_card(body):
    heading = "## Analytical contracts"
    text = body.decode("utf-8")
    suffix = ""
    if heading in text:
        start = text.index(heading)
        end = text.find("\n## ", start + len(heading))
        if end >= 0:
            suffix = text[end:].strip()
        text = text[:start].rstrip() + "\n"
    section = """
## Analytical contracts

Versioned analytical schemas, mappings, validators and model-preparation designs
are maintained in this dataset under `contracts/`:

- `contracts/chocolate/`: the four chocolate silver contracts.
- `contracts/category-processing/chocolate/`: the portable chocolate profile.
- `contracts/category-processing/coffee/`: the portable coffee starter profile.

`contracts/manifest.json` lists their versions and SHA-256 checksums. Application
code keeps only dataset references that pin an immutable dataset commit and each
file checksum. Downloaded contracts are verified and cached for offline use;
generated silver snapshots keep exact copies of the contracts used by the build.
The raw product index and evidence bundles remain separate from these analytical
definitions. No fitted pricing model or reviewed modeling split is published.
"""
    updated = text.rstrip() + "\n\n" + section.strip() + "\n"
    if suffix:
        updated += "\n" + suffix + "\n"
    return updated.encode()


def publish_contract_bundle(source_root, repo_id, *, write_references=False, receipt=None):
    from huggingface_hub import CommitOperationAdd, HfApi

    payloads, references = build_contract_bundle(source_root)
    api = HfApi()
    api.whoami()
    info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    if info.private:
        raise ValueError("The selected dataset must remain public for schema resolution.")
    with urlopen("https://huggingface.co/datasets/" + repo_id + "/resolve/" + info.sha + "/README.md", timeout=30) as response:
        payloads["README.md"] = update_dataset_card(response.read())
    result = api.create_commit(
        repo_id=repo_id, repo_type="dataset", parent_commit=info.sha,
        operations=[CommitOperationAdd(path_in_repo=path, path_or_fileobj=body) for path, body in sorted(payloads.items())],
        commit_message="Store versioned analytical contracts with the dataset",
    )
    revision = result.oid
    verified = []
    for path, expected in payloads.items():
        with urlopen("https://huggingface.co/datasets/" + repo_id + "/resolve/" + revision + "/" + path, timeout=30) as response:
            observed = response.read()
        if observed != expected:
            raise ValueError("Published contract bytes differ from the prepared bundle: " + path)
        verified.append(path)
    for contract_set, reference in references.items():
        reference.update(repo_id=repo_id, revision=revision)
        if write_references:
            destination = CONTRACT_SETS[contract_set]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(json_bytes(reference))
    report = {"repo_id": repo_id, "revision": revision, "parent_revision": info.sha, "commit_url": result.commit_url,
              "verified_files": sorted(verified), "references": references}
    if receipt:
        destination = Path(receipt)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(json_bytes(report))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Prepared directory containing contracts/<contract-set>/ JSON files.")
    parser.add_argument("--repo-id", default="CoralLeiCN/rgc-collections")
    parser.add_argument("--upload", action="store_true", help="Publish the prepared bundle and verify remote bytes.")
    parser.add_argument("--write-references", action="store_true", help="Update local Git reference manifests after a verified upload.")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.write_references and not args.upload:
        parser.error("--write-references requires --upload")
    if args.upload:
        report = publish_contract_bundle(args.source_root, args.repo_id,
                                        write_references=args.write_references, receipt=args.receipt)
        print(json.dumps({key: report[key] for key in ("repo_id", "revision", "commit_url", "verified_files")}, indent=2))
    else:
        payloads, _ = build_contract_bundle(args.source_root)
        print(json.dumps({"files": sorted(payloads), "total_bytes": sum(map(len, payloads.values()))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
