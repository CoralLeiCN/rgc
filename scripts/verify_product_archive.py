#!/usr/bin/env python3
"""Verify preserved plugin records and artifact integrity without network access.

This checks storage integrity, not ingredient completeness, market coverage, or
the accuracy of a source's product statements. Legacy formats are listed only.
Exit status is 0 for a completed successful check, 1 for failures or pending
records, and 2 for an invalid invocation or an unreadable output destination.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE_VERSION = "category-research-raw-1"
ARTIFACT_GROUPS = ("source_artifacts", "source_catalogs", "images")
PROBLEM_STATUSES = {"failed", "truncated", "partial", "reference_only"}


def slug(value):
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not result:
        raise ValueError("Category and market must yield nonempty directory identifiers.")
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON value: " + value)


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream, parse_constant=reject_constant)


class ArchiveVerifier:
    def __init__(self, archive_root, category, market):
        self.root = Path(archive_root).expanduser().resolve()
        self.category = category
        self.market = market
        self.products_root = self.root / slug(category) / slug(market) / "products"
        self.errors = []
        self.inputs = []
        self.expected = defaultdict(list)
        self.file_cache = {}
        self.group_paths = {group: set() for group in ARTIFACT_GROUPS}
        self.group_counts = {group: Counter({
            "references": 0, "references_with_saved_bytes": 0,
            "references_without_saved_bytes": 0, "integrity_verified_references": 0,
        }) for group in ARTIFACT_GROUPS}
        self.storage_statuses = {group: Counter() for group in ARTIFACT_GROUPS}
        self.retrieval_statuses = {group: Counter() for group in ARTIFACT_GROUPS}
        self.collection_problems = {group: [] for group in ARTIFACT_GROUPS}
        self.image_urls = set()
        self.saved_image_urls = set()
        self.saved_image_hashes = set()
        self.legacy = []
        self.pending = set()
        self.counts = Counter({
            "product_folders_observed": 0, "plugin_product_folders": 0,
            "captures": 0, "history_references": 0, "history_records_verified": 0,
        })

    def error(self, code, context, **details):
        self.errors.append({"code": code, **context, **details})

    def matches_study(self, study):
        if not isinstance(study, dict):
            return False
        try:
            return all(isinstance(study.get(key), str) and slug(study[key]) == slug(value)
                       for key, value in (("category", self.category), ("market", self.market)))
        except ValueError:
            return False

    def resolve_reference(self, reference, context, field):
        if not isinstance(reference, str) or not reference:
            self.error("invalid_path_reference", context, field=field)
            return None
        path = Path(reference)
        if path.is_absolute():
            self.error("absolute_archive_reference", context, field=field, path=reference)
            return None
        try:
            resolved = (self.root / path).resolve()
            resolved.relative_to(self.root)
        except (OSError, ValueError, RuntimeError):
            self.error("archive_reference_escapes_root", context, field=field, path=reference)
            return None
        return resolved

    def file_metrics(self, path):
        if path not in self.file_cache:
            try:
                before = path.stat()
                digest = hashlib.sha256()
                length = 0
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        length += len(chunk)
                        digest.update(chunk)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise OSError("File changed during verification.")
                self.file_cache[path] = {"byte_length": length, "sha256": digest.hexdigest()}
            except OSError as error:
                self.file_cache[path] = {"error": str(error)}
        return self.file_cache[path]

    def load_inputs(self, paths):
        for input_path in paths:
            resolved = Path(input_path).expanduser().resolve()
            report = {"path": str(resolved), "records_received": 0,
                      "records_matched": 0, "unmatched_records": [], "errors": []}
            self.inputs.append(report)
            try:
                document = read_json(resolved)
                if not isinstance(document, dict) or not isinstance(document.get("products"), list):
                    raise ValueError("Input must be an object with a products array.")
                study = document.get("study")
                if not self.matches_study(study):
                    raise ValueError("Input study category/market does not match the requested archive.")
                report["records_received"] = len(document["products"])
                for index, record in enumerate(document["products"]):
                    if not isinstance(record, dict) or not isinstance(record.get("product_id"), str):
                        report["errors"].append({"input_record_index": index, "error": "Product must be an object with a string product_id."})
                        continue
                    self.expected[record["product_id"]].append({
                        "record": record, "index": index, "report": report, "matched": False,
                    })
            except (OSError, ValueError, TypeError) as error:
                report["errors"].append({"error": str(error)})

    def verify_artifact(self, artifact, group, context):
        self.group_counts[group]["references"] += 1
        if not isinstance(artifact, dict):
            self.error("invalid_artifact_metadata", context)
            return
        storage = str(artifact.get("status", "missing"))
        retrieval = str(artifact.get("source_retrieval_status", "not_recorded"))
        self.storage_statuses[group][storage] += 1
        self.retrieval_statuses[group][retrieval] += 1
        http_status = artifact.get("http_status")
        if storage in PROBLEM_STATUSES or retrieval in PROBLEM_STATUSES or (isinstance(http_status, int) and http_status >= 400):
            self.collection_problems[group].append({
                **context, "status": storage, "source_retrieval_status": retrieval,
                "http_status": http_status, "url": artifact.get("url"),
                "reason": artifact.get("error", artifact.get("reason")),
            })
        url = artifact.get("url")
        if group == "images" and isinstance(url, str):
            self.image_urls.add(url)
        reference = artifact.get("archive_relative_path")
        if reference is None:
            self.group_counts[group]["references_without_saved_bytes"] += 1
            if storage == "saved":
                self.error("saved_artifact_missing_path", context)
            return
        self.group_counts[group]["references_with_saved_bytes"] += 1
        path = self.resolve_reference(reference, context, "archive_relative_path")
        if path is None:
            return
        self.group_paths[group].add(path)
        actual = self.file_metrics(path)
        if "error" in actual:
            self.error("artifact_file_unreadable", context, path=reference, error=actual["error"])
            return
        length = artifact.get("byte_length")
        expected_hash = artifact.get("sha256")
        valid_length = isinstance(length, int) and not isinstance(length, bool) and length >= 0
        valid_hash = isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) is not None
        if not valid_length or not valid_hash:
            self.error("artifact_integrity_metadata_missing_or_invalid", context, path=reference)
            return
        if actual["byte_length"] != length:
            self.error("artifact_size_mismatch", context, path=reference, expected=length, actual=actual["byte_length"])
        if actual["sha256"] != expected_hash.lower():
            self.error("artifact_hash_mismatch", context, path=reference, expected=expected_hash, actual=actual["sha256"])
        if actual["byte_length"] == length and actual["sha256"] == expected_hash.lower():
            self.group_counts[group]["integrity_verified_references"] += 1
            if group == "images" and storage == "saved":
                self.group_counts[group]["saved_image_references_with_verified_bytes"] += 1
                self.saved_image_hashes.add(actual["sha256"])
                if isinstance(url, str):
                    self.saved_image_urls.add(url)

    def verify_product(self, folder):
        context = {"product_id": folder.name}
        if (folder / ".import.lock").exists():
            self.pending.add(folder.name)
            return
        index_path = folder / "product.json"
        try:
            index_path.resolve().relative_to(self.root)
            document = read_json(index_path)
            if not isinstance(document, dict):
                raise ValueError("Product index must be a JSON object.")
        except (OSError, ValueError, RuntimeError) as error:
            if (folder / ".import.lock").exists():
                self.pending.add(folder.name)
            else:
                self.error("product_index_unreadable", context, error=str(error))
            return
        if (folder / ".import.lock").exists():
            self.pending.add(folder.name)
            return
        if document.get("archive_format_version") != ARCHIVE_VERSION:
            self.legacy.append({"product_id": folder.name,
                                "archive_format_version": document.get("archive_format_version"),
                                "verification_status": "not_checked_unsupported_or_legacy_format"})
            return
        self.counts["plugin_product_folders"] += 1
        if document.get("product_id") != folder.name:
            self.error("product_identity_mismatch", context)
        if not self.matches_study(document):
            self.error("product_study_mismatch", context)
        captures = document.get("captures")
        if not isinstance(captures, list) or not captures:
            self.error("missing_or_invalid_captures", context)
            return
        capture_ids = set()
        for capture_index, capture in enumerate(captures):
            self.counts["captures"] += 1
            capture_context = {**context, "capture_index": capture_index}
            if not isinstance(capture, dict):
                self.error("invalid_capture", capture_context)
                continue
            capture_id = capture.get("capture_id")
            if not isinstance(capture_id, str) or not capture_id or capture_id in capture_ids:
                self.error("invalid_or_duplicate_capture_id", capture_context)
            else:
                capture_ids.add(capture_id)
                capture_context["capture_id"] = capture_id
            record = capture.get("raw_record")
            if not isinstance(record, dict):
                self.error("missing_or_invalid_raw_record", capture_context)
            else:
                if record.get("product_id") != folder.name:
                    self.error("capture_product_identity_mismatch", capture_context)
                if "information" not in capture or record.get("information") != capture["information"]:
                    self.error("capture_information_mismatch", capture_context)
                for expected in self.expected.get(folder.name, []):
                    if not expected["matched"] and expected["record"] == record:
                        expected["matched"] = True
                        expected["report"]["records_matched"] += 1
            history_path = self.resolve_reference(capture.get("history_path"), capture_context, "history_path")
            if history_path is not None:
                self.counts["history_references"] += 1
                try:
                    if read_json(history_path) != capture:
                        self.error("history_capture_mismatch", capture_context)
                    else:
                        self.counts["history_records_verified"] += 1
                except (OSError, ValueError) as error:
                    self.error("history_unreadable", capture_context, error=str(error))
            for group in ARTIFACT_GROUPS:
                artifacts = capture.get(group)
                if not isinstance(artifacts, list):
                    self.error("missing_or_invalid_artifact_list", capture_context, artifact_group=group)
                    continue
                for artifact_index, artifact in enumerate(artifacts):
                    self.verify_artifact(artifact, group, {
                        **capture_context, "artifact_group": group, "artifact_index": artifact_index,
                    })
        latest_id = document.get("latest_capture_id")
        if not isinstance(latest_id, str) or latest_id not in capture_ids:
            self.error("latest_capture_id_does_not_resolve", context)

    def run(self, input_paths):
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.load_inputs(input_paths)
        if not self.products_root.is_dir():
            self.error("products_directory_missing", {}, path=str(self.products_root))
        else:
            for folder in sorted(self.products_root.iterdir()):
                if folder.is_dir():
                    self.counts["product_folders_observed"] += 1
                    self.verify_product(folder)
        for product_id, expectations in self.expected.items():
            for expected in expectations:
                if not expected["matched"]:
                    expected["report"]["unmatched_records"].append({
                        "input_record_index": expected["index"], "product_id": product_id,
                        "reason": "product_import_in_progress" if product_id in self.pending else "exact_raw_record_not_found_in_observed_captures",
                    })
        input_problem = any(report["errors"] or report["unmatched_records"] for report in self.inputs)
        status = "failed" if self.errors else "incomplete" if input_problem or self.pending else "passed"
        artifacts = {}
        for group in ARTIFACT_GROUPS:
            artifacts[group] = {
                **dict(self.group_counts[group]), "unique_referenced_files": len(self.group_paths[group]),
                "storage_status_counts": dict(self.storage_statuses[group]),
                "source_retrieval_status_counts": dict(self.retrieval_statuses[group]),
            }
        return {
            "verification_format_version": "product-archive-verification-1",
            "archive_format_version_checked": ARCHIVE_VERSION,
            "archive_root": str(self.root), "category": self.category, "market": self.market,
            "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "verification_status": status,
            "verification_scope": "Observed plugin indexes, immutable capture histories, referenced artifact bytes, and exact supplied input records. No source-content completeness or market-coverage verification.",
            "counts": {**dict(self.counts), "legacy_or_unsupported_product_folders": len(self.legacy),
                       "product_imports_in_progress": len(self.pending),
                       "input_files": len(self.inputs),
                       "input_records": sum(item["records_received"] for item in self.inputs),
                       "input_records_matched": sum(item["records_matched"] for item in self.inputs),
                       "unique_artifact_files_hashed": sum("sha256" in item for item in self.file_cache.values()),
                       "unique_artifact_bytes_hashed": sum(item.get("byte_length", 0) for item in self.file_cache.values())},
            "artifacts": artifacts,
            "images": {"unique_declared_urls": len(self.image_urls),
                       "unique_saved_urls_with_verified_bytes": len(self.saved_image_urls),
                       "unique_saved_sha256_with_verified_bytes": len(self.saved_image_hashes)},
            "integrity_failure_count": len(self.errors), "integrity_failures": self.errors,
            "collection_outcomes": {group: {"problem_reference_count": len(problems), "problems": problems}
                                    for group, problems in self.collection_problems.items()},
            "inputs": self.inputs, "imports_in_progress": sorted(self.pending),
            "legacy_or_unsupported_folders": self.legacy,
            "limitations": ["This is a point-in-time check; running imports are skipped and make verification incomplete.",
                            "Saved failed HTTP responses can pass byte-integrity checks without being usable product pages or images.",
                            "Legacy folders are reported separately and have not been verified by this checker."],
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, help="Archive root containing category/market directories.")
    parser.add_argument("--category", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--input", action="append", default=[], help="Prepared import JSON to compare; repeatable.")
    parser.add_argument("--report", help="Optional JSON report path; stdout otherwise contains the full report.")
    args = parser.parse_args(argv)
    try:
        report = ArchiveVerifier(args.archive_root, args.category, args.market).run(args.input)
        rendered = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
        if args.report:
            report_path = Path(args.report).expanduser().resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(rendered, encoding="utf-8")
            print(json.dumps({"verification_status": report["verification_status"],
                              "integrity_failure_count": report["integrity_failure_count"],
                              "counts": report["counts"], "report_path": str(report_path)}))
        else:
            sys.stdout.write(rendered)
        return 0 if report["verification_status"] == "passed" else 1
    except (OSError, ValueError, RuntimeError) as error:
        print("Verification could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
