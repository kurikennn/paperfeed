import json
from datetime import date

from pipeline.__main__ import fix_kind, venue_of
from pipeline.config import Config, FieldConfig, load_config
from pipeline.fulltext import html_to_text
from pipeline.models import Candidate, Pick
from pipeline.select import validate_picks
from pipeline.store import Seen, dedupe, update_index, write_day


def cand(i, field="A", **kw):
    return Candidate(id=f"arxiv:{i}", source="arxiv", title=f"Paper {i}", field=field, **kw)


def test_repo_config_loads():
    cfg = load_config()
    assert cfg.fields and cfg.total >= 1


def test_dedupe_and_seen(tmp_path):
    seen = Seen(tmp_path / "seen.json")
    seen.add(cand(1))
    seen.save()
    seen = Seen(tmp_path / "seen.json")
    cands = [cand(1), cand(2), cand(2), Candidate(id="doi:x", source="s", title="paper 2!", field="B")]
    out = dedupe(cands, seen)
    assert [c.id for c in out] == ["arxiv:2"]


def test_validate_picks_limits():
    cfg = Config(total=2, fields=[FieldConfig(name="A", count=1), FieldConfig(name="B", count=5)])
    cands = [cand(1), cand(2), cand(3, field="B"), cand(4, field="B")]
    picks = [Pick(candidate_id=f"arxiv:{i}", field="?", kind="新着", reason="") for i in (1, 2, 99, 3, 3, 4)]
    out = validate_picks(cfg, cands, picks)
    assert [p.candidate_id for p in out] == ["arxiv:1", "arxiv:3"]
    assert out[1].field == "B"


def test_fix_kind():
    c = cand(1, published="2026-10-01")
    p = Pick(candidate_id="arxiv:1", field="A", kind="新着", reason="")
    assert fix_kind(p, c, date(2026, 11, 17), 30) == "通常"
    assert fix_kind(p, c, date(2026, 10, 5), 30) == "新着"


def test_venue():
    assert venue_of(cand(1, arxiv_id="2411.1", categories=["quant-ph"])) == "arXiv:2411.1 [quant-ph]"


def test_html_to_text_keeps_tex():
    html = '<html><body><article><p>Energy <math alttext="E=mc^2"><mi>E</mi></math> holds.</p>' \
           '<math display="block" alttext="\\int f"></math><section class="ltx_bibliography">refs</section></article></body></html>'
    t = html_to_text(html)
    assert "$E=mc^2$" in t and "$$\\int f$$" in t and "refs" not in t


def test_write_day_and_index(tmp_path):
    write_day("2026-11-16", [], tmp_path)
    (tmp_path / "2026-11-17.json").write_text(json.dumps({"date": "2026-11-17", "papers": [{"field": "A"}]}), encoding="utf-8")
    update_index(tmp_path)
    idx = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert [d["date"] for d in idx["days"]] == ["2026-11-17", "2026-11-16"]
    assert idx["days"][0]["fields"] == ["A"]
