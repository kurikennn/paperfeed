from datetime import date

from pipeline.config import FieldConfig
from pipeline.sources.arxiv import build_query, parse_feed
from pipeline.sources.biorxiv import parse_collection
from pipeline.sources.pubmed import parse_efetch
from pipeline.sources.semanticscholar import parse_results

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2411.01234v2</id>
    <updated>2024-11-05T10:00:00Z</updated>
    <published>2024-11-02T18:00:00Z</published>
    <title>Thresholds for   surface codes
      under correlated noise</title>
    <summary>  We study $p_c$ thresholds. </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <arxiv:doi>10.1103/PhysRevX.1.2</arxiv:doi>
    <arxiv:journal_ref>Phys. Rev. X 1, 2 (2024)</arxiv:journal_ref>
    <link title="pdf" href="http://arxiv.org/pdf/2411.01234v2" rel="related" type="application/pdf"/>
    <category term="quant-ph" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""


def test_arxiv_parse():
    [c] = parse_feed(ARXIV_XML, "QEC")
    assert c.id == "arxiv:2411.01234"
    assert c.title == "Thresholds for surface codes under correlated noise"
    assert c.authors == ["Alice Smith", "Bob Jones"]
    assert c.published == "2024-11-02"
    assert c.journal.startswith("Phys. Rev. X")
    assert c.html_url == "https://arxiv.org/html/2411.01234"
    assert c.field == "QEC"


def test_arxiv_query():
    f = FieldConfig(name="x", categories=["quant-ph", "cs.LG"])
    q = build_query(f, "surface code", date(2024, 11, 1), date(2024, 11, 7))
    assert q == "(cat:quant-ph OR cat:cs.LG) AND (all:surface AND all:code) AND submittedDate:[202411010000 TO 202411072359]"


def test_biorxiv_parse_filters_and_dedupes_versions():
    data = {
        "collection": [
            {"doi": "10.1101/2024.01.01.1", "title": "Single-cell RNA-seq atlas", "authors": "A, B.; C, D.",
             "date": "2024-11-01", "version": "1", "category": "genomics", "abstract": "x", "published": "NA"},
            {"doi": "10.1101/2024.01.01.1", "title": "Single-cell RNA-seq atlas", "authors": "A, B.; C, D.",
             "date": "2024-11-03", "version": "2", "category": "genomics", "abstract": "x", "published": "NA"},
            {"doi": "10.1101/2024.01.01.2", "title": "Unrelated ecology", "authors": "E",
             "date": "2024-11-03", "version": "1", "category": "ecology", "abstract": "y", "published": "NA"},
        ]
    }
    f = FieldConfig(name="sc", queries=["single-cell"], sources=["biorxiv"])
    [c] = parse_collection(data, "biorxiv", f)
    assert c.id == "doi:10.1101/2024.01.01.1"
    assert c.url.endswith("v2")
    assert c.authors == ["A, B.", "C, D."]


PUBMED_XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>39000001</PMID>
<Article><Journal><JournalIssue><PubDate><Year>2024</Year><Month>Nov</Month><Day>3</Day></PubDate></JournalIssue>
<Title>Nature Methods</Title></Journal><ArticleTitle>A <i>new</i> method</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">Bg.</AbstractText><AbstractText>Rest.</AbstractText></Abstract>
<AuthorList><Author><LastName>Tanaka</LastName><ForeName>Taro</ForeName></Author></AuthorList></Article>
</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1038/x</ArticleId>
<ArticleId IdType="pmc">PMC123</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""


def test_pubmed_parse():
    [c] = parse_efetch(PUBMED_XML)
    assert c.id == "doi:10.1038/x"
    assert c.title == "A new method"
    assert c.abstract == "BACKGROUND: Bg. Rest."
    assert c.published == "2024-11-03"
    assert c.authors == ["Taro Tanaka"]
    assert c.journal == "Nature Methods"
    assert c.html_url.endswith("PMC123/")


def test_s2_parse_prefers_arxiv_id():
    data = {"data": [
        {"paperId": "abc", "title": "T", "abstract": "A", "authors": [{"name": "X"}],
         "externalIds": {"ArXiv": "2411.00001", "DOI": "10.48550/arXiv.2411.00001"},
         "publicationDate": "2024-11-02", "venue": "arXiv.org", "journal": None, "openAccessPdf": None},
        {"paperId": "def", "title": "U", "abstract": None, "authors": [],
         "externalIds": {"DOI": "10.1/Y"}, "publicationDate": None, "year": 2023,
         "journal": {"name": "J"}, "openAccessPdf": {"url": "https://x/pdf"}},
    ]}
    a, b = parse_results(data)
    assert a.id == "arxiv:2411.00001" and a.journal == ""
    assert b.id == "doi:10.1/y" and b.journal == "J" and b.published == "2023" and b.pdf_url == "https://x/pdf"
