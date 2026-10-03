"""Deterministic capture processing state, independent of mutable folder aliases."""

from collections import Counter
import hashlib
import json


LEDGER_VERSION = "category-processing-ledger-1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _artifact_hashes(value):
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            if key == "sha256" and isinstance(item, str):
                result.append(item)
            else:
                result.extend(_artifact_hashes(item))
        return result
    if isinstance(value, list):
        return [checksum for item in value for checksum in _artifact_hashes(item)]
    return []


def build_ledger(source_rows, processing_fingerprint, failed_capture_ids=()):
    """Track every accepted capture without changing its original evidence.

    Content equality describes repeated evidence, not permission to merge events
    or sellers. A full snapshot is rebuilt today; this ledger exposes the state
    needed for a future selective execution cache without silently skipping work.
    """
    failed = set(failed_capture_ids)
    ledger = {}
    for source in source_rows:
        captures = source["captures"]
        if isinstance(captures, dict):
            captures = list(captures.values())
        for capture in captures:
            cid = capture["capture_id"]
            key = (source["seller_uid"], cid)
            row = {
                "ledger_format_version": LEDGER_VERSION,
                "capture_id": cid,
                "seller_uid": source["seller_uid"],
                "listing_id": source["listing_id"],
                "capture_sha256": digest(capture),
                "content_sha256": digest({
                    "raw_record": capture["raw_record"],
                    "artifact_sha256": sorted(_artifact_hashes({
                        name: capture.get(name) for name in ("source_artifacts", "images")
                    })),
                }),
                "processing_fingerprint": processing_fingerprint,
                "state": "failed" if cid in failed else "succeeded",
                "history_path": capture.get("history_path"),
            }
            if key in ledger and ledger[key] != row:
                raise ValueError("Conflicting processing state for capture: " + cid)
            ledger[key] = row
    return [ledger[key] for key in sorted(ledger)]


def classify_capture(current, previous=None):
    """Explain why a capture needs processing under a frozen set of rules."""
    if previous is None:
        return "new"
    if current["capture_sha256"] != previous.get("capture_sha256"):
        return "capture_changed"
    if current["processing_fingerprint"] != previous.get("processing_fingerprint"):
        return "rules_changed"
    if previous.get("state") != "succeeded":
        return "retry"
    return "unchanged"


def compare_ledgers(current, previous):
    previous_by_key = {(row["seller_uid"], row["capture_id"]): row for row in previous}
    counts = Counter(classify_capture(row, previous_by_key.get((row["seller_uid"], row["capture_id"])))
                     for row in current)
    return {name: counts[name] for name in ("new", "capture_changed", "rules_changed", "retry", "unchanged")}
