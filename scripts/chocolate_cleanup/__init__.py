"""Raw deduplication and evidence-preserving UK chocolate analytical datasets."""

from .core import build_dataset
from .deduplication import build_deduplicated_dataset

__all__ = ["build_dataset", "build_deduplicated_dataset"]
