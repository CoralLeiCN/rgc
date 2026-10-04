"""Atomic publication and verification of immutable local Silver snapshots."""

import hashlib
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from .archive import inside, json_bytes, read_json, sha256
from .silver_contracts import FILES

MANIFEST = "category-silver-manifest-2"


def row_bytes(rows):
    return b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode() for row in rows)


def read_rows(path):
    def reject(value):
        raise ValueError("Non-finite value: " + value)
    return [json.loads(line, parse_constant=reject) for line in Path(path).read_text().splitlines() if line.strip()]


def no_links(path):
    path = Path(path).expanduser().absolute()
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Generated state and snapshots must not use symlinks.")
    return path.resolve()


def publish(output, version, files):
    output = no_links(output)
    destination = output / version
    output.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if any(path.is_symlink() for path in destination.rglob("*")):
            raise ValueError("Immutable snapshots must not contain symlinks.")
        existing = {path.relative_to(destination).as_posix(): path.read_bytes()
                    for path in destination.rglob("*") if path.is_file()}
        if existing != files:
            raise ValueError("Refusing to overwrite an immutable snapshot with different bytes.")
    else:
        with TemporaryDirectory(prefix=".silver-build-", dir=output) as temporary:
            stage = Path(temporary) / version
            stage.mkdir()
            for name, data in files.items():
                target = stage / name
                if Path(name).is_absolute() or not inside(target.resolve(), stage):
                    raise ValueError("Invalid snapshot filename.")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            try:
                os.rename(stage, destination)
            except OSError:
                if not destination.is_dir() or {p.relative_to(destination).as_posix(): p.read_bytes()
                                               for p in destination.rglob("*") if p.is_file()} != files:
                    raise
    # A pointer can change; the snapshot it names cannot.
    with TemporaryDirectory(prefix=".silver-pointer-", dir=output) as temporary:
        pointer = Path(temporary) / "latest.json"
        pointer.write_bytes(json_bytes({"dataset_version": version, "path": version,
                                       "manifest_sha256": sha256(destination / "manifest.json")}))
        shutil.move(str(pointer), str(output / "latest.json"))
    return destination


def verified_snapshot(root):
    root = no_links(root)
    if not (root / "manifest.json").exists():
        latest = read_json(root / "latest.json")
        child = root / latest["path"]
        if child.parent != root or child.name != latest["dataset_version"]:
            raise ValueError("Invalid Silver snapshot pointer.")
        root = no_links(child)
        if sha256(root / "manifest.json") != latest["manifest_sha256"]:
            raise ValueError("Silver snapshot pointer hash mismatch.")
    manifest = read_json(root / "manifest.json")
    if manifest.get("manifest_format_version") != MANIFEST:
        raise ValueError("Expected a standard Silver v2 snapshot.")
    required = {*FILES, "facts.jsonl", "products.jsonl", "subjects.jsonl", "schema-profile.json", "schema-profile.md",
                "quality-report.json", "source-index.json", "corrections.jsonl", "assertions.jsonl", "prices.jsonl",
                "review-queue.jsonl", "data-dictionary.json", "source-listings.jsonl", "raw-inputs.json"}
    managed = manifest.get("managed_files", {})
    if not required <= set(managed):
        raise ValueError("Silver manifest omits required outputs.")
    for name, spec in managed.items():
        path = no_links(root / name)
        if Path(name).is_absolute() or not inside(path, root):
            raise ValueError("Silver file escapes the snapshot.")
        if sha256(path) != spec["sha256"] or path.stat().st_size != spec["byte_length"]:
            raise ValueError("Silver managed file changed: " + name)
    if manifest["contract_sha256"] != {name: managed[name]["sha256"] for name in FILES}:
        raise ValueError("Silver contracts disagree with the manifest.")
    identity = manifest["identity"]
    if identity.get("contract_sha256") != manifest["contract_sha256"]:
        raise ValueError("Silver field contract identity mismatch.")
    version = "silver-" + hashlib.sha256(json_bytes(identity)).hexdigest()[:24]
    if manifest["dataset_version"] != version:
        raise ValueError("Silver snapshot identity mismatch.")
    for key, name in (("source_index_sha256", "source-index.json"), ("corrections_sha256", "corrections.jsonl"),
                      ("raw_inputs_sha256", "raw-inputs.json")):
        if identity[key] != managed[name]["sha256"]:
            raise ValueError("Silver provenance mismatch: " + key)
    return root, manifest
