"""
arXiv MCP Server
Searches arXiv (arxiv.org) — the world's largest preprint server.
Covers computer science, mathematics, physics, quantitative biology,
quantitative finance, statistics, and economics.
API docs: https://info.arxiv.org/help/api/user-manual.html
No API key required. arXiv asks clients to wait ~3 s between requests.
"""

import json
import re
from typing import Literal
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP
import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from export_util import export_pages  # noqa: E402

mcp = FastMCP("arxiv")

BASE_URL = "https://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 30

ATOM = "{http://www.w3.org/2005/Atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# arXiv ORs bare terms ("spaced repetition" -> all:spaced OR all:repetition),
# which floods PRISMA counts. Plain queries are ANDed; explicit syntax passes through.
_SYNTAX = re.compile(r'[:"()]|\b(AND|OR|ANDNOT)\b')


def _build_query(query: str, category: str = None, year_from: int = None, year_to: int = None) -> str:
    q = query.strip()
    if not _SYNTAX.search(q):
        q = " AND ".join(f"all:{w}" for w in q.split())
    if category:
        q = f"cat:{category} AND ({q})"
    if year_from or year_to:
        y1 = f"{year_from}01010000" if year_from else "190001010000"
        y2 = f"{year_to}12312359" if year_to else "300012312359"
        q += f" AND submittedDate:[{y1} TO {y2}]"
    return q


def _fetch(params: dict) -> ET.Element:
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "academic-research-prisma-wiki-rag (research use)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return ET.fromstring(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"arXiv API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"arXiv API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"arXiv API timeout after {DEFAULT_TIMEOUT}s") from None


def _total(root: ET.Element) -> int:
    el = root.find(f"{OPENSEARCH}totalResults")
    if el is not None and el.text:
        try:
            return int(el.text)
        except ValueError:
            pass
    return 0


def _parse(entry: ET.Element) -> dict:
    """Complete arXiv record; `fulltext_url` feeds fetch_fulltext.py (arXiv PDFs are open access)."""
    def txt(tag: str) -> str:
        el = entry.find(tag)
        return " ".join(el.text.split()) if el is not None and el.text else ""

    arxiv_url = txt(f"{ATOM}id")
    arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else arxiv_url
    published = txt(f"{ATOM}published")[:10]
    primary_el = entry.find(f"{ARXIV_NS}primary_category")
    pdf_link = next(
        (lnk.get("href", "") for lnk in entry.findall(f"{ATOM}link") if lnk.get("title") == "pdf"),
        "",
    )
    return {
        "id": arxiv_id,
        "title": txt(f"{ATOM}title"),
        "abstract": txt(f"{ATOM}summary"),
        "published": published,
        "updated": txt(f"{ATOM}updated")[:10],
        "year": published[:4],
        "doi": txt(f"{ARXIV_NS}doi"),
        "journal_ref": txt(f"{ARXIV_NS}journal_ref"),
        "authors": [
            {"name": " ".join(n.text.split())}
            for a in entry.findall(f"{ATOM}author")
            for n in [a.find(f"{ATOM}name")]
            if n is not None and n.text
        ],
        "primary_category": primary_el.get("term", "") if primary_el is not None else "",
        "categories": [c.get("term", "") for c in entry.findall(f"{ATOM}category")],
        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
        "pdf_link": pdf_link,
        "fulltext_url": pdf_link,
    }


def _format_entry(e: dict, index: int = None) -> str:
    names = [a["name"] for a in e["authors"]]
    auth_str = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
    prefix = f"{index}. " if index else ""
    line = f"{prefix}**{e['title'] or '(no title)'}**\n"
    line += f"   {auth_str or 'N/A'} ({e['year'] or 'n.d.'})\n"
    if e["primary_category"]:
        line += f"   Category: {e['primary_category']}\n"
    if e["doi"]:
        line += f"   DOI: {e['doi']}\n"
    if e["url"]:
        line += f"   arXiv: {e['url']}\n"
    if e["pdf_link"]:
        line += f"   PDF: {e['pdf_link']}\n"
    if e["abstract"]:
        line += f"   Abstract: {e['abstract'][:300]}{'...' if len(e['abstract']) > 300 else ''}\n"
    return line


def _check_format(output_format: str):
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")


@mcp.tool()
def arxiv_search(
    query: str,
    category: str = None,
    year_from: int = None,
    year_to: int = None,
    sort_by: str = "relevance",
    rows: int = 10,
    offset: int = 0,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search arXiv for preprints and papers. Best for Computer Science, AI/ML,
    Mathematics, Physics, Quantitative Biology, and Economics.
    All results include direct open-access PDF links.

    Plain queries are combined with AND ("spaced repetition" ->
    all:spaced AND all:repetition). Explicit arXiv syntax is passed as-is:
      ti:attention          -> title only
      au:hinton             -> author surname
      abs:dropout           -> abstract only
      "exact phrase", AND, OR, ANDNOT, parentheses

    arXiv category examples: cs.AI, cs.LG, cs.CL, cs.CY (Computers and Society),
    cs.HC, stat.ML, econ.GN, q-bio.NC.

    Args:
        query: Search terms or arXiv query syntax
        category: arXiv category code (e.g. "cs.AI") — optional
        year_from: Filter papers submitted from this year (inclusive)
        year_to: Filter papers submitted up to this year (inclusive)
        sort_by: "relevance" (default), "lastUpdatedDate", "submittedDate"
        rows: Number of results (default 10, max 100)
        offset: Pagination offset (default 0)
        output_format: text preview or json envelope with complete records and total.
    """
    _check_format(output_format)
    try:
        rows = max(1, min(rows, 100))
        params = {
            "search_query": _build_query(query, category, year_from, year_to),
            "start": offset,
            "max_results": rows,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }
        root = _fetch(params)
        entries = [_parse(e) for e in root.findall(f"{ATOM}entry")]
        total = _total(root)
        if output_format == "json":
            return json.dumps({
                "records": entries, "total": total, "offset": offset, "rows": rows,
                "search_query": params["search_query"],
            }, ensure_ascii=False)
        if not entries:
            return f"arXiv — no results for: {query}"
        lines = [f"arXiv — {total} results for '{query}' (showing {len(entries)}):\n"]
        for i, e in enumerate(entries, 1):
            lines.append(_format_entry(e, i))
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def arxiv_count(
    query: str,
    category: str = None,
    year_from: int = None,
    year_to: int = None,
) -> str:
    """
    Return result count from arXiv without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: Search terms or arXiv query syntax (plain terms are ANDed)
        category: arXiv category code (e.g. "cs.AI") — optional
        year_from: Start year filter — optional
        year_to: End year filter — optional
    """
    try:
        root = _fetch({"search_query": _build_query(query, category, year_from, year_to),
                       "start": 0, "max_results": 1})
        parts = [f"arXiv — results for '{query}'"]
        if category:
            parts.append(f"[{category}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{_total(root)}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def arxiv_get(arxiv_id: str, output_format: Literal["text", "json"] = "text") -> str:
    """
    Retrieve full metadata for a specific arXiv paper by its ID.

    Args:
        arxiv_id: arXiv paper ID, e.g. "2301.00001", "2301.00001v2",
                  or a full URL "https://arxiv.org/abs/2301.00001"
        output_format: text details or json envelope with complete records and total.
    """
    _check_format(output_format)
    try:
        clean_id = arxiv_id.strip()
        if "arxiv.org/abs/" in clean_id:
            clean_id = clean_id.split("arxiv.org/abs/")[-1]
        root = _fetch({"id_list": clean_id, "max_results": 1})
        entries = [_parse(e) for e in root.findall(f"{ATOM}entry")]
        # The API answers unknown IDs with an error entry that has no title.
        entries = [e for e in entries if e["title"] and e["title"] != "Error"]
        if output_format == "json":
            return json.dumps({"records": entries, "total": len(entries)}, ensure_ascii=False)
        if not entries:
            return f"Paper not found: {arxiv_id}"
        e = entries[0]
        text = _format_entry({**e, "abstract": ""})
        if e["abstract"]:
            text += f"\nAbstract:\n{e['abstract']}"
        return text
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def arxiv_export(
    query: str,
    output_path: str,
    category: str = None,
    year_from: int = None,
    year_to: int = None,
    max_records: int = 5000,
) -> str:
    """
    Download ALL matching arXiv records to a JSON file and return only the counts
    (total, downloaded, complete, error, path). Use this for the PRISMA Phase 1
    download instead of paging arxiv_search or writing scripts that call the API:
    records never pass through the conversation. Same query syntax and filters
    as arxiv_search. Log total/downloaded/query/retrieved_at in prisma_log.md.
    """
    # arXiv asks for 3 s between API calls.
    return export_pages(
        lambda i, offset, size: arxiv_search(
            query, category, year_from, year_to, rows=size, offset=offset, output_format="json"),
        output_path, query, max_records, page_size=100, delay_s=3.0)


if __name__ == "__main__":
    mcp.run(transport="stdio")
