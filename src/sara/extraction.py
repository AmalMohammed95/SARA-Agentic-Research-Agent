"""
Evidence extraction utilities for SARA.

This module converts selected academic papers into structured
evidence records that can later be validated by the evidence gate.
"""
import re
REQUIRED_EXTRACTION_FIELDS = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)

NOT_APPLICABLE = "NOT_APPLICABLE"

def is_valid_not_applicable(field: str, record: dict) -> bool:
    """Allow N/A only for dataset_sample in non-empirical studies."""
    if field != "dataset_sample":
        return False

    if record.get(field) != NOT_APPLICABLE:
        return False

    return record.get("study_type") in {
        "theoretical",
        "conceptual",
        "narrative_review",
    }



def create_empty_evidence_record(paper: dict) -> dict:
    """
    Create a structured evidence record for a selected paper.

    Missing academic evidence is kept empty rather than invented.
    """
    return {
        "paper_id": paper.get("doi") or paper.get("id"),
        "study_type": "unknown",
        "objective": "",
        "methodology": "",
        "dataset_sample": "",
        "findings": "",
        "limitations": "",
        "supported_subquestions": [],
        "conflict_status": "none",
        "claim_support_status": "unsupported",
    }
def verify_supporting_evidence(
    abstract: str,
    supporting_evidence: list[str],
) -> dict:
    """Verify that extracted evidence quotes occur in the source abstract."""

    if not abstract or not supporting_evidence:
        return {
            "verified": False,
            "verified_quotes": [],
            "unverified_quotes": supporting_evidence,
        }

    normalized_abstract = " ".join(abstract.lower().split())

    verified_quotes = []
    unverified_quotes = []

    for quote in supporting_evidence:
        normalized_quote = " ".join(quote.lower().split())

        # Remove an optional trailing source label.
        normalized_quote = re.sub(
            r"\s*\(abstract\)\s*$",
            "",
            normalized_quote,
        )

        # Remove surrounding quotation marks.
        normalized_quote = normalized_quote.strip().strip(
            "\"'“”‘’"
        ).strip()
        if normalized_quote and normalized_quote in normalized_abstract:
            verified_quotes.append(quote)
        else:
            unverified_quotes.append(quote)

    return {
        "verified": bool(verified_quotes) and not unverified_quotes,
        "verified_quotes": verified_quotes,
        "unverified_quotes": unverified_quotes,
    }