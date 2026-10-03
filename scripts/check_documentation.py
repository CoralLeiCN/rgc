#!/usr/bin/env python3
"""Check documentation contracts and same-change updates for affected components."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from dataset_contracts import cache_directory, load_manifest, verify_contract_directory

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md", "README", "docs/intention.md", "docs/spec.md",
    "docs/lifecycle/intent.md", "docs/lifecycle/spec.md", "docs/lifecycle/plan.md",
    "docs/documentation-policy.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md",
    "docs/category-processing.md", "plugins/category-processing/README.md", "docs/chocolate-gold.md",
    "docs/dataset-contracts.md",
    "plugins/category-processing/skills/category-processing/SKILL.md",
    "plugins/category-processing/skills/category-processing/references/processing-contract.md",
    "plugins/category-processing/skills/category-processing/references/profile-contract.md",
    "plugins/category-processing/skills/category-processing/references/mapping-maintenance.md",
    "plugins/category-processing/skills/category-processing/references/model-handoff.md",
)

PROCESSING_PROFILES = ("chocolate", "coffee")


def required_updates(changed):
    required = set()
    for path in changed:
        if path in ("scripts/chocolate_gold.py", "scripts/build_chocolate_gold.py", "scripts/review_chocolate_gold.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md",
                             "docs/chocolate-gold.md", "docs/lifecycle/plan.md", "README"))
        if path in ("scripts/train_chocolate_model.py", "scripts/chocolate_regression.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
        if path == "scripts/train_chocolate_model.py":
            required.add("docs/chocolate-gold.md")
        if path in ("scripts/chocolate_silver.py", "scripts/build_chocolate_silver.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
        if path.startswith("schemas/chocolate/") or path.startswith("scripts/chocolate_standardization/") or path in ("scripts/standardize_chocolate_data.py", "scripts/chocolate_model.py", "scripts/dataset_contracts.py", "scripts/fetch_contracts.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
        if path in ("scripts/dataset_contracts.py", "scripts/fetch_contracts.py"):
            required.update(("docs/dataset-contracts.md", "README"))
        if path == "scripts/publish_contracts.py":
            required.update(("docs/spec.md", "docs/dataset-contracts.md", "README", "docs/lifecycle/plan.md"))
        if path.startswith("scripts/chocolate_cleanup/") or path in ("scripts/clean_chocolate_data.py", "scripts/deduplicate_chocolate_data.py"):
            required.update(("docs/spec.md", "docs/chocolate-cleaning.md", "docs/chocolate-deduplication.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
        if path.startswith("plugins/category-research/") and "/tests/" not in path:
            required.update(("docs/spec.md", "plugins/category-research/README.md", "docs/lifecycle/plan.md"))
        if path.startswith("plugins/category-processing/") and "/tests/" not in path:
            required.update(("docs/spec.md", "docs/category-processing.md", "plugins/category-processing/README.md", "docs/lifecycle/plan.md"))
        if path == "scripts/publish_collections.py":
            required.update(("docs/spec.md", "README", "docs/lifecycle/plan.md"))
        if path in ("scripts/archive_product_sources.py", "scripts/verify_product_archive.py"):
            required.update(("docs/spec.md", "README", "docs/lifecycle/plan.md"))
        if path in ("AGENTS.md", "scripts/check_documentation.py", ".github/workflows/validation.yml"):
            required.update(("docs/documentation-policy.md", "docs/lifecycle/plan.md"))
    return required


def changed_paths(root, base):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).splitlines()
    changed = set(git("diff", "--name-only", base))
    changed.update(git("ls-files", "--others", "--exclude-standard"))
    return changed



def check_dataset_reference(root, name, contract_set, category, cache_root, guide_name, errors):
    """Check immutable metadata offline, and inspect already-cached bodies only."""
    try:
        manifest = load_manifest(root / name)
    except (OSError, ValueError) as error:
        errors.append("Unreadable dataset contract reference " + name + ": " + str(error))
        return
    portable = contract_set.startswith("category-processing/")
    expected_files = {"profile.json", "source-mappings.json", "product.schema.json", "model-design.json"}
    if portable:
        expected_files.add("pipeline.json")
    if manifest.get("repo_id") != "CoralLeiCN/rgc-collections":
        errors.append("Dataset contract repository mismatch: " + name)
    if manifest.get("contract_set") != contract_set or manifest.get("category") != category or manifest.get("market") != "uk":
        errors.append("Dataset contract category/set/market mismatch: " + name)
    if set(manifest.get("files", {})) != expected_files:
        errors.append("Dataset contract file set mismatch: " + name)
    guide = (root / guide_name).read_text(encoding="utf-8")
    version_keys = ("schema_version", "mapping_version", "model_design_version")
    if portable:
        version_keys += ("pipeline_version",)
    for key in version_keys:
        value = manifest.get(key)
        if not isinstance(value, str) or not value or value not in guide:
            errors.append("Contract guide does not document " + category + " " + key + ": " + guide_name)
    directory = cache_directory(manifest, cache_root)
    if not directory.exists() and not directory.is_symlink():
        return
    try:
        verify_contract_directory(manifest, directory, require_all=False)
    except (OSError, ValueError) as error:
        errors.append("Invalid cached dataset contracts " + name + ": " + str(error))
        return
    # Partial caches are valid offline: check cross-file semantics only when complete.
    if not all((directory / filename).is_file() for filename in expected_files):
        return
    try:
        documents = {filename: json.loads((directory / filename).read_text(encoding="utf-8")) for filename in expected_files}
    except (OSError, ValueError) as error:
        errors.append("Unreadable cached dataset contract " + name + ": " + str(error))
        return
    profile = documents["profile.json"]
    version = profile.get("schema_version")
    attributes = profile.get("attributes", {})
    if not isinstance(attributes, dict):
        errors.append("Cached profile attributes must be an object: " + name)
        return
    if profile.get("category") != category or profile.get("market") != manifest.get("market"):
        errors.append("Cached profile category/market mismatch: " + name)
    if profile.get("attribute_count") != len(attributes) or manifest.get("attribute_count") != len(attributes):
        errors.append("Cached profile attribute_count differs from the declared catalog/reference: " + name)
    if version != manifest.get("schema_version"):
        errors.append("Cached profile schema version differs from dataset reference: " + name)
    for filename in ("source-mappings.json", "model-design.json") + (("pipeline.json",) if portable else ()):
        if documents[filename].get("schema_version") != version:
            errors.append("Cached schema version mismatch: " + category + "/" + filename)
    for filename, key in (("source-mappings.json", "mapping_version"), ("model-design.json", "model_design_version")) + ((("pipeline.json", "pipeline_version"),) if portable else ()):
        if documents[filename].get(key) != manifest.get(key):
            errors.append("Cached contract version differs from dataset reference: " + category + "/" + key)
    properties = documents["product.schema.json"].get("properties", {})
    if not isinstance(properties, dict):
        errors.append("Cached product validator properties must be an object: " + category)
        return
    validator_version = properties.get("schema_version", {})
    if not isinstance(validator_version, dict) or validator_version.get("const") != version:
        errors.append("Cached product validator version differs from the profile: " + category)
    catalog = properties.get("attributes", {})
    if (not isinstance(catalog, dict) or not isinstance(catalog.get("properties", {}), dict)
            or not isinstance(catalog.get("required", []), list)
            or not all(isinstance(value, str) for value in catalog.get("required", []))):
        errors.append("Cached product validator catalog has an invalid shape: " + category)
        return
    if set(catalog.get("properties", {})) != set(attributes) or set(catalog.get("required", [])) != set(attributes):
        errors.append("Cached product validator attribute catalog differs from the profile: " + category)
    for filename, field in (("source-mappings.json", "aliases"), ("model-design.json", "predictors")):
        values = documents[filename].get(field, {})
        if not isinstance(values, dict):
            errors.append("Cached contract " + field + " must be an object: " + category)
            continue
        for attribute in values:
            if attribute not in attributes:
                errors.append("Cached contract references an undefined attribute: " + category + "/" + attribute)
    if portable:
        fields = documents["pipeline.json"].get("fields", [])
        if not isinstance(fields, list):
            errors.append("Cached processing recipe fields must be a list: " + category)
            return
        for field in fields:
            attribute = field.get("attribute") if isinstance(field, dict) else None
            if attribute not in attributes:
                errors.append("Cached processing recipe references an undefined attribute: " + category + "/" + str(attribute))


def check(root=ROOT, changed=None):
    root = Path(root)
    errors = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append("Missing maintained document: " + name)
    if errors:
        return errors
    for name in REQUIRED:
        text = (root / name).read_text(encoding="utf-8")
        if re.search(r"\[(?:Describe|What |List |Implementation step|Person or team|Unresolved|Resolve |Flag |Carry forward|Next step)", text):
            errors.append("Unfilled lifecycle/documentation template: " + name)
        for target in re.findall(r"\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            path = (root / name).parent / target
            if not path.exists():
                errors.append("Broken local link in " + name + ": " + target)
    check_dataset_reference(
        root, "schemas/chocolate/dataset-contract.json", "chocolate", "chocolate",
        root / "data/contract-cache", "docs/chocolate-schema.md", errors,
    )
    for category in PROCESSING_PROFILES:
        check_dataset_reference(
            root, "plugins/category-processing/profiles/" + category + "/dataset-contract.json",
            "category-processing/" + category, category,
            root / "plugins/category-processing/.contract-cache", "docs/category-processing.md", errors,
        )
    if changed is not None:
        for name in sorted(required_updates(set(changed)) - set(changed)):
            errors.append("Affected implementation needs an accompanying documentation update: " + name)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="HEAD", help="Git revision to compare; default includes current local changes.")
    parser.add_argument("--structural-only", action="store_true", help="Check contracts and links without a Git change comparison.")
    args = parser.parse_args(argv)
    try:
        changed = None if args.structural_only else changed_paths(ROOT, args.base)
        errors = check(ROOT, changed)
        for error in errors:
            print(error, file=sys.stderr)
        if not errors:
            print("Documentation contracts and maintenance checks passed.")
        return 1 if errors else 0
    except (OSError, subprocess.CalledProcessError) as error:
        print("Documentation check could not complete: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
