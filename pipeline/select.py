"""Step 1: ask Claude to pick today's papers from the candidates."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from .claude import Claude, system_blocks
from .config import Config
from .models import Candidate, Pick, Selection

PROMPT = (Path(__file__).parent / "prompts" / "select.md").read_text(encoding="utf-8")


def format_candidates(cfg: Config, cands: list[Candidate]) -> str:
    by_field: dict[str, list[Candidate]] = defaultdict(list)
    for c in cands:
        by_field[c.field].append(c)
    lines: list[str] = []
    for f in cfg.fields:
        items = by_field.get(f.name, [])
        lines.append(f"## 分野: {f.name}（本数: {f.count}）\n")
        if not items:
            lines.append("（候補なし）\n")
        for c in items:
            authors = ", ".join(c.authors[:6]) + (" ほか" if len(c.authors) > 6 else "")
            lines.append(
                f"- id: {c.id}\n  title: {c.title}\n  authors: {authors}\n  published: {c.published}\n"
                f"  journal: {c.journal or '-'}\n  abstract: {c.abstract[:1500]}\n"
            )
    return "\n".join(lines)


def select(claude: Claude, cfg: Config, persona: str, cands: list[Candidate], today: date) -> list[Pick]:
    instructions = PROMPT.format(total=cfg.total, new_within_days=cfg.new_within_days, today=today.isoformat())
    result = claude.structured(
        system=system_blocks(instructions, persona),
        user="# 候補一覧\n\n" + format_candidates(cfg, cands),
        schema=Selection,
        effort=cfg.claude.select_effort,
        max_tokens=16000,
    )
    return validate_picks(cfg, cands, result.picks)


def validate_picks(cfg: Config, cands: list[Candidate], picks: list[Pick]) -> list[Pick]:
    """Drop unknown ids / duplicates and enforce per-field and total limits."""
    known = {c.id: c for c in cands}
    limits = {f.name: f.count for f in cfg.fields}
    used: dict[str, int] = defaultdict(int)
    out: list[Pick] = []
    seen: set[str] = set()
    for p in picks:
        c = known.get(p.candidate_id)
        if c is None or p.candidate_id in seen:
            continue
        p.field = c.field  # trust our own record over the model's echo
        if used[p.field] >= limits.get(p.field, 0) or len(out) >= cfg.total:
            continue
        used[p.field] += 1
        seen.add(p.candidate_id)
        out.append(p)
    return out
