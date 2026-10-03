"""Discover unhandled raw fields without interpreting or changing source evidence."""

from copy import deepcopy

from .archive import pointer_token, pointer_value

DEFAULT_ROOTS = ("/raw_record",)
DEFAULT_IGNORED_POINTERS = tuple(sorted(
    "/raw_record/" + name for name in (
        "product_id", "source_key", "source_url", "source_artifacts", "images",
        "source_catalog", "source_catalogs", "collection_notes",
        "identity/name", "identity/brand", "identity/source_product_id",
        "identity/source_variant_id",
    )
))


def _inside(pointer, parent):
    """Compare complete pointer tokens, including the empty document pointer."""
    return pointer == parent or pointer.startswith(parent + "/")


def _minimal_pointers(pointers):
    result = []
    for pointer in sorted(set(pointers)):
        if not any(_inside(pointer, parent) for parent in result):
            result.append(pointer)
    return result


def discovery_policy(recipe):
    """Return the effective discovery boundary, including control exclusions.

    Profile validation checks optional configuration before extraction. Explicit
    ignores add to the fixed control context exclusions; overlapping roots or
    ignores collapse to their shallowest pointer without widening the boundary.
    """
    config = recipe.get("discovery", {})
    return {
        "enabled": config.get("enabled", True),
        "roots": _minimal_pointers(config.get("roots", DEFAULT_ROOTS)),
        "ignore_pointers": _minimal_pointers(
            list(DEFAULT_IGNORED_POINTERS) + list(config.get("ignore_pointers", []))
        ),
    }


def _configured_pointers(capture, recipe):
    """Account for fields already handled by the declared extraction recipe."""
    pointers = [field["pointer"] for field in recipe.get("fields", [])]
    pointers.extend(value for key, value in recipe.get("price", {}).items()
                    if key.endswith("_pointer"))
    for pointer in recipe.get("sections", {}):
        try:
            section = pointer_value(capture, pointer)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if isinstance(section, dict):
            # Section extraction already retains every child, including an
            # undeclared field or a value rejected by the current schema.
            pointers.extend(pointer + "/" + pointer_token(key) for key in section)
    return pointers


def _meaningful(value):
    """Missing leaves are omitted; numeric zero and explicit false are evidence."""
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_meaningful(item) for item in value.values())
    if isinstance(value, list):
        return any(_meaningful(item) for item in value)
    return value != ""


def _value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    raise ValueError("Raw field discovery requires JSON values.")


def _resolves(capture, pointer):
    try:
        pointer_value(capture, pointer)
    except (KeyError, IndexError, TypeError, ValueError):
        return False
    return True


def discover_fields(capture, recipe, handled_pointers=()):
    """Return exact, typed unhandled subtrees with capture-root JSON pointers.

    A wholly unhandled meaningful object or array is retained as one candidate,
    preserving relationships and internal missing values. A partly handled
    subtree is traversed to its unhandled siblings. This identifies structural
    coverage gaps; it does not infer concepts hidden inside already used prose,
    canonical attributes, units, or schema eligibility.
    """
    policy = discovery_policy(recipe)
    if not policy["enabled"]:
        return []
    coverage = (
        policy["ignore_pointers"] + _configured_pointers(capture, recipe)
        + list(handled_pointers)
    )
    covered = _minimal_pointers(pointer for pointer in coverage if _resolves(capture, pointer))
    result = []

    def visit(value, pointer):
        if any(_inside(pointer, parent) for parent in covered) or not _meaningful(value):
            return
        if any(_inside(parent, pointer) for parent in covered):
            if isinstance(value, dict):
                for key in sorted(value):
                    visit(value[key], pointer + "/" + pointer_token(key))
                return
            if isinstance(value, list):
                for index, item in enumerate(value):
                    visit(item, pointer + "/" + str(index))
                return
        result.append({"field_pointer": pointer, "raw_value": deepcopy(value),
                       "value_type": _value_type(value)})

    for root in policy["roots"]:
        try:
            value = pointer_value(capture, root)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        visit(value, root)
    return sorted(result, key=lambda item: item["field_pointer"])
