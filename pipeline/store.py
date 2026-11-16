"""Read/write site data and the history of already-introduced papers."""
from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT
from .models import Candidate, Paper, normalize_title

DATA_DIR = ROOT / "site" / "data"
SEEN_PATH = ROOT / "data" / "seen.json"


class Seen:
    """IDs, DOIs and normalized titles of papers already shown."""

    def __init__(self, path: Path = SEEN_PATH):
        self.path = path
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.ids: set[str] = set(raw.get("ids", []))
        self.dois: set[str] = set(raw.get("dois", []))
        self.titles: set[str] = set(raw.get("titles", []))

    def contains(self, c: Candidate) -> bool:
        return (
            c.id in self.ids
            or (c.doi and c.doi.lower() in self.dois)
            or c.title_key() in self.titles
        )

    def add(self, c: Candidate) -> None:
        self.ids.add(c.id)
        if c.doi:
            self.dois.add(c.doi.lower())
        self.titles.add(c.title_key())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: sorted(v) for k, v in (("ids", self.ids), ("dois", self.dois), ("titles", self.titles))}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def dedupe(cands: list[Candidate], seen: Seen) -> list[Candidate]:
    """Remove already-seen papers and duplicates across sources/queries (first wins)."""
    out: list[Candidate] = []
    ids: set[str] = set()
    dois: set[str] = set()
    titles: set[str] = set()
    for c in cands:
        tk = normalize_title(c.title)
        if not c.title or seen.contains(c) or c.id in ids or tk in titles or (c.doi and c.doi.lower() in dois):
            continue
        ids.add(c.id)
        titles.add(tk)
        if c.doi:
            dois.add(c.doi.lower())
        out.append(c)
    return out


def day_path(day: str, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{day}.json"


def write_day(day: str, papers: list[Paper], data_dir: Path = DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    p = day_path(day, data_dir)
    payload = {"date": day, "papers": [x.model_dump() for x in papers]}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    update_index(data_dir)
    return p


def update_index(data_dir: Path = DATA_DIR) -> None:
    days = []
    for f in sorted(data_dir.glob("????-??-??.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        fields = sorted({x.get("field", "") for x in d.get("papers", [])} - {""})
        days.append({"date": d.get("date", f.stem), "count": len(d.get("papers", [])), "fields": fields})
    (data_dir / "index.json").write_text(
        json.dumps({"days": days}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
