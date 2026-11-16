"""Common helpers for source adapters."""
from __future__ import annotations

import logging
import time
from datetime import date

import httpx

from ..config import FieldConfig
from ..models import Candidate

log = logging.getLogger("paperfeed.sources")

USER_AGENT = "paperfeed/0.1 (+https://github.com/; daily paper digest)"


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    )


def get_with_retry(c: httpx.Client, url: str, *, params=None, headers=None, tries: int = 3, wait: float = 5.0) -> httpx.Response:
    """GET with simple backoff for 429/5xx (arXiv and S2 throttle aggressively)."""
    last: Exception | None = None
    for i in range(tries):
        try:
            r = c.get(url, params=params, headers=headers)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r
        except (httpx.HTTPError,) as e:  # network or status
            last = e
            log.warning("GET %s failed (%s), retry %d/%d", url, e, i + 1, tries)
            time.sleep(wait * (i + 1))
    assert last is not None
    raise last


def matches_queries(text: str, queries: list[str]) -> bool:
    """Local keyword filter: every word of at least one query appears in text."""
    if not queries:
        return True
    low = text.lower()
    return any(all(w in low for w in q.lower().split()) for q in queries)


class Source:
    name: str = ""

    def fetch(self, field: FieldConfig, since: date, until: date) -> list[Candidate]:  # pragma: no cover
        raise NotImplementedError
