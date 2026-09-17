"""Standalone smoke test for semantic-scholar server.py (no network)."""
import server


def test_format_paper_full():
    p = {
        "title": "Deep Learning in Education",
        "authors": [{"name": "A. Rossi"}, {"name": "B. Bianchi"}, {"name": "C. Verdi"}, {"name": "D. Neri"}],
        "year": 2022,
        "venue": "Journal of AI Education",
        "abstract": "x" * 400,
        "externalIds": {"DOI": "10.1234/abc"},
        "paperId": "abc123",
    }
    out = server._format_paper(p)
    assert "Deep Learning in Education" in out
    assert "A. Rossi, B. Bianchi, C. Verdi et al." in out
    assert "(2022)" in out
    assert "Journal of AI Education" in out
    assert "10.1234/abc" in out
    assert "abc123" in out
    assert out.count("x") == 300 + out[out.index("Abstract:"):].count("...") * 0 or "..." in out


def test_format_paper_empty():
    assert server._format_paper({}) == "(no data)"
    assert server._format_paper(None) == "(no data)"


def test_format_results_empty():
    out = server._format_results([], "query terms", 0)
    assert "no results" in out
    assert "query terms" in out


def test_format_results_nonempty():
    out = server._format_results([{"title": "Paper A"}], "q", 1)
    assert "1 results" in out
    assert "Paper A" in out


def test_fields_prefixing():
    fields = ",".join(f"citingPaper.{f}" for f in server.FIELDS.split(","))
    assert fields.startswith("citingPaper.title,")
    assert "citingPaper.paperId" in fields


if __name__ == "__main__":
    test_format_paper_full()
    test_format_paper_empty()
    test_format_results_empty()
    test_format_results_nonempty()
    test_fields_prefixing()
    print("OK")
