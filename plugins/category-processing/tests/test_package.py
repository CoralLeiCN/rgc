"""Check portable package metadata against the published plugin/skill constraints."""

import hashlib
import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


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


class CategoryProcessingPackageTests:
    def test_manifest_matches_agent_plugins_1_0_schema_constraints(self):
        official_bytes = (PLUGIN_ROOT / "tests/fixtures/plugin.schema.json").read_bytes()
        assert (hashlib.sha256(official_bytes).hexdigest()) == ("0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883")
        schema = json.loads(official_bytes)
        assert (schema["$id"]) == ("https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text())
        validate_schema(manifest, schema)

    @pytest.mark.parametrize("skill", sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md")),
                             ids=lambda skill: skill.parent.name)
    def test_discoverable_skill_frontmatter_and_local_references_resolve(self, skill):
        # Primary constraints: https://agentskills.io/specification
        source = skill.read_text()
        assert (source.startswith("---\n"))
        frontmatter = source.split("---", 2)[1]
        fields = dict(re.findall(r"^([a-z-]+):\s*(.+)$", frontmatter, flags=re.MULTILINE))
        assert (fields["name"]) == (skill.parent.name)
        assert re.search((r"^[a-z0-9]+(?:-[a-z0-9]+)*$"), (fields["name"]))
        assert (1 <= len(fields["name"]) <= 64)
        assert (1 <= len(fields["description"]) <= 1024)
        for document in (skill, *sorted((skill.parent / "references").glob("*.md"))):
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
                if "://" not in target and not target.startswith("#"):
                    destination = (document.parent / target.split("#")[0]).resolve()
                    assert destination.is_relative_to(PLUGIN_ROOT), target
                    assert destination.exists(), target
