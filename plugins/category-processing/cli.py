#!/usr/bin/env python3
"""Run the portable category processing plugin."""

import sys
from pathlib import Path

# Isolated Python removes the script directory from its import path. Resolve
# only this package's local modules so the launcher remains relocatable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from category_processing.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
