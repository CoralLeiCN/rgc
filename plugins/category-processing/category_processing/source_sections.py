"""Resolve literal source excerpts without adjudicating their factual claims."""

import re


def navigation_claim(text):
    text = re.sub(r"^\ue200cite\ue202[^†]+†|\ue201\s*$", "", text.strip())
    return text == "Ocado Price Promise" or re.fullmatch(r"Shop all [^\n]+", text) is not None


def ingredient_excerpt(text):
    """Bound a single labeled recipe using explicit following section headings."""
    labels = list(re.finditer(r"\bingredients\s*:\s*", text, re.I))
    if len(labels) > 1:
        return text.strip()
    start = labels[0].start() if len(labels) == 1 else 0
    excerpt = text[start:]
    boundary = re.search(r"\n\s*(?:origin|nutrition(?:al)?(?: information|s)?|allergens?|allergy advice|"
                         r"shelf life|storage)(?:\s*[:\-]?\s*(?:\n|$)|\s*:)", excerpt, re.I)
    return excerpt[:boundary.start()].strip() if boundary else excerpt.strip()


def resolve_text(candidates, policy):
    """Collection joins exact excerpts; equivalence retains the first wording."""
    values = [item["result"] for item in candidates]
    if not all(isinstance(value, str) for value in values):
        return {"state": "conflict"}
    distinct = list(dict.fromkeys(values))
    if policy == "collect_sections":
        # A warning extracted from its own enclosing section adds no new text.
        # Retain every assertion/reference; collapse only within identical evidence.
        nested = {item["result"] for item in candidates if item.get("source")
                  for other in candidates if item.get("source") == other.get("source")
                  and item["result"] != other["result"] and item["result"] in other["result"]}
        distinct = [value for value in distinct if value not in nested]
        return "\n".join(distinct)
    if policy == "equivalent_sections":
        normalized = set()
        for value in distinct:
            value = re.sub(r"^(?:\s*ingredients\s*(?::|[—–-]|\n)\s*)+", "", value, flags=re.I)
            normalized.add(" ".join(value.casefold().split()))
        if len(normalized) == 1:
            return distinct[0]
    return {"state": "conflict"}
