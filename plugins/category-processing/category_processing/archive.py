"""Read and verify immutable raw captures without changing the archive."""

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ARCHIVE_VERSION = "category-research-raw-1"
IDENTITY_RULE = "Exact source key, source hostname, source product ID and nullable variant ID; never merge different sellers."


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def read_json(path):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(Path(path).read_bytes(), parse_constant=reject)


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inside(path, root):
    try:
        Path(path).relative_to(root)
        return True
    except ValueError:
        return False


def pointer_value(document, pointer):
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("Evidence pointers must be JSON pointers rooted at a capture.")
    value = document
    if pointer:
        for token in pointer[1:].split("/"):
            if re.search(r"~(?:[^01]|$)", token):
                raise ValueError("Invalid JSON pointer escape.")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError("Invalid JSON pointer array index.")
                value = value[int(token)]
            else:
                value = value[token]
    return value


def pointer_token(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def positive(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        result = float(number)
        return result if number.is_finite() and math.isfinite(result) and result > 0 else None
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        return None


def aware_time(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def normalized_price(price, quantity, base_quantity):
    values = [positive(item) for item in (price, quantity, base_quantity)]
    if any(item is None for item in values):
        return None
    result = float(Decimal(str(values[0])) / Decimal(str(values[1])) * Decimal(str(values[2])))
    rounded = round(result, 8) if math.isfinite(result) else None
    return rounded if rounded is not None and rounded > 0 else None


def source_identity(raw):
    identity = raw.get("identity") if isinstance(raw.get("identity"), dict) else {}
    source = raw.get("source_key")
    product, variant = identity.get("source_product_id"), identity.get("source_variant_id")
    if not isinstance(source, str) or not source.strip():
        return None
    if isinstance(product, bool) or not isinstance(product, (str, int)) or not str(product).strip():
        return None
    if variant is not None and (isinstance(variant, bool) or not isinstance(variant, (str, int))):
        return None
    try:
        hostname = urlsplit(raw.get("source_url") or "").hostname
    except (ValueError, TypeError, AttributeError):
        return None
    return (source, hostname, str(product), None if variant is None else str(variant)) if hostname else None


def seller_uid(raw, category, market, raw_listing_id):
    identity = source_identity(raw)
    basis = {"category": category, "market": market,
             "source_identity": list(identity) if identity else None}
    if identity is None:
        basis["unresolved_raw_listing_id"] = raw_listing_id
    return "seller-" + digest(basis)[:32]


def raw_study_slug(value):
    """Match collector directory names without changing study identity values."""
    if not isinstance(value, str):
        raise ValueError("Raw study identifiers must be strings.")
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not result:
        raise ValueError("Raw study identifiers must yield a nonempty directory name.")
    return result


def load_raw_archive(archive_root, category, market):
    root = Path(archive_root).expanduser().resolve()
    products = root / raw_study_slug(category) / raw_study_slug(market) / "products"
    if not products.is_dir() and all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value)
                                    for value in (category, market)):
        # Older/other producers may retain exact safe identifiers as directories.
        exact_products = root / category / market / "products"
        if exact_products.is_dir():
            products = exact_products
    if not products.is_dir():
        raise ValueError("Expected " + raw_study_slug(category) + "/" + raw_study_slug(market) + "/products under --archive-root.")
    inventory = sorted(products.glob("*/product.json"))
    result = {"root": root, "product_root": products, "inventory": inventory,
              "initial_locks": {str(path.relative_to(root)): (path.parent / ".import.lock").exists() for path in inventory},
              "listings": {}, "captures": {}, "latest": {}, "snapshots": {},
              "inputs": [], "errors": [], "unsupported": [], "product_folders": len(inventory)}

    def read(path):
        if not inside(path.resolve(), root) or path.is_symlink():
            raise ValueError("Archive reference escapes its root or uses a symlink.")
        data = path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        result["snapshots"][path] = checksum
        result["inputs"].append({"path": path.relative_to(root).as_posix(), "sha256": checksum})
        def reject(value):
            raise ValueError("Non-finite JSON value: " + value)
        return json.loads(data, parse_constant=reject)

    for path in inventory:
        listing = path.parent.name
        if (path.parent / ".import.lock").exists():
            result["errors"].append({"listing_id": listing, "code": "import_in_progress"})
            continue
        try:
            document = read(path)
            if not isinstance(document, dict):
                raise ValueError("Product index must be an object.")
            if document.get("archive_format_version") != ARCHIVE_VERSION:
                result["unsupported"].append({"listing_id": listing, "archive_format_version": document.get("archive_format_version"),
                                               "reason": "unsupported_archive_not_interpreted"})
                continue
            if document.get("product_id") != listing or document.get("category") != category or document.get("market") != market:
                raise ValueError("Product envelope does not match its source listing or study.")
            values = document.get("captures")
            if not isinstance(values, list) or not values:
                raise ValueError("Product has no captures.")
            lookup = {}
            for capture in values:
                if not isinstance(capture, dict) or not isinstance(capture.get("raw_record"), dict):
                    raise ValueError("Capture lacks an original raw record.")
                cid = capture.get("capture_id")
                if not isinstance(cid, str) or not cid or cid in lookup:
                    raise ValueError("Capture ID is missing or repeated.")
                if capture["raw_record"].get("product_id") != listing:
                    raise ValueError("Capture identity does not match source listing.")
                history = capture.get("history_path")
                if not isinstance(history, str) or Path(history).is_absolute():
                    raise ValueError("Capture lacks a relative immutable-history reference.")
                if read(root / history) != capture:
                    raise ValueError("Immutable history differs from indexed capture.")
                lookup[cid] = capture
            identities = {(source_identity(cap["raw_record"]), digest(cap["raw_record"].get("source_key"))) for cap in lookup.values()}
            if len(identities) > 1:
                raise ValueError("Seller-listing identity changes across captures; separate seller listings are required.")
            if document.get("latest_capture_id") not in lookup:
                raise ValueError("Latest capture ID does not resolve.")
            if (path.parent / ".import.lock").exists():
                raise ValueError("Product import is in progress.")
            result["listings"][listing] = document
            result["captures"][listing] = lookup
            result["latest"][listing] = document["latest_capture_id"]
        except (OSError, ValueError, TypeError, KeyError) as error:
            result["errors"].append({"listing_id": listing, "code": "invalid_archive_record", "reason": str(error)})
    result["inputs"] = sorted({item["path"]: item for item in result["inputs"]}.values(), key=lambda item: item["path"])
    return result


def confirm_raw_snapshot(archive):
    if sorted(archive["product_root"].glob("*/product.json")) != archive["inventory"]:
        raise RuntimeError("Raw archive listing inventory changed during the build.")
    locks = {str(path.relative_to(archive["root"])): (path.parent / ".import.lock").exists() for path in archive["inventory"]}
    if locks != archive["initial_locks"]:
        raise RuntimeError("Raw archive import locks changed during the build.")
    for path, checksum in archive["snapshots"].items():
        if not inside(path.resolve(), archive["root"]) or path.is_symlink() or sha256(path) != checksum:
            raise RuntimeError("Raw archive changed during the build.")


def deduplicate_archive(archive, category, market, source_roles):
    grouped = defaultdict(list)
    for listing in archive["listings"]:
        raw = archive["captures"][listing][archive["latest"][listing]]["raw_record"]
        grouped[seller_uid(raw, category, market, listing)].append(listing)
    rows, aliases, duplicate_groups = [], [], []
    for uid, members in sorted(grouped.items()):
        members.sort()
        canonical = members[0]
        merged = {}
        for member in members:
            for cid, capture in archive["captures"][member].items():
                if cid in merged and merged[cid] != capture:
                    raise ValueError("Conflicting capture ID across seller-listing aliases: " + cid)
                merged[cid] = capture
        latest = max(merged, key=lambda cid: (merged[cid].get("recorded_at", ""), cid))
        raw = merged[latest]["raw_record"]
        identity = raw.get("identity") if isinstance(raw.get("identity"), dict) else {}
        source = raw.get("source_key") if isinstance(raw.get("source_key"), str) and raw["source_key"].strip() else "unknown"
        seller = source_roles.get(source, {"source_role": "unknown", "retailer": source})
        row = {"listing_id": canonical, "seller_uid": uid, "source_listing_ids": members,
               "source_key": source, "source_role": seller["source_role"], "retailer": seller.get("retailer"),
               "brand": identity.get("brand") if isinstance(identity.get("brand"), str) else None,
               "name": identity.get("name"),
               "source_product_id": identity.get("source_product_id"), "source_variant_id": identity.get("source_variant_id"),
               "latest_capture_id": latest, "captures": [merged[cid] for cid in sorted(merged)]}
        rows.append(row)
        aliases.extend({"listing_id": canonical, "seller_uid": uid, "source_listing_id": member,
                        "source_key": source, "source_role": seller["source_role"],
                        "original_latest_capture_id": archive["latest"][member]} for member in members)
        if len(members) > 1:
            duplicate_groups.append({"listing_id": canonical, "seller_uid": uid, "source_listing_ids": members,
                                     "rule": "same_source_hostname_product_and_variant_identifiers"})
    return rows, aliases, {"scope": "within_selling_source_only", "rule": IDENTITY_RULE,
                          "duplicate_groups": duplicate_groups, "cross_source_merges": 0}
