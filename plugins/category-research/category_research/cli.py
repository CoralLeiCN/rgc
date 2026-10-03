"""Command-line entry point for another agent or plugin to call."""

import argparse
import json
import sys
from pathlib import Path

from .archive import DEFAULT_MAX_BYTES, ArchiveError, import_document


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preserve broad raw product records and original evidence without a feature taxonomy.")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="Archive a supplied JSON collection document.")
    importer.add_argument("--input", type=Path, required=True)
    importer.add_argument("--output", type=Path, required=True, help="Archive root; category/market directories are created below it.")
    importer.add_argument("--download-images", action="store_true")
    importer.add_argument("--image-limit", type=int, default=None, help="Maximum fetched images per product; omitted means all supplied references.")
    importer.add_argument("--fetch-pages", action="store_true", help="Fetch URL-only source artifacts, or source_url when no artifact is supplied.")
    importer.add_argument("--workers", type=int, default=4)
    importer.add_argument("--timeout", type=float, default=20)
    importer.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    importer.add_argument("--input-base", type=Path, help="Base for local artifact paths; defaults to the import document's directory.")
    importer.add_argument("--quiet-progress", action="store_true", help="Suppress per-product JSON progress on stderr.")
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0 or args.max_bytes < 1:
            raise ArchiveError("timeout and max-bytes must be positive.")
        document = json.loads(args.input.read_text(encoding="utf-8"))
        result = import_document(document, args.output, download_images=args.download_images,
            image_limit=args.image_limit, fetch_pages=args.fetch_pages, workers=args.workers,
            timeout=args.timeout, max_bytes=args.max_bytes, input_base=args.input_base or args.input.resolve().parent,
            progress=None if args.quiet_progress else lambda event: print(json.dumps({
                key: event[key] for key in ("completed", "total", "product_id", "status", "image_files_saved") if key in event
            }), file=sys.stderr, flush=True))
    except (ArchiveError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    summary = {key: result[key] for key in ("run_id", "status", "completeness", "records_received", "unique_product_ids", "unique_http_transfers", "report_path", "section_presence_contract_version")}
    summary.update({"image_files_saved": sum(item.get("image_files_saved", 0) for item in result["products"]),
                    "source_files_saved": sum(item.get("source_files_saved", 0) for item in result["products"]),
                    "failed_products": sum(item["status"] == "failed" for item in result["products"]),
                    "section_fields_unknown": {name: sum(item.get("section_field_statuses", {}).get(name) == "unknown" for item in result["products"])
                                               for name in result["collection_sections"]}})
    if "ingredients" in result["collection_sections"]:
        summary["ingredient_fields_unknown"] = summary["section_fields_unknown"]["ingredients"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if any(product["status"] == "failed" for product in result["products"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
