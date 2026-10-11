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


SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_semantic_scholar(query: str, max_results: int = 5) -> list[dict]:
    """Return source-grounded Semantic Scholar metadata in SARA's paper schema.

    A failed request raises an exception; the multi-source wrapper isolates it.
    """
    import os
    import urllib.error
    if not isinstance(query, str) or not query.strip() or type(max_results) is not int or not 1 <= max_results <= 20:
        return []
    params = urllib.parse.urlencode({
        "query": query.strip(), "limit": max_results,
        "fields": "paperId,title,year,abstract,externalIds",
    })
    headers = {"User-Agent": "SARA-Academic-Research-Agent"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(f"{SEMANTIC_SCHOLAR_API_URL}?{params}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        print(f"[Semantic Scholar] HTTP error: {exc.code}")
        return []

    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"[Semantic Scholar] Connection error: {exc}")
        return []
    papers = []
    for item in payload.get("data", []):
        if not isinstance(item, dict) or not item.get("title"):
            continue
        paper_id = item.get("paperId")
        ids = item.get("externalIds") or {}
        doi = ids.get("DOI") if isinstance(ids, dict) else None
        papers.append({
            "id": f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else None,
            "title": item["title"], "year": item.get("year"),
            "doi": f"https://doi.org/{doi}" if doi else None,
            "abstract": item.get("abstract") or "",
            "source": "semantic_scholar",
        })
    return papers


def _canonical_doi(value):
    if not value:
        return None
    value = str(value).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value.strip() or None


def search_scholarly(query: str, max_results: int = 10) -> list[dict]:
    """Search both sources independently; deduplicate and preserve provenance.

    Return at most max_results papers total, with usable abstracts prioritized.
    Raise only if both providers fail (not if either returns zero results).
    """
    if not isinstance(query, str) or not query.strip() or type(max_results) is not int or not 1 <= max_results <= 20:
        return []
    sources = (("openalex", search_openalex), ("semantic_scholar", search_semantic_scholar))
    collected, errors, successes = [], [], 0
    for name, function in sources:
        try:
            papers = function(query, max_results=max_results)
            successes += 1
            for paper in papers:
                if isinstance(paper, dict):
                    collected.append({**paper, "source": paper.get("source") or name})
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
    if not successes:
        raise RuntimeError("Both scholarly providers failed: " + "; ".join(errors))
    unique, by_doi, by_id = [], {}, {}
    for paper in collected:
        doi = _canonical_doi(paper.get("doi"))
        identifier = str(paper.get("id") or "").strip().lower()
        index = by_doi.get(doi) if doi else None
        if index is None and identifier:
            index = by_id.get(identifier)
        if index is not None:
            previous = unique[index]
            # Prefer a longer source abstract, without replacing a stable DOI.
            if len(paper.get("abstract") or "") > len(previous.get("abstract") or ""):
                previous["abstract"] = paper["abstract"]
            if not previous.get("doi") and paper.get("doi"):
                previous["doi"] = paper["doi"]
            previous["sources"] = sorted(set(previous["sources"] + [paper["source"]]))
            if doi:
                by_doi[doi] = index
            if identifier:
                by_id[identifier] = index
            continue
        index = len(unique)
        unique.append({**paper, "sources": [paper["source"]]})
        if doi:
            by_doi[doi] = index
        if identifier:
            by_id[identifier] = index
    # Prioritize usable abstracts, while keeping original provider order within bands.
    unique.sort(key=lambda paper: not bool((paper.get("abstract") or "").strip()))
    return unique[:max_results]
