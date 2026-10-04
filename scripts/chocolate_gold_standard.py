"""Prepare chocolate study inputs from standard Silver and freeze them in Parquet."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from chocolate_current_price import LIMITATIONS
from chocolate_gold import (
    PARQUET_OPTIONS,
    PYARROW_VERSION,
    arrow_runtime,
    checksum,
    json_bytes,
    parquet_bytes,
    read_json,
    read_managed,
    read_parquet,
    row_bytes,
    rows,
    write_snapshot,
)
from dataset_contracts import resolve_standard_gold_contract_root

# dataset_contracts initializes the independently installable processing package path.
# isort: split
from category_processing.gold_preparation import prepare_gold, prepare_values
from category_processing.silver_snapshot import no_links, verified_snapshot

FORMAT = "chocolate-gold-standard-2"


def study_design(source, silver):
    design = deepcopy(source)
    if design.get("preparation_contract_version") == FORMAT:
        if (design.get("schema_version") != silver["schema_version"]
                or design.get("model_design_version") != design.get("source_model_design_version", "") + ".silver-2"):
            raise ValueError("The versioned Gold study contract does not match this Silver schema.")
        return design
    design["source_model_design_version"] = design["model_design_version"]
    design["source_schema_version"] = design["schema_version"]
    design["model_design_version"] += ".silver-2"
    design["schema_version"] = silver["schema_version"]
    design["preparation_contract_version"] = FORMAT
    design["comparison_rule"] = "chocolate_name_group-1"
    design["silver_contexts"] = source.get("silver_contexts", {})
    design["accepted_silver_methods"] = source.get("accepted_silver_methods", ["reviewed", "parsed", "inferred"])
    design["eligibility_gates"] = [
        {"id": "identity", "requirement": "Evidence-backed stable physical product and family IDs without merging sellers."},
        {"id": "facts", "requirement": "Available typed facts in explicitly selected contexts; parsed, inferred and reviewed results are usable."},
        {"id": "price", "requirement": "Positive displayed GBP price and edible mass; no separate regular-price, promotion or tax gate."},
        {"id": "observation", "requirement": "One current source price with explicit observation time and source availability."},
        {"id": "support", "requirement": "Training establishes support, rank and coverage separately from Gold preparation."},
    ]
    design["price_target_limitations"] = list(LIMITATIONS)
    return design


def schema(design):
    pa, _ = arrow_runtime()
    strings = ("observation_id", "listing_id", "variant_id", "family_id", "comparable_group", "source_role",
               "dataset_version", "source_dataset_version", "schema_version")
    features = [pa.field(name, pa.float64() if definition["type"] == "numeric" else pa.string())
                for name, definition in sorted(design["predictors"].items())]
    targets = design["target"].get("stored_target_fields", ["current_price_per_100g_gbp", "log_current_price_per_100g_gbp"])
    targets = list(dict.fromkeys([*targets, *design["target"].get("legacy_alias_fields", [])]))
    return pa.schema([*(pa.field(name, pa.string()) for name in strings),
                      pa.field("predictors", pa.struct(features), nullable=False),
                      pa.field("target", pa.struct([pa.field(name, pa.float64()) for name in targets]), nullable=False)],
                     metadata={b"gold_arrow_schema_version": FORMAT.encode()})


def build_standard_gold(silver_root, output, *, model_design=None, relationships=None, offline=False):
    source, silver = verified_snapshot(silver_root)
    output = no_links(output)
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Gold output must be separate from Silver.")
    design_path = Path(model_design) if model_design else resolve_standard_gold_contract_root(offline=offline) / "model-design.json"
    original_design = design_path.read_bytes()
    design = study_design(read_json(original_design), silver)
    if design["target"]["price_basis_contract_version"] != "current-consumer-price-1":
        raise ValueError("The standard chocolate study requires its explicit current displayed-price contract.")
    with TemporaryDirectory(prefix="chocolate-gold-preparation-") as temporary:
        preparation = prepare_gold(source, Path(temporary).resolve() / "prepared", design, relationships)
        prepared = Path(preparation["output"])
        metadata = read_json((prepared / "manifest.json").read_bytes())
        files = {"preparation/" + name: data for name, data in read_managed(prepared, metadata["managed_files"], "Gold preparation").items()}
        files["preparation/manifest.json"] = (prepared / "manifest.json").read_bytes()
        files["source-model-design.json"] = original_design
        tables = {}
        for filename, input_name in (("training-data.parquet", "training-candidates.jsonl"), ("model-inputs.parquet", "model-inputs.jsonl")):
            data, decoded = parquet_bytes(rows((prepared / input_name).read_bytes()), schema(design))
            files[filename] = data
            tables[filename] = {"rows": len(decoded), "logical_sha256": checksum(row_bytes(decoded))}
        identity = {"format_version": FORMAT, "preparation_manifest_sha256": checksum(files["preparation/manifest.json"]),
                    "source_model_design_sha256": checksum(original_design), "pyarrow_version": PYARROW_VERSION,
                    "parquet_options": PARQUET_OPTIONS,
                    "implementation_sha256": checksum(Path(__file__).read_bytes())}
        version = "gold-" + checksum(json_bytes(identity))[:24]
        report = {**preparation, "dataset_version": version, "status": "complete_training_population",
                  "gold_ready_for_loading": True, "preparation_layer": "gold", "price_target_limitations": LIMITATIONS}
        report.pop("output")
        files["report.json"] = json_bytes(report)
        manifest = {"manifest_format_version": FORMAT, "processing_rule_version": FORMAT, "dataset_version": version,
                    "identity": identity, "tables": tables,
                    "managed_files": {name: {"sha256": checksum(data), "byte_length": len(data)} for name, data in files.items()}}
        files["manifest.json"] = json_bytes(manifest)
        verified_snapshot(source)
        if design_path.read_bytes() != original_design:
            raise ValueError("Model design changed during preparation.")
        destination = write_snapshot(output, version, files)
    verified_standard_gold(destination)
    return report, destination


def verified_standard_gold(root):
    root = no_links(root)
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = read_json(manifest_bytes)
    if manifest.get("manifest_format_version") != FORMAT or manifest["dataset_version"] != "gold-" + checksum(json_bytes(manifest["identity"]))[:24]:
        raise ValueError("Unsupported standard Gold identity.")
    files = read_managed(root, manifest["managed_files"], "Gold")
    if checksum(files["preparation/manifest.json"]) != manifest["identity"]["preparation_manifest_sha256"]:
        raise ValueError("Gold preparation fingerprint mismatch.")
    source, silver = verified_snapshot(root / "preparation/inputs/silver")
    design = read_json(files["preparation/model-design.json"])
    if (checksum(files["source-model-design.json"]) != manifest["identity"]["source_model_design_sha256"]
            or design != study_design(read_json(files["source-model-design.json"]), silver)
            or manifest["identity"].get("pyarrow_version") != PYARROW_VERSION
            or manifest["identity"].get("parquet_options") != PARQUET_OPTIONS):
        raise ValueError("Gold design or storage settings disagree with their recorded source.")
    relationships = read_json(files["preparation/relationships.json"])
    candidates, selected, prices, audit = prepare_values(source, silver, design, relationships)
    expected = {"training-candidates.jsonl": candidates, "model-inputs.jsonl": selected, "prices.jsonl": prices, "eligibility.jsonl": audit}
    for name, values in expected.items():
        if rows(files["preparation/" + name]) != values:
            raise ValueError("Gold preparation disagrees with its source facts: " + name)
    for name, values in (("training-data.parquet", candidates), ("model-inputs.parquet", selected)):
        decoded = read_parquet(files[name], schema(design))
        if decoded != values or manifest["tables"][name] != {"rows": len(decoded), "logical_sha256": checksum(row_bytes(decoded))}:
            raise ValueError("Gold Parquet differs from verified study preparation.")
    # A training view identifies the Silver population and the separate Gold preparation.
    # It never labels model policy as a Silver output.
    context = {**silver, "preparation_layer": "gold", "gold_dataset_version": manifest["dataset_version"],
               "source_dataset_version": silver["identity"]["raw_inputs_sha256"]}
    inputs = {name: (source / name).read_bytes() for name in ("profile.json", "source-mappings.json", "product.schema.json")}
    inputs.update({name: files["preparation/" + name] for name in ("model-design.json", *expected)})
    inputs["quality-report.json"] = (source / "quality-report.json").read_bytes()
    inputs["gold-preparation-report.json"] = files["report.json"]
    return context, (source / "manifest.json").read_bytes(), inputs
