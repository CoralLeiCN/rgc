"""Apply explicit user eligibility to Gold while retaining the complete parent."""

from pathlib import Path

from chocolate_gold import (
    IDENTITY_FIELDS,
    LAYER_VERSION,
    MANIFEST_VERSION,
    PARQUET_OPTIONS,
    PYARROW_VERSION,
    REPORT_VERSION,
    ROOT,
    SCHEMA_VERSION,
    TABLES,
    checked_path,
    checksum,
    copied_input_names,
    json_bytes,
    parquet_bytes,
    read_json,
    read_managed,
    read_parquet,
    reject_output_links,
    row_bytes,
    rows,
    training_schema,
    verified_gold,
    write_snapshot,
)

RULE_VERSION = "chocolate-gold-bulk-eligibility-1"
IMPLEMENTATION = ("scripts/chocolate_gold.py", "scripts/chocolate_gold_eligibility.py",
                  "scripts/make_chocolate_gold_eligible.py")
ELIGIBILITY_IDENTITY_FIELDS = (*IDENTITY_FIELDS, "source_gold_manifest_sha256", "eligibility_provenance")
PARENT = "inputs/parent-gold"


def eligibility_provenance(authorized_by, reason):
    if any(not isinstance(value, str) or not value.strip() for value in (authorized_by, reason)):
        raise ValueError("Gold eligibility requires an explicit user instruction and authorizing identity.")
    return {"model_eligible": True, "eligibility_basis": "user_instruction",
            "authorized_by": authorized_by, "reason": reason, "evidence_validation_performed": False}


def promote(values):
    return [{**row, "model_eligible": True, "exclusion_reasons": []} for row in values]


def mark_gold_eligible(gold_root, output, authorized_by, reason):
    """Write every candidate to both training views under a versioned override."""
    provenance = eligibility_provenance(authorized_by, reason)
    source = Path(gold_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    reject_output_links(output)
    if source == output.resolve() or source in output.resolve().parents:
        raise ValueError("Gold eligibility output must be separate from its source snapshot.")
    parent_bytes = checked_path(source, "manifest.json", "Gold").read_bytes()
    silver, silver_bytes, inputs = verified_gold(source)
    parent = read_json(parent_bytes)
    if parent.get("processing_rule_version") == RULE_VERSION:
        raise ValueError("Gold snapshot already has a bulk eligibility override; select its original parent.")
    parent_files = read_managed(source, parent["managed_files"], "Gold")
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    identity = {"manifest_format_version": MANIFEST_VERSION, "layer_version": LAYER_VERSION,
                "processing_rule_version": RULE_VERSION, "arrow_schema_version": SCHEMA_VERSION,
                "source_silver_manifest_sha256": checksum(silver_bytes),
                "source_gold_manifest_sha256": checksum(parent_bytes), "eligibility_provenance": provenance,
                "implementation_sha256": implementation, "pyarrow_version": PYARROW_VERSION,
                "parquet_options": PARQUET_OPTIONS}
    version = "gold-" + checksum(json_bytes(identity))[:24]
    candidates = rows(inputs["training-candidates.jsonl"])
    promoted = promote(candidates)
    files = {"inputs/" + name: inputs[name] for name in copied_input_names(silver)}
    files["inputs/silver-manifest.json"] = silver_bytes
    files.update({PARENT + "/" + name: data for name, data in parent_files.items()})
    files[PARENT + "/manifest.json"] = parent_bytes
    schema = training_schema(read_json(inputs["model-design.json"]))
    tables = {}
    for name, source_name in TABLES.items():
        data, decoded = parquet_bytes(promoted, schema)
        files[name] = data
        tables[name] = {"silver_input": source_name, "rows": len(decoded),
                        "logical_sha256": checksum(row_bytes(decoded))}
    counts = {"training_candidates": len(candidates), "eligible_model_inputs": len(candidates)}
    report = {"report_format_version": REPORT_VERSION, "layer_version": LAYER_VERSION,
              "processing_rule_version": RULE_VERSION, "dataset_version": version,
              "silver_dataset_version": silver["dataset_version"],
              "source_dataset_version": silver["source_dataset_version"], "schema_version": silver["schema_version"],
              "model_design_version": read_json(inputs["model-design.json"])["model_design_version"],
              "parent_gold_dataset_version": parent["dataset_version"], "eligibility_provenance": provenance,
              "status": "all_candidates_model_eligible", "gold_ready_for_loading": True,
              "counts": counts, "source_counts": {"training_candidates": len(candidates),
              "eligible_model_inputs": len(rows(inputs["model-inputs.jsonl"]))},
              "exclusion_counts": {}, "row_values_preserved": False, "eligibility_preserved": False,
              "analytical_values_preserved": True, "source_snapshot_preserved": True, "release_ready": False,
              "limitations": ["Eligibility records the explicit user instruction; missing values remain missing.",
                              "Models still validate actual inputs and regular-consumer-price-1 targets."]}
    files["report.json"] = json_bytes(report)
    manifest = {**identity, "dataset_version": version, "parent_gold_dataset_version": parent["dataset_version"],
                "silver_dataset_version": silver["dataset_version"], "source_dataset_version": silver["source_dataset_version"],
                "schema_version": silver["schema_version"], "contract_sha256": silver["contract_sha256"], "tables": tables,
                "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}}
    files["manifest.json"] = json_bytes(manifest)
    verified_gold(source)
    if (checked_path(source, "manifest.json", "Gold").read_bytes() != parent_bytes
            or {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION} != implementation):
        raise ValueError("Gold source or eligibility implementation changed during the build.")
    destination = write_snapshot(output, version, files)
    verified_gold(destination)
    return report, destination


def verified_eligible_gold(root, manifest_bytes):
    """Verify the retained parent and the exact permitted change before loading."""
    manifest = read_json(manifest_bytes)
    provenance = manifest.get("eligibility_provenance", {})
    identity = {name: manifest.get(name) for name in ELIGIBILITY_IDENTITY_FIELDS}
    if (manifest.get("manifest_format_version") != MANIFEST_VERSION or manifest.get("layer_version") != LAYER_VERSION
            or manifest.get("processing_rule_version") != RULE_VERSION
            or manifest.get("arrow_schema_version") != SCHEMA_VERSION
            or manifest.get("pyarrow_version") != PYARROW_VERSION or manifest.get("parquet_options") != PARQUET_OPTIONS
            or not isinstance(provenance, dict)
            or provenance != eligibility_provenance(provenance.get("authorized_by"), provenance.get("reason"))
            or manifest.get("dataset_version") != "gold-" + checksum(json_bytes(identity))[:24]):
        raise ValueError("Invalid Gold eligibility identity or explicit instruction provenance.")
    files = read_managed(root, manifest.get("managed_files"), "Gold")
    parent_bytes = files.get(PARENT + "/manifest.json", b"")
    if checksum(parent_bytes) != manifest.get("source_gold_manifest_sha256"):
        raise ValueError("Gold eligibility parent manifest checksum mismatch.")
    parent = read_json(parent_bytes)
    if parent.get("processing_rule_version") == RULE_VERSION:
        raise ValueError("Gold eligibility parent must be an original or reviewed snapshot.")
    silver, silver_bytes, inputs = verified_gold(root / PARENT)
    expected = {PARENT + "/" + name for name in parent["managed_files"]} | {PARENT + "/manifest.json",
                "inputs/silver-manifest.json", "report.json", *TABLES,
                *("inputs/" + name for name in copied_input_names(silver))}
    if set(files) != expected:
        raise ValueError("Gold eligibility managed file inventory disagrees with its parent.")
    if (manifest.get("parent_gold_dataset_version") != parent.get("dataset_version")
            or manifest.get("source_silver_manifest_sha256") != checksum(silver_bytes)
            or files["inputs/silver-manifest.json"] != silver_bytes
            or any(manifest.get(name) != parent.get(name) for name in
                   ("silver_dataset_version", "source_dataset_version", "schema_version", "contract_sha256"))
            or any(files["inputs/" + name] != inputs[name] for name in copied_input_names(silver))):
        raise ValueError("Gold eligibility changed original source provenance or auxiliary inputs.")
    promoted = promote(rows(inputs["training-candidates.jsonl"]))
    schema = training_schema(read_json(inputs["model-design.json"]))
    if set(manifest.get("tables", {})) != set(TABLES):
        raise ValueError("Gold eligibility table inventory is incomplete.")
    for name, source_name in TABLES.items():
        decoded = read_parquet(files[name], schema)
        metadata = {"silver_input": source_name, "rows": len(decoded), "logical_sha256": checksum(row_bytes(decoded))}
        if decoded != promoted or manifest["tables"][name] != metadata:
            raise ValueError("Gold eligibility changed analytical values or failed to promote every candidate.")
    report = read_json(files["report.json"])
    required_report = {"report_format_version": REPORT_VERSION, "layer_version": LAYER_VERSION,
                       "processing_rule_version": RULE_VERSION, "dataset_version": manifest["dataset_version"],
                       "silver_dataset_version": silver["dataset_version"], "source_dataset_version": silver["source_dataset_version"],
                       "schema_version": silver["schema_version"],
                       "model_design_version": read_json(inputs["model-design.json"])["model_design_version"],
                       "parent_gold_dataset_version": parent["dataset_version"], "eligibility_provenance": provenance,
                       "counts": {"training_candidates": len(promoted), "eligible_model_inputs": len(promoted)},
                       "source_counts": {"training_candidates": len(promoted), "eligible_model_inputs": len(rows(inputs["model-inputs.jsonl"]))},
                       "status": "all_candidates_model_eligible", "exclusion_counts": {}, "eligibility_preserved": False,
                       "row_values_preserved": False, "analytical_values_preserved": True, "source_snapshot_preserved": True,
                       "release_ready": False, "gold_ready_for_loading": True}
    if any(report.get(name) != value for name, value in required_report.items()):
        raise ValueError("Gold eligibility report disagrees with verified data.")
    for source_name in TABLES.values():
        inputs[source_name] = row_bytes(promoted)
    if checked_path(root, "manifest.json", "Gold").read_bytes() != manifest_bytes:
        raise ValueError("Gold manifest changed during verification.")
    return silver, silver_bytes, inputs
