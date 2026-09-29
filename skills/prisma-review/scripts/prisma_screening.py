"""PRISMA Phase 2 — normalize raw_*.json, deduplicate across databases, apply agreed filters.

Deterministic and study-independent: only explicit, user-agreed filters are applied.
Language and publication type are judged only from what a record declares; records
that declare nothing are kept for human screening, never guessed.

Usage (from the review's prisma folder):
    python prisma_screening.py --dir . --year-from 2020 --year-to 2026 \
        [--languages en,it] [--exclude-types "Book,Editorial"] [--peer-reviewed-only] \
        [--arxiv-published-only] [--pdf-inbox ../sources/pdf-inbox]
    python prisma_screening.py --dir . --census   # list declared languages/types, write nothing

Writes screening_prisma.json (kept), screening_excluded.json (with "exclusion_reason")
and screening_summary.json, and prints the summary.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Order = precedence when duplicates merge (first source keeps its metadata).
SOURCES = ["pdf_manual", "pubmed", "semantic_scholar", "openaire", "eric", "core", "doaj", "zenodo", "arxiv"]

# Declared values meaning "language unknown".
UNKNOWN_LANG = {"", "und", "undetermined", "ng", "unknown", "zxx", "mul"}
LANG_NAMES = {
    "english": "en", "eng": "en", "italian": "it", "ita": "it", "spanish": "es", "spa": "es",
    "french": "fr", "fre": "fr", "fra": "fr", "german": "de", "ger": "de", "deu": "de",
    "portuguese": "pt", "por": "pt", "russian": "ru", "rus": "ru", "ukrainian": "uk", "ukr": "uk",
    "chinese": "zh", "chi": "zh", "zho": "zh", "arabic": "ar", "ara": "ar", "turkish": "tr", "tur": "tr",
}


def _names(authors) -> list:
    out = []
    for a in authors or []:
        name = (a.get("name") or a.get("fullName")) if isinstance(a, dict) else a
        if name:
            out.append(str(name))
    return out


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def _year(value):
    m = re.search(r"\d{4}", str(value or ""))
    return int(m.group()) if m else None


def _lang_codes(values) -> list:
    codes = []
    for v in _as_list(values):
        if isinstance(v, dict):
            v = v.get("code") or v.get("name")
        v = str(v or "").strip().lower()
        if v in UNKNOWN_LANG:
            continue
        codes.append(LANG_NAMES.get(v, v))
    return sorted(set(codes))


def normalize(r: dict, db: str) -> dict:
    """Map one raw record to the common shape; unknown fields become None/[]."""
    if db == "semantic_scholar":
        ext = r.get("externalIds") or {}
        rec = dict(title=r.get("title"), doi=ext.get("DOI"), year=r.get("year"), abstract=r.get("abstract"),
                   authors=_names(r.get("authors")), journal=r.get("venue"), languages=[],
                   pub_types=_as_list(r.get("publicationTypes")),
                   fulltext_url=(r.get("openAccessPdf") or {}).get("url"), id=r.get("paperId"))
    elif db == "eric":
        rec = dict(title=r.get("title"), doi=r.get("doi"), year=r.get("publicationdateyear"),
                   abstract=r.get("description"), authors=_as_list(r.get("author")), journal=r.get("source"),
                   languages=_lang_codes(r.get("language")), pub_types=_as_list(r.get("publicationtype")),
                   fulltext_url=None, id=r.get("id"))
    elif db == "core":
        urls = r.get("sourceFulltextUrls") or []
        journals = r.get("journals") or []
        rec = dict(title=r.get("title"), doi=r.get("doi"), year=r.get("yearPublished"), abstract=r.get("abstract"),
                   authors=_names(r.get("authors")), journal=journals[0].get("title") if journals else None,
                   languages=_lang_codes(r.get("language")), pub_types=_as_list(r.get("documentType")),
                   fulltext_url=r.get("downloadUrl") or (urls[0] if urls else None), id=r.get("id"))
    elif db == "doaj":
        b = r.get("bibjson") or {}
        doi = next((i.get("id") for i in b.get("identifier", []) if (i.get("type") or "").lower() == "doi"), None)
        journal = b.get("journal") or {}
        # DOAJ declares the journal's languages, not the article's: any match keeps the record.
        rec = dict(title=b.get("title"), doi=doi, year=b.get("year"), abstract=b.get("abstract"),
                   authors=_names(b.get("author")), journal=journal.get("title"),
                   languages=_lang_codes(journal.get("language")), pub_types=[], fulltext_url=None, id=r.get("id"))
    elif db == "zenodo":
        m = r.get("metadata") or {}
        rt = m.get("resource_type") or {}
        rec = dict(title=m.get("title"), doi=m.get("doi") or r.get("doi"), year=m.get("publication_date"),
                   abstract=m.get("description"), authors=_names(m.get("creators")), journal=None,
                   languages=_lang_codes(m.get("language")),
                   pub_types=[t for t in (rt.get("subtype") or rt.get("type"),) if t], fulltext_url=None,
                   id=r.get("id"))
    elif db == "pubmed":
        rec = dict(title=r.get("title"), doi=r.get("doi"), year=r.get("year"), abstract=r.get("abstract"),
                   authors=_names(r.get("authors")), journal=r.get("journal"),
                   languages=_lang_codes(r.get("language")), pub_types=_as_list(r.get("publication_types")),
                   fulltext_url=None, id=r.get("pmid"))
    elif db == "openaire":
        rec = dict(title=r.get("title"), doi=r.get("doi"), year=r.get("year"), abstract=r.get("abstract"),
                   authors=_names(r.get("authors")), journal=r.get("journal"),
                   languages=_lang_codes(r.get("language")), pub_types=[], fulltext_url=None,
                   id=r.get("openaire_id"))
    else:  # arxiv, pdf_manual: already normalized by the server / extract_pdf_metadata.py
        rec = dict(title=r.get("title"), doi=r.get("doi"), year=r.get("year"), abstract=r.get("abstract"),
                   authors=_names(r.get("authors")), journal=r.get("journal_ref") or r.get("journal"),
                   languages=_lang_codes(r.get("language")), pub_types=[], fulltext_url=r.get("fulltext_url"),
                   id=r.get("id") or r.get("file"))
    peer = str(r.get("peerreviewed") or "").upper()  # only ERIC declares it: "T"/"F"
    rec["peer_reviewed"] = {"T": True, "F": False}.get(peer)
    rec["year"] = _year(rec["year"])
    rec["title"] = " ".join(str(rec["title"] or "").split()) or None
    rec["source_db"] = db
    rec["source_dbs"] = [db]
    rec["source_ids"] = {db: rec.pop("id")}
    return rec


def doi_key(doi) -> str:
    d = str(doi or "").strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d)
    return d if d.startswith("10.") else ""


def title_key(title) -> str:
    """Casefolded letters/digits of any script (Cyrillic titles are titles too)."""
    return "".join(c for c in str(title or "").casefold() if c.isalnum())


def _merge(kept: dict, dup: dict) -> None:
    for db in dup["source_dbs"]:
        if db not in kept["source_dbs"]:
            kept["source_dbs"].append(db)
    kept["source_ids"].update(dup["source_ids"])
    for field in ("doi", "year", "abstract", "journal", "fulltext_url", "title"):
        if not kept.get(field) and dup.get(field):
            kept[field] = dup[field]
    if kept["peer_reviewed"] is None:
        kept["peer_reviewed"] = dup["peer_reviewed"]
    if not kept["authors"]:
        kept["authors"] = dup["authors"]
    for field in ("languages", "pub_types"):
        kept[field] = sorted(set(kept[field]) | set(dup[field]))


def deduplicate(records: list) -> tuple:
    """DOI first, then normalized title; duplicates merge into the first record seen."""
    by_doi, by_title, kept, dups = {}, {}, [], 0
    for rec in records:
        d, t = doi_key(rec["doi"]), title_key(rec["title"])
        target = by_doi.get(d) if d else None
        if target is None and t:
            target = by_title.get(t)
        if target is None:
            target = rec
            kept.append(rec)
        else:
            _merge(target, rec)
            dups += 1
        for key, index in ((doi_key(target["doi"]), by_doi), (d, by_doi), (t, by_title)):
            if key:
                index.setdefault(key, target)
    return kept, dups


def exclusion_reason(rec: dict, year_from, year_to, languages, exclude_types,
                     peer_reviewed_only=False, arxiv_published_only=False):
    if not title_key(rec["title"]):
        return "senza titolo"
    y = rec["year"]
    if y is not None and ((year_from and y < year_from) or (year_to and y > year_to)):
        return "anno fuori intervallo"
    if languages and rec["languages"] and not set(rec["languages"]) & languages:
        return "lingua non ammessa (dichiarata: " + ", ".join(rec["languages"]) + ")"
    types = {t.casefold() for t in rec["pub_types"]}
    if exclude_types and types and types <= exclude_types:
        return "tipo di pubblicazione escluso (" + ", ".join(rec["pub_types"]) + ")"
    if peer_reviewed_only and rec["peer_reviewed"] is False:
        return "non peer-reviewed (dichiarato)"
    if (arxiv_published_only and rec["source_dbs"] == ["arxiv"]
            and not doi_key(rec["doi"]) and not rec["journal"]):
        return "preprint arXiv senza versione pubblicata"
    return None


def load(folder: Path) -> tuple:
    records, per_db = [], {}
    for db in SOURCES:
        path = folder / f"raw_{db}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):  # tolerate {records: [...]} envelopes
            data = data.get("records", [])
        per_db[db] = len(data)
        records.extend(normalize(r, db) for r in data if isinstance(r, dict))
    return records, per_db


def census(records: list) -> dict:
    out = {}
    for field in ("languages", "pub_types"):
        c = Counter()
        for r in records:
            for v in r[field] or ["(non dichiarato)"]:
                c[f"{r['source_db']}: {v}"] += 1
        out[field] = dict(c.most_common())
    out["senza_anno"] = sum(r["year"] is None for r in records)
    return out


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".", help="folder with raw_*.json (the study's prisma folder)")
    ap.add_argument("--year-from", type=int)
    ap.add_argument("--year-to", type=int)
    ap.add_argument("--languages", default="", help="comma-separated ISO 639-1 codes, e.g. en,it")
    ap.add_argument("--exclude-types", default="",
                    help="comma-separated declared types; a record is excluded only if ALL its types are listed")
    ap.add_argument("--peer-reviewed-only", action="store_true",
                    help="exclude records that declare they are not peer-reviewed (ERIC); undeclared are kept")
    ap.add_argument("--arxiv-published-only", action="store_true",
                    help="keep arXiv-only records only with a DOI or journal-ref")
    ap.add_argument("--pdf-inbox", help="download open-access PDFs here (sealed study: sources/pdf-inbox)")
    ap.add_argument("--census", action="store_true", help="print declared languages/types and exit")
    a = ap.parse_args(argv)
    folder = Path(a.dir)
    records, per_db = load(folder)
    if not records:
        sys.exit(f"no raw_*.json records in {folder.resolve()}")
    if a.census:
        result = census(records)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return result

    kept, dups = deduplicate(records)
    languages = {x.strip().lower() for x in a.languages.split(",") if x.strip()}
    exclude_types = {x.strip().casefold() for x in a.exclude_types.split(",") if x.strip()}
    included, excluded = [], []
    for rec in kept:
        reason = exclusion_reason(rec, a.year_from, a.year_to, languages, exclude_types,
                                  a.peer_reviewed_only, a.arxiv_published_only)
        if reason:
            excluded.append(dict(rec, exclusion_reason=reason))
        else:
            included.append(rec)
    if a.pdf_inbox:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from fetch_fulltext import enrich_records_with_fulltext
        Path(a.pdf_inbox).mkdir(parents=True, exist_ok=True)
        enrich_records_with_fulltext(included, Path(a.pdf_inbox))

    reasons = Counter(r["exclusion_reason"].split(" (")[0] for r in excluded)
    summary = {
        "totale_lordo": len(records), "per_db": per_db, "duplicati_rimossi": dups,
        "dopo_deduplicazione": len(kept), "esclusi_per_motivo": dict(reasons.most_common()),
        "dopo_screening": len(included), "senza_anno_mantenuti": sum(r["year"] is None for r in included),
        "lingua_non_dichiarata_mantenuti": sum(not r["languages"] for r in included) if languages else None,
        "filtri": {"year_from": a.year_from, "year_to": a.year_to, "languages": sorted(languages),
                   "exclude_types": sorted(exclude_types), "peer_reviewed_only": a.peer_reviewed_only,
                   "arxiv_published_only": a.arxiv_published_only},
    }
    for name, data in (("screening_prisma.json", included), ("screening_excluded.json", excluded),
                       ("screening_summary.json", summary)):
        (folder / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


if __name__ == "__main__":
    main()
