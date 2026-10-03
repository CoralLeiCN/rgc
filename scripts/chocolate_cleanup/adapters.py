"""Conservative, offline adapters for the collected UK chocolate evidence.

Adapters return candidates, rather than reviewed product facts. Original records
are never changed. A JSON pointer identifies each supporting value in the capture.
Shopify ``grams`` is deliberately excluded: it can describe shipping weight.
"""

from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import math
import re


INFO = "/raw_record/information"
IDENTITY = "/raw_record/identity"
MASS = r"(?<![\w.,\-])(?P<mass>\d+(?:\.\d+)?)\s*(?P<unit>kg|g|grams?|kilograms?)\b"
NUTS = r"\b(?:nuts?|peanuts?|almonds?|hazelnuts?|cashews?|pistachios?|walnuts?|pecans?|macadamias?|brazil nuts?)\b"
UNKNOWN_FEATURES = (
    ("ingredients_text", "string"), ("allergen_text", "string"),
    ("nutrition_text", "string"), ("chocolate_type", "categorical"),
    ("cocoa_percentage", "number"), ("nuts_as_ingredient", "presence"),
    ("may_contain_nuts", "presence"), ("fairtrade_claim", "presence"),
    ("organic_claim", "presence"), ("vegan_claim", "presence"),
)


def parse_money(value):
    """Return a positive finite Decimal in major units, or None.

    Symbols are accepted for standalone human-readable prices. This helper does
    not extract numbers from arbitrary prose or convert pence implicitly.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    text = str(value).strip()
    text = re.sub(r"^(?:£|GBP\s*)", "", text, flags=re.I).strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and amount > 0 else None


def _mass(match):
    amount = parse_money(match.group("mass"))
    if amount is None:
        return None
    if match.group("unit").lower().startswith("k"):
        amount *= 1000
    return amount


def parse_weight(text):
    """Parse one explicit mass or an explicit identical-unit multipack.

    Return None for a range, conflicting masses, nutrition quantities, or a
    count-only pack. A lone mass does not imply a known pack count.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.replace("\u00a0", " ")
    if re.search(r"\d,\s*\d", text):
        return None
    if re.search(r"(?<!\w)[<>−-]\s*\d+(?:\.\d+)?\s*(?:[x×]|kg\b|g\b)", text, re.I):
        return None
    if re.search(r"\bper\s+\d+(?:\.\d+)?\s*(?:kg|g)\b|\bserving|\benergy\b|\bkcal\b|\bshipping\b", text, re.I):
        return None
    if re.search(r"\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*(?:kg|g)\b", text, re.I):
        return None
    mass_matches = list(re.finditer(MASS, text, re.I))
    if not mass_matches:
        return None
    masses = {_mass(match) for match in mass_matches}
    if None in masses or len(masses) != 1:
        return None
    amount = next(iter(masses))
    count = None
    count_candidates = []
    for pattern in (
        r"\b(?P<count>\d+)\s*[x×]\s*" + MASS,
        MASS + r"\s*(?:bars?\s*)?[x×]\s*(?P<count>\d+)\b",
        r"\b(?P<count>\d+)\s*[x×]\s+[^\n—;]{0,90}?\(?" + MASS,
    ):
        for match in re.finditer(pattern, text, re.I):
            count_candidates.append(int(match.group("count")))
    # A count and a mass in the same name can mean total pack mass. Multiplying
    # them is justified only with an explicit per-unit/each statement.
    if not count_candidates:
        counts = re.findall(r"\b(?:pack\s+of\s+(\d+)|(\d+)\s+bars?)\b", text, re.I)
        if counts and re.search(MASS + r"\s*each\b", text, re.I):
            count_candidates = [int(a or b) for a, b in counts]
        elif counts:
            return None
    if count_candidates:
        if len(set(count_candidates)) != 1 or count_candidates[0] <= 0:
            return None
        count = count_candidates[0]
        amount *= count
    normalized = float(amount)
    if not math.isfinite(normalized) or normalized <= 0:
        return None
    return {
        "total_edible_weight_g": normalized, "pack_count": count,
        "method": "explicit_multipack_mass" if count is not None else "explicit_mass",
    }


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "table", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def _html_text(value):
    if not isinstance(value, str):
        return ""
    parser = _TextParser()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _feature(name, value, pointer, method, value_type="string", unit=None, raw_value=None):
    result = {
        "name": name, "value": value, "value_type": value_type,
        "unit": unit, "status": "known" if value is not None and value != "unknown" else "unknown",
        "raw_pointer": pointer, "method": method,
    }
    if raw_value is not None:
        result["raw_value"] = raw_value
    return result


def _pointer_key(key):
    return str(key).replace("~", "~0").replace("/", "~1")


def _quantity(text, pointer, method=None):
    result = parse_weight(text)
    if result is None:
        return None
    result.update(raw_pointer=pointer, raw_value=text)
    if method:
        result["method"] = method + ":" + result["method"]
    return result


def _source_time(capture, information, source_key):
    for key in ("source_collected_at", "catalogue_collected_at", "catalogue_archived_at"):
        if isinstance(information.get(key), str):
            return information[key], "source_catalogue_observation"
    original_path = information.get("original_catalogue_archive_path")
    matches = []
    for entry in capture.get("source_catalogs", []):
        descriptor = entry.get("descriptor", {})
        if original_path and descriptor.get("local_path") != original_path:
            continue
        if descriptor.get("source_key") not in (source_key, None):
            continue
        if not original_path and descriptor.get("source_key") != source_key:
            continue
        time = descriptor.get("retrieved_at") or descriptor.get("archived_at")
        if not time:
            metadata = descriptor.get("retrieval_metadata", {})
            time = metadata.get("archived_at") or metadata.get("retrieved_at")
        if time:
            matches.append(time)
    if len(set(matches)) == 1:
        return matches[0], "source_catalogue_observation"
    return None, "unknown"


def _price(displayed, pointer, method, currency, observed_at, time_basis,
           reference=None, regular=None, promotion=None, available=None, allow_invalid=False):
    value = parse_money(displayed)
    if value is None and not allow_invalid:
        return None
    ref = parse_money(reference)
    ordinary = parse_money(regular)
    def finite_float(amount):
        if amount is None:
            return None
        normalized = float(amount)
        return normalized if math.isfinite(normalized) and normalized > 0 else None
    return {
        "displayed_price": finite_float(value), "regular_price": finite_float(ordinary),
        "reference_price": finite_float(ref), "currency": currency,
        "promotion_status": "promotional" if promotion else "unknown",
        "promotion": promotion, "tax_basis": "unknown", "available": available,
        "observed_at": observed_at, "time_basis": time_basis,
        "raw_pointer": pointer, "method": method, "raw_value": displayed,
    }


def _tool_lines(text):
    """Decode only tool line/citation framing; original evidence stays intact."""
    text = re.sub(r"cite[^†\n]*†([^]*)", r"\1", text)
    text = re.sub(r"cite[^]*", "", text)
    text = re.sub(r"(?:^|\s)L\d+:\s?", "\n", text)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _pounds_after(label, text):
    match = re.search(label + r"\s*£\s*(\d+(?:\.\d+)?)", text, re.I)
    return match.group(1) if match else None


def _ocado_price(text, pointer, method, observed_at=None, cached=False, header=False):
    lines = _tool_lines(text)
    if header:
        start = next((i for i, line in enumerate(lines) if line.startswith("# ") and not line.startswith("##")), None)
        if start is None:
            return None
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("##")), len(lines))
        context = "\n".join(lines[start:end])
        offers = "\n".join(lines[end:next((i for i in range(end + 1, len(lines)) if lines[i].startswith("##")), len(lines))]) if end < len(lines) and lines[end].lower() == "## offers" else ""
    else:
        context = "\n".join(lines)
        offers = context
    displayed = _pounds_after(r"(?:^|\n)Price", context)
    if displayed is None:
        # A product header can expose concatenated current/previous prices. Use
        # only a line made entirely of GBP amounts, after the product heading.
        for line in context.splitlines():
            if re.fullmatch(r"(?:£\s*\d+(?:\.\d+)?\s*){1,2}", line):
                displayed = re.findall(r"£\s*(\d+(?:\.\d+)?)", line)[0]
                break
    if displayed is None:
        return None
    reference = _pounds_after(r"(?:Previous price|\bwas)", offers)
    regular = _pounds_after(r"(?:Regular price|Ordinary price)", context)
    promotion = offers if re.search(r"\b(?:offer|now|was|save|buy|for\s+£|will be)\b", offers, re.I) else None
    result = _price(displayed, pointer, method, "GBP", observed_at,
                    "cached_web_representation" if cached else "source_catalogue_observation",
                    reference=reference, regular=regular, promotion=promotion)
    if result:
        # Quantity must come from this price's header/card, never from unrelated
        # nutrition tables or later recommended products.
        quantities = []
        for line in context.splitlines():
            if re.search(r"\d\s*(?:g|kg)\b", line, re.I):
                quantity = _quantity(re.split(r"(?:Ordinarily|£)", line)[0].strip(), pointer, "price_context_mass")
                if quantity:
                    quantities.append(quantity)
        result["quantities"] = quantities
        result["raw_value"] = text
    return result


def _statements(information):
    """Yield (kind, exact source wording, pointer, method) from bounded sections."""
    pp = information.get("product_page_information", {})
    if isinstance(pp, dict):
        direct = pp.get("ingredients_source_statement")
        if isinstance(direct, str) and direct.strip() and pp.get("ingredients_statement_captured") is not False:
            yield "ingredients_text", direct, INFO + "/product_page_information/ingredients_source_statement", "source_ingredient_statement"
        for key in ("source_sections", "source_section_candidates"):
            for index, section in enumerate(pp.get(key, [])):
                if not isinstance(section, dict):
                    continue
                label = str(section.get("heading", section.get("source_heading", ""))).lower()
                text_key = next((k for k in ("source_text", "following_source_text", "text") if isinstance(section.get(k), str)), None)
                if text_key is None:
                    continue
                text = section[text_key]
                if not text.strip():
                    continue
                if "ingredient" in label:
                    kind = "ingredients_text"
                elif "allergen" in label or "allerg" in label:
                    kind = "allergen_text"
                elif "nutrition" in label:
                    kind = "nutrition_text"
                elif label in ("features", "dietary information", "product attributes", "packaging"):
                    kind = "claim_text"
                elif not label and re.search(r"\bingredients\s*:", text, re.I):
                    kind = "ingredients_text"
                else:
                    continue
                yield kind, text, INFO + "/product_page_information/" + key + "/" + str(index) + "/" + text_key, "bounded_source_section"
    evidence = information.get("collection_evidence", {})
    if isinstance(evidence, dict):
        for key in ("ingredient_statement_candidates_from_body_html", "ingredient_statement_candidates_from_product_html"):
            for index, text in enumerate(evidence.get(key, [])):
                if isinstance(text, str) and text.strip():
                    yield "ingredients_text", text, INFO + "/collection_evidence/" + key + "/" + str(index), "source_ingredient_candidate"
    supplement = information.get("web_tool_supplement", {})
    if isinstance(supplement, dict):
        for index, observation in enumerate(supplement.get("observations", [])):
            for section_index, section in enumerate(observation.get("source_ingredient_sections", [])):
                if isinstance(section, dict) and isinstance(section.get("source_text"), str) and section["source_text"].strip():
                    yield "ingredients_text", section["source_text"], INFO + "/web_tool_supplement/observations/" + str(index) + "/source_ingredient_sections/" + str(section_index) + "/source_text", "cached_source_ingredient_section"
    for index, observation in enumerate(information.get("original_product_page_observations", [])):
        if observation.get("response_status") == "failed":
            continue
        sections = observation.get("original_heading_sections", {})
        for heading, lines in sections.items():
            kind = {"Ingredients": "ingredients_text", "Allergen Information": "allergen_text", "Nutritional data": "nutrition_text", "Features": "claim_text", "Dietary Information": "claim_text", "Product attributes": "claim_text"}.get(heading)
            if kind is None:
                continue
            for line_index, line in enumerate(lines):
                if isinstance(line, dict) and isinstance(line.get("text"), str) and line["text"].strip():
                    yield kind, line["text"], INFO + "/original_product_page_observations/" + str(index) + "/original_heading_sections/" + _pointer_key(heading) + "/" + str(line_index) + "/text", "cached_source_section_line"


def _nut_features(text, pointer, kind):
    # A warning may appear in the ingredient section. Remove warning sentences
    # before recognizing recipe nuts; preserve the warning separately.
    warning = next((match for match in re.finditer(r"(?:may\s+contain|made\s+(?:in|on)|produced\s+(?:in|on)|handles?|processes?)\b[^\n.]*\.?", text, re.I) if re.search(NUTS, match.group(0), re.I)), None)
    if warning is not None:
        yield _feature("may_contain_nuts", "present", pointer, "explicit_nut_warning", "presence", raw_value=text)
        if kind != "allergen_text":
            yield _feature("allergen_text", warning.group(0), pointer, "explicit_warning_in_source_statement", raw_value=text)
    if kind != "ingredients_text":
        return
    recipe = re.split(r"\b(?:may contain|made in|made on|produced in|allergens?|allergy|nutrition|storage|suitable for)\b", text, maxsplit=1, flags=re.I)[0]
    recipe = re.sub(r"\b(?:nut|peanut|tree nut)[ -]free\b|\bfree from\s+[^\n.]*", "", recipe, flags=re.I)
    if re.search(NUTS, recipe, re.I):
        yield _feature("nuts_as_ingredient", "present", pointer, "nut_term_in_ingredient_statement", "presence", raw_value=text)


def _group(name, product_type, pointer):
    text = (name + " " + product_type).lower()
    for pattern, value in (
        (r"hot chocolate|drinking chocolate", "hot_chocolate"),
        (r"baking|pastilles", "baking_chocolate"),
        (r"assort|selection|gift box|collection|hamper|bundle|advent", "assorted_box"),
        (r"\bbar\b|\bbars\b|\bslabs?\b", "bar"),
        (r"truffle|buttons|bites|egg|snowball|chocolate[s]?\b|coins", "chocolate_pieces"),
    ):
        if re.search(pattern, text):
            return {"value": value, "raw_pointer": pointer, "method": "provisional_name_and_source_type_rule"}
    return {"value": None, "raw_pointer": pointer, "method": "unresolved_group"}


def _positive_claim(text, term):
    """Require an affirmative term, excluding nearby product suitability negation."""
    for match in re.finditer(term, text, re.I):
        prefix = re.split(r"[\n.!?;]", text[:match.start()])[-1][-90:]
        if re.search(r"\b(?:not|non|never|without)\b(?:[\s-]+\w+){0,8}[\s-]*$", prefix, re.I):
            continue
        return True
    return False


def extract_capture(capture):
    """Extract reviewable candidates from one raw plugin capture, offline."""
    raw = capture.get("raw_record", {})
    information = raw.get("information", {})
    identity = raw.get("identity", {})
    if not isinstance(information, dict):
        information = {}
    if not isinstance(identity, dict):
        identity = {}
    source = raw.get("source_key")
    features, quantities, prices, warnings = [], [], [], []
    for key in ("name", "brand", "source_product_id", "source_variant_id", "gtin"):
        value = identity.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            features.append(_feature(key, str(value), IDENTITY + "/" + key, "source_identity"))
    name = str(identity.get("name") or information.get("title") or information.get("source_name_text") or "")
    product = information.get("shopify_product", information)
    product_type = str(product.get("product_type") or "") if isinstance(product, dict) else ""
    name_pointer = IDENTITY + "/name" if identity.get("name") else INFO + "/title" if information.get("title") else INFO + "/source_name_text" if information.get("source_name_text") else "/raw_record"
    group = _group(name, product_type, name_pointer)
    boundary = information.get("category_boundary_status") or "review_required"
    if boundary != "included":
        warnings.append("Category inclusion remains provisional; source category membership is not a reviewed chocolate classification.")
    for text, pointer in ((name, name_pointer), (information.get("source_weight_text"), INFO + "/source_weight_text")):
        quantity = _quantity(text, pointer, "source_title_or_weight")
        if quantity:
            quantities.append(quantity)
    variant = information.get("selected_variant", {})
    if isinstance(variant, dict):
        variant_title = variant.get("title")
        quantity = _quantity(variant_title, INFO + "/selected_variant/title", "selected_variant_title")
        if quantity:
            quantities.append(quantity)
        if variant.get("grams") is not None:
            warnings.append("Shopify variant grams was retained in raw evidence and excluded from edible-weight normalization.")
    body_html = information.get("body_html")
    body_text = _html_text(body_html)
    for line in body_text.splitlines():
        if re.match(r"^(?:net\s+)?weight\s*[:\-]?\s*\d", line, re.I) or re.fullmatch(MASS + r"\s*(?:bag|bar|box|pack)?", line, re.I):
            quantity = _quantity(line, INFO + "/body_html", "decoded_explicit_body_weight")
            if quantity:
                quantity["raw_value"] = body_html
                quantities.append(quantity)
    statements = list(_statements(information))
    # Where no prepared ingredient statement exists, a labeled body paragraph
    # can be retained with its HTML as the supporting raw value.
    if not any(kind == "ingredients_text" for kind, _, _, _ in statements):
        for line in body_text.splitlines():
            match = re.search(r"\bingredients\s*:\s*(.+)", line, re.I)
            if match:
                statements.append(("ingredients_text", match.group(1), INFO + "/body_html", "decoded_labeled_ingredient_paragraph"))
    for kind, text, pointer, method in statements:
        features.append(_feature(kind, text, pointer, method, raw_value=body_html if pointer == INFO + "/body_html" else None))
        features.extend(_nut_features(text, pointer, kind))
    # Only product-specific titles, descriptions and bounded source statements
    # support claims; full pages include store navigation and unrelated products.
    claim_contexts = [(name, name_pointer, "source_product_name")]
    if body_text:
        claim_contexts.append((body_text, INFO + "/body_html", "decoded_product_description"))
    claim_contexts.extend((text, pointer, method) for kind, text, pointer, method in statements if kind != "nutrition_text")
    tags = product.get("tags", []) if isinstance(product, dict) else []
    if isinstance(tags, list):
        product_pointer = INFO + "/shopify_product" if "shopify_product" in information else INFO
        claim_contexts.extend((tag, product_pointer + "/tags/" + str(index), "source_product_tag") for index, tag in enumerate(tags) if isinstance(tag, str))
    for text, pointer, method in claim_contexts:
        features.extend(_nut_features(text, pointer, "claim_text"))
        for term, key in ((r"\bfairtrade\b", "fairtrade_claim"), (r"\bfair[\s-]+trade\b", "fair_trade_claim"), (r"\borganic\b", "organic_claim"), (r"\bvegans?\b", "vegan_claim")):
            if re.search(term, text, re.I):
                features.append(_feature("claim_text", text, pointer, method))
            if _positive_claim(text, term):
                features.append(_feature(key, "present", pointer, "source_claim_term", "presence", raw_value=text))
        for match in re.finditer(r"(?:cocoa\s+solids?\s*[:\-]?\s*(?:of\s*)?(?:minimum|min\.?|at least)?\s*|cocoa\s+content\s*[:\-]?\s*)(\d+(?:\.\d+)?)\s*%|(\d+(?:\.\d+)?)\s*%\s*cocoa\b", text, re.I):
            value = parse_money(match.group(1) or match.group(2))
            if value is not None and value <= 100:
                assertion = _feature("cocoa_percentage", float(value), pointer, "explicit_cocoa_percentage", "number", "%", text)
                nearby = text[max(0, match.start() - 35):match.end() + 25]
                assertion["qualifier"] = "minimum" if re.search(r"\bmin(?:imum)?\.?\b|at least", nearby, re.I) else "source_stated"
                assertion["scope"] = "source_declared_chocolate"
                features.append(assertion)
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%\s+(?:dark|milk|white|ruby)\s+chocolate\b", name, re.I):
        value = parse_money(match.group(1))
        if value is not None and value <= 100:
            assertion = _feature("cocoa_percentage", float(value), name_pointer, "explicit_chocolate_name_percentage", "number", "%", name)
            assertion.update(qualifier="source_stated", scope="source_declared_chocolate")
            features.append(assertion)
    chocolate_types = re.findall(r"\b(dark|milk|white|ruby)\s+chocolate\b", name, re.I)
    if len(set(value.lower() for value in chocolate_types)) == 1:
        features.append(_feature("chocolate_type", chocolate_types[0].lower(), name_pointer, "explicit_product_name_type", "categorical", raw_value=name))
    observed_at, time_basis = _source_time(capture, information, source)
    currency = information.get("source_price_currency") or information.get("catalogue_retrieval_currency")
    if isinstance(variant, dict) and "price" in variant:
        available = variant.get("available") if isinstance(variant.get("available"), bool) else None
        raw_display = variant.get("price")
        raw_ref = variant.get("compare_at_price")
        price_unit = information.get("source_price_unit")
        price_method = "shopify_major_unit_price"
        def unit_amount(value):
            if price_unit == "minor":
                amount = parse_money(value)
                return amount / 100 if amount is not None else None
            if price_unit == "major" or (price_unit is None and isinstance(value, str)):
                return value
            return None
        display_value = unit_amount(raw_display)
        ref = unit_amount(raw_ref)
        if price_unit == "minor":
            price_method = "shopify_explicit_minor_unit_price"
        elif price_unit == "major":
            price_method = "shopify_explicit_major_unit_price"
        elif not isinstance(raw_display, str):
            warnings.append("Numeric Shopify prices have an unconfirmed major/minor currency unit and were excluded from normalization.")
        comparison = parse_money(ref)
        display = parse_money(display_value)
        promo = "Source compare-at price: " + str(ref) if comparison is not None and display is not None and comparison > display else None
        price = _price(display_value, INFO + "/selected_variant/price", price_method, currency, observed_at, time_basis, reference=ref, promotion=promo, available=available, allow_invalid=True)
        if price:
            price["raw_value"] = raw_display
            if raw_ref is not None:
                price["reference_price_raw_value"] = raw_ref
            prices.append(price)
        if price and price["displayed_price"] is None:
            warnings.append("Selected variant price was nonpositive, nonfinite or invalid and was excluded.")
        if source == "tonys-uk":
            warnings.append("Tony's catalogue prices may differ from VAT-inclusive rendered prices; no tax conversion or price reconciliation was applied.")
    if source == "waitrose":
        context = information.get("catalogue_text_context", "")
        if isinstance(context, str):
            displayed = _pounds_after(r"\bItem price", context)
            reference = _pounds_after(r"\bWas", context)
            promotion = "\n".join(line for line in context.splitlines() if re.search(r"\b(?:save|was|offer|for\s+£)\b", line, re.I)) or None
            price = _price(displayed, INFO + "/catalogue_text_context", "waitrose_explicit_item_price", currency, observed_at, time_basis, reference=reference, promotion=promotion)
            if price:
                price["raw_value"] = context
                prices.append(price)
    if source == "ocado":
        listing = information.get("original_listing_record", {})
        card = listing.get("card", {}) if isinstance(listing, dict) else {}
        if isinstance(card, dict) and isinstance(card.get("text"), str):
            listing_time = None
            for artifact in capture.get("source_artifacts", []):
                desc = artifact.get("descriptor", {})
                metadata = desc.get("catalogue_retrieval_metadata", {})
                if isinstance(metadata, dict) and metadata.get("archived_at"):
                    listing_time = metadata["archived_at"]
                    break
            price = _ocado_price(card["text"], INFO + "/original_listing_record/card/text", "ocado_rendered_listing_price", listing_time)
            if price:
                prices.append(price)
        for index, observation in enumerate(information.get("original_category_observations", [])):
            text = observation.get("raw_card_window")
            if isinstance(text, str):
                price = _ocado_price(text, INFO + "/original_category_observations/" + str(index) + "/raw_card_window", "ocado_cached_category_price", cached=True)
                if price:
                    prices.append(price)
        for key in ("original_product_page_observations", "original_web_observations"):
            for index, observation in enumerate(information.get(key, [])):
                if observation.get("response_status") == "failed":
                    continue
                text = observation.get("raw_web_tool_response_block")
                if isinstance(text, str):
                    price = _ocado_price(text, INFO + "/" + key + "/" + str(index) + "/raw_web_tool_response_block", "ocado_cached_product_header_price", observation.get("queried_at"), cached=True, header=True)
                    if price:
                        prices.append(price)
        warnings.append("Ocado visibility does not establish checkout availability without a delivery location.")
    known = {feature["name"] for feature in features}
    for key, value_type in UNKNOWN_FEATURES:
        if key not in known:
            features.append(_feature(key, "unknown" if value_type == "presence" else None, INFO if "information" in raw else "/raw_record", "not_established_by_available_source_evidence", value_type, "%" if key == "cocoa_percentage" else None))
    # Deduplicate the exact same candidate while retaining independent pointers.
    def unique(items):
        seen, result = set(), []
        for item in items:
            fingerprint = repr(sorted(item.items()))
            if fingerprint not in seen:
                seen.add(fingerprint)
                result.append(item)
        return result
    return {"features": unique(features), "quantities": unique(quantities),
            "prices": unique(prices), "group": group,
            "boundary_status": boundary, "warnings": list(dict.fromkeys(warnings))}
