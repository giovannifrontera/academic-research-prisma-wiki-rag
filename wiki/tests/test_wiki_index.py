import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from wiki_index import is_stale, rebuild_index

def test_is_stale_no_index(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    assert is_stale(index_path, wiki_dir) is True

def test_is_stale_after_new_page(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    (tmp_workspace / "wiki" / "index.md").write_text("# Index\n")
    time.sleep(0.05)
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    assert is_stale(index_path, wiki_dir) is True

def test_is_not_stale_when_current(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    time.sleep(0.05)
    (tmp_workspace / "wiki" / "index.md").write_text("# Index\n")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    assert is_stale(index_path, wiki_dir) is False

def test_rebuild_index_basic(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    (tmp_workspace / "wiki" / "concepts" / "mean-reversion.md").write_text(
        "---\ntitle: Mean Reversion\ndescription: Strategia di mean reversion\n---\n# Mean Reversion\n"
    )
    content = rebuild_index(wiki_dir, token_budget=4000)
    assert "mean-reversion" in content
    assert "Concepts" in content

def test_rebuild_index_excludes_raw(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    raw_dir = tmp_workspace / "wiki" / "raw"
    raw_dir.mkdir()
    (raw_dir / "2026-05-20-source.md").write_text("# Fonte grezza\n")
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    content = rebuild_index(wiki_dir, token_budget=4000)
    assert "source" not in content
    assert "test" in content

def test_rebuild_index_budget_exceeded(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    for i in range(10):
        (tmp_workspace / "wiki" / "concepts" / f"concept-{i}.md").write_text(
            f"# Concept {i}\n" + "Descrizione molto lunga. " * 20
        )
    content = rebuild_index(wiki_dir, token_budget=50)
    # Strategia 3: scrive su disco e ritorna index leggero
    assert "index-concepts.md" in content or "Concepts" in content
    # Verifica che il file separato sia stato scritto
    index_concepts_path = tmp_workspace / "wiki" / "index-concepts.md"
    assert index_concepts_path.exists()
    assert "concept-" in index_concepts_path.read_text()
