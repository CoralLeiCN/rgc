"""Resolve immutable, checksum-pinned dataset contracts without bundled payloads."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import urlopen

REFERENCE_FORMAT = "rgc-dataset-contract-reference-1"
REFERENCE_FILE = "dataset-contract.json"
CONTRACT_FILES = {"profile.json", "source-mappings.json", "product.schema.json",
                  "model-design.json", "pipeline.json"}


def _validate_manifest(document):
    if not isinstance(document, dict) or document.get("format_version") != REFERENCE_FORMAT:
        raise ValueError("Unsupported dataset contract reference format.")
    repo = document.get("repo_id", "")
    if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repo):
        raise ValueError("Dataset reference requires a namespace/repository ID.")
    if not re.fullmatch(r"[0-9a-f]{40}", str(document.get("revision", ""))):
        raise ValueError("Dataset reference must pin an immutable 40-character commit revision.")
    contract_set = document.get("contract_set", "")
    if not isinstance(contract_set, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*", contract_set):
        raise ValueError("Invalid dataset contract set path.")
    fields = ["category", "market", "schema_version", "mapping_version"]
    if isinstance(document.get("files"), dict) and "model-design.json" in document["files"]:
        fields.append("model_design_version")
    for field in fields:
        if not isinstance(document.get(field), str) or not document[field]:
            raise ValueError("Dataset reference is missing metadata: " + field)
    count = document.get("attribute_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("Dataset reference requires a positive attribute count.")
    files = document.get("files")
    if not isinstance(files, dict) or not files or not set(files) <= CONTRACT_FILES:
        raise ValueError("Dataset reference has an unsupported contract file set.")
    for name, metadata in files.items():
        if not isinstance(metadata, dict):
            raise ValueError("Invalid dataset contract file metadata: " + name)
        expected_path = "contracts/" + contract_set + "/" + name
        if metadata.get("path") != expected_path or PurePosixPath(expected_path).is_absolute():
            raise ValueError("Invalid remote dataset contract path: " + name)
        if not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("sha256", ""))):
            raise ValueError("Invalid dataset contract SHA-256: " + name)
        size = metadata.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ValueError("Invalid dataset contract byte length: " + name)
    return document


def load_manifest(path):
    """Read a small Git-tracked reference, never downloading contract payloads."""
    return _validate_manifest(json.loads(Path(path).read_text(encoding="utf-8")))


def cache_directory(manifest, cache_root):
    _validate_manifest(manifest)
    return Path(cache_root) / manifest["repo_id"] / manifest["revision"] / manifest["contract_set"]


def _verify_bytes(body, metadata, name):
    if len(body) != metadata["size_bytes"] or hashlib.sha256(body).hexdigest() != metadata["sha256"]:
        raise ValueError("Dataset contract checksum/length mismatch: " + name)
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Dataset contract is not valid JSON: " + name) from error
    if not isinstance(document, dict):
        raise ValueError("Dataset contract must be a JSON object: " + name)


def verify_contract_directory(manifest, directory, require_all=True, required_files=None):
    """Validate available cache bytes; reject corruption rather than repairing it."""
    _validate_manifest(manifest)
    required = set(manifest["files"]) if required_files is None else set(required_files)
    if not required <= set(manifest["files"]):
        raise ValueError("Requested contract files are outside the immutable reference.")
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Dataset contract cache cannot be a symlink.")
    marker = directory / REFERENCE_FILE
    if marker.is_symlink():
        raise ValueError("Dataset contract cache reference cannot be a symlink.")
    if marker.exists() and load_manifest(marker) != manifest:
        raise ValueError("Dataset contract cache reference differs from the pinned reference.")
    for name, metadata in manifest["files"].items():
        path = directory / name
        if path.is_symlink():
            raise ValueError("Dataset contract cache file cannot be a symlink: " + name)
        if not path.exists():
            if require_all and name in required:
                raise FileNotFoundError("Pinned dataset contract is absent from the local cache: " + name)
            continue
        _verify_bytes(path.read_bytes(), metadata, name)


def _download(url):
    with urlopen(url, timeout=30) as response:
        return response.read()


def _atomic_write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".contract-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def resolve_contracts(manifest_path, cache_root, *, offline=False, download=None, required_files=None):
    """Materialize and verify one pinned contract set, or use its offline cache."""
    manifest = load_manifest(manifest_path)
    required = set(manifest["files"]) if required_files is None else set(required_files)
    if not required <= set(manifest["files"]):
        raise ValueError("Requested contract files are outside the immutable reference.")
    directory = cache_directory(manifest, cache_root)
    root = Path(cache_root).absolute()
    for path in (directory.absolute(), *directory.absolute().parents):
        if path.is_symlink():
            raise ValueError("Dataset contract cache paths cannot contain symlinks.")
        if path == root:
            break
    verify_contract_directory(manifest, directory, require_all=False)
    missing = [name for name in manifest["files"] if name in required and not (directory / name).exists()]
    if missing and offline:
        raise FileNotFoundError("Pinned dataset contracts are not cached; fetch them before offline use: " + ", ".join(missing))
    fetch = download or _download
    for name in missing:
        metadata = manifest["files"][name]
        url = "https://huggingface.co/datasets/{}/resolve/{}/{}".format(
            quote(manifest["repo_id"], safe="/"), manifest["revision"], quote(metadata["path"], safe="/"))
        body = fetch(url)
        _verify_bytes(body, metadata, name)
        _atomic_write(directory / name, body)
    marker = directory / REFERENCE_FILE
    if not marker.exists():
        _atomic_write(marker, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode())
    verify_contract_directory(manifest, directory, required_files=required)
    return directory
