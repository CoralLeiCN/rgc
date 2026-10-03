"""Preserve supplied product information and source bytes before schema design."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


ARCHIVE_VERSION = "category-research-raw-1"
DEFAULT_MAX_BYTES = 20 * 1024 * 1024


class ArchiveError(ValueError):
    """Invalid envelope or an archive conflict requiring caller attention."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def write_index(path, value):
    temporary = path.parent / ("." + path.name + "." + uuid4().hex + ".tmp")
    try:
        write_new(temporary, json_bytes(value))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def slug(value):
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not result:
        raise ArchiveError("Category and market must yield a nonempty directory identifier.")
    return result


def require_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ArchiveError(field + " must be a nonempty string.")


def validate_document(document):
    if not isinstance(document, dict):
        raise ArchiveError("The import document must be a JSON object.")
    require_string(document.get("contract_version"), "contract_version")
    study = document.get("study")
    if not isinstance(study, dict):
        raise ArchiveError("study must be an object.")
    for key in ("study_id", "category", "market"):
        require_string(study.get(key), "study." + key)
    products = document.get("products")
    if not isinstance(products, list):
        raise ArchiveError("products must be an array.")
    if not isinstance(document.get("source_catalogs", []), list):
        raise ArchiveError("source_catalogs must be an array when supplied.")
    for index, product in enumerate(products):
        if not isinstance(product, dict):
            raise ArchiveError(f"products[{index}] must be an object.")
        identifier = product.get("product_id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,199}", identifier):
            raise ArchiveError(f"products[{index}].product_id must be a safe alphanumeric identifier.")
        for key in ("identity",):
            if key in product and not isinstance(product[key], dict):
                raise ArchiveError(f"products[{index}].{key} must be an object.")
        for key in ("source_artifacts", "images", "collection_notes"):
            if key in product and not isinstance(product[key], list):
                raise ArchiveError(f"products[{index}].{key} must be an array.")
        for artifact in product.get("source_artifacts", []):
            if not isinstance(artifact, dict) or not isinstance(artifact.get("kind", "page"), str) or not artifact.get("kind", "page"):
                raise ArchiveError("Source artifacts must be objects with a nonempty kind label.")
        if any(not isinstance(image, dict) for image in product.get("images", [])):
            raise ArchiveError("Image references must be objects.")
    try:
        json_bytes(document)
    except (TypeError, ValueError) as error:
        raise ArchiveError("The complete import document must contain finite JSON values.") from error


def get_raw(url, *, timeout=20, max_bytes=DEFAULT_MAX_BYTES):
    """Return retrieval metadata and unchanged response bytes, including errors."""
    metadata = {"url": url, "retrieved_at": now(), "timezone": "UTC", "retrieval_method": "HTTP GET"}
    if not isinstance(url, str) or urlparse(url).scheme not in ("https", "http"):
        return {**metadata, "status": "failed", "error": "Only HTTP and HTTPS source URLs are supported."}, b""
    request = Request(url, headers={"User-Agent": "CategoryResearch/0.1 (+raw product archive)", "Accept": "*/*", "Accept-Encoding": "identity", "Accept-Language": "en-GB,en;q=0.9"})
    body = b""
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            metadata.update({
                "status": "downloaded" if len(body) <= max_bytes else "truncated",
                "http_status": response.status, "final_url": response.url,
                "content_type": response.headers.get("Content-Type", ""),
                "content_encoding": response.headers.get("Content-Encoding"),
                "charset": response.headers.get_content_charset(),
                "etag": response.headers.get("ETag"), "last_modified": response.headers.get("Last-Modified"),
            })
    except HTTPError as error:
        body = error.read(max_bytes + 1)
        metadata.update({"status": "failed", "http_status": error.code, "final_url": error.url,
                         "content_type": error.headers.get("Content-Type", ""), "error": str(error),
                         "response_truncated": len(body) > max_bytes})
    except (URLError, TimeoutError, OSError, ValueError) as error:
        metadata.update({"status": "failed", "error": str(error)})
    metadata.update({"byte_length": len(body), "sha256": digest(body) if body else None})
    return metadata, body


def _resolved_local(value, input_base):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (input_base / path).resolve()


def _extension(kind, metadata, local_path=None):
    if local_path and Path(local_path).suffix:
        suffixes = Path(local_path).suffixes
        return "".join(suffixes[-2:]) if suffixes[-1].lower() in (".gz", ".gzip", ".bz2", ".xz") else suffixes[-1]
    if kind != "image":
        suffix = {"page": ".html", "json": ".json", "text": ".txt", "derived_text": ".txt", "fetch_error": ".response"}.get(kind, ".bin")
        return suffix + ".gz" if metadata.get("content_encoding") == "gzip" else suffix
    media_type = metadata.get("content_type", "").split(";", 1)[0].lower().strip()
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg", "image/avif": ".avif"}.get(media_type, Path(local_path).suffix if local_path else ".image")


def archive_artifact(descriptor, directory, stem, output_root, input_base, *, fetch_enabled, kind, timeout, max_bytes, retriever=None):
    """Archive one supplied/retrieved artifact without parsing or re-encoding it."""
    metadata = {"descriptor": deepcopy(descriptor), "url": descriptor.get("url"), "kind": kind,
                "recorded_at": now(), "archived_at": now(), "timezone": "UTC", "completeness": "not_verified"}
    if descriptor.get("retrieved_at") is not None:
        metadata["retrieved_at"] = descriptor["retrieved_at"]
    if kind == "derived_text":
        metadata["representation"] = "derived_text"
        metadata["derivation"] = descriptor.get("derivation", "supplied derived text; original-page completeness not established")
    for key in ("http_status", "final_url", "content_encoding", "charset", "etag", "last_modified"):
        if key in descriptor:
            metadata[key] = deepcopy(descriptor[key])
    supplied_status = descriptor.get("source_retrieval_status", descriptor.get("status"))
    http_status = descriptor.get("http_status")
    if http_status is None and isinstance(supplied_status, int) and not isinstance(supplied_status, bool):
        http_status = supplied_status
        metadata["http_status"] = http_status
    metadata["source_retrieval_status"] = "failed" if kind == "fetch_error" or (isinstance(http_status, int) and http_status >= 400) else supplied_status or "unknown"
    body = None
    try:
        if descriptor.get("local_path") is not None:
            source_path = _resolved_local(descriptor["local_path"], input_base)
            body = source_path.read_bytes()
            guessed_type, guessed_encoding = mimetypes.guess_type(source_path.name)
            metadata.update({"status": "saved", "retrieval_method": "copied local bytes",
                             "original_local_path": str(source_path),
                             "content_type": descriptor.get("content_type") or guessed_type or "application/octet-stream"})
            if guessed_encoding and "content_encoding" not in metadata:
                metadata["content_encoding"] = guessed_encoding
        elif "content" in descriptor:
            content = descriptor["content"]
            body = content.encode("utf-8") if isinstance(content, str) else json_bytes(content)
            metadata.update({"status": "saved", "retrieval_method": "supplied inline text" if isinstance(content, str) else "serialized supplied JSON value",
                             "content_type": descriptor.get("content_type") or {"page": "text/html; charset=utf-8", "text": "text/plain; charset=utf-8", "derived_text": "text/plain; charset=utf-8"}.get(kind, "application/json; charset=utf-8")})
        elif fetch_enabled:
            retrieval, received = (retriever or get_raw)(descriptor.get("url"), timeout=timeout, max_bytes=max_bytes)
            metadata.update(retrieval)
            metadata["source_retrieval_status"] = retrieval["status"]
            body = received if received or retrieval["status"] == "downloaded" else None
            if retrieval["status"] == "downloaded":
                metadata["status"] = "saved"
            if kind == "image" and metadata["status"] == "saved" and not metadata.get("content_type", "").lower().startswith("image/"):
                metadata.update({"status": "failed", "error": "Retrieved response was not an image; response bytes retained."})
        else:
            metadata.update({"status": "reference_only", "retrieval_method": "not requested"})
    except (OSError, ValueError, TypeError) as error:
        metadata.update({"status": "failed", "error": str(error)})
    if body is not None:
        suffix = _extension(kind, metadata, descriptor.get("local_path")) if metadata["status"] == "saved" else ".response"
        path = directory / (stem + suffix)
        write_new(path, body)
        metadata.update({"archive_relative_path": str(path.relative_to(output_root)), "sha256": digest(body), "byte_length": len(body), "archived_at": now()})
        if not body:
            metadata.update({"status": "failed", "error": "Empty source response retained; information completeness is unknown."})
    return metadata


def section_presence(information):
    """Report explicit source-field presence, never inferred completeness."""
    sections = {name: {"status": "unknown", "paths": [], "completeness": "not_verified"}
                for name in ("ingredients", "nutrition", "description", "prices", "availability", "packaging")}
    markers = {"ingredients": ("ingredient",), "nutrition": ("nutrition", "nutritional"),
               "description": ("description", "bodyhtml"), "prices": ("price",),
               "availability": ("availability", "available", "stock"), "packaging": ("packaging", "wrapper")}
    ingredient_metadata = ("status", "error", "quality", "note", "method", "path", "hash",
                           "encoding", "complete", "review", "verif", "missing", "available",
                           "availability", "present", "sourceurl", "sourcekey", "retrievedat",
                           "interpret", "provenance", "metadata")
    unknown_values = {"unknown", "missing", "unavailable", "not available", "not captured",
                      "not extracted", "not listed", "none", "null", "n/a", "not stated",
                      "not provided", "not found", "unverified"}

    def ingredient_evidence(value):
        if isinstance(value, str):
            text = value.strip()
            return bool(text) and text.casefold() not in unknown_values and not re.match(r"https?://\S+$", text)
        if isinstance(value, list):
            return any(ingredient_evidence(item) for item in value)
        if isinstance(value, dict):
            return any(ingredient_evidence(item) for key, item in value.items()
                       if not any(word in re.sub(r"[^a-z]", "", key.casefold()) for word in ingredient_metadata))
        return False

    def visit(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = re.sub(r"[^a-z]", "", key.casefold())
                meaningful = item is not None and item != "" and item != [] and item != {}
                for name, words in markers.items():
                    if name == "ingredients" and (any(word in normalized for word in ingredient_metadata) or not ingredient_evidence(item)):
                        continue
                    if meaningful and any(word in normalized for word in words):
                        sections[name]["status"] = "source_field_present"
                        sections[name]["paths"].append(path + "." + key)
                visit(item, path + "." + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
    visit(information, "$.information")
    return sections


@contextmanager
def product_lock(folder):
    """Reject concurrent writers rather than lose current-index history."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ".import.lock"
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ArchiveError("Product archive is locked: " + str(folder)) from error
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "created_at": now()}))
        yield
    finally:
        path.unlink(missing_ok=True)


def import_document(document, output_root, *, download_images=False, image_limit=None,
                    fetch_pages=False, input_base=None, workers=4, timeout=20, max_bytes=DEFAULT_MAX_BYTES, progress=None):
    """Append raw imports; only the complete product.json current index is replaced."""
    validate_document(document)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ArchiveError("workers must be a positive integer.")
    if image_limit is not None and (not isinstance(image_limit, int) or isinstance(image_limit, bool) or image_limit < 0):
        raise ArchiveError("image_limit must be a nonnegative integer or None.")
    if timeout <= 0 or max_bytes < 1:
        raise ArchiveError("timeout and max_bytes must be positive.")
    output_root = Path(output_root).resolve()
    input_base = Path(input_base or Path.cwd()).resolve()
    study = document["study"]
    study_root = output_root / slug(study["category"]) / slug(study["market"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:10]
    run_folder = study_root / "runs" / run_id
    write_new(run_folder / "import.json", json_bytes(document))
    shared_catalogs = {}
    catalog_lock = Lock()
    transfer_lock = Lock()
    transfer_locks = {}
    transfers = {}
    progress_lock = Lock()
    completed = 0

    def cached_raw(url, **options):
        key = digest(json_bytes({"url": url, **options}))
        with transfer_lock:
            individual_lock = transfer_locks.setdefault(key, Lock())
        with individual_lock:
            if key not in transfers:
                metadata, body = get_raw(url, **options)
                path = study_root / "transfers" / run_id / (key + ".response")
                write_new(path, body)
                metadata["shared_transfer_path"] = str(path.relative_to(output_root))
                write_new(path.with_suffix(".metadata.json"), json_bytes(metadata))
                transfers[key] = metadata
            metadata = deepcopy(transfers[key])
            return metadata, (output_root / metadata["shared_transfer_path"]).read_bytes()

    def catalog_artifact(descriptor):
        if isinstance(descriptor, str):
            descriptor = {"local_path": descriptor, "kind": "json"}
        if not isinstance(descriptor, dict):
            return {"status": "failed", "error": "source_catalog must be an artifact object or local path.", "descriptor": deepcopy(descriptor)}
        cache_key = digest(json_bytes(descriptor))
        with catalog_lock:
            if cache_key not in shared_catalogs:
                shared_catalogs[cache_key] = archive_artifact(descriptor, study_root / "catalogs" / run_id, cache_key[:16], output_root,
                    input_base, fetch_enabled=fetch_pages, kind=descriptor.get("kind", "json"), timeout=timeout, max_bytes=max_bytes, retriever=cached_raw)
            return deepcopy(shared_catalogs[cache_key])

    global_catalogs = [catalog_artifact(item) for item in document.get("source_catalogs", [])]

    def archive_product(item):
        index, record = item
        folder = study_root / "products" / record["product_id"]
        capture_id = run_id + f"-{index:06d}"
        with product_lock(folder):
            current_path = folder / "product.json"
            current = json.loads(current_path.read_text(encoding="utf-8")) if current_path.exists() else {
                "archive_format_version": ARCHIVE_VERSION, "product_id": record["product_id"],
                "category": study["category"], "market": study["market"], "captures": [],
            }
            if current.get("product_id") != record["product_id"] or not isinstance(current.get("captures"), list):
                raise ArchiveError("Existing product index has an incompatible identity/history envelope: " + str(current_path))
            capture = {"capture_id": capture_id, "recorded_at": now(), "timezone": "UTC",
                       "contract_version": document["contract_version"], "study": deepcopy(study),
                       "raw_record": deepcopy(record), "information": deepcopy(record.get("information")),
                       "collection_notes": deepcopy(record.get("collection_notes", [])),
                       "source_artifacts": [], "images": [], "source_catalogs": deepcopy(global_catalogs),
                       "raw_section_presence": section_presence(record.get("information")),
                       "completeness": "not_verified"}
            if "source_catalog" in record:
                values = record["source_catalog"] if isinstance(record["source_catalog"], list) else [record["source_catalog"]]
                capture["source_catalogs"].extend(catalog_artifact(value) for value in values)
            descriptors = record.get("source_artifacts", [])
            if not descriptors and fetch_pages and record.get("source_url"):
                descriptors = [{"url": record["source_url"], "kind": "page", "source_key": record.get("source_key")}]
            for artifact_index, descriptor in enumerate(descriptors):
                capture["source_artifacts"].append(archive_artifact(descriptor, folder / "sources" / capture_id,
                    f"{artifact_index:04d}", output_root, input_base, fetch_enabled=fetch_pages,
                    kind=descriptor.get("kind", "page"), timeout=timeout, max_bytes=max_bytes, retriever=cached_raw))
            for image_index, descriptor in enumerate(record.get("images", [])):
                supplied = descriptor.get("local_path") is not None or "content" in descriptor
                allowed = supplied or (download_images and (image_limit is None or image_index < image_limit))
                if allowed:
                    result = archive_artifact(descriptor, folder / "images" / capture_id, f"{image_index:04d}",
                        output_root, input_base, fetch_enabled=download_images, kind="image", timeout=timeout, max_bytes=max_bytes, retriever=cached_raw)
                else:
                    result = {"descriptor": deepcopy(descriptor), "url": descriptor.get("url"), "status": "reference_only",
                              "reason": "image limit" if download_images else "image downloading not requested"}
                capture["images"].append(result)
            artifacts = capture["source_artifacts"] + capture["images"] + capture["source_catalogs"]
            capture["status"] = "partial" if any(item["status"] in ("failed", "truncated", "reference_only") or item.get("source_retrieval_status") in ("failed", "truncated", "partial") for item in artifacts) else "raw_record_preserved_review_pending"
            capture["history_path"] = str((folder / "history" / (capture_id + ".json")).relative_to(output_root))
            capture["finished_at"] = now()
            write_new(output_root / capture["history_path"], json_bytes(capture))
            current["captures"].append(capture)
            current.update({"latest_capture_id": capture_id, "identity": deepcopy(record.get("identity", {})),
                            "updated_at": now()})
            write_index(current_path, current)
            return {"product_id": record["product_id"], "capture_id": capture_id,
                    "product_json": str(current_path.relative_to(output_root)), "history_path": capture["history_path"],
                    "status": capture["status"], "ingredient_field_status": capture["raw_section_presence"]["ingredients"]["status"],
                    "source_files_saved": sum("archive_relative_path" in item for item in capture["source_artifacts"]),
                    "image_files_saved": sum(item["status"] == "saved" for item in capture["images"])}

    grouped = {}
    for index, record in enumerate(document["products"]):
        grouped.setdefault(record["product_id"], []).append((index, record))

    def archive_group(items):
        nonlocal completed
        outcomes = []
        for item in items:
            try:
                outcomes.append(archive_product(item))
            except (OSError, ValueError, TypeError) as error:
                outcomes.append({"product_id": item[1]["product_id"], "status": "failed", "error": str(error)})
            if progress is not None:
                with progress_lock:
                    completed += 1
                    progress({"completed": completed, "total": len(document["products"]), **outcomes[-1]})
        return outcomes

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = [item for group in executor.map(archive_group, grouped.values()) for item in group]
    report = {"archive_format_version": ARCHIVE_VERSION, "contract_version": document["contract_version"],
              "run_id": run_id, "study": deepcopy(study), "finished_at": now(), "timezone": "UTC",
              "status": "partial" if any(item["status"] in ("failed", "partial") for item in results) or any(item["status"] != "saved" or item.get("source_retrieval_status") in ("failed", "truncated", "partial") for item in global_catalogs) else "raw_import_preserved_review_pending",
              "completeness": "not_verified", "records_received": len(document["products"]),
              "unique_product_ids": len(grouped), "source_catalogs": list(shared_catalogs.values()), "products": results,
              "unique_http_transfers": len(transfers),
              "report_path": str((run_folder / "report.json").relative_to(output_root))}
    write_new(output_root / report["report_path"], json_bytes(report))
    return report
