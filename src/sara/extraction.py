"""
Evidence extraction utilities for SARA.

This module converts selected academic papers into structured
evidence records that can later be validated by the evidence gate.
"""

REQUIRED_EXTRACTION_FIELDS = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)


def create_empty_evidence_record(paper: dict) -> dict:
    """
    Create a structured evidence record for a selected paper.

    Missing academic evidence is kept empty rather than invented.
    """
    return {
        "paper_id": paper.get("doi") or paper.get("id"),
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

        if normalized_quote and normalized_quote in normalized_abstract:
            verified_quotes.append(quote)
        else:
            unverified_quotes.append(quote)

    return {
        "verified": bool(verified_quotes) and not unverified_quotes,
        "verified_quotes": verified_quotes,
        "unverified_quotes": unverified_quotes,
    }