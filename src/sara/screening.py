"""
Deterministic paper screening for the SARA non-agentic baseline.

This module applies simple fixed rules to retrieved papers.
It does not use an LLM or autonomous decision-making.
"""


def screen_papers(
    papers: list[dict],
    search_query: str,
    start_year: int = 2021,
) -> tuple[list[dict], list[dict]]:
    """
    Screen papers using simple deterministic baseline rules.

    Papers are included when:
    - the publication year is within the allowed range; and
    - the title contains at least one search-query keyword.

    Returns:
        A tuple containing included and excluded papers.
    """

    keywords = {
        word.lower()
        for word in search_query.split()
        if len(word) > 2
    }

    included = []
    excluded = []

    for paper in papers:
        title = (paper.get("title") or "").lower()
        year = paper.get("year")

        if not year or year < start_year:
            excluded.append(
                {
                    **paper,
                    "exclusion_reason": "Publication year outside allowed range.",
                }
            )
            continue

        matched_keywords = [
            keyword for keyword in keywords
            if keyword in title
        ]

        if not matched_keywords:
            excluded.append(
                {
                    **paper,
                    "exclusion_reason": "No search-query keywords found in title.",
                }
            )
            continue

        included.append(
            {
                **paper,
                "matched_keywords": matched_keywords,
            }
        )

    return included, excluded


def screen_agent_papers(
    papers: list[dict],
    start_year: int = 2021,
) -> tuple[list[dict], list[dict]]:
    """Screen papers using deterministic eligibility rules for the agent."""
    included = []
    excluded = []

    for paper in papers:
        year = paper.get("year")

        if not year or year < start_year:
            excluded.append(
                {
                    **paper,
                    "exclusion_reason": "Publication year outside allowed range.",
                }
            )
            continue
        abstract = (paper.get("abstract") or "").strip()

        if not abstract:
            excluded.append(
                {
                    **paper,
                    "exclusion_reason": "No public abstract available.",
                }
            )
            continue
        paper_id = paper.get("doi") or paper.get("id")

        if not paper_id:
            excluded.append(
                {
                    **paper,
                    "exclusion_reason": "No verifiable persistent identifier.",
                }
            )
            continue
        included.append(
            {
                **paper,
                "screening_status": "eligible",
            }
        )


    return included, excluded