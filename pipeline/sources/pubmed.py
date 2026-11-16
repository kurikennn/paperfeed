"""PubMed adapter via NCBI E-utilities."""
from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date

from ..config import FieldConfig
from ..models import Candidate
from .base import Source, client, get_with_retry, log

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _pubdate(art: ET.Element) -> str:
    for path in ("Journal/JournalIssue/PubDate", "ArticleDate"):
        d = art.find(path)
        if d is None:
            continue
        y = d.findtext("Year")
        if not y:
            continue
        m = d.findtext("Month") or "1"
        m = MONTHS.get(m[:3].lower(), None) or (int(m) if m.isdigit() else 1)
        day = d.findtext("Day") or "1"
        return f"{int(y):04d}-{int(m):02d}-{int(day):02d}"
    return ""


def parse_efetch(xml_text: str, field_name: str = "") -> list[Candidate]:
    root = ET.fromstring(xml_text)
    out: list[Candidate] = []
    for pa in root.findall("PubmedArticle"):
        mc = pa.find("MedlineCitation")
        if mc is None:
            continue
        pmid = mc.findtext("PMID", "")
        art = mc.find("Article")
        if art is None:
            continue
        title = "".join(art.find("ArticleTitle").itertext()) if art.find("ArticleTitle") is not None else ""
        abstract = " ".join(
            ((t.get("Label") + ": ") if t.get("Label") else "") + "".join(t.itertext())
            for t in art.findall("Abstract/AbstractText")
        )
        authors = []
        for a in art.findall("AuthorList/Author"):
            if a.findtext("CollectiveName"):
                authors.append(a.findtext("CollectiveName"))
            else:
                authors.append(" ".join(x for x in [a.findtext("ForeName"), a.findtext("LastName")] if x))
        doi = ""
        pmc = ""
        for aid in pa.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text or ""
            if aid.get("IdType") == "pmc":
                pmc = aid.text or ""
        out.append(
            Candidate(
                id=f"doi:{doi.lower()}" if doi else f"pmid:{pmid}",
                source="pubmed",
                title=re.sub(r"\s+", " ", title).strip(),
                authors=[a for a in authors if a],
                abstract=re.sub(r"\s+", " ", abstract).strip(),
                published=_pubdate(art),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                html_url=f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc}/" if pmc else "",
                doi=doi,
                journal=art.findtext("Journal/Title", ""),
                field=field_name,
            )
        )
    return out


class PubmedSource(Source):
    name = "pubmed"

    def __init__(self, retmax: int = 40):
        self.retmax = retmax
        self.api_key = os.environ.get("NCBI_API_KEY", "")

    def _params(self, **kw):
        if self.api_key:
            kw["api_key"] = self.api_key
        return kw

    def fetch(self, field: FieldConfig, since: date, until: date) -> list[Candidate]:
        out: list[Candidate] = []
        delay = 0.15 if self.api_key else 0.4
        with client() as c:
            for q in field.queries:
                try:
                    r = get_with_retry(
                        c,
                        f"{EUTILS}/esearch.fcgi",
                        params=self._params(
                            db="pubmed", term=q, retmode="json", retmax=self.retmax, sort="pub_date",
                            datetype="edat", mindate=since.strftime("%Y/%m/%d"), maxdate=until.strftime("%Y/%m/%d"),
                        ),
                    )
                    ids = r.json().get("esearchresult", {}).get("idlist", [])
                    time.sleep(delay)
                    if not ids:
                        continue
                    r = get_with_retry(
                        c, f"{EUTILS}/efetch.fcgi",
                        params=self._params(db="pubmed", id=",".join(ids), retmode="xml"),
                    )
                    time.sleep(delay)
                    got = parse_efetch(r.text, field.name)
                    log.info("PubMed %r: %d", q, len(got))
                    out.extend(got)
                except Exception as e:
                    log.error("PubMed query %r failed: %s", q, e)
        return out
