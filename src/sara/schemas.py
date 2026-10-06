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

def parse_research_plan(response: str) -> dict:
    """
    Extract structured fields from a validated research plan.
    """
    if not all(
        section in response
        for section in REQUIRED_PLANNING_SECTIONS
    ):
        return {
            "objective": "",
            "subquestions": [],
            "keywords": [],
        }

    objective_section = response.split("OBJECTIVE:", 1)[1].split(
        "SUBQUESTIONS:", 1
    )[0]

    subquestion_section = response.split("SUBQUESTIONS:", 1)[1].split(
        "KEYWORDS:", 1
    )[0]

    keyword_section = response.split("KEYWORDS:", 1)[1]

    objective = objective_section.strip()

    subquestions = [
        line[1:].strip().strip('"').strip("'")
        for line in subquestion_section.splitlines()
        if line.strip().startswith("-")
    ]

    keywords = [
        line[1:].strip().strip('"').strip("'")
        for line in keyword_section.splitlines()
        if line.strip().startswith("-")
    ]

    return {
        "objective": objective,
        "subquestions": subquestions,
        "keywords": keywords,
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
REQUIRED_EXTRACTION_SECTIONS = (
    "OBJECTIVE:",
    "METHODOLOGY:",
    "DATASET_SAMPLE:",
    "FINDINGS:",
    "LIMITATIONS:",
    "SUPPORTED_SUBQUESTIONS:",
    "SUPPORTING_EVIDENCE:",
)

def validate_evidence_extraction(response: str) -> dict:
    """
    Validate the required structure of an evidence extraction response.
    """
    if not response or not response.strip():
        return {
            "valid": False,
            "missing_sections": list(REQUIRED_EXTRACTION_SECTIONS),
        }

    missing_sections = [
        section
        for section in REQUIRED_EXTRACTION_SECTIONS
        if section not in response
    ]

    return {
        "valid": not missing_sections,
        "missing_sections": missing_sections,
    }
def parse_evidence_extraction(response: str) -> dict:
    """
    Parse a validated evidence extraction response into structured fields.
    """
    def extract_section(start: str, end: str | None = None) -> str:
        content = response.split(start, 1)[1]

        if end:
            content = content.split(end, 1)[0]

        value = content.strip()

        if value.upper() == "NOT_AVAILABLE":
            return ""

        return value

    objective = extract_section("OBJECTIVE:", "METHODOLOGY:")
    methodology = extract_section("METHODOLOGY:", "DATASET_SAMPLE:")
    dataset_sample = extract_section("DATASET_SAMPLE:", "FINDINGS:")
    findings = extract_section("FINDINGS:", "LIMITATIONS:")
    limitations = extract_section(
        "LIMITATIONS:",
        "SUPPORTED_SUBQUESTIONS:",
    )

    supported_section = response.split(
        "SUPPORTED_SUBQUESTIONS:", 1
    )[1].split("SUPPORTING_EVIDENCE:", 1)[0]

    supported_subquestions = [
        line[1:].strip().strip('"').strip("'")
        for line in supported_section.splitlines()
        if line.strip().startswith("-")
        and line[1:].strip().upper() != "NOT_AVAILABLE"
    ]

    evidence_section = response.split(
        "SUPPORTING_EVIDENCE:", 1
    )[1]

    supporting_evidence = [
        line[1:].strip().strip('"').strip("'")
        for line in evidence_section.splitlines()
        if line.strip().startswith("-")
        and line[1:].strip().upper() != "NOT_AVAILABLE"
    ]

    return {
        "objective": objective,
        "methodology": methodology,
        "dataset_sample": dataset_sample,
        "findings": findings,
        "limitations": limitations,
        "supported_subquestions": supported_subquestions,
        "supporting_evidence": supporting_evidence,
    }

def validate_extraction_quality(extraction: dict) -> dict:
    """
    Evaluate whether a parsed extraction contains substantive evidence.
    """
    substantive_fields = (
        "objective",
        "methodology",
        "dataset_sample",
        "findings",
        "limitations",
    )

    populated_fields = [
        field
        for field in substantive_fields
        if extraction.get(field)
        and str(extraction.get(field)).strip()
    ]

    return {
        "usable": bool(populated_fields),
        "populated_fields": populated_fields,
        "populated_field_count": len(populated_fields),
        "total_fields": len(substantive_fields),
    }

    
def validate_semantic_screening(response: str) -> dict:
    """
    Validate the structure and decision of a semantic screening response.
    """
    if not response or not response.strip():
        return {
            "valid": False,
            "reason": "Semantic screening response is empty.",
        }

    if "DECISION:" not in response or "REASON:" not in response:
        return {
            "valid": False,
            "reason": "Required semantic screening sections are missing.",
        }

    decision_section = response.split("DECISION:", 1)[1].split(
        "REASON:", 1
    )[0].strip().upper()

    if decision_section not in {"INCLUDE", "EXCLUDE"}:
        return {
            "valid": False,
            "reason": "Semantic screening decision must be INCLUDE or EXCLUDE.",
        }

    return {
        "valid": True,
        "reason": "Semantic screening response is valid.",
    }
def parse_semantic_screening(response: str) -> dict:
    """
    Parse a validated semantic screening response.
    """
    decision = response.split("DECISION:", 1)[1].split(
        "REASON:", 1
    )[0].strip().upper()

    reason = response.split("REASON:", 1)[1].strip()

    return {
        "decision": decision,
        "reason": reason,
    }