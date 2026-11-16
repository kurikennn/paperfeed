"""paperfeed daily run.

    python -m pipeline                 # today's digest (Asia/Tokyo date)
    python -m pipeline --date 2026-11-17
    python -m pipeline --dry-run       # fetch candidates only, no Claude calls
    python -m pipeline --limit 1       # write at most 1 paper (cheap test)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config, load_config, load_persona
from .fulltext import fetch_fulltext
from .models import Candidate, Paper, Pick
from .sources import get_source
from .store import DATA_DIR, Seen, day_path, dedupe, write_day

log = logging.getLogger("paperfeed")


def load_dotenv(path: Path) -> None:
    """Minimal .env loader for local runs (KEY=VALUE lines; existing env wins)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def today_tokyo() -> date:
    tz = os.environ.get("PAPERFEED_TZ", "Asia/Tokyo")
    return datetime.now(ZoneInfo(tz)).date()


def collect(cfg: Config, today: date) -> list[Candidate]:
    out: list[Candidate] = []
    for f in cfg.fields:
        if f.count == 0:
            continue
        since = today - timedelta(days=f.lookback_days)
        field_cands: list[Candidate] = []
        for s in f.sources:
            try:
                field_cands.extend(get_source(s).fetch(f, since, today))
            except Exception as e:  # one broken source must not stop the run
                log.error("source %s failed for %s: %s", s, f.name, e)
        field_cands.sort(key=lambda c: c.published, reverse=True)
        out.extend(field_cands)
    return out


def cap_per_field(cfg: Config, cands: list[Candidate]) -> list[Candidate]:
    count: dict[str, int] = {}
    out = []
    for c in cands:
        n = count.get(c.field, 0)
        if n < cfg.max_candidates_per_field:
            out.append(c)
            count[c.field] = n + 1
    return out


def venue_of(c: Candidate) -> str:
    if c.source == "arxiv" or c.arxiv_id:
        cat = f" [{c.categories[0]}]" if c.categories else ""
        return f"arXiv:{c.arxiv_id}{cat}"
    return {"biorxiv": "bioRxiv", "medrxiv": "medRxiv", "pubmed": "PubMed", "semanticscholar": "Semantic Scholar"}.get(c.source, c.source)


def fix_kind(p: Pick, c: Candidate, today: date, new_days: int) -> str:
    try:
        pub = date.fromisoformat(c.published[:10])
    except ValueError:
        return p.kind
    is_new = (today - pub).days <= new_days
    if p.kind == "新着" and not is_new:
        return "通常"
    if p.kind == "通常" and is_new:
        return "新着"
    return p.kind


def make_paper(day: date, order: int, p: Pick, c: Candidate, digest, kind: str) -> Paper:
    return Paper(
        id=f"{day.isoformat()}-{order}",
        date=day.isoformat(),
        order=order,
        field=c.field,
        kind=kind,
        source=c.source,
        title=c.title,
        authors=c.authors,
        published=c.published,
        venue=venue_of(c),
        journal=c.journal or "未掲載（プレプリントのみ）",
        doi=c.doi,
        url=c.url,
        pdf_url=c.pdf_url,
        arxiv_id=c.arxiv_id,
        abstract=c.abstract,
        reason=p.reason,
        **digest.model_dump(),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="paperfeed")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in Asia/Tokyo)")
    ap.add_argument("--dry-run", action="store_true", help="fetch candidates only; write placeholder digests without calling Claude")
    ap.add_argument("--limit", type=int, default=0, help="write at most N papers")
    ap.add_argument("--force", action="store_true", help="overwrite an existing day file")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    from .config import ROOT

    load_dotenv(ROOT / ".env")
    cfg = load_config()
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY is not set (GitHub Secrets, environment, or .env)")
        return 2
    persona = load_persona()
    today = date.fromisoformat(args.date) if args.date else today_tokyo()
    log.info("date: %s", today)

    if day_path(today.isoformat(), args.data_dir).exists() and not args.force:
        log.info("already have %s; nothing to do (use --force to redo)", today)
        return 0

    seen = Seen()
    cands = cap_per_field(cfg, dedupe(collect(cfg, today), seen))
    log.info("candidates after dedupe: %d", len(cands))
    for f in cfg.fields:
        log.info("  %s: %d", f.name, sum(1 for c in cands if c.field == f.name))
    if not cands:
        log.warning("no candidates; nothing written")
        return 0

    by_id = {c.id: c for c in cands}

    if args.dry_run:
        from .models import Digest
        from .select import validate_picks

        picks = validate_picks(cfg, cands, [Pick(candidate_id=c.id, field=c.field, kind="新着", reason="(dry-run)") for c in cands])
        if args.limit:
            picks = picks[: args.limit]
        papers = []
        for i, p in enumerate(picks, 1):
            c = by_id[p.candidate_id]
            d = Digest(summary=c.abstract[:300], background="(dry-run)", method="(dry-run)", results="(dry-run)",
                       relation="(dry-run)", recommend="(dry-run)", note="dry-run: Claude は呼んでいない")
            papers.append(make_paper(today, i, p, c, d, fix_kind(p, c, today, cfg.new_within_days)))
        path = write_day(today.isoformat(), papers, args.data_dir)
        log.info("dry-run wrote %d papers to %s (seen.json not updated)", len(papers), path)
        return 0

    from .claude import Claude
    from .select import select
    from .summarize import summarize

    claude = Claude(cfg.claude)
    picks = select(claude, cfg, persona, cands, today)
    if args.limit:
        picks = picks[: args.limit]
    log.info("selected %d papers", len(picks))

    papers: list[Paper] = []
    failures = 0
    for p in picks:
        c = by_id[p.candidate_id]
        log.info("reading: %s", c.title)
        text, note = fetch_fulltext(c)
        try:
            digest = summarize(claude, cfg, persona, c, text)
        except Exception as e:
            failures += 1
            log.error("summarize failed for %s: %s", c.id, e)
            continue
        if note and not digest.note:
            digest.note = note
        papers.append(make_paper(today, len(papers) + 1, p, c, digest, fix_kind(p, c, today, cfg.new_within_days)))
        seen.add(c)

    if papers:
        path = write_day(today.isoformat(), papers, args.data_dir)
        seen.save()
        log.info("wrote %d papers to %s", len(papers), path)
    log.info("done: %d written, %d failed", len(papers), failures)
    for x in papers:
        log.info("  [%s] %s", x.field, x.title)
    return 1 if failures and not papers else 0


if __name__ == "__main__":
    sys.exit(main())
