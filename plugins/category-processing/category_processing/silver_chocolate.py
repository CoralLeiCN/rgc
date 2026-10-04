"""Silver extraction refinements validated against preserved chocolate sources."""

import re

from .adapters import IDENTITY, INFO, MASS, _html_text, parse_weight


def refine_quantities(capture, extracted, recipe):
    """Distinguish sale packs, individual units and nutrition-table masses."""
    if recipe["adapter"] != "chocolate":
        return extracted
    attributes = extracted["attributes"]
    mass_field = recipe.get("quantity", {}).get("attribute")
    if not mass_field:
        return extracted
    unit_field = "quantity.unit_edible_weight_g"
    name = capture["raw_record"].get("identity", {}).get("name") or ""
    pack = parse_weight(name)
    count = pack.get("pack_count") if pack else None
    unit_mass = pack["total_edible_weight_g"] / count if count else None
    if count is None:
        # These forms explicitly name the identical-unit count in the selected sale offer.
        patterns = [MASS + r"\s*\(\s*(?:box|case)\s+of\s+(?P<count>\d+)\s*\)",
                    MASS + r"\s*/\s*(?P<count>\d+)\s+(?:bars|bags|pieces)\b",
                    MASS + r"\)?\s*[—–-]\s*(?:case\s+of\s+)?(?P<count>\d+)\s*[x×]\s*(?:bags|bars)\b"]
        matches = [match for pattern in patterns for match in re.finditer(pattern, name, re.I)]
        if len(matches) == 1:
            match = matches[0]
            count = int(match.group("count"))
            unit_mass = float(match.group("mass")) * (1000 if match.group("unit").lower().startswith("k") else 1)
    replacements = []
    retained = []
    rejected = []
    for item in attributes:
        if item["attribute"] != mass_field:
            retained.append(item)
            continue
        if item["method"].startswith("decoded_explicit_body_weight"):
            # Plain cells such as 31.9g under a fat heading are nutrient quantities.
            rejected.append({**item, "reason": "mass_requires_explicit_pack_or_unit_basis"})
            continue
        if count and unit_mass and item["value"] == unit_mass and item["pointer"] in (IDENTITY + "/name", INFO + "/selected_variant/title"):
            replacements.append({**item, "attribute": unit_field, "scope": "selling_unit", "basis": "per_unit"})
        else:
            retained.append(item)
    body = capture["raw_record"].get("information", {}).get("body_html")
    for line in _html_text(body).splitlines():
        match = re.search(r"\b(?:net\s+)?weight\s*[:\-]?\s*" + MASS, line, re.I)
        each = re.search(r"\beach\s+(?:bag|bar|piece)\b.{0,40}?" + MASS, line, re.I)
        match = match or each
        if match:
            value = float(match.group("mass")) * (1000 if match.group("unit").lower().startswith("k") else 1)
            replacements.append({"attribute": unit_field if each else mass_field, "value": value, "unit": "g",
                                 "scope": "selling_unit" if each else "product", "basis": "per_unit" if each else None,
                                 "pointer": INFO + "/body_html", "method": "explicit_labeled_source_mass", "source_text": line})
    if count and count > 0 and unit_mass and unit_mass > 0:
        replacements.extend([
            {"attribute": mass_field, "value": unit_mass * count, "unit": "g", "pointer": IDENTITY + "/name", "method": "explicit_identical_pack_arithmetic"},
            {"attribute": unit_field, "value": unit_mass, "unit": "g", "scope": "selling_unit", "basis": "per_unit",
             "pointer": IDENTITY + "/name", "method": "explicit_identical_unit_mass"},
            {"attribute": recipe.get("pack_count_attribute", "quantity.pack_count"), "value": count, "unit": "count",
             "pointer": IDENTITY + "/name", "method": "explicit_identical_pack_count"},
        ])
    return {**extracted, "attributes": retained + replacements, "rejected_candidates": rejected}
