"""Publish immutable Parquet training tables and provenance while preserving source values."""

import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
LAYER_VERSION = "chocolate-gold-1"
MANIFEST_VERSION = "chocolate-gold-manifest-1"
REPORT_VERSION = "chocolate-gold-report-1"
RULE_VERSION = "chocolate-gold-pass-through-1"
SCHEMA_VERSION = "chocolate-gold-arrow-1"
REVIEW_RULE_VERSION = "chocolate-gold-bulk-review-1"
REVIEW_SCHEMA_VERSION = "chocolate-gold-arrow-2"
REVIEW_IMPLEMENTATION = ("scripts/chocolate_gold.py", "scripts/review_chocolate_gold.py")
REVIEW_FIELDS = ("review_status", "review_basis")
PYARROW_VERSION = "21.0.0"
CONTRACTS = ("profile.json", "source-mappings.json", "product.schema.json", "model-design.json")
COPIED_INPUTS = (*CONTRACTS, "quality-report.json", "prices.jsonl")
REQUIRED_SILVER_INPUTS = (*COPIED_INPUTS, "training-candidates.jsonl", "model-inputs.jsonl")
OPTIONAL_COPIED_INPUTS = ("family-mappings.json",)
TABLES = {"training-data.parquet": "training-candidates.jsonl", "model-inputs.parquet": "model-inputs.jsonl"}
IMPLEMENTATION = ("scripts/chocolate_gold.py", "scripts/build_chocolate_gold.py")
PARQUET_OPTIONS = {"compression": "zstd", "version": "2.6", "data_page_version": "1.0",
                   "use_dictionary": True, "write_statistics": True,
                   "use_compliant_nested_type": True, "row_group_size": 65536}
IDENTITY_FIELDS = ("manifest_format_version", "layer_version", "processing_rule_version", "arrow_schema_version",
                   "source_silver_manifest_sha256", "implementation_sha256", "pyarrow_version", "parquet_options")
REVIEW_IDENTITY_FIELDS = (*IDENTITY_FIELDS, "source_gold_manifest_sha256", "review_provenance")
STRING_FIELDS = ("observation_id", "listing_id", "variant_id", "family_id", "comparable_group",
                 "source_role", "dataset_version", "source_dataset_version", "schema_version")
TARGET_FIELDS = ("regular_price_per_100g_gbp", "log_regular_price_per_100g_gbp")
ROW_FIELDS = set(STRING_FIELDS) | {"model_eligible", "exclusion_reasons", "predictors", "target"}


def copied_input_names(manifest):
    """Preserve identity decisions when present, including historical snapshots."""
    managed = manifest.get("managed_files", {})
    return (*COPIED_INPUTS, *(name for name in OPTIONAL_COPIED_INPUTS
                             if name in managed or "inputs/" + name in managed))


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def read_json(data):
    def reject(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(data, parse_constant=reject)


def rows(data):
    return [read_json(line) for line in data.split(b"\n") if line.strip()]


def row_bytes(values):
    """Canonical logical values, independent of the original JSONL whitespace."""
    return b"".join((json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()
                    for row in values)


def arrow_runtime():
    # The standard-library pipeline and tests can import this module without Arrow.
    import pyarrow as pa
    import pyarrow.parquet as pq
    if pa.__version__ != PYARROW_VERSION:
        raise ValueError("Gold requires the pinned PyArrow runtime " + PYARROW_VERSION + ".")
    return pa, pq


def checked_path(root, name, layer):
    if not isinstance(name, str):
        raise ValueError(layer + " managed paths must be strings.")
    relative = Path(name)
    path = root / relative
    if (relative.is_absolute() or ".." in relative.parts
            or relative.as_posix() != name or name in ("", ".")
            or path.is_symlink() or root not in path.resolve().parents
            or any(parent.is_symlink() for parent in path.parents if parent != root and root in parent.parents)):
        raise ValueError(layer + " managed path escapes or links outside its snapshot: " + str(name))
    return path


def read_managed(root, managed, layer, retain=None):
    if not isinstance(managed, dict):
        raise ValueError(layer + " manifest has no managed files.")
    result = {}
    for name, metadata in managed.items():
        path = checked_path(root, name, layer)
        if (not isinstance(metadata, dict) or type(metadata.get("byte_length")) is not int
                or not isinstance(metadata.get("sha256"), str)):
            raise ValueError(layer + " file metadata is invalid: " + name)
        if retain is None or name in retain:
            data = path.read_bytes()
            byte_length, digest = len(data), checksum(data)
            result[name] = data
        else:
            # Silver also contains large capture/evidence tables. Verify them
            # without loading their full bytes into a training conversion.
            hasher = hashlib.sha256()
            byte_length = 0
            with path.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    hasher.update(block)
                    byte_length += len(block)
            digest = hasher.hexdigest()
        if byte_length != metadata["byte_length"] or digest != metadata["sha256"]:
            raise ValueError(layer + " checksum mismatch: " + name)
    return result


def verified_silver(root):
    """Verify every managed silver file before using any training data."""
    root = Path(root).expanduser().resolve()
    manifest_path = checked_path(root, "manifest.json", "Silver")
    manifest_bytes = manifest_path.read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("manifest_format_version") != "chocolate-silver-manifest-1":
        raise ValueError("Gold requires a combined chocolate silver snapshot.")
    managed = manifest.get("managed_files")
    if not isinstance(managed, dict) or not set(REQUIRED_SILVER_INPUTS) <= set(managed):
        raise ValueError("Silver manifest is missing required training inputs.")
    required = set(REQUIRED_SILVER_INPUTS) | set(copied_input_names(manifest))
    inputs = read_managed(root, managed, "Silver", retain=required)
    for name in CONTRACTS:
        if manifest.get("contract_sha256", {}).get(name) != checksum(inputs[name]):
            raise ValueError("Silver contract checksum mismatch: " + name)
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Silver manifest changed during verification.")
    return manifest, manifest_bytes, {name: inputs[name] for name in required}


def training_schema(design, schema_version=SCHEMA_VERSION):
    """Use explicit types even when all values or the entire table are missing."""
    pa, _ = arrow_runtime()
    predictor_fields = []
    predictors = design.get("predictors")
    if not isinstance(predictors, dict) or not predictors:
        raise ValueError("The copied model design must declare predictor types.")
    for name, specification in sorted(predictors.items()):
        kind = specification.get("type")
        if kind == "numeric":
            dtype = pa.float64()
        elif kind in ("categorical", "presence"):
            dtype = pa.string()
        else:
            raise ValueError("Unsupported gold predictor type: " + str(kind))
        predictor_fields.append(pa.field(name, dtype))
    fields = [pa.field(name, pa.string()) for name in STRING_FIELDS]
    fields.extend([pa.field("model_eligible", pa.bool_(), nullable=False),
                   pa.field("exclusion_reasons", pa.list_(pa.field("element", pa.string(), nullable=False)), nullable=False),
                   pa.field("predictors", pa.struct(predictor_fields), nullable=False),
                   pa.field("target", pa.struct([pa.field(name, pa.float64()) for name in TARGET_FIELDS]), nullable=False)])
    if schema_version == REVIEW_SCHEMA_VERSION:
        fields.extend(pa.field(name, pa.string(), nullable=False) for name in REVIEW_FIELDS)
    elif schema_version != SCHEMA_VERSION:
        raise ValueError("Unsupported gold Arrow schema version.")
    return pa.schema(fields, metadata={b"gold_arrow_schema_version": schema_version.encode()})


def check_fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Unexpected or missing gold " + label + " fields; refusing to discard or add values.")


def check_numeric(value, label):
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
        raise ValueError("Gold numeric value is unsupported: " + label)


def validate_rows(values, design, manifest, *, selection_metadata=True):
    """Validate representation and upstream versions, without reclassifying values."""
    predictors = design["predictors"]
    for row in values:
        expected = ROW_FIELDS if selection_metadata else ROW_FIELDS - {"model_eligible", "exclusion_reasons"}
        check_fields(row, expected, "row")
        check_fields(row["predictors"], predictors, "predictor")
        check_fields(row["target"], TARGET_FIELDS, "target")
        for name in STRING_FIELDS:
            if row[name] is not None and not isinstance(row[name], str):
                raise ValueError("Gold string value is unsupported: " + name)
        if selection_metadata and type(row["model_eligible"]) is not bool:
            raise ValueError("Gold eligibility must retain a silver boolean.")
        if selection_metadata and (not isinstance(row["exclusion_reasons"], list)
                                   or any(not isinstance(reason, str) for reason in row["exclusion_reasons"])):
            raise ValueError("Gold exclusion reasons must retain a silver string list.")
        for name, specification in predictors.items():
            value = row["predictors"][name]
            if specification["type"] == "numeric":
                check_numeric(value, name)
            elif value is not None and not isinstance(value, str):
                raise ValueError("Gold categorical value is unsupported: " + name)
        for name in TARGET_FIELDS:
            check_numeric(row["target"][name], name)
        for name in ("dataset_version", "source_dataset_version", "schema_version"):
            if row[name] != manifest.get(name):
                raise ValueError("Gold source row versions disagree with silver: " + name)


def verify_tables(candidates, eligible, design, manifest, quality):
    for values in (candidates, eligible):
        validate_rows(values, design, manifest)
    if [row for row in candidates if row["model_eligible"] is True] != eligible:
        raise ValueError("Model inputs differ from reviewed eligible silver candidates.")
    if (quality.get("dataset_version") != manifest.get("dataset_version")
            or design.get("schema_version") != manifest.get("schema_version")):
        raise ValueError("Silver quality/design versions disagree with its manifest.")
    for name, count in (("training_candidates", len(candidates)), ("eligible_model_inputs", len(eligible))):
        if quality.get("counts", {}).get(name) != count:
            raise ValueError("Silver quality counts disagree with its training tables: " + name)


def parquet_bytes(values, schema):
    pa, pq = arrow_runtime()
    table = pa.Table.from_pylist(values, schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, **PARQUET_OPTIONS)
    data = sink.getvalue().to_pybytes()
    decoded = read_parquet(data, schema)
    if decoded != values:
        raise ValueError("Parquet roundtrip changed silver training values.")
    return data, decoded


def read_parquet(data, schema):
    pa, pq = arrow_runtime()
    table = pq.ParquetFile(pa.BufferReader(data)).read()
    if not table.schema.equals(schema, check_metadata=True):
        raise ValueError("Gold Parquet schema differs from the copied model design.")
    return table.to_pylist()


def reject_output_links(path):
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Gold output must not use symlinked directories.")


def write_snapshot(output, version, files):
    """An identical replay verifies the snapshot; differing bytes never overwrite it."""
    reject_output_links(output)
    destination = output / version
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Gold destination must be an immutable directory.")
        actual = {path.relative_to(destination).as_posix() for path in destination.rglob("*")
                  if path.is_file() or path.is_symlink()}
        if (actual != set(files) or any(path.is_symlink() for path in destination.rglob("*"))
                or any((destination / name).read_bytes() != data for name, data in files.items())):
            raise ValueError("Existing gold snapshot differs; refusing to overwrite immutable training data.")
        return destination
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".gold-", dir=output) as temporary:
        staging = Path(temporary) / version
        staging.mkdir()
        for name, data in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        os.rename(staging, destination)
    return destination


def build_legacy_gold_dataset(silver_root, output):
    source = Path(silver_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    reject_output_links(output)
    resolved_output = output.resolve()
    if source == resolved_output or source in resolved_output.parents or resolved_output in source.parents:
        raise ValueError("Gold output must be separate from silver (no overlap).")
    manifest, manifest_bytes, inputs = verified_silver(source)
    design, quality = read_json(inputs["model-design.json"]), read_json(inputs["quality-report.json"])
    candidates, eligible = rows(inputs["training-candidates.jsonl"]), rows(inputs["model-inputs.jsonl"])
    verify_tables(candidates, eligible, design, manifest, quality)
    schema = training_schema(design)
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    identity = {"manifest_format_version": MANIFEST_VERSION, "layer_version": LAYER_VERSION,
                "processing_rule_version": RULE_VERSION, "arrow_schema_version": SCHEMA_VERSION,
                "source_silver_manifest_sha256": checksum(manifest_bytes),
                "implementation_sha256": implementation, "pyarrow_version": PYARROW_VERSION,
                "parquet_options": PARQUET_OPTIONS}
    version = "gold-" + checksum(json_bytes(identity))[:24]
    files = {"inputs/" + name: inputs[name] for name in copied_input_names(manifest)}
    files["inputs/silver-manifest.json"] = manifest_bytes
    table_metadata = {}
    for name, values in (("training-data.parquet", candidates), ("model-inputs.parquet", eligible)):
        data, decoded = parquet_bytes(values, schema)
        files[name] = data
        table_metadata[name] = {"silver_input": TABLES[name], "rows": len(decoded),
                                "logical_sha256": checksum(row_bytes(decoded))}
    report = {"report_format_version": REPORT_VERSION, "layer_version": LAYER_VERSION,
              "processing_rule_version": RULE_VERSION, "dataset_version": version,
              "silver_dataset_version": manifest["dataset_version"],
              "source_dataset_version": manifest["source_dataset_version"],
              "schema_version": manifest["schema_version"],
              "model_design_version": design["model_design_version"],
              "status": quality.get("status"), "gold_ready_for_loading": True,
              "counts": {"training_candidates": len(candidates), "eligible_model_inputs": len(eligible)},
              "exclusion_counts": dict(sorted(Counter(reason for row in candidates for reason in row["exclusion_reasons"]).items())),
              "row_values_preserved": True, "eligibility_preserved": True,
              "release_ready": False,
              "limitations": ["Gold currently changes storage only; silver values, missingness and eligibility are preserved.",
                              "Loadable candidate data does not establish reviewed training or model release readiness.",
                              "Original evidence references still resolve in the source silver dataset and raw archive."]}
    files["report.json"] = json_bytes(report)
    files["manifest.json"] = json_bytes({**identity, "dataset_version": version,
                                          "silver_dataset_version": manifest["dataset_version"],
                                          "source_dataset_version": manifest["source_dataset_version"],
                                          "schema_version": manifest["schema_version"],
                                          "contract_sha256": manifest["contract_sha256"], "tables": table_metadata,
                                          "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)}
                                                            for name, data in files.items()}})
    if (verified_silver(source)[1] != manifest_bytes
            or {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION} != implementation):
        raise ValueError("Silver snapshot or gold implementation changed during the build.")
    return report, write_snapshot(output, version, files)


def review_provenance(reviewed_by, reason):
    """Record the supplied authority without asserting evidence verification."""
    if any(not isinstance(value, str) or not value.strip() for value in (reviewed_by, reason)):
        raise ValueError("Gold bulk review requires a nonempty reviewed_by and explicit user-request reason.")
    return {"review_status": "reviewed", "review_basis": "user_instruction",
            "reviewed_by": reviewed_by, "reason": reason, "evidence_validation_performed": False}


def validate_gold_identity(manifest):
    rule = manifest.get("processing_rule_version")
    reviewed = rule == REVIEW_RULE_VERSION
    expected_schema = REVIEW_SCHEMA_VERSION if reviewed else SCHEMA_VERSION
    if (manifest.get("manifest_format_version") != MANIFEST_VERSION
            or manifest.get("layer_version") != LAYER_VERSION
            or rule not in (RULE_VERSION, REVIEW_RULE_VERSION)
            or manifest.get("arrow_schema_version") != expected_schema
            or manifest.get("pyarrow_version") != PYARROW_VERSION
            or manifest.get("parquet_options") != PARQUET_OPTIONS):
        raise ValueError("Unsupported gold snapshot contract.")
    if reviewed:
        provenance = manifest.get("review_provenance")
        if (not isinstance(provenance, dict)
                or provenance != review_provenance(provenance.get("reviewed_by"), provenance.get("reason"))):
            raise ValueError("Gold review provenance must record the explicit user instruction and no evidence validation.")
    identity = {name: manifest.get(name) for name in (REVIEW_IDENTITY_FIELDS if reviewed else IDENTITY_FIELDS)}
    if manifest.get("dataset_version") != "gold-" + checksum(json_bytes(identity))[:24]:
        raise ValueError("Gold content version differs from its manifest identity.")
    expected = {"inputs/" + name for name in copied_input_names(manifest)} | {"inputs/silver-manifest.json", "report.json", *TABLES}
    if reviewed:
        expected.add("inputs/parent-gold-manifest.json")
    if set(manifest.get("managed_files", {})) != expected:
        raise ValueError("Gold manifest is missing or adds unexpected managed inputs.")
    return reviewed


def validate_review_parent(manifest, parent_bytes):
    if checksum(parent_bytes) != manifest.get("source_gold_manifest_sha256"):
        raise ValueError("Gold parent manifest checksum mismatch.")
    parent = read_json(parent_bytes)
    validate_gold_identity(parent)
    for name in ("source_silver_manifest_sha256", "silver_dataset_version", "source_dataset_version",
                 "schema_version", "contract_sha256"):
        if parent.get(name) != manifest.get(name):
            raise ValueError("Gold review changed source provenance: " + name)
    if copied_input_names(parent) != copied_input_names(manifest):
        raise ValueError("Gold review changed copied identity mapping inputs.")
    for name in ("inputs/silver-manifest.json", *("inputs/" + name for name in copied_input_names(manifest))):
        if parent["managed_files"].get(name) != manifest["managed_files"].get(name):
            raise ValueError("Gold review changed copied source input: " + name)
    if set(parent.get("tables", {})) != set(TABLES):
        raise ValueError("Gold parent logical table metadata is incomplete.")
    return parent


def strip_review(values):
    result = []
    for row in values:
        check_fields(row, ROW_FIELDS | set(REVIEW_FIELDS), "reviewed row")
        if row["review_status"] != "reviewed" or row["review_basis"] != "user_instruction":
            raise ValueError("Gold bulk review rows require the user-instruction annotation.")
        result.append({name: value for name, value in row.items() if name not in REVIEW_FIELDS})
    return result


def mark_legacy_gold_reviewed(gold_root, output, reviewed_by, reason):
    """Create an immutable user-directed review annotation; keep eligibility intact."""
    provenance = review_provenance(reviewed_by, reason)
    source = Path(gold_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    reject_output_links(output)
    resolved_output = output.resolve()
    # The ordinary output is the source snapshot's containing directory. It is
    # safe to publish a sibling snapshot there, but never inside the source.
    if source == resolved_output or source in resolved_output.parents:
        raise ValueError("Gold review output must be separate from its source snapshot.")
    parent_bytes = checked_path(source, "manifest.json", "Gold").read_bytes()
    silver, silver_bytes, inputs = verified_gold_storage(source)
    parent = read_json(parent_bytes)
    if checked_path(source, "manifest.json", "Gold").read_bytes() != parent_bytes:
        raise ValueError("Gold source manifest changed during review.")
    design, quality = read_json(inputs["model-design.json"]), read_json(inputs["quality-report.json"])
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in REVIEW_IMPLEMENTATION}
    identity = {"manifest_format_version": MANIFEST_VERSION, "layer_version": LAYER_VERSION,
                "processing_rule_version": REVIEW_RULE_VERSION, "arrow_schema_version": REVIEW_SCHEMA_VERSION,
                "source_silver_manifest_sha256": checksum(silver_bytes), "source_gold_manifest_sha256": checksum(parent_bytes),
                "review_provenance": provenance, "implementation_sha256": implementation,
                "pyarrow_version": PYARROW_VERSION, "parquet_options": PARQUET_OPTIONS}
    version = "gold-" + checksum(json_bytes(identity))[:24]
    files = {"inputs/" + name: inputs[name] for name in copied_input_names(silver)}
    files["inputs/silver-manifest.json"] = silver_bytes
    files["inputs/parent-gold-manifest.json"] = parent_bytes
    tables, decoded_tables = {}, {}
    schema = training_schema(design, REVIEW_SCHEMA_VERSION)
    for name, source_name in TABLES.items():
        original = rows(inputs[source_name])
        annotated = [{**row, "review_status": "reviewed", "review_basis": "user_instruction"} for row in original]
        data, decoded = parquet_bytes(annotated, schema)
        if strip_review(decoded) != original:
            raise ValueError("Gold bulk review changed original row values.")
        files[name] = data
        decoded_tables[source_name] = original
        tables[name] = {"silver_input": source_name, "rows": len(decoded), "logical_sha256": checksum(row_bytes(decoded)),
                        "source_fields_logical_sha256": checksum(row_bytes(original)),
                        "parent_logical_sha256": parent["tables"][name]["logical_sha256"]}
    candidates, eligible = decoded_tables["training-candidates.jsonl"], decoded_tables["model-inputs.jsonl"]
    counts = {"training_candidates": len(candidates), "eligible_model_inputs": len(eligible)}
    report = {"report_format_version": REPORT_VERSION, "layer_version": LAYER_VERSION,
              "processing_rule_version": REVIEW_RULE_VERSION, "dataset_version": version,
              "silver_dataset_version": silver["dataset_version"], "source_dataset_version": silver["source_dataset_version"],
              "schema_version": silver["schema_version"], "model_design_version": design["model_design_version"],
              "parent_gold_dataset_version": parent["dataset_version"], "review_provenance": provenance,
              "status": quality.get("status"), "gold_ready_for_loading": True, "counts": counts,
              "reviewed_counts": counts.copy(),
              "exclusion_counts": dict(sorted(Counter(reason for row in candidates for reason in row["exclusion_reasons"]).items())),
              "row_values_preserved": True, "source_row_values_preserved": True, "eligibility_preserved": True,
              "release_ready": False,
              "limitations": ["All rows are annotated as reviewed solely on the recorded user instruction; evidence validation was not performed.",
                              "Existing source fields, missingness, eligibility and exclusions are unchanged; the annotation does not establish training eligibility.",
                              "Training loaders omit the additive annotation while retaining its Gold manifest provenance."]}
    files["report.json"] = json_bytes(report)
    files["manifest.json"] = json_bytes({**identity, "dataset_version": version,
                                         "parent_gold_dataset_version": parent["dataset_version"],
                                         "silver_dataset_version": silver["dataset_version"],
                                         "source_dataset_version": silver["source_dataset_version"], "schema_version": silver["schema_version"],
                                         "contract_sha256": silver["contract_sha256"], "tables": tables,
                                         "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}})
    if (checked_path(source, "manifest.json", "Gold").read_bytes() != parent_bytes
            or {name: checksum((ROOT / name).read_bytes()) for name in REVIEW_IMPLEMENTATION} != implementation):
        raise ValueError("Gold source or review implementation changed during the build.")
    # Recheck the source's managed data before publishing the new snapshot.
    verified_gold_storage(source)
    if checked_path(source, "manifest.json", "Gold").read_bytes() != parent_bytes:
        raise ValueError("Gold source manifest changed during review.")
    return report, write_snapshot(output, version, files)


def verified_gold_storage(root):
    """Return the original silver manifest and verified in-memory training inputs.

    Parquet logical hashes verify decoded typed values. Reconstructed JSONL is a
    loader interface, not a byte-identical copy of source JSONL; original hashes
    and evidence routing remain recorded in inputs/silver-manifest.json.
    User-directed review annotations are validated then omitted from returned
    trainer rows; their provenance remains in the immutable Gold manifest.
    """
    root = Path(root).expanduser().resolve()
    manifest_path = checked_path(root, "manifest.json", "Gold")
    manifest_bytes = manifest_path.read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("processing_rule_version") == "chocolate-gold-bulk-eligibility-1":
        from chocolate_gold_eligibility import verified_eligible_gold
        return verified_eligible_gold(root, manifest_bytes)
    reviewed = validate_gold_identity(manifest)
    files = read_managed(root, manifest["managed_files"], "Gold")
    parent = validate_review_parent(manifest, files["inputs/parent-gold-manifest.json"]) if reviewed else None
    if reviewed and manifest.get("parent_gold_dataset_version") != parent.get("dataset_version"):
        raise ValueError("Gold parent dataset version disagrees with its provenance.")
    source_bytes = files["inputs/silver-manifest.json"]
    source = read_json(source_bytes)
    if (checksum(source_bytes) != manifest.get("source_silver_manifest_sha256")
            or source.get("manifest_format_version") != "chocolate-silver-manifest-1"
            or manifest.get("silver_dataset_version") != source.get("dataset_version")
            or manifest.get("source_dataset_version") != source.get("source_dataset_version")
            or manifest.get("schema_version") != source.get("schema_version")
            or manifest.get("contract_sha256") != source.get("contract_sha256")):
        raise ValueError("Gold source silver provenance disagrees with its manifest.")
    if not set(REQUIRED_SILVER_INPUTS) <= set(source.get("managed_files", {})):
        raise ValueError("Gold source silver manifest is missing required training inputs.")
    if copied_input_names(source) != copied_input_names(manifest):
        raise ValueError("Gold copied identity mappings disagree with the silver source.")
    inputs = {name: files["inputs/" + name] for name in copied_input_names(source)}
    for name, data in inputs.items():
        metadata = source.get("managed_files", {}).get(name, {})
        if metadata.get("sha256") != checksum(data) or metadata.get("byte_length") != len(data):
            raise ValueError("Gold copied input differs from the silver source: " + name)
    for name in CONTRACTS:
        if source.get("contract_sha256", {}).get(name) != checksum(inputs[name]):
            raise ValueError("Gold copied contract differs from the silver source: " + name)
    design, quality = read_json(inputs["model-design.json"]), read_json(inputs["quality-report.json"])
    schema = training_schema(design, manifest["arrow_schema_version"])
    decoded_tables = {}
    if set(manifest.get("tables", {})) != set(TABLES):
        raise ValueError("Gold logical table metadata is incomplete.")
    for name, source_name in TABLES.items():
        decoded = read_parquet(files[name], schema)
        canonical = row_bytes(decoded)
        metadata = manifest["tables"][name]
        if (metadata.get("silver_input") != source_name or metadata.get("rows") != len(decoded)
                or metadata.get("logical_sha256") != checksum(canonical)):
            raise ValueError("Gold logical row checksum mismatch: " + name)
        if reviewed:
            decoded = strip_review(decoded)
            canonical = row_bytes(decoded)
            parent_table = parent["tables"][name]
            parent_original_hash = parent_table.get("source_fields_logical_sha256") if parent.get("processing_rule_version") == REVIEW_RULE_VERSION else parent_table.get("logical_sha256")
            if (metadata.get("source_fields_logical_sha256") != checksum(canonical)
                    or parent_original_hash != checksum(canonical)
                    or metadata.get("parent_logical_sha256") != parent_table.get("logical_sha256")
                    or parent_table.get("rows") != len(decoded) or parent_table.get("silver_input") != source_name):
                raise ValueError("Gold bulk review changed parent source row values: " + name)
        decoded_tables[source_name] = decoded
        inputs[source_name] = canonical
    verify_tables(decoded_tables["training-candidates.jsonl"], decoded_tables["model-inputs.jsonl"], design, source, quality)
    report = read_json(files["report.json"])
    expected_counts = {"training_candidates": len(decoded_tables["training-candidates.jsonl"]),
                       "eligible_model_inputs": len(decoded_tables["model-inputs.jsonl"])}
    exclusions = dict(sorted(Counter(reason for row in decoded_tables["training-candidates.jsonl"]
                                     for reason in row["exclusion_reasons"]).items()))
    if (report.get("report_format_version") != REPORT_VERSION or report.get("layer_version") != LAYER_VERSION
            or report.get("processing_rule_version") != manifest["processing_rule_version"]
            or report.get("counts") != expected_counts or report.get("dataset_version") != manifest.get("dataset_version")
            or report.get("silver_dataset_version") != source.get("dataset_version")
            or report.get("source_dataset_version") != source.get("source_dataset_version")
            or report.get("schema_version") != source.get("schema_version")
            or report.get("model_design_version") != design.get("model_design_version")
            or report.get("status") != quality.get("status") or report.get("exclusion_counts") != exclusions
            or report.get("gold_ready_for_loading") is not True or report.get("release_ready") is not False
            or report.get("eligibility_preserved") is not True or report.get("row_values_preserved") is not True):
        raise ValueError("Gold report disagrees with its verified training tables.")
    if reviewed and (report.get("review_provenance") != manifest.get("review_provenance")
                     or report.get("parent_gold_dataset_version") != parent.get("dataset_version")
                     or report.get("reviewed_counts") != expected_counts or report.get("source_row_values_preserved") is not True):
        raise ValueError("Gold review report disagrees with its annotation and parent provenance.")
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Gold manifest changed during verification.")
    return source, source_bytes, inputs


def build_gold_dataset(silver_root, output, *, model_design=None, relationships=None, offline=False):
    """Prepare standard Silver in Gold, or preserve a historical Silver handoff."""
    source = Path(silver_root)
    if ((source / "latest.json").is_file() and not (source / "manifest.json").is_file()
            or read_json((source / "manifest.json").read_bytes()).get("manifest_format_version") == "category-silver-manifest-2"):
        from chocolate_gold_standard import build_standard_gold
        return build_standard_gold(silver_root, output, model_design=model_design, relationships=relationships, offline=offline)
    from chocolate_gold_population import build_population
    return build_population(silver_root, output, input_kind="silver")


def verified_gold(root):
    """Verify immutable storage and expose every Gold row without selection flags."""
    from chocolate_gold_population import (
        POPULATION_RULE,
        population_rows,
        verified_population,
    )
    root = Path(root).expanduser().resolve()
    manifest = read_json(checked_path(root, "manifest.json", "Gold").read_bytes())
    if manifest.get("manifest_format_version") == "chocolate-gold-standard-2":
        from chocolate_gold_standard import verified_standard_gold
        return verified_standard_gold(root)
    if manifest.get("processing_rule_version") == POPULATION_RULE:
        return verified_population(root)
    source, source_bytes, inputs = verified_gold_storage(root)
    population = row_bytes(population_rows(rows(inputs["training-candidates.jsonl"])))
    # These aliases keep existing trainer interfaces usable with one population.
    inputs["training-candidates.jsonl"] = inputs["model-inputs.jsonl"] = population
    return source, source_bytes, inputs


def mark_gold_reviewed(gold_root, output, reviewed_by, reason):
    """Record an administrative review in a new population snapshot."""
    provenance = review_provenance(reviewed_by, reason)
    from chocolate_gold_population import build_population
    return build_population(gold_root, output, input_kind="gold", review=provenance)
