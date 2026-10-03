"""Offline conformance checks against the downloaded official manifest schema."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "fixtures/plugin.schema.json"


def validate_schema(value, schema):
    """Validate the keywords used by the official v1.0.0 manifest schema."""
    supported = {"$schema", "$id", "title", "description", "type", "properties", "required", "additionalProperties", "items", "const", "minLength", "maxLength", "pattern"}
    unknown = set(schema) - supported
    if unknown:
        raise AssertionError("Unsupported schema keywords: " + repr(unknown))
    if "const" in schema and value != schema["const"]:
        raise ValueError("Schema constant mismatch.")
    expected = schema.get("type")
    types = {"string": str, "object": dict, "array": list}
    if expected and not isinstance(value, types[expected]):
        raise ValueError("Schema type mismatch.")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            raise ValueError("Schema string length mismatch.")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError("Schema pattern mismatch.")
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                raise ValueError("Required schema field is missing: " + required)
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key])
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    raise ValueError("Unknown schema field: " + key)
                if isinstance(additional, dict):
                    validate_schema(item, additional)
    if isinstance(value, list) and "items" in schema:
        for item in value:
            validate_schema(item, schema["items"])


class PackagingTests(unittest.TestCase):
    def test_manifest_conforms_to_official_versioned_schema(self):
        official_bytes = SCHEMA_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(official_bytes).hexdigest(), "0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883")
        schema = json.loads(official_bytes)
        self.assertEqual(schema["$id"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text())
        validate_schema(manifest, schema)
        invalid = deepcopy(manifest)
        invalid["entrypoints"] = {"cli": "./cli.py"}
        with self.assertRaises(ValueError):
            validate_schema(invalid, schema)

    def test_skill_is_discoverable_and_uses_valid_plain_yaml_metadata(self):
        skill = PLUGIN_ROOT / "skills/category-research/SKILL.md"
        lines = skill.read_text().splitlines()
        self.assertEqual(lines[0], "---")
        finish = lines.index("---", 1)
        frontmatter = {}
        for line in lines[1:finish]:
            key, separator, value = line.partition(":")
            self.assertEqual(separator, ":")
            frontmatter[key] = value.strip()
        name = frontmatter["name"]
        self.assertEqual(name, skill.parent.name)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertTrue(1 <= len(frontmatter["description"]) <= 1024)
        self.assertLessEqual(len(frontmatter["compatibility"]), 500)
        self.assertTrue((skill.parent / "scripts/import_products.py").is_file())
        self.assertTrue((skill.parent / "references/import-contract.md").is_file())

    def test_package_files_remain_inside_root_without_a_server_config(self):
        self.assertFalse((PLUGIN_ROOT / "mcp.json").exists())
        for path in PLUGIN_ROOT.rglob("*"):
            path.resolve().relative_to(PLUGIN_ROOT.resolve())


if __name__ == "__main__":
    unittest.main()
