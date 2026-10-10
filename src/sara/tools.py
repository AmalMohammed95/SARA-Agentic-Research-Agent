"""Academic search tools for SARA.

Prefer OpenAlex records with usable abstracts while preserving the existing
search_openalex(query, max_results) interface and output fields.
"""

import json
import urllib.parse
import urllib.request

OPENALEX_API_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruct plain abstract text from an OpenAlex inverted index."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    positioned_words = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and position >= 0:
                positioned_words.append((position, word))
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(str(word) for _, word in positioned_words)


def search_openalex(query: str, max_results: int = 5) -> list[dict]:
    """Search OpenAlex, prioritizing relevant works with informative abstracts.

    Output keys remain: id, title, year, doi, abstract.
    The abstract is always reconstructed from the source; missing fields are
    never inferred or generated.
    """
    if not isinstance(query, str) or not query.strip() or max_results <= 0:
        return []

    # Search a modestly larger pool to avoid returning papers with empty or
    # extremely short abstracts when better documented papers are available.
    candidate_count = min(max(max_results * 3, max_results), 50)
    params = {"search": query.strip(), "per-page": candidate_count}
    url = f"{OPENALEX_API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SARA-Academic-Research-Agent"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print(f"OpenAlex search failed: {error}")
        return []

    candidates = []
    seen = set()
    for rank, work in enumerate(data.get("results", [])):
        if not isinstance(work, dict):
            continue
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        title = work.get("title")
        if not title:
            continue
        doi = work.get("doi")
        identifier = doi or work.get("id") or title.casefold()
        if identifier in seen:
            continue
        seen.add(identifier)
        paper = {
            "id": work.get("id"),
            "title": title,
            "year": work.get("publication_year"),
            "doi": doi,
            "abstract": abstract,
        }
        # Preserve OpenAlex relevance as the primary ordering signal. Within
        # similar relevance bands, prefer richer abstracts. Never create data.
        score = work.get("relevance_score")
        if not isinstance(score, (int, float)):
            score = 0.0
        candidates.append((paper, rank, score, len(abstract.split())))

    if not candidates:
        return []

    # Start from the most relevant results, but give papers with useful
    # abstracts priority over equally relevant papers with little/no text.
    candidates.sort(key=lambda x: (-x[2], x[1]))
    best_score = max(c[2] for c in candidates)
    if best_score > 0:
        # Only re-rank within a reasonable relevance range of the best result.
        eligible = [c for c in candidates if c[2] >= best_score * 0.5]
        remaining = [c for c in candidates if c[2] < best_score * 0.5]
        eligible.sort(key=lambda x: (x[3] < 100, -x[2], -x[3], x[1]))
        ordered = eligible + remaining
    else:
        # Some API fixtures do not provide relevance_score; keep API ordering.
        ordered = candidates

    return [paper for paper, _, _, _ in ordered[:max_results]]
