"""Semantic Scholar Graph API adapter (bulk search)."""
from __future__ import annotations

import os
import time
from datetime import date

from ..config import FieldConfig
from ..models import Candidate
from .base import Source, client, get_with_retry, log

API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "title,abstract,authors,externalIds,publicationDate,venue,journal,openAccessPdf,url,year"


def parse_results(data: dict, field_name: str = "") -> list[Candidate]:
    out: list[Candidate] = []
    for p in data.get("data", []) or []:
        ext = p.get("externalIds") or {}
        doi = ext.get("DOI", "") or ""
        aid = ext.get("ArXiv", "") or ""
        if aid:
            cid = f"arxiv:{aid}"
            url = f"https://arxiv.org/abs/{aid}"
            html = f"https://arxiv.org/html/{aid}"
        else:
            cid = f"doi:{doi.lower()}" if doi else f"s2:{p.get('paperId', '')}"
            url = f"https://doi.org/{doi}" if doi else p.get("url", "")
            html = ""
        journal = ((p.get("journal") or {}).get("name") or p.get("venue") or "").strip()
        if journal.lower() == "arxiv.org":
            journal = ""
        out.append(
            Candidate(
                id=cid,
                source="semanticscholar",
                title=(p.get("title") or "").strip(),
                authors=[a.get("name", "") for a in p.get("authors") or [] if a.get("name")],
                abstract=(p.get("abstract") or "").strip(),
                published=p.get("publicationDate") or (str(p["year"]) if p.get("year") else ""),
                url=url,
                pdf_url=((p.get("openAccessPdf") or {}).get("url") or (f"https://arxiv.org/pdf/{aid}" if aid else "")),
                html_url=html,
                doi=doi,
                journal=journal,
                arxiv_id=aid,
                field=field_name,
            )
        )
    return out


class SemanticScholarSource(Source):
    name = "semanticscholar"

    def __init__(self, limit: int = 40):
        self.limit = limit
        self.api_key = os.environ.get("S2_API_KEY", "")

    def fetch(self, field: FieldConfig, since: date, until: date) -> list[Candidate]:
        headers = {"x-api-key": self.api_key} if self.api_key else None
        out: list[Candidate] = []
        with client() as c:
            for i, q in enumerate(field.queries):
                if i:
                    time.sleep(1.1 if self.api_key else 3.0)
                params = {
                    "query": " + ".join(q.split()),
                    "fields": FIELDS,
                    "publicationDateOrYear": f"{since.isoformat()}:{until.isoformat()}",
                    "sort": "publicationDate:desc",
                }
                if field.fields_of_study:
                    params["fieldsOfStudy"] = ",".join(field.fields_of_study)
                try:
                    r = get_with_retry(c, API, params=params, headers=headers, wait=10)
                except Exception as e:
                    log.error("Semantic Scholar query %r failed: %s", q, e)
                    continue
                got = parse_results(r.json(), field.name)[: self.limit]
                log.info("S2 %r: %d", q, len(got))
                out.extend(got)
        return out
