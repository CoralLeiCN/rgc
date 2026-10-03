#!/usr/bin/env python3
"""Agent Skills entry point using the library bundled within this plugin."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from category_research.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
