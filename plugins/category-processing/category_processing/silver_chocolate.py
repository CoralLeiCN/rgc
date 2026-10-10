"""Silver extraction refinements validated against preserved chocolate sources."""

import math
import re
from decimal import Decimal

from .adapters import IDENTITY, INFO, MASS, _html_text, parse_weight


def _identical_pack(text):
    """Return (count, unit grams) only for explicit identical-unit expressions."""
    pack = parse_weight(text)
    if pack and pack.get("pack_count"):
        count = pack["pack_count"]
        match = next(re.finditer(MASS, text, re.I))
        unit_mass = float(Decimal(match.group("mass")) * (1000 if match.group("unit").lower().startswith("k") else 1))
        return count, unit_mass
    if not isinstance(text, str) or len(list(re.finditer(MASS, text, re.I))) != 1:
        return None
    patterns = [MASS + r"\s*\(\s*(?:box|case)\s+of\s+(?P<count>\d+)\s*\)",
                MASS + r"\s*/\s*(?P<count>\d+)\s+(?:bars|bags|pieces|lollies)\b",
                MASS + r"\)?\s*[—–-]\s*(?:case\s+of\s+)?(?P<count>\d+)\s*[x×]\s*(?:bags|bars)\b"]
    matches = [match for pattern in patterns for match in re.finditer(pattern, text, re.I)]
    if len(matches) != 1:
        return None
    match = matches[0]
    count = int(match.group("count"))
    unit_mass = float(Decimal(match.group("mass")) * (1000 if match.group("unit").lower().startswith("k") else 1))
    return (count, unit_mass) if count > 0 and unit_mass > 0 and math.isfinite(unit_mass * count) else None


def _other_variant_packs(identity, information):
    """Attribute other-option quantities only with consistent selected source IDs."""
    selected = information.get("selected_variant")
    variants = information.get("variants")
    source_id = identity.get("source_variant_id")
    if source_id is None or not isinstance(selected, dict) or not isinstance(variants, list):
        return set()
    if str(selected.get("id")) != str(source_id):
        return set()
    matching = [variant for variant in variants if isinstance(variant, dict) and str(variant.get("id")) == str(source_id)]
    selected_pack = _identical_pack(selected.get("title"))
    name_pack = _identical_pack(identity.get("name"))
    if (len(matching) != 1 or selected_pack is None
            or _identical_pack(matching[0].get("title")) != selected_pack
            or (name_pack is not None and name_pack != selected_pack)):
        return set()
    return {pack for variant in variants if isinstance(variant, dict)
            and variant.get("id") is not None and str(variant["id"]) != str(source_id)
            and (pack := _identical_pack(variant.get("title"))) is not None and pack != selected_pack}


def _pack_attributes(pack, pointer, mass_field, count_field):
    count, unit_mass = pack
    return [
        {"attribute": mass_field, "value": float(Decimal(str(unit_mass)) * count), "unit": "g", "pointer": pointer,
         "method": "explicit_identical_pack_arithmetic"},
        {"attribute": "quantity.unit_edible_weight_g", "value": unit_mass, "unit": "g", "scope": "selling_unit",
         "basis": "per_unit", "pointer": pointer, "method": "explicit_identical_unit_mass"},
        {"attribute": count_field, "value": count, "unit": "count", "pointer": pointer,
         "method": "explicit_identical_pack_count"},
    ]


def refine_quantities(capture, extracted, recipe):
    """Distinguish sale packs, individual units and nutrition-table masses."""
    if recipe["adapter"] != "chocolate":
        return extracted
    attributes = extracted["attributes"]
    mass_field = recipe.get("quantity", {}).get("attribute")
    if not mass_field:
        return extracted
    unit_field = "quantity.unit_edible_weight_g"
    identity = capture["raw_record"].get("identity", {})
    information = capture["raw_record"].get("information", {})
    selected = information.get("selected_variant")
    selected = selected if isinstance(selected, dict) else {}
    packs = {IDENTITY + "/name": _identical_pack(identity.get("name")),
             INFO + "/selected_variant/title": _identical_pack(selected.get("title"))}
    other_packs = _other_variant_packs(identity, information)
    count_field = recipe.get("pack_count_attribute", "quantity.pack_count")
    replacements = []
    retained = []
    rejected = list(extracted.get("rejected_candidates", []))
    for item in attributes:
        if item["attribute"] in (mass_field, count_field) and item["method"].startswith("decoded_explicit_body_weight"):
            # Reconstruct body quantities below, retaining their full pack/unit basis.
            continue
        if item["attribute"] != mass_field:
            retained.append(item)
            continue
        pack = packs.get(item["pointer"])
        if pack and item["value"] == pack[1]:
            replacements.append({**item, "attribute": unit_field, "scope": "selling_unit", "basis": "per_unit"})
        else:
            retained.append(item)
    body = information.get("body_html")
    for line in _html_text(body).splitlines():
        match = re.search(r"\b(?:net\s+)?weight\s*[:\-]?\s*" + MASS, line, re.I)
        each = re.search(r"\beach\s+(?:bag|bar|piece|lolly)\b.{0,40}?" + MASS, line, re.I)
        each = each or re.search(r"\beach\s*" + MASS + r"\s*(?:bag|bar|piece|lolly)\b", line, re.I)
        match = match or each
        pack = _identical_pack(line) if match else None
        if pack:
            candidates = [{**item, "source_text": line} for item in _pack_attributes(pack, INFO + "/body_html", mass_field, count_field)]
            if pack in other_packs:
                rejected.extend({**item, "reason": "quantity_refers_to_other_variant"} for item in candidates)
            else:
                replacements.extend(candidates)
            continue
        if match:
            value = float(match.group("mass")) * (1000 if match.group("unit").lower().startswith("k") else 1)
            replacements.append({"attribute": unit_field if each else mass_field, "value": value, "unit": "g",
                                 "scope": "selling_unit" if each else "product", "basis": "per_unit" if each else None,
                                 "pointer": INFO + "/body_html", "method": "explicit_labeled_source_mass", "source_text": line})
    for pointer, pack in packs.items():
        if pack:
            replacements.extend(_pack_attributes(pack, pointer, mass_field, count_field))
    # Plain cells such as 31.9g under a fat heading are nutrient quantities.
    for item in attributes:
        if item["attribute"] in (mass_field, count_field) and item["method"].startswith("decoded_explicit_body_weight"):
            if not any(all(candidate.get(key) == item.get(key) for key in ("pointer", "attribute", "value"))
                       for candidate in replacements + rejected):
                rejected.append({**item, "reason": "mass_requires_explicit_pack_or_unit_basis"})
    refined = retained + replacements
    quantities = [{key: item[key] for key in ("value", "unit", "pointer", "method") if key in item}
                  for item in refined if item["attribute"] == mass_field]
    prices = [{**price, "quantity_candidates": quantities}
              if price["pointer"].startswith(INFO + "/selected_variant/") else price
              for price in extracted.get("prices", [])]
    return {**extracted, "attributes": refined, "quantities": quantities, "prices": prices,
            "rejected_candidates": rejected}
