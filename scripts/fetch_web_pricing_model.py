"""Materialize the immutable web demo model; never train or publish artifacts."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

APP = Path(__file__).resolve().parents[1] / "apps" / "web"


def verify(data, entry):
    if len(data) != entry["byteLength"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError("Web pricing model integrity mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    reference = json.loads((APP / "pricing-model.json").read_text())
    cache = APP / "model-cache"
    cache.mkdir(exist_ok=True)
    for name, entry in reference["files"].items():
        path = cache / name
        if path.exists():
            verify(path.read_bytes(), entry)
        else:
            if args.offline:
                raise FileNotFoundError("Fetch the pinned web pricing model before offline use")
            url = (f"https://huggingface.co/datasets/{reference['repoId']}/resolve/"
                   f"{reference['revision']}/{reference['path']}/{name}")
            with urlopen(url, timeout=60) as response:
                data = response.read(entry["byteLength"] + 1)
            verify(data, entry)
            path.write_bytes(data)
    print("Verified immutable synthetic web pricing model; no market validation claimed.")


if __name__ == "__main__":
    main()
