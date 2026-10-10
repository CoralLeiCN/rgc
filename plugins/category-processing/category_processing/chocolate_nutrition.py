"""Read explicitly based nutrition tables from retained chocolate evidence."""

import re
from html.parser import HTMLParser

from .adapters import _html_text, _tool_lines
from .archive import pointer_value


class Tables(HTMLParser):
    """Keep table cells and columns instead of flattening serving values."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.rows, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.rows = []
        elif tag == "tr" and self.rows is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.rows is not None:
            self.tables.append(self.rows)
            self.rows = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def _rows(text):
    if "<table" in text.lower():
        parser = Tables()
        parser.feed(text)
        return parser.tables
    lines = _tool_lines(text) if re.search(r"\bL\d+:", text) else text.splitlines()
    rows = [line.split("|") for line in lines if "|" in line]
    return [[list(map(str.strip, row)) for row in rows]] if rows else []


def sections(capture, rule):
    """Resolve one configured representation without searching arbitrary metadata."""
    try:
        value = pointer_value(capture, rule["pointer"])
    except (KeyError, IndexError, TypeError):
        return
    if rule["format"] == "text":
        if isinstance(value, str) and value.strip():
            yield rule["pointer"], value
        return
    if rule["format"] == "heading_map":
        if not isinstance(value, dict):
            return
        for heading, lines in value.items():
            if not re.search(rule.get("heading_pattern", "nutrition"), heading, re.I):
                continue
            text = "\n".join(line.get("text", "") for line in lines if isinstance(line, dict))
            pointer = rule["pointer"] + "/" + heading.replace("~", "~0").replace("/", "~1")
            yield pointer, text
        return
    if not isinstance(value, list):
        return
    for n, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        heading = item.get(rule.get("heading_key", "heading"), "")
        if rule.get("heading_pattern") and not re.search(rule["heading_pattern"], str(heading), re.I):
            continue
        key = rule["text_key"]
        if isinstance(item.get(key), str) and item[key].strip():
            yield rule["pointer"] + "/" + str(n) + "/" + key, item[key]


def _label(text):
    text = re.sub(r"[^a-z]+", " ", text.casefold()).strip()
    return re.sub(r"\s+(?:mg|g)$", "", text)


def _numbers(label, cell, config):
    """Return declared values and units, retaining inequality qualifiers."""
    if config.get("energy"):
        explicit = list(re.finditer(r"([<>≤≥~]?)\s*(\d+(?:\.\d+)?)\s*(kcal|kj)\b", cell, re.I))
        if explicit:
            remainder = cell
            for match in reversed(explicit):
                remainder = remainder[:match.start()] + remainder[match.end():]
            if re.sub(r"[\s/()]", "", remainder):
                return
            for match in explicit:
                yield match.group(3).lower(), match.group(2), match.group(1)
            return
        unit = re.search(r"\b(kcal|kj)\b", label, re.I)
    else:
        unit = re.search(r"(?<![a-z])(mg|g)\b", cell, re.I) or re.search(r"\b(mg|g)\b", label, re.I)
    suffix = r"(?:kcal|kj)?" if config.get("energy") else r"(?:mg|g)?"
    match = re.fullmatch(r"\s*([<>≤≥~]?)\s*(\d+(?:\.\d+)?)\s*" + suffix + r"\s*", cell, re.I)
    if match and unit:
        yield unit.group(1).lower(), match.group(2), match.group(1)


def _based_tables(text):
    for table in _rows(text):
        for n, row in enumerate(table):
            columns = [j for j, cell in enumerate(row) if re.fullmatch(
                r"(?:(?:typical values|nutrition(?:al)? information)\s*)?(?:per|/)\s*100\s*g\s*:?", cell, re.I)]
            if len(columns) == 1:
                yield table, n, columns[0] if columns[0] else 1


def _panel_rows(table, header):
    for row in table[header + 1:]:
        if any(re.match(r"\s*(?:per|/)\s*(?:\d|portion\b|serving\b|bar\b|pack\b|half\b)", cell, re.I) for cell in row):
            break
        yield row


def _panel_signature(table, header, column, config):
    values = []
    previous_energy = False
    for row in _panel_rows(table, header):
        if previous_energy and row and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*(?:kj|kcal)\s*", row[0], re.I):
            row = ["", *row]
        if len(row) <= column:
            continue
        label = row[0]
        spec = config["labels"].get(_label(label))
        if not _label(label) and previous_energy:
            spec = {"energy": True}
        previous_energy = bool(spec and spec.get("energy"))
        if spec:
            for unit, number, qualifier in _numbers(label, row[column], spec):
                field = config["energy"][unit] if spec.get("energy") else spec["attribute"]
                values.append((field, unit, float(number), qualifier))
    return frozenset(values)


def extract_nutrition(capture, recipe):
    """Apply an opt-in recipe; unfamiliar panels remain evidence and diagnostics."""
    config = recipe.get("nutrition_tables")
    if not config:
        return [], [], []
    attributes, rejected, handled = [], [], []
    source_key = capture["raw_record"].get("source_key")
    aliases = config["labels"]
    qualifiers = {"<": "upper_bound_exclusive", "≤": "upper_bound_inclusive",
                  ">": "lower_bound_exclusive", "≥": "lower_bound_inclusive", "~": "approximate", "": None}
    seen, evidence = set(), []
    for rule in config["sections"]:
        if rule.get("source_keys") and source_key not in rule["source_keys"]:
            continue
        evidence.extend((rule, pointer, text) for pointer, text in sections(capture, rule))
    if config.get("require_single_product_panel"):
        component_keys = {key for _, _, text in evidence
                          for key in re.findall(r"\bgtin_number-([0-9]+)\b", text)}
        signatures = {_panel_signature(table, header, column, config)
                      for _, _, text in evidence for table, header, column in _based_tables(text)} - {frozenset()}
        # An abridged duplicate may be a subset of the complete panel. Incompatible
        # panels require identified components or resolution of source disagreement.
        largest = sorted(signatures, key=len, reverse=True)
        inconsistent_rows = any(len({(unit, value, qualifier) for name, unit, value, qualifier in signature
                                     if name == field}) > 1
                                for signature in signatures for field in {item[0] for item in signature})
        if inconsistent_rows:
            return [], [{"pointer": pointer, "reason": "nutrition_inconsistent_rows_within_panel"}
                        for _, pointer, text in evidence if list(_based_tables(text))], []
        if len(component_keys) > 1 or largest and any(not signature <= largest[0] for signature in largest[1:]):
            return [], [{"pointer": pointer, "reason": "nutrition_requires_component_or_conflict_resolution"}
                        for _, pointer, text in evidence if list(_based_tables(text))], []
    for rule, pointer, text in evidence:
        product_id = str(capture["raw_record"].get("identity", {}).get("source_product_id"))
        if product_id in config.get("excluded_source_products", {}).get(source_key, []):
            rejected.append({"pointer": pointer, "reason": "nutrition_source_product_attribution_unresolved"})
            continue
        tables = _rows(text)
        based = list(_based_tables(text))
        if len(based) != 1:
            if tables or re.search(r"\bper\s*100\s*g", _html_text(text), re.I):
                rejected.append({"pointer": pointer, "reason": "nutrition_requires_one_explicit_panel_and_basis"})
            continue
        table, header, column = based[0]
        # Whole-product values cannot be assigned from several component panels.
        header_count = len(re.findall(r"(?:per|/)\s*100\s*g", _html_text(text) if "<" in text else text, re.I))
        if header_count > 1 and rule.get("format") == "text":
            rejected.append({"pointer": pointer, "reason": "nutrition_requires_component_subject"})
            continue
        panel_values = []
        previous_energy = False
        for row in _panel_rows(table, header):
            if previous_energy and row and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*(?:kj|kcal)\s*", row[0], re.I):
                row = ["", *row]
            if len(row) <= column or column == 0:
                continue
            label, cell = row[0], row[column]
            normalized = _label(label)
            spec = aliases.get(normalized)
            if not normalized and previous_energy:
                spec = {"energy": True}
            if spec is None:
                if re.match(r"\s*[<>≤≥~]?\s*\d", cell) and re.search(r"[a-z]", label, re.I):
                    rejected.append({"pointer": pointer, "reason": "nutrition_label_requires_mapping",
                                     "source_label": label, "source_cell": cell})
                previous_energy = False
                continue
            previous_energy = bool(spec.get("energy"))
            values = list(_numbers(label, cell, spec))
            if not values and cell.strip():
                rejected.append({"pointer": pointer, "reason": "nutrition_value_or_unit_unresolved",
                                 "source_label": label, "source_cell": cell})
            for unit, number, qualifier in values:
                field = config["energy"][unit] if spec.get("energy") else spec["attribute"]
                expected_unit = "kJ_per_100g" if unit == "kj" else unit + "_per_100g"
                signature = (pointer, field, float(number), qualifier)
                if signature in seen:
                    continue
                seen.add(signature)
                panel_values.append({"attribute": field, "value": float(number), "unit": expected_unit,
                                     "scope": "product", "basis": "per_100g", "qualifier": qualifiers[qualifier],
                                     "pointer": pointer, "method": "declared_nutrition_table_column"})
        if panel_values:
            attributes.extend(panel_values)
            # The whole bounded panel replaces individual line fragments for this source.
            original_tables = re.findall(r"<table\b[^>]*>.*?</table>", text, re.I | re.S)
            if original_tables:
                panel_text = original_tables[tables.index(table)] if len(original_tables) == len(tables) else text
            else:
                panel_text = "\n".join(line for line in text.splitlines() if "|" in line)
            attributes.append({"attribute": "nutrition.source_text", "value": panel_text, "unit": None,
                               "scope": "product", "pointer": pointer,
                               "method": "retained_nutrition_panel"})
            handled.append(pointer)
    return attributes, rejected, handled
