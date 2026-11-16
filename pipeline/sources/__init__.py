from .arxiv import ArxivSource
from .base import Source
from .biorxiv import BiorxivSource
from .pubmed import PubmedSource
from .semanticscholar import SemanticScholarSource


def get_source(name: str) -> Source:
    if name == "arxiv":
        return ArxivSource()
    if name in ("biorxiv", "medrxiv"):
        return BiorxivSource(name)
    if name == "pubmed":
        return PubmedSource()
    if name == "semanticscholar":
        return SemanticScholarSource()
    raise ValueError(f"unknown source: {name}")


__all__ = ["get_source", "Source"]
