"""Fetch the full text of a paper as plain text (arXiv HTML first)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .models import Candidate
from .sources.base import client, log

MAX_CHARS = 180_000  # ~45k tokens; plenty for most papers, keeps cost bounded


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg"]):
        tag.decompose()
    # arXiv (LaTeXML) keeps TeX source in <math alttext="...">; use it so equations survive.
    for m in soup.find_all("math"):
        alt = m.get("alttext")
        disp = m.get("display") == "block"
        m.replace_with(f" $${alt}$$ " if disp and alt else f" ${alt}$ " if alt else m.get_text(" "))
    for ref in soup.select(".ltx_bibliography, #bib, .references"):
        ref.decompose()
    main = soup.select_one("article, main, .ltx_document, #main-content") or soup.body or soup
    text = main.get_text("\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def fetch_fulltext(c: Candidate) -> tuple[str, str]:
    """Return (text, note). note explains what could not be read ("" = full text)."""
    urls = [u for u in [c.html_url] if u]
    with client() as http:
        for url in urls:
            try:
                r = http.get(url)
                if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
                    log.info("full text unavailable at %s (%s)", url, r.status_code)
                    continue
                text = html_to_text(r.text)
                if len(text) < 2000:  # landing page, not the paper
                    continue
                note = ""
                if len(text) > MAX_CHARS:
                    text = text[:MAX_CHARS]
                    note = "本文が長いため冒頭から一部のみ読んだ。"
                return text, note
            except Exception as e:
                log.warning("full text fetch failed %s: %s", url, e)
    return "", "本文を取得できなかったため、アブストラクトに基づいて書いた。"
