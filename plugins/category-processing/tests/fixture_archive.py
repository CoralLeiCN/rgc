"""Create minimal compatible immutable archives without a collector dependency."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4


def import_document(document, output, workers=1):
    root = Path(output)
    study = document["study"]
    results = []
    for raw in document["products"]:
        listing = raw["product_id"]
        folder = root / study["category"] / study["market"] / "products" / listing
        index_path = folder / "product.json"
        folder.mkdir(parents=True, exist_ok=True)
        index = json.loads(index_path.read_text()) if index_path.exists() else {
            "archive_format_version": "category-research-raw-1", "product_id": listing,
            "category": study["category"], "market": study["market"], "captures": [],
        }
        cid = uuid4().hex
        history = folder / "history" / (cid + ".json")
        capture = {"capture_id": cid, "recorded_at": "2026-10-03T10:00:" + str(len(index["captures"])).zfill(2) + "Z",
                   "history_path": history.relative_to(root).as_posix(), "raw_record": deepcopy(raw),
                   "source_artifacts": [], "images": []}
        for number, descriptor in enumerate(raw.get("source_artifacts", [])):
            content = descriptor.get("content", "").encode("utf-8")
            artifact = folder / "sources" / cid / (str(number) + ".html")
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(content)
            capture["source_artifacts"].append({"descriptor": deepcopy(descriptor), "status": "saved",
                                                "archive_relative_path": artifact.relative_to(root).as_posix(),
                                                "sha256": hashlib.sha256(content).hexdigest()})
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n")
        index["captures"].append(capture)
        index["latest_capture_id"] = cid
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
        results.append({"product_id": listing, "capture_id": cid})
    return {"products": results}
