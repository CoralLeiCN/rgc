"""Exercise source directories through collection, verification and local export."""

import json
import tarfile

from category_research import import_document
from chocolate_cleanup.deduplication import load_raw_archive
from publish_collections import build_export, verify_export
from verify_product_archive import ArchiveVerifier


def test_source_directories_preserve_history_and_export_evidence(tmp_path):
    root = tmp_path / "collections"
    products = [
        {
            "product_id": source + "-one", "source_key": source,
            "source_url": "https://" + source + ".test/one",
            "identity": {"source_product_id": "one"},
            "information": {"original_field": "Original chocolat noir"},
            "source_artifacts": [{"kind": "text", "content": "Original chocolat noir"}],
            "images": [{"content": "retained image response"}],
        }
        for source in ["shop-a", "shop-b"]
    ]
    document = {"contract_version": "1", "study": {
        "study_id": "layout-test", "category": "chocolate", "market": "uk"}, "products": products}
    first = import_document(document, root)
    first_history = {row["history_path"]: (root / row["history_path"]).read_bytes() for row in first["products"]}
    import_document(document, root)
    archive = load_raw_archive(root)
    assert archive["errors"] == []
    assert set(archive["listings"]) == {"shop-a-one", "shop-b-one"}
    verification = ArchiveVerifier(root, "chocolate", "uk").run([])
    assert verification["verification_status"] == "passed"
    assert verification["counts"]["plugin_product_folders"] == 2
    assert verification["counts"]["history_records_verified"] == 4
    assert all((root / name).read_bytes() == content for name, content in first_history.items())
    output = tmp_path / "export"
    manifest = build_export(root, output)
    verify_export(output, manifest)
    with tarfile.open(output / "evidence/chocolate/uk.tar.gz") as bundle:
        names = bundle.getnames()
        assert not any("/images/" in name for name in names)
        for row in first["products"]:
            index = row["product_json"]
            assert bundle.extractfile(index).read() == (root / index).read_bytes()
            history = json.loads(first_history[row["history_path"]])
            source = history["source_artifacts"][0]["archive_relative_path"]
            assert bundle.extractfile(source).read() == b"Original chocolat noir"
