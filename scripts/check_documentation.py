#!/usr/bin/env python3
"""Check documentation contracts and same-change updates for affected components."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md", "README", "docs/intention.md", "docs/spec.md",
    "docs/lifecycle/intent.md", "docs/lifecycle/spec.md", "docs/lifecycle/plan.md",
    "docs/documentation-policy.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md",
    "docs/category-processing.md", "plugins/category-processing/README.md",
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
        if path in ("scripts/chocolate_silver.py", "scripts/build_chocolate_silver.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
        if path.startswith("schemas/chocolate/") or path.startswith("scripts/chocolate_standardization/") or path in ("scripts/standardize_chocolate_data.py", "scripts/chocolate_model.py"):
            required.update(("docs/spec.md", "docs/chocolate-schema.md", "docs/chocolate-silver.md", "docs/lifecycle/plan.md"))
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
    schema_root = root / "schemas/chocolate"
    documents = {}
    for name in ("profile.json", "source-mappings.json", "model-design.json", "product.schema.json"):
        try:
            documents[name] = json.loads((schema_root / name).read_text())
        except (OSError, ValueError) as error:
            errors.append("Unreadable category contract " + name + ": " + str(error))
    if len(documents) == 4:
        version = documents["profile.json"].get("schema_version")
        if not version:
            errors.append("Profile has no schema_version.")
        for name in ("source-mappings.json", "model-design.json"):
            if documents[name].get("schema_version") != version:
                errors.append("Schema version mismatch: " + name)
        if documents["product.schema.json"].get("properties", {}).get("schema_version", {}).get("const") != version:
            errors.append("Product validator version differs from the profile.")
        if version and version not in (root / "docs/chocolate-schema.md").read_text():
            errors.append("Schema guide does not document the current version.")
        attributes = documents["profile.json"].get("attributes", {})
        if documents["profile.json"].get("attribute_count") != len(attributes):
            errors.append("Profile attribute_count differs from the declared catalog.")
        validator_attributes = documents["product.schema.json"].get("properties", {}).get("attributes", {})
        if set(validator_attributes.get("properties", {})) != set(attributes) or set(validator_attributes.get("required", [])) != set(attributes):
            errors.append("Product validator attribute catalog differs from the profile.")
        guide = (root / "docs/chocolate-schema.md").read_text()
        for name, key in (("source-mappings.json", "mapping_version"), ("model-design.json", "model_design_version")):
            contract_version = documents[name].get(key)
            if not isinstance(contract_version, str) or not contract_version or contract_version not in guide:
                label = "mapping version" if key == "mapping_version" else "model design version"
                errors.append("Schema guide does not document the " + label + ".")
        for name in documents["source-mappings.json"].get("aliases", {}):
            if name not in attributes:
                errors.append("Vocabulary mappings reference an undefined attribute: " + name)
        for name in documents["model-design.json"].get("predictors", {}):
            if name not in attributes:
                errors.append("Model design references an undefined attribute: " + name)
    profile_base = root / "plugins/category-processing/profiles"
    guide = (root / "docs/category-processing.md").read_text(encoding="utf-8")
    for category in PROCESSING_PROFILES:
        contracts = {}
        for name in ("profile.json", "source-mappings.json", "product.schema.json", "model-design.json", "pipeline.json"):
            try:
                contracts[name] = json.loads((profile_base / category / name).read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                errors.append("Unreadable processing profile " + category + "/" + name + ": " + str(error))
        if len(contracts) != 5:
            continue
        profile = contracts["profile.json"]
        version = profile.get("schema_version")
        attributes = profile.get("attributes", {})
        if profile.get("category") != category or profile.get("attribute_count") != len(attributes):
            errors.append("Processing profile category/catalog mismatch: " + category)
        for name in ("source-mappings.json", "model-design.json", "pipeline.json"):
            if contracts[name].get("schema_version") != version:
                errors.append("Processing profile version mismatch: " + category + "/" + name)
        properties = contracts["product.schema.json"].get("properties", {})
        if properties.get("schema_version", {}).get("const") != version:
            errors.append("Processing product validator version mismatch: " + category)
        catalog = properties.get("attributes", {})
        if set(catalog.get("properties", {})) != set(attributes) or set(catalog.get("required", [])) != set(attributes):
            errors.append("Processing product validator catalog mismatch: " + category)
        for name, key in (("profile.json", "schema_version"), ("source-mappings.json", "mapping_version"),
                          ("model-design.json", "model_design_version"), ("pipeline.json", "pipeline_version")):
            value = contracts[name].get(key)
            if not isinstance(value, str) or not value or value not in guide:
                errors.append("Processing guide must document " + category + " " + key + ".")
        for name, field in (("source-mappings.json", "aliases"), ("model-design.json", "predictors")):
            for attribute in contracts[name].get(field, {}):
                if attribute not in attributes:
                    errors.append("Processing profile references undefined attribute: " + category + "/" + attribute)
        for field in contracts["pipeline.json"].get("fields", []):
            if field.get("attribute") not in attributes:
                errors.append("Processing recipe references undefined attribute: " + category + "/" + str(field.get("attribute")))
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
