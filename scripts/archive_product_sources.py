#!/usr/bin/env python3
"""Archive public product sources and images without an analytical feature schema."""

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from uuid import uuid4


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


class PageContent(HTMLParser):
    """Keep source wording, table rows, headings, metadata, and embedded JSON."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.headings = []
        self.sections = [{"heading": None, "text_fragments": []}]
        self.metadata = []
        self.images = []
        self.embedded_json = []
        self.tables = []
        self.hidden_depth = 0
        self.script = None
        self.heading = None
        self.title = []
        self.in_title = False
        self.table = None
        self.row = None
        self.cell = None
        self.ancestors = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self.hidden_depth += 1
            if tag == "script" and "json" in attributes.get("type", "").lower():
                self.script = {"attributes": attributes, "fragments": []}
        elif tag == "title" and any(item["tag"] == "head" for item in self.ancestors):
            self.in_title = True
        elif tag == "meta":
            self.metadata.append(attributes)
        elif tag == "img":
            self.images.append({"attributes": attributes, "ancestor_context": self.ancestors[-10:].copy()})
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = {"level": int(tag[1]), "fragments": []}
        elif tag == "table":
            self.table = {"rows": []}
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        if tag in ("p", "li", "br", "div", "tr"):
            self.text.append("\n")
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            self.ancestors.append({"tag": tag, "attributes": {
                key: value for key, value in attributes.items()
                if key in ("id", "class", "data-target", "data-testid", "role", "aria-label")
            }})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.script is not None:
            self.script["fragments"].append(data)
        if self.in_title:
            self.title.append(data)
        if self.hidden_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        self.text.append(value + " ")
        if self.heading is not None:
            self.heading["fragments"].append(value)
        else:
            self.sections[-1]["text_fragments"].append(value)
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden_depth = max(0, self.hidden_depth - 1)
            if tag == "script" and self.script is not None:
                raw = "".join(self.script.pop("fragments"))
                self.script["raw_text"] = raw
                try:
                    self.script["value"] = json.loads(raw)
                except json.JSONDecodeError:
                    try:
                        self.script["value"] = json.loads(raw, strict=False)
                        self.script["parse_method"] = "non-strict JSON decoding; original text retained"
                    except json.JSONDecodeError:
                        pass
                self.embedded_json.append(self.script)
                self.script = None
        elif tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self.heading:
            heading = " ".join(self.heading["fragments"])
            self.headings.append({"level": self.heading["level"], "text": heading})
            self.sections.append({"heading": heading, "text_fragments": []})
            self.heading = None
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None
        for index in range(len(self.ancestors) - 1, -1, -1):
            if self.ancestors[index]["tag"] == tag:
                del self.ancestors[index:]
                break

    def result(self):
        return {
            "title": " ".join(self.title).strip(),
            "metadata": self.metadata,
            "headings": self.headings,
            "sections": self.sections,
            "tables": self.tables,
            "embedded_json": self.embedded_json,
            "image_references": self.images,
        }


def fetch(url, limit=30 * 1024 * 1024):
    if urlparse(url).scheme != "https":
        return {"url": url, "status": "failed", "error": "Only HTTPS sources are supported."}, b""
    result = {"url": url, "retrieved_at": timestamp()}
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-GB,en;q=0.9"})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read(limit + 1)
            result.update({
                "status": "downloaded" if len(body) <= limit else "truncated",
                "http_status": response.status,
                "final_url": response.url,
                "content_type": response.headers.get("Content-Type", ""),
                "charset": response.headers.get_content_charset() or "utf-8",
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            })
    except HTTPError as error:
        body = error.read(limit)
        result.update({"status": "failed", "http_status": error.code, "error": str(error), "content_type": error.headers.get("Content-Type", "")})
    except (URLError, TimeoutError, OSError) as error:
        body = b""
        result.update({"status": "failed", "error": str(error)})
    result.update({"byte_length": len(body), "sha256": hashlib.sha256(body).hexdigest() if body else None})
    return result, body


def identity_text(value):
    value = re.sub(r"(\d)\s+(g|kg|ml|l)\b", r"\1\2", unescape(str(value)).casefold())
    return " ".join(re.findall(r"[a-z0-9]+", value))


def page_identity(url):
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www."), parsed.path.rstrip("/")


def json_objects(value, path="$"):
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from json_objects(item, path + "." + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from json_objects(item, f"{path}[{index}]")


def primary_products(content, page_url):
    headings = {identity_text(item["text"]) for item in content.get("headings", []) if item["level"] == 1}
    matches = []
    for script_index, script in enumerate(content.get("embedded_json", [])):
        for path, node in json_objects(script.get("value")):
            types = node.get("@type", [])
            if "Product" not in (types if isinstance(types, list) else [types]):
                continue
            urls = [node.get("url")]
            for _, offer in json_objects(node.get("offers")):
                urls.append(offer.get("url"))
            urls = [urljoin(page_url, value) for value in urls if isinstance(value, str)]
            matches_page = any(page_identity(url) == page_identity(page_url) for url in urls)
            if matches_page or (not urls and identity_text(node.get("name", "")) in headings):
                matches.append({"script_index": script_index, "json_path": path, "product": node})
    return matches


def product_content_status(content, page_url, product):
    matches = primary_products(content, page_url)
    product_name = identity_text(product.get("name", ""))
    headings = [item["text"] for item in content.get("headings", []) if item["level"] == 1]
    matching_headings = [heading for heading in headings if product_name and product_name in identity_text(heading)]
    return {
        "status": "identifiable_product_content_review_pending" if matches or matching_headings else "no_identifiable_product_content",
        "matched_h1_text": matching_headings,
        "primary_product_names": [match["product"].get("name") for match in matches],
        "completeness": "not_verified",
    }


def asset_identity(url):
    parsed = urlparse(url)
    resizing = {"width", "height", "w", "h", "crop", "fit", "quality", "q", "dpr"}
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() not in resizing]
    return urlunparse(("", parsed.netloc.lower(), parsed.path, "", urlencode(sorted(query)), ""))


def merge_image_candidates(target, incoming):
    for key, candidate in incoming.items():
        if key not in target:
            target[key] = candidate
            continue
        current = target[key]
        observations = current["selection_observations"] + candidate["selection_observations"]
        if candidate["selection_priority"] > current["selection_priority"]:
            target[key] = candidate
            current = candidate
        current["selection_observations"] = observations


def image_urls(content, page_url, product, known_urls, source_key=None):
    """Select one source-referenced rendition per asset; retain uncertain references."""
    candidates = {}

    def add(reference, role, basis, priority, **details):
        if not reference or reference.startswith("data:"):
            return
        url = urljoin(page_url, reference)
        if urlparse(url).scheme not in ("http", "https"):
            return
        selected = priority >= 80
        resizing = {"width", "height", "w", "h", "crop", "fit", "quality", "q", "dpr"}
        original = not any(key.lower() in resizing for key, _ in parse_qsl(urlparse(url).query))
        ranking = priority + (20 if original else 0) + (1 if urlparse(url).scheme == "https" else 0)
        observation = {
            "source_key": source_key, "source_page_url": page_url or None,
            "observed_reference": reference, "resolved_url": url,
            "candidate_role": role, "selection_basis": basis, "alt": None, **details,
        }
        incoming = {asset_identity(url): {
            "url": url, "candidate_role": role, "selected_for_download": selected,
            "selection_priority": ranking, "selection_observations": [observation],
        }}
        merge_image_candidates(candidates, incoming)

    known_items = known_urls.items() if isinstance(known_urls, dict) else ((None, url) for url in known_urls)
    for key, url in known_items:
        add(url, "prior_product_image_reference", "previously inspected seed image; review pending", 90,
            source_key=key, source_page_url=None, observation_kind="seed_source_reference")

    matches = primary_products(content, page_url)
    names = {identity_text(item["text"]) for item in content.get("headings", []) if item["level"] == 1}
    names.update(identity_text(match["product"].get("name", "")) for match in matches)
    identifiable = product_content_status(content, page_url, product)["status"] == "identifiable_product_content_review_pending"
    primary_assets = set()
    for match in matches:
        images = match["product"].get("image", [])
        images = images if isinstance(images, list) else [images]
        for index, image in enumerate(images):
            reference = image if isinstance(image, str) else image.get("contentUrl", image.get("url")) if isinstance(image, dict) else None
            if reference:
                primary_assets.add(asset_identity(urljoin(page_url, reference)))
                add(reference, "structured_primary_product_image", "image of the structured Product matching this page", 95,
                    observation_kind="embedded_product_json", script_index=match["script_index"],
                    json_path=match["json_path"] + f".image[{index}]", structured_product_name=match["product"].get("name"))
    for meta in content.get("metadata", []):
        if meta.get("property") in ("og:image", "og:image:secure_url") and meta.get("content"):
            add(meta["content"], "primary_page_image_candidate" if identifiable else "uncertain_page_image_candidate",
                "primary-image metadata on an identifiable product page" if identifiable else "page image without identifiable product content",
                80 if identifiable else 10, observation_kind="page_metadata", metadata_attributes=meta)
    for image in content.get("image_references", []):
        attributes = image.get("attributes", image)
        context = image.get("ancestor_context", [])
        context_text = " ".join(item.get("tag", "") + " " + " ".join(str(value) for value in item.get("attributes", {}).values()) for item in context).lower()
        gallery = any(marker in context_text for marker in ("product-images", "product-gallery", "product__media", "product-media", "image-slider"))
        related = any(marker in context_text for marker in ("recommend", "related", "upsell", "cross-sell"))
        alt = attributes.get("alt")
        label = re.sub(r"^(?:image|picture|photo)\s+\d+\s+of\s+", "", alt or "", flags=re.I)
        reference = next((attributes.get(key) for key in ("data-original", "src", "data-src") if attributes.get(key) and not attributes[key].startswith("data:")), None)
        if not reference:
            srcset = attributes.get("srcset", attributes.get("data-srcset", ""))
            choices = [item.strip().split() for item in srcset.split(",") if item.strip()]
            if choices:
                reference = max(choices, key=lambda item: float(re.sub(r"[^0-9.]", "", item[-1]) or 0) if len(item) > 1 else 0)[0]
        if not reference:
            continue
        asset = asset_identity(urljoin(page_url, reference))
        if asset in primary_assets:
            role, basis, priority = "structured_primary_product_image", "same asset as the page's primary structured Product image", 90
        elif identifiable and gallery and not related and identity_text(label) in names:
            role, basis, priority = "product_gallery_image_candidate", "gallery label exactly matches the page's product heading/name", 90
        elif related or (gallery and alt and identity_text(label) not in names):
            role, basis, priority = "related_or_different_label_candidate", "related context or gallery label differs from the primary product name", 10
        else:
            role, basis, priority = "uncertain_page_image_candidate", "insufficient primary-product image evidence; not selected", 5
        add(reference, role, basis, priority, observation_kind="html_image", alt=alt,
            image_attributes=attributes, ancestor_context=context)
    return candidates


def archive_product(product, sample, seed_path, root, capture_id):
    product_id = product["product_id"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", product_id):
        raise ValueError("Unsafe product identifier: " + product_id)
    folder = root / product_id
    manifest_path = folder / "product.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "archive_format_version": "draft-raw-1",
        "product_id": product_id,
        "category": sample["category"],
        "market": sample["market"],
        "identity_hints": {key: product[key] for key in ("brand", "name", "form", "net_weight_g") if key in product},
        "prior_extractions": [{"source_file": str(seed_path), "retrieved_on": sample["retrieved_on"], "record": product}],
        "captures": [],
    }
    capture = {"capture_id": capture_id, "started_at": timestamp(), "sources": [], "images": [], "limitations": [
        "HTTP source snapshots may omit JavaScript-rendered or collapsed content; completeness requires later review.",
        "Page text is an HTML-to-text derivative. page.html retains the downloaded response bytes.",
        "Image candidates retain their selection basis; matching a label is not independent product verification.",
        "Related or uncertain image references are retained without download; responsive renditions are consolidated by asset.",
        "Raw product fields and analytical feature schemas have not been finalized."
    ]}
    known_images = {key: url for key, url in product["sources"].items() if "pack" in key or "image" in key}
    candidates = image_urls({}, "", product, known_images)
    for source_key, url in product["sources"].items():
        if "pack" in source_key or "image" in source_key:
            continue
        metadata, body = fetch(url)
        metadata["source_key"] = source_key
        source_folder = folder / "sources" / capture_id / source_key
        source_folder.mkdir(parents=True, exist_ok=True)
        if body or metadata["status"] == "downloaded":
            is_html = "html" in metadata.get("content_type", "").lower()
            raw_path = source_folder / ("page.html" if metadata["status"] == "downloaded" and is_html else "response.body")
            raw_path.write_bytes(body)
            metadata["response_path"] = str(raw_path.relative_to(folder))
        if metadata["status"] == "downloaded" and "html" in metadata["content_type"].lower():
            parser = PageContent()
            parser.feed(body.decode(metadata["charset"], errors="replace"))
            content = parser.result()
            text_path = source_folder / "page.txt"
            text_path.write_text("".join(parser.text))
            metadata["page_text_path"] = str(text_path.relative_to(folder))
            metadata["page_text_sha256"] = hashlib.sha256(text_path.read_bytes()).hexdigest()
            metadata["original_information"] = content
            metadata["product_content_assessment"] = product_content_status(content, metadata["final_url"], product)
            if metadata["product_content_assessment"]["status"] == "no_identifiable_product_content":
                capture["limitations"].append(f"{source_key}: HTTP bytes were retrieved, but identifiable product content was not found.")
            merge_image_candidates(candidates, image_urls(content, metadata["final_url"], product, {}, source_key))
        else:
            metadata["product_content_assessment"] = {
                "status": "not_assessed_non_html" if metadata["status"] == "downloaded" else "retrieval_failed",
                "completeness": "not_verified",
            }
        capture["sources"].append(metadata)
    capture["image_candidates"] = list(candidates.values())
    selected = [candidate for candidate in candidates.values() if candidate["selected_for_download"]]
    if not selected:
        capture["limitations"].append("No image candidate met the primary-product selection criteria.")
    for index, candidate in enumerate(selected, 1):
        metadata, body = fetch(candidate["url"])
        metadata.update({key: value for key, value in candidate.items() if key != "url"})
        media_type = metadata.get("content_type", "").split(";", 1)[0].strip().lower()
        if metadata["status"] == "downloaded" and media_type.startswith("image/") and body:
            extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg", "image/avif": ".avif"}.get(media_type, ".image")
            image_path = folder / "images" / capture_id / (f"{index:03d}-" + metadata["sha256"][:12] + extension)
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(body)
            metadata["path"] = str(image_path.relative_to(folder))
        elif metadata["status"] == "downloaded":
            metadata["status"] = "failed"
            metadata["error"] = "Response was empty or was not an image."
        capture["images"].append(metadata)
    capture["finished_at"] = timestamp()
    content_identified = bool(capture["sources"]) and all(
        item["product_content_assessment"]["status"] == "identifiable_product_content_review_pending"
        for item in capture["sources"]
    )
    capture["status"] = "captured_with_review_pending" if content_identified and selected and all(
        item["status"] == "downloaded" for item in capture["sources"] + capture["images"]
    ) else "partial"
    manifest["captures"].append(capture)
    history_path = folder / "history" / (capture_id + ".json")
    capture["history_path"] = str(history_path.relative_to(folder))
    write_json(history_path, capture)
    write_json(manifest_path, manifest)
    return {
        "product_id": product_id,
        "manifest": str(manifest_path.relative_to(root)),
        "status": capture["status"],
        "source_http_responses_downloaded": sum(item["status"] == "downloaded" for item in capture["sources"]),
        "sources_with_identifiable_product_content": sum(item["product_content_assessment"]["status"] == "identifiable_product_content_review_pending" for item in capture["sources"]),
        "selected_image_candidate_files_downloaded": sum("path" in item for item in capture["images"]),
        "image_candidates_not_selected": len(candidates) - len(selected),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=Path("examples/collections/uk-chocolate-five-products.json"))
    parser.add_argument("--output", type=Path, default=Path("collections/chocolate/uk/products"))
    args = parser.parse_args()
    sample = json.loads(args.seed.read_text())
    capture_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    with ThreadPoolExecutor(max_workers=3) as executor:
        summaries = list(executor.map(lambda product: archive_product(product, sample, args.seed, args.output, capture_id), sample["products"]))
    report = {"capture_id": capture_id, "finished_at": timestamp(), "products": summaries}
    write_json(args.output.parent / "runs" / (capture_id + ".json"), report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
