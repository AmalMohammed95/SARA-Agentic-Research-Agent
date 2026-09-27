"""
SARA Non-Agentic Baseline

This module provides a simple fixed workflow that will later be used
as a comparison point for the agentic version of SARA.

The baseline does not perform autonomous planning, replanning,
tool selection, or iterative decision-making.
"""

from .tools import search_openalex
from .screening import screen_papers
def build_search_query(research_question: str) -> str:
    """
    Convert a research question into a simple fixed search query.

    This baseline uses deterministic text processing only.
    It does not use an LLM or autonomous query planning.
    """

    stop_words = {
        "how", "are", "is", "the", "a", "an", "in", "on",
        "of", "for", "to", "used", "using", "what", "which",
        "why", "when", "where", "do", "does"
    }

    words = research_question.lower().replace("?", "").split()

    keywords = [
        word for word in words
        if word not in stop_words
    ]

    return " ".join(keywords)
def run_baseline(research_question: str) -> dict:
    """
    Run the initial non-agentic baseline workflow.

    Args:
        research_question: The academic research question provided by the user.

    Returns:
        A structured dictionary containing the baseline result.
    """

    if not research_question or not research_question.strip():
        return {
            "status": "INVALID_INPUT",
            "research_question": research_question,
            "message": "A research question is required.",
        }

    search_query = build_search_query(research_question.strip())
    papers = search_openalex(search_query, max_results=5)
    included_papers, excluded_papers = screen_papers(
    papers,
    search_query,
)
    return {
    "status": "COMPLETED",
    "research_question": research_question.strip(),
    "search_query": search_query,
    "workflow": "non_agentic_baseline",
    "papers_found": len(papers),
    "papers_included": len(included_papers),
    "papers_excluded": len(excluded_papers),
    "included_papers": included_papers,
    "excluded_papers": excluded_papers,
    "message": "Baseline academic search and screening completed.",
}


if __name__ == "__main__":
    question = input("Enter a research question: ")

    result = run_baseline(question)

    print("\nSARA Baseline Result")
    print("-" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")