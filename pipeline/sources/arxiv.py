"""arXiv API adapter (https://info.arxiv.org/help/api/)."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import date

from ..config import FieldConfig
from ..models import Candidate
from .base import Source, client, get_with_retry, log

API = "https://export.arxiv.org/api/query"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
# arXiv asks for at most one request every 3 seconds.
DELAY = 3.1


def build_query(field: FieldConfig, query: str, since: date, until: date) -> str:
    parts = []
    if field.categories:
        cats = " OR ".join(f"cat:{c}" for c in field.categories)
        parts.append(f"({cats})")
    words = [w for w in re.split(r"\s+", query.strip()) if w]
    if words:
        parts.append("(" + " AND ".join(f"all:{w}" for w in words) + ")")
    parts.append(f"submittedDate:[{since:%Y%m%d}0000 TO {until:%Y%m%d}2359]")
    return " AND ".join(parts)


def _text(el: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", el.text or "").strip() if el is not None else ""


def parse_feed(xml_text: str, field_name: str = "") -> list[Candidate]:
    root = ET.fromstring(xml_text)
    out: list[Candidate] = []
    for e in root.findall("a:entry", NS):
        abs_url = _text(e.find("a:id", NS))
        m = re.search(r"abs/([^v\s]+)(v\d+)?$", abs_url)
        if not m:
            continue
        aid = m.group(1)
        pdf = ""
        for link in e.findall("a:link", NS):
            if link.get("title") == "pdf":
                pdf = link.get("href", "")
        cats = [c.get("term", "") for c in e.findall("a:category", NS)]
        out.append(
            Candidate(
                id=f"arxiv:{aid}",
                source="arxiv",
                title=_text(e.find("a:title", NS)),
                authors=[_text(a.find("a:name", NS)) for a in e.findall("a:author", NS)],
                abstract=_text(e.find("a:summary", NS)),
                published=_text(e.find("a:published", NS))[:10],
                updated=_text(e.find("a:updated", NS))[:10],
                url=f"https://arxiv.org/abs/{aid}",
                pdf_url=pdf or f"https://arxiv.org/pdf/{aid}",
                html_url=f"https://arxiv.org/html/{aid}",
                doi=_text(e.find("arxiv:doi", NS)),
                journal=_text(e.find("arxiv:journal_ref", NS)),
                arxiv_id=aid,
                categories=[c for c in cats if c],
                field=field_name,
            )
        )
    return out


class ArxivSource(Source):
    name = "arxiv"

    def __init__(self, max_results: int = 50):
        self.max_results = max_results

    def fetch(self, field: FieldConfig, since: date, until: date) -> list[Candidate]:
        queries = field.queries or [""]
        out: list[Candidate] = []
        with client() as c:
            for i, q in enumerate(queries):
                if i:
                    time.sleep(DELAY)
                params = {
                    "search_query": build_query(field, q, since, until),
                    "start": 0,
                    "max_results": self.max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
                try:
                    r = get_with_retry(c, API, params=params)
                except Exception as e:  # keep other queries going
                    log.error("arXiv query %r failed: %s", q, e)
                    continue
                got = parse_feed(r.text, field.name)
                log.info("arXiv %r: %d", q, len(got))
                out.extend(got)
        return out
