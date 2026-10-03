"""Store one Gold training population and verify its immutable source projection."""

from pathlib import Path

from chocolate_gold import (
    CONTRACTS,
    IDENTITY_FIELDS,
    LAYER_VERSION,
    MANIFEST_VERSION,
    PARQUET_OPTIONS,
    PYARROW_VERSION,
    REPORT_VERSION,
    ROOT,
    ROW_FIELDS,
    SCHEMA_VERSION,
    checked_path,
    checksum,
    copied_input_names,
    json_bytes,
    parquet_bytes,
    read_json,
    read_managed,
    read_parquet,
    reject_output_links,
    review_provenance,
    row_bytes,
    rows,
    training_schema,
    validate_rows,
    verified_gold_storage,
    verified_silver,
    verify_tables,
    write_snapshot,
)

POPULATION_RULE = "chocolate-gold-population-1"
POPULATION_SCHEMA = "chocolate-gold-arrow-3"
REMOVED_FIELDS = {"model_eligible", "exclusion_reasons"}
POPULATION_FIELDS = ROW_FIELDS - REMOVED_FIELDS
IMPLEMENTATION = ("scripts/chocolate_gold.py", "scripts/chocolate_gold_population.py",
                  "scripts/build_chocolate_gold.py")
POPULATION_IDENTITY = (*IDENTITY_FIELDS, "source_gold_manifest_sha256", "review_provenance")
PARENT = "inputs/parent-gold"
SOURCE_ROWS = ("training-candidates.jsonl", "model-inputs.jsonl")
TABLE = "training-data.parquet"


def population_rows(values):
    """Remove selection metadata while preserving all analytical values and rows."""
    return [{name: value for name, value in row.items() if name not in REMOVED_FIELDS} for row in values]


def population_schema(design):
    schema = training_schema(design, SCHEMA_VERSION)
    import pyarrow as pa
    return pa.schema([field for field in schema if field.name not in REMOVED_FIELDS],
                     metadata={b"gold_arrow_schema_version": POPULATION_SCHEMA.encode()})


def validate_population(values, design, silver):
    # Validate representation without a row selection requirement.
    for row in values:
        if not isinstance(row, dict) or set(row) != POPULATION_FIELDS:
            raise ValueError("Unexpected or missing Gold population fields.")
    validate_rows(values, design, silver, selection_metadata=False)


def table_metadata(values):
    return {"source_input": "training-candidates.jsonl", "rows": len(values),
            "logical_sha256": checksum(row_bytes(values))}


def population_report(manifest, silver, design, values):
    return {"report_format_version": REPORT_VERSION, "layer_version": LAYER_VERSION,
            "processing_rule_version": POPULATION_RULE, "dataset_version": manifest["dataset_version"],
            "silver_dataset_version": silver["dataset_version"],
            "source_dataset_version": silver["source_dataset_version"], "schema_version": silver["schema_version"],
            "model_design_version": design["model_design_version"], "status": "complete_training_population",
            "gold_ready_for_loading": True, "counts": {"training_rows": len(values)},
            "analytical_values_preserved": True, "source_snapshot_preserved": True, "release_ready": False,
            "review_provenance": manifest.get("review_provenance"),
            "limitations": ["Every Gold row belongs to the training population; actual model inputs must still be valid.",
                            "Missing targets, quantities and identity values remain missing.",
                            "Source contracts and price observations retain their original evidence and study basis."]}


def build_population(source_root, output, *, input_kind, review=None):
    source = Path(source_root).expanduser().resolve()
    output = Path(output).expanduser().absolute()
    reject_output_links(output)
    if source == output.resolve() or source in output.resolve().parents or (input_kind == "silver" and output.resolve() in source.parents):
        raise ValueError("Gold output must be separate from its source snapshot (no overlap).")
    parent_bytes = checked_path(source, "manifest.json", input_kind.title()).read_bytes()
    parent = read_json(parent_bytes)
    parent_files = {}
    if input_kind == "silver":
        silver, silver_bytes, inputs = verified_silver(source)
        source_rows = {name: inputs[name] for name in SOURCE_ROWS}
        verify_tables(*(rows(source_rows[name]) for name in SOURCE_ROWS), read_json(inputs["model-design.json"]),
                      silver, read_json(inputs["quality-report.json"]))
        values = population_rows(rows(source_rows["training-candidates.jsonl"]))
    elif input_kind == "gold":
        if parent.get("processing_rule_version") == POPULATION_RULE:
            silver, silver_bytes, inputs = verified_population(source)
            source_rows = {name: (source / ("inputs/source-" + name)).read_bytes() for name in SOURCE_ROWS}
        else:
            silver, silver_bytes, inputs = verified_gold_storage(source)
            source_rows = {name: inputs[name] for name in SOURCE_ROWS}
        values = population_rows(rows(inputs["training-candidates.jsonl"]))
        parent_files = read_managed(source, parent["managed_files"], "Gold")
        if review is None:
            review = parent.get("review_provenance")
    else:
        raise ValueError("Gold population source must be Silver or Gold.")
    if review is not None and review != review_provenance(review.get("reviewed_by"), review.get("reason")):
        raise ValueError("Invalid Gold population review provenance.")
    design = read_json(inputs["model-design.json"])
    validate_population(values, design, silver)
    implementation = {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION}
    identity = {"manifest_format_version": MANIFEST_VERSION, "layer_version": LAYER_VERSION,
                "processing_rule_version": POPULATION_RULE, "arrow_schema_version": POPULATION_SCHEMA,
                "source_silver_manifest_sha256": checksum(silver_bytes),
                "source_gold_manifest_sha256": checksum(parent_bytes) if input_kind == "gold" else None,
                "review_provenance": review, "implementation_sha256": implementation,
                "pyarrow_version": PYARROW_VERSION, "parquet_options": PARQUET_OPTIONS}
    version = "gold-" + checksum(json_bytes(identity))[:24]
    files = {"inputs/" + name: inputs[name] for name in copied_input_names(silver)}
    files["inputs/silver-manifest.json"] = silver_bytes
    files.update({"inputs/source-" + name: data for name, data in source_rows.items()})
    if input_kind == "gold":
        files.update({PARENT + "/" + name: data for name, data in parent_files.items()})
        files[PARENT + "/manifest.json"] = parent_bytes
    data, decoded = parquet_bytes(values, population_schema(design))
    files[TABLE] = data
    manifest = {**identity, "dataset_version": version, "silver_dataset_version": silver["dataset_version"],
                "source_dataset_version": silver["source_dataset_version"], "schema_version": silver["schema_version"],
                "contract_sha256": silver["contract_sha256"], "tables": {TABLE: table_metadata(decoded)}}
    report = population_report(manifest, silver, design, decoded)
    files["report.json"] = json_bytes(report)
    manifest["managed_files"] = {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}
    files["manifest.json"] = json_bytes(manifest)
    if input_kind == "silver":
        verified_silver(source)
    elif parent.get("processing_rule_version") == POPULATION_RULE:
        verified_population(source)
    else:
        verified_gold_storage(source)
    if (checked_path(source, "manifest.json", input_kind.title()).read_bytes() != parent_bytes
            or {name: checksum((ROOT / name).read_bytes()) for name in IMPLEMENTATION} != implementation):
        raise ValueError("Gold source or population implementation changed during the build.")
    destination = write_snapshot(output, version, files)
    verified_population(destination)
    return report, destination


def verified_population(root):
    root = Path(root).expanduser().resolve()
    manifest_bytes = checked_path(root, "manifest.json", "Gold").read_bytes()
    manifest = read_json(manifest_bytes)
    identity = {name: manifest.get(name) for name in POPULATION_IDENTITY}
    if (manifest.get("manifest_format_version") != MANIFEST_VERSION or manifest.get("layer_version") != LAYER_VERSION
            or manifest.get("processing_rule_version") != POPULATION_RULE
            or manifest.get("arrow_schema_version") != POPULATION_SCHEMA
            or manifest.get("pyarrow_version") != PYARROW_VERSION or manifest.get("parquet_options") != PARQUET_OPTIONS
            or manifest.get("dataset_version") != "gold-" + checksum(json_bytes(identity))[:24]):
        raise ValueError("Unsupported Gold population identity.")
    review = manifest.get("review_provenance")
    if review is not None and (not isinstance(review, dict)
                              or review != review_provenance(review.get("reviewed_by"), review.get("reason"))):
        raise ValueError("Invalid Gold population review provenance.")
    files = read_managed(root, manifest.get("managed_files"), "Gold")
    silver_bytes = files["inputs/silver-manifest.json"]
    silver = read_json(silver_bytes)
    if (checksum(silver_bytes) != manifest.get("source_silver_manifest_sha256")
            or silver.get("manifest_format_version") != "chocolate-silver-manifest-1"
            or any(manifest.get(name) != silver.get(name) for name in
                   ("source_dataset_version", "schema_version", "contract_sha256"))
            or manifest.get("silver_dataset_version") != silver.get("dataset_version")):
        raise ValueError("Gold population source provenance disagrees with its manifest.")
    inputs = {name: files["inputs/" + name] for name in copied_input_names(silver)}
    expected = {"inputs/" + name for name in inputs} | {"inputs/silver-manifest.json", TABLE, "report.json",
                                                      *("inputs/source-" + name for name in SOURCE_ROWS)}
    for name, data in inputs.items():
        if silver.get("managed_files", {}).get(name) != {"sha256": checksum(data), "byte_length": len(data)}:
            raise ValueError("Gold copied input differs from the Silver source: " + name)
        if name in CONTRACTS and silver.get("contract_sha256", {}).get(name) != checksum(data):
            raise ValueError("Gold copied contract differs from the Silver source: " + name)
    design = read_json(inputs["model-design.json"])
    if manifest.get("source_gold_manifest_sha256") is not None:
        parent_bytes = files[PARENT + "/manifest.json"]
        parent = read_json(parent_bytes)
        if checksum(parent_bytes) != manifest["source_gold_manifest_sha256"]:
            raise ValueError("Gold population parent manifest checksum mismatch.")
        if parent.get("processing_rule_version") == POPULATION_RULE:
            parent_source, parent_silver, parent_inputs = verified_population(root / PARENT)
        else:
            parent_source, parent_silver, parent_inputs = verified_gold_storage(root / PARENT)
        if (parent_source != silver or parent_silver != silver_bytes
                or any(inputs[name] != parent_inputs[name] for name in inputs)):
            raise ValueError("Gold population changed parent source provenance.")
        expected.update({PARENT + "/manifest.json", *(PARENT + "/" + name for name in parent["managed_files"])})
        original = population_rows(rows(parent_inputs["training-candidates.jsonl"]))
        for name in SOURCE_ROWS:
            parent_data = (root / PARENT / ("inputs/source-" + name)).read_bytes() if parent.get(
                "processing_rule_version") == POPULATION_RULE else parent_inputs[name]
            if files["inputs/source-" + name] != parent_data:
                raise ValueError("Gold population changed retained source rows.")
    else:
        for name in SOURCE_ROWS:
            data = files["inputs/source-" + name]
            if silver.get("managed_files", {}).get(name) != {"sha256": checksum(data), "byte_length": len(data)}:
                raise ValueError("Gold population source row checksum mismatch: " + name)
        candidates, selected = (rows(files["inputs/source-" + name]) for name in SOURCE_ROWS)
        verify_tables(candidates, selected, design, silver, read_json(inputs["quality-report.json"]))
        original = population_rows(candidates)
    if set(files) != expected or set(manifest.get("tables", {})) != {TABLE}:
        raise ValueError("Gold population file/table inventory is incomplete or adds unexpected inputs.")
    values = read_parquet(files[TABLE], population_schema(design))
    validate_population(values, design, silver)
    if manifest["tables"][TABLE] != table_metadata(values):
        raise ValueError("Gold logical row checksum mismatch: " + TABLE)
    if values != original:
        raise ValueError("Gold population changed analytical source values or omitted rows.")
    if read_json(files["report.json"]) != population_report(manifest, silver, design, values):
        raise ValueError("Gold population report disagrees with verified data.")
    inputs["training-candidates.jsonl"] = inputs["model-inputs.jsonl"] = row_bytes(values)
    if checked_path(root, "manifest.json", "Gold").read_bytes() != manifest_bytes:
        raise ValueError("Gold manifest changed during verification.")
    return silver, silver_bytes, inputs
