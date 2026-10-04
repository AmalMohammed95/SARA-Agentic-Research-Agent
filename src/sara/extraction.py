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