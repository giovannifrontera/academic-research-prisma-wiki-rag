"""
arXiv MCP Server
Searches arXiv (arxiv.org) — the world's largest preprint server.
Covers computer science, mathematics, physics, quantitative biology,
quantitative finance, statistics, and economics.
API docs: https://arxiv.org/help/api/user-manual
No API key required.
"""

import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("arxiv")

BASE_URL = "https://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 30

ATOM = "{http://www.w3.org/2005/Atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def _fetch(params: dict) -> ET.Element:
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "academic-prisma-workflow/1.0 (research use)"},
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


def _parse_entry(entry: ET.Element) -> dict:
    def txt(tag: str) -> str:
        el = entry.find(tag)
        return " ".join(el.text.split()) if el is not None and el.text else ""

    arxiv_url = txt(f"{ATOM}id")
    arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else arxiv_url
    title = txt(f"{ATOM}title")
    abstract = txt(f"{ATOM}summary")
    published = txt(f"{ATOM}published")[:10]
    doi = txt(f"{ARXIV_NS}doi")

    authors = [
        name_el.text.strip()
        for a in entry.findall(f"{ATOM}author")
        for name_el in [a.find(f"{ATOM}name")]
        if name_el is not None and name_el.text
    ]

    primary_cat_el = entry.find(f"{ARXIV_NS}primary_category")
    primary_cat = primary_cat_el.get("term", "") if primary_cat_el is not None else ""

    pdf_link = next(
        (lnk.get("href", "") for lnk in entry.findall(f"{ATOM}link")
         if lnk.get("title") == "pdf"),
        "",
    )

    return {
        "id": arxiv_id,
        "title": title,
        "abstract": abstract,
        "published": published,
        "doi": doi,
        "authors": authors,
        "primary_category": primary_cat,
        "pdf_link": pdf_link,
    }


def _format_entry(e: dict, index: int = None) -> str:
    auth_str = ", ".join(e["authors"][:3])
    if len(e["authors"]) > 3:
        auth_str += " et al."
    year = e["published"][:4] if e["published"] else "n.d."
    prefix = f"{index}. " if index else ""
    line = f"{prefix}**{e['title'] or '(no title)'}**\n"
    line += f"   {auth_str or 'N/A'} ({year})\n"
    if e["primary_category"]:
        line += f"   Category: {e['primary_category']}\n"
    if e["doi"]:
        line += f"   DOI: {e['doi']}\n"
    if e["id"]:
        line += f"   arXiv: https://arxiv.org/abs/{e['id']}\n"
    if e["pdf_link"]:
        line += f"   PDF: {e['pdf_link']}\n"
    if e["abstract"]:
        line += f"   Abstract: {e['abstract'][:300]}{'...' if len(e['abstract']) > 300 else ''}\n"
    return line


@mcp.tool()
def arxiv_search(
    query: str,
    category: str = None,
    year_from: int = None,
    year_to: int = None,
    sort_by: str = "relevance",
    rows: int = 10,
    offset: int = 0,
) -> str:
    """
    Search arXiv for preprints and papers. Best for Computer Science, AI/ML,
    Mathematics, Physics, Quantitative Biology, and Economics.
    All results include direct PDF links.

    arXiv category examples:
      cs.AI   — Artificial Intelligence
      cs.LG   — Machine Learning
      cs.CL   — Computation and Language (NLP)
      cs.CV   — Computer Vision
      cs.HC   — Human-Computer Interaction
      stat.ML — Statistics / Machine Learning
      econ.GN — Economics / General

    Query field prefixes:
      ti:attention          -> title only
      au:hinton             -> author surname
      abs:dropout           -> abstract only
      all:BERT language     -> all fields (default)

    sort_by values: "relevance" (default), "lastUpdatedDate", "submittedDate"

    Args:
        query: Search terms or arXiv query syntax
        category: arXiv category code (e.g. "cs.AI") — optional
        year_from: Filter papers submitted from this year (inclusive)
        year_to: Filter papers submitted up to this year (inclusive)
        sort_by: Result ordering strategy
        rows: Number of results (default 10, max 100)
        offset: Pagination offset (default 0)
    """
    try:
        q = query
        if category:
            q = f"cat:{category} AND ({query})"
        if year_from or year_to:
            y1 = f"{year_from}0101" if year_from else "19000101"
            y2 = f"{year_to}1231" if year_to else "30001231"
            q += f" AND submittedDate:[{y1} TO {y2}]"

        params = {
            "search_query": q,
            "start": offset,
            "max_results": min(rows, 100),
            "sortBy": sort_by,
            "sortOrder": "descending",
        }
        root = _fetch(params)
        entries = [_parse_entry(e) for e in root.findall(f"{ATOM}entry")]
        total = _total(root)

        if not entries:
            return f"arXiv — no results for: {query}"

        lines = [f"arXiv — ~{total} results for '{query}' (showing {len(entries)}):\n"]
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
    Return approximate result count from arXiv without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: Search terms or arXiv query syntax
        category: arXiv category code (e.g. "cs.AI") — optional
        year_from: Start year filter — optional
        year_to: End year filter — optional
    """
    try:
        q = query
        if category:
            q = f"cat:{category} AND ({query})"
        if year_from or year_to:
            y1 = f"{year_from}0101" if year_from else "19000101"
            y2 = f"{year_to}1231" if year_to else "30001231"
            q += f" AND submittedDate:[{y1} TO {y2}]"

        params = {"search_query": q, "start": 0, "max_results": 1}
        root = _fetch(params)
        total = _total(root)
        parts = [f"arXiv — results for '{query}'"]
        if category:
            parts.append(f"[{category}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **~{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def arxiv_get(arxiv_id: str) -> str:
    """
    Retrieve full metadata for a specific arXiv paper by its ID.
    Use to get complete details for a paper identified during screening.

    Args:
        arxiv_id: arXiv paper ID, e.g.:
                  "2301.00001"   -> latest version
                  "2301.00001v2" -> specific version
                  Full URL accepted: "https://arxiv.org/abs/2301.00001"
    """
    try:
        clean_id = arxiv_id.strip()
        if "arxiv.org/abs/" in clean_id:
            clean_id = clean_id.split("arxiv.org/abs/")[-1]
        params = {"id_list": clean_id, "max_results": 1}
        root = _fetch(params)
        entries = root.findall(f"{ATOM}entry")
        if not entries:
            return f"Paper not found: {arxiv_id}"
        return _format_entry(_parse_entry(entries[0]))
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
