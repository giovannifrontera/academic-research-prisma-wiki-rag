"""
extract_pdf_metadata.py — PRISMA 2020 Stream 2
Estrae metadati da PDF trovati manualmente e salva raw_pdf_manual.json
nel formato normalizzato usato dallo script di screening (Fase 2).

Uso:
    py extract_pdf_metadata.py <cartella_pdf> [--output raw_pdf_manual.json]

Output: lista JSON con campi title, doi, year, abstract, authors, source_db, file
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    print("ERRORE: pdfplumber non installato. Esegui: pip install pdfplumber")
    sys.exit(1)

DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"<>\]]+', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(19[5-9]\d|20[0-3]\d)\b')
ABSTRACT_RE = re.compile(
    r'(?:abstract|riassunto|sommario|summary)\s*[:\-–]?\s*\n?\s*(.{80,2000}?)(?:\n{2,}|\Z)',
    re.IGNORECASE | re.DOTALL
)


def extract_text(pdf_path: Path, n_pages: int = 4) -> str:
    """Estrae testo dalle prime n pagine del PDF."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:n_pages]:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"  ATTENZIONE: errore lettura {pdf_path.name}: {e}")
    return text


def extract_doi(text: str) -> Optional[str]:
    m = DOI_RE.search(text)
    if m:
        return m.group(0).rstrip(".,;)>").lower()
    return None


def extract_year(text: str) -> Optional[str]:
    # Prefer years appearing near publication metadata keywords (more reliable)
    meta_zone = re.search(
        r'(?:published|received|accepted|copyright|©|volume|vol\.|issue|\bpp\b)[^\n]{0,60}',
        text, re.IGNORECASE
    )
    candidates = []
    if meta_zone:
        candidates = YEAR_RE.findall(meta_zone.group(0))
    if not candidates:
        candidates = YEAR_RE.findall(text)[:15]
    for year in candidates:
        if 1950 <= int(year) <= 2030:
            return year
    return None


def extract_title(text: str) -> str:
    """Primo blocco di testo non-banale come stima del titolo."""
    skip = re.compile(r'^(doi|vol|issn|isbn|http|page|pp\.|abstract|copyright|©)', re.I)
    for line in text.split('\n')[:20]:
        line = line.strip()
        if len(line) > 20 and not skip.match(line):
            return line
    return ""


def extract_abstract(text: str) -> str:
    m = ABSTRACT_RE.search(text)
    if m:
        return m.group(1).replace('\n', ' ').strip()
    return ""


def process_folder(folder: Path, output: Path) -> None:
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"Nessun PDF trovato in {folder}")
        sys.exit(0)

    print(f"Elaborazione {len(pdfs)} file PDF...\n")
    records = []

    for pdf_path in pdfs:
        print(f"  → {pdf_path.name}")
        text = extract_text(pdf_path)

        if not text.strip():
            print(f"    ⚠ Testo vuoto — PDF probabilmente scannerizzato (immagine)")
            print(f"    → Aggiungi i metadati manualmente in {output.name}")
            records.append({
                "title": pdf_path.stem,
                "doi": None,
                "year": None,
                "abstract": "",
                "authors": [],
                "source_db": "pdf_manual",
                "file": pdf_path.name,
                "_warning": "testo_vuoto_pdf_scannerizzato"
            })
            continue

        record = {
            "title": extract_title(text),
            "doi": extract_doi(text),
            "year": extract_year(text),
            "abstract": extract_abstract(text),
            "authors": [],  # estrazione affidabile richiede ML — compilare manualmente se necessario
            "source_db": "pdf_manual",
            "file": pdf_path.name
        }
        records.append(record)

        print(f"    DOI:      {record['doi'] or '—'}")
        print(f"    Anno:     {record['year'] or '—'}")
        print(f"    Titolo:   {record['title'][:60]}...")
        print(f"    Abstract: {'sì' if record['abstract'] else '⚠ non trovato'}")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with_doi = sum(1 for r in records if r.get("doi"))
    no_abstract = sum(1 for r in records if not r.get("abstract"))
    warnings = sum(1 for r in records if r.get("_warning"))

    print(f"\n{'─'*50}")
    print(f"Salvati {len(records)} record → {output}")
    print(f"  DOI trovati:        {with_doi}/{len(records)}")
    print(f"  Senza abstract:     {no_abstract}/{len(records)}")
    if warnings:
        print(f"  PDF scannerizzati:  {warnings} — compilare manualmente")
    print(f"\nVERIFICA OBBLIGATORIA prima di procedere:")
    print(f"  1. Apri {output.name} e controlla titolo/autori per ogni record")
    print(f"  2. Aggiungi autori mancanti (campo 'authors': ['Cognome N', ...])")
    print(f"  3. Per i PDF scannerizzati: inserisci abstract e DOI manualmente")
    print(f"  4. Comunica il totale alla skill prisma-review per il diagramma PRISMA 2020")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PRISMA 2020 Stream 2 — estrazione metadati PDF manuali"
    )
    parser.add_argument("folder", help="Cartella contenente i file PDF")
    parser.add_argument("--output", default="raw_pdf_manual.json",
                        help="File JSON di output (default: raw_pdf_manual.json)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"ERRORE: cartella non trovata: {folder}")
        sys.exit(1)

    process_folder(folder, Path(args.output))
