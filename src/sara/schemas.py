"""
Structured output validation for SARA.

This module validates model-generated outputs before they are
accepted by the rest of the system.
"""


REQUIRED_PLANNING_SECTIONS = (
    "OBJECTIVE:",
    "SUBQUESTIONS:",
    "KEYWORDS:",
)


def validate_research_plan(response: str) -> dict:
    """
    Validate the basic structure of a model-generated research plan.

    Args:
        response: Raw text returned by the language model.

    Returns:
        A dictionary containing validation status and missing sections.
    """

    if not response or not response.strip():
        return {
            "valid": False,
            "missing_sections": list(REQUIRED_PLANNING_SECTIONS),
            "reason": "Model response is empty.",
        }

    missing_sections = [
        section
        for section in REQUIRED_PLANNING_SECTIONS
        if section not in response
    ]

    if missing_sections:
        return {
            "valid": False,
            "missing_sections": missing_sections,
            "reason": "Required planning sections are missing.",
        }

    return {
        "valid": True,
        "missing_sections": [],
        "reason": "Research plan structure is valid.",
    }
def validate_replanning_response(response: str) -> dict:
    """
    Validate the structure of a replanning model response.
    """
    if not response or not response.strip():
        return {
            "valid": False,
            "reason": "Replanning response is empty.",
        }

    if "REVISED_KEYWORDS:" not in response:
        return {
            "valid": False,
            "reason": "Missing REVISED_KEYWORDS section.",
        }

    return {
        "valid": True,
        "reason": "Replanning response has the required structure.",
    }
def parse_revised_keywords(response: str) -> list[str]:
    """
    Extract revised search keywords from a validated replanning response.
    """
    if "REVISED_KEYWORDS:" not in response:
        return []

    keyword_section = response.split("REVISED_KEYWORDS:", 1)[1]

    keywords = []
    for line in keyword_section.splitlines():
        line = line.strip()

        if line.startswith("-"):
            keyword = line[1:].strip().strip('"').strip("'")
            if keyword:
                keywords.append(keyword)

    return keywords