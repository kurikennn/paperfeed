"""bioRxiv / medRxiv adapter (https://api.biorxiv.org/).

The API has no keyword search, so we page through the date range and filter
locally by the field's queries (and optional subject categories).
"""
from __future__ import annotations

from datetime import date

from ..config import FieldConfig
from ..models import Candidate
from .base import Source, client, get_with_retry, log, matches_queries

API = "https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}"
MAX_PAGES = 40  # 100 records per page


def parse_collection(data: dict, server: str, field: FieldConfig) -> list[Candidate]:
    out: list[Candidate] = []
    cats = {c.lower() for c in field.categories}
    seen: dict[str, Candidate] = {}
    for rec in data.get("collection", []):
        if cats and rec.get("category", "").lower() not in cats:
            continue
        text = f"{rec.get('title', '')} {rec.get('abstract', '')}"
        if not matches_queries(text, field.queries):
            continue
        doi = rec.get("doi", "")
        version = rec.get("version", "1")
        base = f"https://www.{server}.org/content/{doi}v{version}"
        cand = Candidate(
            id=f"doi:{doi.lower()}",
            source=server,
            title=" ".join(rec.get("title", "").split()),
            authors=[a.strip() for a in rec.get("authors", "").split(";") if a.strip()],
            abstract=" ".join(rec.get("abstract", "").split()),
            published=rec.get("date", ""),
            url=base,
            pdf_url=base + ".full.pdf",
            html_url=base + ".full",
            doi=doi,
            journal=rec.get("published", "") if rec.get("published", "NA") != "NA" else "",
            categories=[rec.get("category", "")],
            field=field.name,
        )
        seen[cand.id] = cand  # later versions overwrite earlier
    out.extend(seen.values())
    return out


class BiorxivSource(Source):
    def __init__(self, server: str = "biorxiv"):
        self.server = server
        self.name = server

    def fetch(self, field: FieldConfig, since: date, until: date) -> list[Candidate]:
        out: list[Candidate] = []
        cursor = 0
        with client() as c:
            for _ in range(MAX_PAGES):
                url = API.format(server=self.server, start=since.isoformat(), end=until.isoformat(), cursor=cursor)
                try:
                    data = get_with_retry(c, url).json()
                except Exception as e:
                    log.error("%s page %d failed: %s", self.server, cursor, e)
                    break
                out.extend(parse_collection(data, self.server, field))
                msg = (data.get("messages") or [{}])[0]
                total = int(msg.get("total", 0) or 0)
                count = int(msg.get("count", 0) or 0)
                cursor += count
                if count == 0 or cursor >= total:
                    break
        log.info("%s %s: %d", self.server, field.name, len(out))
        return out
