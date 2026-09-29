import json

from prisma_screening import main


def _write(folder, db, records):
    (folder / f"raw_{db}.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def test_dedup_filters_and_undeclared_language_kept(tmp_path):
    _write(tmp_path, "semantic_scholar", [
        {"paperId": "s1", "title": "AI Tutors in Higher Education", "year": 2024,
         "externalIds": {"DOI": "10.1/ABC"}, "abstract": "a", "authors": [{"name": "A"}],
         "publicationTypes": ["Book", "Conference"]},
        {"paperId": "s2", "title": "Цифрові інструменти в освіті", "year": 2023, "externalIds": {},
         "publicationTypes": None},  # Cyrillic title, no declared language: kept
        {"paperId": "s3", "title": "Old study", "year": 2015, "externalIds": {}},
    ])
    _write(tmp_path, "core", [
        {"id": 1, "title": "AI tutors in higher education!", "doi": "https://doi.org/10.1/abc",
         "yearPublished": 2024, "language": {"code": "en"}, "documentType": "research article",
         "downloadUrl": "https://x/p.pdf"},  # duplicate by DOI
        {"id": 2, "title": "Estudio en español", "yearPublished": 2022, "language": {"code": "es"}},
        {"id": 3, "title": "   ", "yearPublished": 2022},
    ])
    _write(tmp_path, "eric", [
        {"id": "EJ1", "title": "A handbook", "publicationdateyear": 2021, "language": ["English"],
         "publicationtype": ["Books"]},
        {"id": "EJ2", "title": "AI Tutors in Higher Education", "publicationdateyear": 2024},  # dup by title
    ])
    _write(tmp_path, "openaire", [
        {"openaire_id": "o1", "title": "Undetermined language paper", "year": 2025, "language": "Undetermined"},
    ])

    s = main(["--dir", str(tmp_path), "--year-from", "2020", "--year-to", "2026",
              "--languages", "en,it", "--exclude-types", "Books,Book"])

    kept = json.loads((tmp_path / "screening_prisma.json").read_text(encoding="utf-8"))
    excluded = json.loads((tmp_path / "screening_excluded.json").read_text(encoding="utf-8"))
    assert s["totale_lordo"] == 9 and s["duplicati_rimossi"] == 2 and s["dopo_deduplicazione"] == 7
    assert s["esclusi_per_motivo"] == {"anno fuori intervallo": 1, "lingua non ammessa": 1,
                                       "senza titolo": 1, "tipo di pubblicazione escluso": 1}
    titles = {r["title"] for r in kept}
    assert titles == {"AI Tutors in Higher Education", "Цифрові інструменти в освіті", "Undetermined language paper"}
    merged = next(r for r in kept if r["title"] == "AI Tutors in Higher Education")
    assert merged["source_dbs"] == ["semantic_scholar", "eric", "core"]  # SOURCES precedence
    assert merged["fulltext_url"] == "https://x/p.pdf" and merged["languages"] == ["en"]
    # Book+Conference is not excluded by "Book" alone; ERIC "Books" only is.
    assert "A handbook" in {r["title"] for r in excluded}


def test_census_writes_nothing(tmp_path):
    _write(tmp_path, "eric", [{"id": "EJ1", "title": "T", "publicationdateyear": 2021,
                               "language": ["English"], "publicationtype": ["Books"]}])
    c = main(["--dir", str(tmp_path), "--census"])
    assert c["pub_types"] == {"eric: Books": 1} and c["languages"] == {"eric: en": 1}
    assert not (tmp_path / "screening_prisma.json").exists()


def test_peer_review_and_arxiv_published_only(tmp_path):
    _write(tmp_path, "eric", [
        {"id": "E1", "title": "Reviewed", "publicationdateyear": 2022, "peerreviewed": "T"},
        {"id": "E2", "title": "Not reviewed", "publicationdateyear": 2022, "peerreviewed": "F"},
    ])
    _write(tmp_path, "arxiv", [
        {"id": "a1", "title": "Bare preprint", "year": "2024", "doi": "", "journal_ref": ""},
        {"id": "a2", "title": "Published preprint", "year": "2024", "doi": "", "journal_ref": "J. Ed. 3 (2024)"},
        {"id": "a3", "title": "Reviewed", "year": "2022", "doi": ""},  # also in ERIC: kept
    ])
    s = main(["--dir", str(tmp_path), "--peer-reviewed-only", "--arxiv-published-only"])
    kept = {r["title"] for r in json.loads((tmp_path / "screening_prisma.json").read_text(encoding="utf-8"))}
    assert kept == {"Reviewed", "Published preprint"}
    assert s["esclusi_per_motivo"] == {"non peer-reviewed": 1, "preprint arXiv senza versione pubblicata": 1}
