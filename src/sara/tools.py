"""
Academic search tools for SARA.

This module contains simple scholarly search functions used by the
non-agentic baseline. Agent-specific tool selection and validation
will be added in later development stages.
"""

import json
import urllib.parse
import urllib.request


OPENALEX_API_URL = "https://api.openalex.org/works"


def search_openalex(query: str, max_results: int = 5) -> list[dict]:
    """
    Search OpenAlex for scholarly works matching a research query.

    Args:
        query: Academic search query.
        max_results: Maximum number of works to return.

    Returns:
        A list of dictionaries containing basic paper metadata.
    """

    if not query or not query.strip():
        return []

    params = {
        "search": query.strip(),
        "per-page": max_results,
    }

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

    papers = []

    for work in data.get("results", []):
        papers.append(
            {
                "id": work.get("id"),
                "title": work.get("title"),
                "year": work.get("publication_year"),
                "doi": work.get("doi"),
            }
        )

    return papers