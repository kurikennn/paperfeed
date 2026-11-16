"""Step 2: read one paper and write the digest."""
from __future__ import annotations

from pathlib import Path

from .claude import Claude, system_blocks
from .config import Config
from .models import Candidate, Digest

PROMPT = (Path(__file__).parent / "prompts" / "summarize.md").read_text(encoding="utf-8")


def build_user_message(c: Candidate, fulltext: str) -> str:
    meta = (
        f"# 書誌情報\n"
        f"- title: {c.title}\n"
        f"- authors: {', '.join(c.authors)}\n"
        f"- published: {c.published}\n"
        f"- journal: {c.journal or '未掲載（プレプリントのみ）'}\n"
        f"- doi: {c.doi or '-'}\n"
        f"- url: {c.url}\n\n"
        f"# アブストラクト\n{c.abstract}\n"
    )
    if fulltext:
        meta += f"\n# 本文\n{fulltext}\n"
    else:
        meta += "\n# 本文\n（取得できなかった。アブストラクトのみに基づいて書くこと。）\n"
    return meta


def summarize(claude: Claude, cfg: Config, persona: str, c: Candidate, fulltext: str) -> Digest:
    return claude.structured(
        system=system_blocks(PROMPT.format(length=cfg.length), persona),
        user=build_user_message(c, fulltext),
        schema=Digest,
        effort=cfg.claude.summarize_effort,
    )
