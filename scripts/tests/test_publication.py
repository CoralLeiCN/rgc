"""Check publication boundaries, source preservation, and category portability."""

import gzip
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "publish_collections.py"
SPEC = importlib.util.spec_from_file_location("publish_collections", MODULE_PATH)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "collections"
        self.output = self.base / "export"

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def study(self, category="tea", market="fr"):
        prefix = f"{category}/{market}"
        document = {"product_id": "sample", "identity": {"brand": "Example"}, "captures": [
            {"capture_id": "first", "information": {"unfamiliar_field": "original\u2028source\u2029value"},
             "raw_record": {"source_url": "https://example.com/product"},
             "images": [{"url": "https://example.com/image.png", "archive_relative_path": f"{prefix}/products/sample/images/capture/one.png"}]}]}
        self.put(f"{prefix}/products/sample/product.json", publisher.json_bytes(document))
        return prefix

    def test_preserves_text_and_excludes_images_cache_and_code(self):
        prefix = self.study()
        original = "Original source evidence: café.\n".encode()
        self.put(f"{prefix}/products/sample/sources/capture/page.html", original)
        self.put(f"{prefix}/products/sample/sources/capture/page.html.gz", gzip.compress(original))
        self.put(f"{prefix}/products/sample/images/capture/one.png", b"\x89PNG\r\n\x1a\nimage bytes")
        self.put(f"{prefix}/products/sample/sources/capture/disguised.response", b"\x89PNG\r\n\x1a\nimage bytes")
        self.put(f"{prefix}/transfers/cache.response", original)
        self.put(f"{prefix}/transfers/cache.metadata.json", b'{"status":"downloaded"}')
        self.put(f"{prefix}/discovery/build_import.py", b"print('collection helper')")
        self.put(f"{prefix}/discovery/report.json", b'{"unknown_field":null}')
        self.put(f"{prefix}/discovery/unsupported.txt", b"\xff\xfeunsupported encoding")
        outside = self.base / "outside.txt"
        outside.write_text("must remain local")
        (self.root / prefix / "discovery/linked.txt").symlink_to(outside)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        manifest = publisher.build_export(self.root, self.output)
        publisher.verify_export(self.output, manifest)
        with tarfile.open(self.output / f"evidence/{prefix}.tar.gz") as bundle:
            names = bundle.getnames()
            self.assertEqual(bundle.extractfile(f"{prefix}/products/sample/sources/capture/page.html").read(), original)
            inventory = json.load(bundle.extractfile("export-manifest.json"))
        omissions = {item["path"]: item["reason"] for item in inventory["omitted_files"]}
        self.assertEqual(omissions[f"{prefix}/products/sample/sources/capture/disguised.response"], "binary_content")
        self.assertEqual(omissions[f"{prefix}/transfers/cache.response"], "transfer_cache")
        self.assertEqual(omissions[f"{prefix}/discovery/linked.txt"], "symlink")
        self.assertFalse(any("/images/" in n or "/transfers/" in n or n.endswith(".py") for n in names))
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        first = {name: (self.output / name).read_bytes() for name in manifest["managed_files"]}
        second_manifest = publisher.build_export(self.root, self.output)
        self.assertEqual(manifest, second_manifest)
        self.assertEqual(first, {name: (self.output / name).read_bytes() for name in manifest["managed_files"]})

    def test_discovers_future_categories_and_preserves_arbitrary_fields(self):
        self.study("tea", "fr")
        self.study("shampoo", "us")
        manifest = publisher.build_export(self.root, self.output)
        publisher.verify_export(self.output, manifest)
        self.assertEqual({(s["category"], s["market"]) for s in manifest["studies"]}, {("tea", "fr"), ("shampoo", "us")})
        with (self.output / "products.jsonl").open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual(len(rows), 2)
        self.assertEqual(json.loads(rows[0]["latest_information_json"]), {"unfamiliar_field": "original\u2028source\u2029value"})

    def test_rejects_output_inside_collections_and_detects_corrupt_export(self):
        self.study()
        with self.assertRaises(ValueError):
            publisher.build_export(self.root, self.root / "export")
        manifest = publisher.build_export(self.root, self.output)
        (self.output / manifest["studies"][0]["bundle"]).write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            publisher.verify_export(self.output, manifest)


if __name__ == "__main__":
    unittest.main()
