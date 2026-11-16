"""Data models shared by sources, Claude calls and the site JSON."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel


class Candidate(BaseModel):
    """A paper found by a source adapter, before selection."""

    id: str  # stable key, e.g. "arxiv:2411.01234", "doi:10.1101/..." or "pmid:123"
    source: str
    title: str
    authors: list[str] = []
    abstract: str = ""
    published: str = ""  # YYYY-MM-DD (first submission / publication)
    updated: str = ""
    url: str = ""
    pdf_url: str = ""
    html_url: str = ""  # full-text HTML if known
    doi: str = ""
    journal: str = ""  # journal / venue if published
    arxiv_id: str = ""
    categories: list[str] = []
    field: str = ""  # config field name that found it

    def title_key(self) -> str:
        return normalize_title(self.title)


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


# ---- Claude structured outputs -------------------------------------------------


class Pick(BaseModel):
    candidate_id: str
    field: str
    kind: Literal["新着", "通常", "古典"]
    reason: str


class Selection(BaseModel):
    picks: list[Pick]


class Digest(BaseModel):
    """The body Claude writes for one paper."""

    summary: str
    background: str
    method: str
    results: str
    relation: str
    recommend: str
    note: str


# ---- Site JSON -----------------------------------------------------------------


class Paper(BaseModel):
    id: str
    date: str
    order: int
    field: str
    kind: str
    source: str
    title: str
    authors: list[str]
    published: str
    venue: str  # e.g. "arXiv:2411.01234 [quant-ph]" / "bioRxiv"
    journal: str  # "未掲載（arXiv のみ）" or journal name
    doi: str
    url: str
    pdf_url: str
    arxiv_id: str
    abstract: str
    reason: str
    summary: str
    background: str
    method: str
    results: str
    relation: str
    recommend: str
    note: str
