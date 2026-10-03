"""Build a separate, lossless Parquet wrapper for reviewed inferred Silver cells."""

import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from chocolate_gold import (
    PARQUET_OPTIONS,
    PYARROW_VERSION,
    REQUIRED_SILVER_INPUTS,
    arrow_runtime,
    checked_path,
    checksum,
    json_bytes,
    read_json,
    read_managed,
    row_bytes,
    verified_silver,
    write_snapshot,
)
from chocolate_gold import (
    build_legacy_gold_dataset as build_gold_dataset,
)
from chocolate_gold import (
    verified_gold_storage as verified_gold,
)

ROOT = Path(__file__).resolve().parents[1]
LAYER_VERSION = "chocolate-gold-inferred-1"
MANIFEST_VERSION = "chocolate-gold-inferred-manifest-1"
REPORT_VERSION = "chocolate-gold-inferred-report-1"
ARROW_SCHEMA_VERSION = "chocolate-gold-inferred-arrow-1"
IMPLEMENTATION = ("scripts/chocolate_gold_inferred.py", "scripts/build_chocolate_gold_inferred.py")
METADATA_FIELDS = ("listing_id", "source_key", "source_role", "silver_dataset_version", "source_dataset_version")
PRICE_BASIS_VERSION = "regular-consumer-price-1"


def _read_rows(data, label):
    result = []
    for number, line in enumerate(data.splitlines(), 1):
        if line.strip():
            try:
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError(f"{label} contains invalid JSON on line {number}.") from error
            if not isinstance(value, dict):
                raise ValueError(f"{label} rows must be JSON objects.")
            result.append(value)
    return result


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _product_schema(profile):
    pa, _ = arrow_runtime()
    fields = [pa.field(name, pa.string(), nullable=False) for name in METADATA_FIELDS]
    for name, specification in sorted(profile["attributes"].items()):
        kind = specification.get("type")
        if kind in ("enum", "string"):
            dtype = pa.string()
        elif kind == "number":
            dtype = pa.float64()
        elif kind == "integer":
            dtype = pa.int64()
        elif kind == "string_list":
            dtype = pa.list_(pa.field("element", pa.string()))
        else:
            raise ValueError("Unsupported profile type in inferred Gold: " + str(kind))
        fields.append(pa.field(name, dtype))
    fields.append(pa.field("record_json", pa.string(), nullable=False))
    return pa.schema(fields, metadata={b"gold_inferred_arrow_schema_version": ARROW_SCHEMA_VERSION.encode()})


def _typed_rows(products, profile):
    attribute_names = set(profile["attributes"])
    result = []
    unknown_counts = {name: 0 for name in attribute_names}
    for product in products:
        attributes = product.get("attributes")
        if not isinstance(attributes, dict) or set(attributes) != attribute_names:
            raise ValueError("Silver product attributes differ from the pinned profile.")
        row = {
            "listing_id": product["listing_id"],
            "source_key": product["source_key"],
            "source_role": product["source_role"],
            "silver_dataset_version": product["dataset_version"],
            "source_dataset_version": product["source_dataset_version"],
            "record_json": _canonical_json(product),
        }
        for name, specification in profile["attributes"].items():
            cell = attributes[name]
            if not isinstance(cell, dict) or "value" not in cell or "status" not in cell:
                raise ValueError("Silver attribute state is incomplete: " + name)
            value = cell["value"]
            kind = specification["type"]
            if cell["status"] == "unknown":
                unknown_counts[name] += 1
                if value is not None:
                    raise ValueError("Unknown Silver values must remain null: " + name)
            if value is not None:
                valid = (
                    isinstance(value, str) if kind in ("enum", "string")
                    else type(value) in (int, float) and math.isfinite(value) if kind == "number"
                    else type(value) is int if kind == "integer"
                    else isinstance(value, list) and all(isinstance(item, str) for item in value) if kind == "string_list"
                    else False
                )
                if not valid:
                    raise ValueError("Silver attribute value disagrees with its profile type: " + name)
            row[name] = value
        result.append(row)
    return result, unknown_counts


def _resolve(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Evidence pointer must be a JSON pointer.")
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _source_index(data):
    result = {}
    for source in _read_rows(data, "Silver source listings"):
        listing_id = source.get("listing_id")
        if not isinstance(listing_id, str) or listing_id in result:
            raise ValueError("Silver source listing IDs must be unique nonempty strings.")
        result[listing_id] = source
    return result


def _validate_provenance(provenance, silver_manifest_bytes, silver_manifest, decisions_bytes, decision_count=None):
    """Require provenance to bind this exact Silver snapshot and decision file."""
    if not isinstance(provenance, dict):
        raise ValueError("Inference provenance must be a JSON object.")
    if (provenance.get("source_silver_manifest_sha256") != checksum(silver_manifest_bytes)
            or provenance.get("source_silver_dataset_version") != silver_manifest.get("dataset_version")):
        raise ValueError("Inference provenance refers to a different or unidentified reviewed Silver snapshot.")
    expected_decisions_hash = checksum(decisions_bytes)
    audit_decisions = provenance.get("audit_files", {}).get("adoption/accepted-decisions.jsonl")
    input_decisions_hash = provenance.get("inputs_sha256", {}).get("adoption/accepted-decisions.jsonl")
    bound_hashes = []
    if audit_decisions is not None:
        if not isinstance(audit_decisions, dict):
            raise ValueError("Inference provenance accepted-decision audit record is malformed.")
        bound_hashes.append(audit_decisions.get("sha256"))
    if input_decisions_hash is not None:
        bound_hashes.append(input_decisions_hash)
    if not bound_hashes or any(value != expected_decisions_hash for value in bound_hashes):
        raise ValueError("Inference provenance must bind the exact accepted-decision file.")
    if decision_count is not None and provenance.get("accepted_attribute_cells") not in (None, decision_count):
        raise ValueError("Inference provenance accepted decision count disagrees with its file.")


def _validate_decisions(decisions, products, source_listings, profile, *, check_source_quotes):
    products_by_id = {product["listing_id"]: product for product in products}
    seen = set()
    for decision in decisions:
        listing_id, attribute = decision.get("listing_id"), decision.get("attribute")
        key = (listing_id, attribute)
        if key in seen:
            raise ValueError("Inferred decisions contain duplicate listing/attribute pairs.")
        seen.add(key)
        if attribute not in profile["attributes"] or listing_id not in products_by_id:
            raise ValueError("Inferred decision does not identify a Silver product attribute.")
        product = products_by_id[listing_id]
        cell = product["attributes"][attribute]
        if (cell.get("status") != "known" or cell.get("review_status") != "reviewed"
                or cell.get("value") != decision.get("value")
                or cell.get("unit") != decision.get("unit")
                or cell.get("scope") != decision.get("scope")
                or cell.get("qualifier") != decision.get("qualifier")):
            raise ValueError(f"Accepted inference disagrees with reviewed Silver cell: {listing_id} {attribute}.")
        refs = decision.get("evidence")
        capture_id = decision.get("capture_id")
        if not isinstance(refs, list) or not refs or not isinstance(capture_id, str):
            raise ValueError("Accepted inference is missing exact capture evidence.")
        silver_refs = {(ref.get("capture_id"), ref.get("pointer")) for ref in cell.get("evidence", [])}
        source = source_listings.get(listing_id)
        if check_source_quotes and source is None:
            raise ValueError("Accepted inference has no Silver source listing.")
        captures = {capture.get("capture_id"): capture for capture in source.get("captures", [])} if source else {}
        capture = captures.get(capture_id)
        if check_source_quotes and capture is None:
            raise ValueError("Accepted inference capture is absent from Silver source listings.")
        for ref in refs:
            pointer, quote = ref.get("pointer"), ref.get("quote")
            if (capture_id, pointer) not in silver_refs:
                raise ValueError("Accepted inference evidence is absent from the reviewed Silver cell.")
            if not isinstance(quote, str) or not quote:
                raise ValueError("Accepted inference quote must be nonempty source text.")
            if check_source_quotes:
                try:
                    leaf = _resolve(capture, pointer)
                except (KeyError, IndexError, TypeError, ValueError) as error:
                    raise ValueError("Accepted inference pointer does not resolve in Silver source listings.") from error
                if not isinstance(leaf, str) or quote not in leaf:
                    raise ValueError("Accepted inference quote is not in its cited Silver source capture.")
    return len(seen)


def _verify_silver_files(root):
    root = Path(root).expanduser().resolve()
    manifest, manifest_bytes, _ = verified_silver(root)
    names = set(REQUIRED_SILVER_INPUTS) | {"products.jsonl", "source-listings.jsonl"}
    retained = read_managed(root, manifest["managed_files"], "Silver", retain=names)
    if checked_path(root, "manifest.json", "Silver").read_bytes() != manifest_bytes:
        raise ValueError("Silver manifest changed during inferred Gold verification.")
    return root, manifest, manifest_bytes, retained


def _parquet_bytes(rows, schema):
    pa, pq = arrow_runtime()
    table = pa.Table.from_pylist(rows, schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, **PARQUET_OPTIONS)
    data = sink.getvalue().to_pybytes()
    decoded = pq.ParquetFile(pa.BufferReader(data)).read()
    if not decoded.schema.equals(schema, check_metadata=True) or decoded.to_pylist() != rows:
        raise ValueError("Inferred product Parquet roundtrip changed source values.")
    return data, decoded.to_pylist()


def _implementation_hashes():
    return {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}


def _input_file(path, label):
    path = Path(path).expanduser()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(label + " must not follow symlinked paths.")
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(label + " must be a regular file.")
    return resolved


def build_gold_inferred_dataset(silver_root, output, decisions_path, provenance_path):
    """Build an immutable inferred-product wrapper with an ordinary Gold child."""
    source, silver_manifest, silver_manifest_bytes, silver_inputs = _verify_silver_files(silver_root)
    output = Path(output).expanduser().absolute()
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError("Inferred Gold output must not use symlinked directories.")
    resolved_output = output.resolve()
    if source == resolved_output or source in resolved_output.parents or resolved_output in source.parents:
        raise ValueError("Inferred Gold output must be separate from Silver.")
    decisions_path = _input_file(decisions_path, "Accepted decisions")
    provenance_path = _input_file(provenance_path, "Inference provenance")
    decisions_bytes = decisions_path.read_bytes()
    provenance_bytes = provenance_path.read_bytes()
    provenance = read_json(provenance_bytes)
    products = _read_rows(silver_inputs["products.jsonl"], "Silver products")
    source_listings = _source_index(silver_inputs["source-listings.jsonl"])
    profile = read_json(silver_inputs["profile.json"])
    if profile.get("attribute_count") != len(profile.get("attributes", {})):
        raise ValueError("Silver profile attribute count is inconsistent.")
    if len({product.get("listing_id") for product in products}) != len(products):
        raise ValueError("Silver product listing IDs must be unique.")
    for product in products:
        if (product.get("dataset_version") != silver_manifest.get("dataset_version")
                or product.get("source_dataset_version") != silver_manifest.get("source_dataset_version")):
            raise ValueError("Silver product version fields disagree with the source manifest.")
    decisions = _read_rows(decisions_bytes, "Accepted inference decisions")
    _validate_provenance(provenance, silver_manifest_bytes, silver_manifest, decisions_bytes, len(decisions))
    accepted_count = _validate_decisions(decisions, products, source_listings, profile, check_source_quotes=True)
    product_rows, unknown_counts = _typed_rows(products, profile)
    schema = _product_schema(profile)
    products_parquet, decoded_rows = _parquet_bytes(product_rows, schema)

    candidates = _read_rows(silver_inputs["training-candidates.jsonl"], "Silver training candidates")
    eligible = _read_rows(silver_inputs["model-inputs.jsonl"], "Silver model inputs")
    design = read_json(silver_inputs["model-design.json"])
    target = design.get("target", {})
    if target.get("price_basis_contract_version") != PRICE_BASIS_VERSION:
        raise ValueError("Inferred Gold requires the regular-consumer-price-1 contract.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".gold-inferred-", dir=output.parent) as temporary:
        _, child_root = build_gold_dataset(source, Path(temporary) / "training")
        child_manifest_bytes = checked_path(child_root, "manifest.json", "Gold").read_bytes()
        child_manifest = read_json(child_manifest_bytes)
        verified_child_silver, _, child_inputs = verified_gold(child_root)
        if (checksum(silver_manifest_bytes) != child_manifest.get("source_silver_manifest_sha256")
                or verified_child_silver.get("dataset_version") != silver_manifest.get("dataset_version")
                or child_inputs.get("prices.jsonl") != silver_inputs.get("prices.jsonl")):
            raise ValueError("Nested Gold child changed its Silver, price, or target provenance.")
        if (_read_rows(child_inputs["model-inputs.jsonl"], "Nested Gold model inputs") != eligible
                or child_manifest.get("tables", {}).get("model-inputs.parquet", {}).get("rows") != len(eligible)):
            raise ValueError("Nested Gold child changed source eligibility.")
        files = {
            "products.parquet": products_parquet,
            "inputs/silver-manifest.json": silver_manifest_bytes,
            "inference/accepted-decisions.jsonl": decisions_bytes,
            "inference/provenance.json": provenance_bytes,
        }
        for path in child_root.rglob("*"):
            if path.is_file():
                files["training/" + path.relative_to(child_root).as_posix()] = path.read_bytes()

    source_managed = silver_manifest["managed_files"]
    implementation = _implementation_hashes()
    identity = {
        "manifest_format_version": MANIFEST_VERSION,
        "layer_version": LAYER_VERSION,
        "arrow_schema_version": ARROW_SCHEMA_VERSION,
        "source_silver_manifest_sha256": checksum(silver_manifest_bytes),
        "source_products_sha256": source_managed["products.jsonl"]["sha256"],
        "source_products_logical_sha256": checksum(row_bytes(products)),
        "source_listings_sha256": source_managed["source-listings.jsonl"]["sha256"],
        "accepted_decisions_sha256": checksum(decisions_bytes),
        "provenance_sha256": checksum(provenance_bytes),
        "training_gold_manifest_sha256": checksum(child_manifest_bytes),
        "implementation_sha256": implementation,
        "pyarrow_version": PYARROW_VERSION,
        "parquet_options": PARQUET_OPTIONS,
    }
    version = "gold-inferred-" + checksum(json_bytes(identity))[:24]
    report = {
        "report_format_version": REPORT_VERSION,
        "dataset_version": version,
        "layer_version": LAYER_VERSION,
        "source_silver_dataset_version": silver_manifest["dataset_version"],
        "source_dataset_version": silver_manifest["source_dataset_version"],
        "training_gold_dataset_version": child_manifest["dataset_version"],
        "counts": {
            "products": len(products),
            "attributes_per_product": len(profile["attributes"]),
            "accepted_inference_decisions": accepted_count,
            "training_candidates": len(candidates),
            "eligible_model_inputs": len(eligible),
            "price_observations": len(_read_rows(silver_inputs["prices.jsonl"], "Silver prices")),
        },
        "unknown_cells_by_attribute": dict(sorted(unknown_counts.items())),
        "regular_price_basis_contract_version": PRICE_BASIS_VERSION,
        "eligibility_preserved": True,
        "unknown_values_preserved": True,
        "record_json_is_authoritative": True,
        "release_ready": False,
    }
    files["report.json"] = json_bytes(report)
    manifest = {
        **identity,
        "dataset_version": version,
        "training_gold_dataset_version": child_manifest["dataset_version"],
        "source_silver_dataset_version": silver_manifest["dataset_version"],
        "source_dataset_version": silver_manifest["source_dataset_version"],
        "product_count": len(products),
        "attribute_count": len(profile["attributes"]),
        "accepted_inference_decision_count": accepted_count,
        "unknown_values_by_attribute": dict(sorted(unknown_counts.items())),
        "training_gold_root": "training",
        "managed_files": {
            name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()
        },
    }
    files["manifest.json"] = json_bytes(manifest)
    if (checked_path(source, "manifest.json", "Silver").read_bytes() != silver_manifest_bytes
            or _implementation_hashes() != implementation):
        raise ValueError("Silver or inferred Gold implementation changed during build.")
    destination = write_snapshot(output, version, files)
    verified_gold_inferred(destination, source)
    return report, destination


def verified_gold_inferred(root, silver_root=None):
    """Verify bundle bytes, product Parquet and its ordinary trainer-compatible Gold child."""
    root = Path(root).expanduser().resolve()
    manifest_path = checked_path(root, "manifest.json", "Inferred Gold")
    manifest_bytes = manifest_path.read_bytes()
    manifest = read_json(manifest_bytes)
    if (manifest.get("manifest_format_version") != MANIFEST_VERSION
            or manifest.get("layer_version") != LAYER_VERSION
            or manifest.get("arrow_schema_version") != ARROW_SCHEMA_VERSION
            or manifest.get("pyarrow_version") != PYARROW_VERSION
            or manifest.get("parquet_options") != PARQUET_OPTIONS):
        raise ValueError("Unsupported inferred Gold contract.")
    identity_fields = (
        "manifest_format_version", "layer_version", "arrow_schema_version", "source_silver_manifest_sha256",
        "source_products_sha256", "source_listings_sha256", "accepted_decisions_sha256", "provenance_sha256",
        "source_products_logical_sha256", "training_gold_manifest_sha256", "implementation_sha256",
        "pyarrow_version", "parquet_options",
    )
    identity = {key: manifest.get(key) for key in identity_fields}
    if manifest.get("dataset_version") != "gold-inferred-" + checksum(json_bytes(identity))[:24]:
        raise ValueError("Inferred Gold version differs from manifest identity.")
    implementation = manifest.get("implementation_sha256")
    if (not isinstance(implementation, dict) or set(implementation) != set(IMPLEMENTATION)
            or any(not isinstance(value, str) or len(value) != 64 for value in implementation.values())):
        raise ValueError("Inferred Gold implementation provenance is malformed.")
    managed = manifest.get("managed_files")
    if not isinstance(managed, dict):
        raise ValueError("Inferred Gold managed-file manifest is missing.")
    files = read_managed(root, managed, "Inferred Gold")
    if set(files) != set(managed):
        raise ValueError("Inferred Gold managed files could not be read.")
    training_root = root / manifest.get("training_gold_root", "training")
    if not training_root.is_dir():
        raise ValueError("Inferred Gold has no nested conventional Gold child.")
    child_manifest_bytes = checked_path(training_root, "manifest.json", "Gold").read_bytes()
    if checksum(child_manifest_bytes) != manifest.get("training_gold_manifest_sha256"):
        raise ValueError("Inferred Gold child manifest checksum mismatch.")
    child_manifest = read_json(child_manifest_bytes)
    if child_manifest.get("dataset_version") != manifest.get("training_gold_dataset_version"):
        raise ValueError("Inferred Gold child version disagrees with its manifest.")
    expected_files = {
        "products.parquet", "inputs/silver-manifest.json", "inference/accepted-decisions.jsonl",
        "inference/provenance.json", "report.json",
    }
    expected_files.update("training/" + name for name in (*child_manifest.get("managed_files", {}), "manifest.json"))
    if set(managed) != expected_files:
        raise ValueError("Inferred Gold managed file set differs from the wrapper and child contracts.")
    _, _, training_inputs = verified_gold(training_root)
    source_silver_manifest_bytes = files["inputs/silver-manifest.json"]
    source_silver_manifest = read_json(source_silver_manifest_bytes)
    if (checksum(source_silver_manifest_bytes) != manifest["source_silver_manifest_sha256"]
            or checksum(source_silver_manifest_bytes) != read_json(child_manifest_bytes).get("source_silver_manifest_sha256")
            or source_silver_manifest.get("dataset_version") != manifest.get("source_silver_dataset_version")
            or source_silver_manifest.get("managed_files", {}).get("products.jsonl", {}).get("sha256") != manifest.get("source_products_sha256")
            or source_silver_manifest.get("managed_files", {}).get("source-listings.jsonl", {}).get("sha256") != manifest.get("source_listings_sha256")
            or training_inputs.get("prices.jsonl") is None
            or source_silver_manifest.get("managed_files", {}).get("prices.jsonl", {}).get("sha256") != checksum(training_inputs["prices.jsonl"])):
        raise ValueError("Inferred Gold source or regular-price provenance mismatch.")
    design = read_json(training_inputs["model-design.json"])
    if design.get("target", {}).get("price_basis_contract_version") != PRICE_BASIS_VERSION:
        raise ValueError("Inferred Gold lost the regular-consumer-price-1 contract.")
    candidates = _read_rows(training_inputs["training-candidates.jsonl"], "Nested Gold candidates")
    eligible_rows = _read_rows(training_inputs["model-inputs.jsonl"], "Nested Gold model inputs")

    profile = read_json(training_inputs["profile.json"])
    schema = _product_schema(profile)
    pa, pq = arrow_runtime()
    table = pq.ParquetFile(pa.BufferReader(files["products.parquet"])).read()
    if not table.schema.equals(schema, check_metadata=True):
        raise ValueError("Inferred products Parquet schema mismatch.")
    product_rows = table.to_pylist()
    records = []
    for row in product_rows:
        product = read_json(row["record_json"].encode())
        records.append(product)
        source_fields = {
            "listing_id": "listing_id", "source_key": "source_key", "source_role": "source_role",
            "silver_dataset_version": "dataset_version", "source_dataset_version": "source_dataset_version",
        }
        if any(row.get(column) != product.get(field) for column, field in source_fields.items()):
            raise ValueError("Typed inferred product metadata differs from its full record.")
        for attribute in profile["attributes"]:
            if row.get(attribute) != product["attributes"][attribute]["value"]:
                raise ValueError("Typed inferred attribute differs from its full record: " + attribute)
    if len(records) != manifest.get("product_count") or len(profile["attributes"]) != manifest.get("attribute_count"):
        raise ValueError("Inferred Gold product or attribute count mismatch.")
    if checksum(row_bytes(records)) != manifest.get("source_products_logical_sha256"):
        raise ValueError("Inferred Gold product logical checksum mismatch.")
    unknown_counts = {name: 0 for name in profile["attributes"]}
    for product in records:
        for name, cell in product["attributes"].items():
            if cell.get("status") == "unknown":
                unknown_counts[name] += 1
                if cell.get("value") is not None:
                    raise ValueError("Inferred Gold changed an unknown value from null: " + name)
    if unknown_counts != manifest.get("unknown_values_by_attribute"):
        raise ValueError("Inferred Gold unknown-cell counts disagree with its manifest.")
    decisions = _read_rows(files["inference/accepted-decisions.jsonl"], "Accepted inference decisions")
    provenance = read_json(files["inference/provenance.json"])
    if checksum(files["inference/accepted-decisions.jsonl"]) != manifest.get("accepted_decisions_sha256") or checksum(files["inference/provenance.json"]) != manifest.get("provenance_sha256"):
        raise ValueError("Inferred Gold inference input checksum mismatch.")
    _validate_provenance(
        provenance,
        source_silver_manifest_bytes,
        source_silver_manifest,
        files["inference/accepted-decisions.jsonl"],
        len(decisions),
    )
    source_listings = None
    if silver_root is not None:
        _, silver_manifest, silver_manifest_bytes, silver_inputs = _verify_silver_files(silver_root)
        if (checksum(silver_manifest_bytes) != manifest["source_silver_manifest_sha256"]
                or checksum(silver_inputs["products.jsonl"]) != manifest["source_products_sha256"]
                or checksum(silver_inputs["source-listings.jsonl"]) != manifest["source_listings_sha256"]):
            raise ValueError("Inferred Gold does not match the supplied Silver source snapshot.")
        source_products = _read_rows(silver_inputs["products.jsonl"], "Silver products")
        if source_products != records:
            raise ValueError("Inferred Gold product records differ from source Silver.")
        source_listings = _source_index(silver_inputs["source-listings.jsonl"])
    _validate_decisions(decisions, records, source_listings or {}, profile, check_source_quotes=source_listings is not None)
    report = read_json(files["report.json"])
    if (report.get("dataset_version") != manifest.get("dataset_version")
            or report.get("counts", {}).get("products") != len(records)
            or report.get("counts", {}).get("accepted_inference_decisions") != len(decisions)
            or report.get("counts", {}).get("training_candidates") != len(candidates)
            or report.get("counts", {}).get("eligible_model_inputs") != len(eligible_rows)
            or report.get("counts", {}).get("price_observations") != len(_read_rows(training_inputs["prices.jsonl"], "Nested Gold prices"))
            or report.get("regular_price_basis_contract_version") != PRICE_BASIS_VERSION
            or report.get("unknown_values_preserved") is not True
            or report.get("eligibility_preserved") is not True):
        raise ValueError("Inferred Gold report disagrees with its preserved data.")
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Inferred Gold manifest changed during verification.")
    return manifest, records, training_root
