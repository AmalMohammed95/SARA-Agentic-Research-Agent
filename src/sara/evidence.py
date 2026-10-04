"""
Evidence sufficiency evaluation for SARA.

This module evaluates whether the collected research evidence
meets explicit deterministic sufficiency criteria before the
agent proceeds toward synthesis.
"""


MIN_RELEVANT_STUDIES = 5

MIN_STUDIES_PER_SUBQUESTION = 2

MAX_MISSING_FIELD_RATE = 0.20

REQUIRED_EVIDENCE_FIELDS = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)
REQUIRED_PROVENANCE_FIELDS = (
    "paper_id",
)
VALID_CONFLICT_STATUSES = (
    "none",
    "identified",
)
VALID_CLAIM_SUPPORT_STATUSES = (
    "supported",
    "unsupported",
)
def get_paper_identifier(paper: dict) -> str | None:
    """
    Return the best available persistent identifier for a paper.
    DOI is preferred, followed by the paper ID.
    """
    return paper.get("doi") or paper.get("id")
def evaluate_evidence_sufficiency(
    selected_papers: list[dict],
    subquestions: list[str] | None = None,
    evidence: list[dict] | None = None,
) -> dict:
    """
    Evaluate the minimum relevant-study requirement.

    Args:
        selected_papers: Papers currently selected as relevant.
        subquestions: Research subquestions that require evidence coverage.
        evidence: Structured evidence records extracted from selected papers.
    Returns:
        A structured sufficiency decision.
    """

    relevant_count = len(selected_papers)
    unique_identifiers = {
        get_paper_identifier(paper)
        for paper in selected_papers
        if get_paper_identifier(paper) is not None
    }

    unique_relevant_count = len(unique_identifiers)

    unidentified_papers_count = sum(
    1
    for paper in selected_papers
    if get_paper_identifier(paper) is None
)
    evidence = evidence or []

    invalid_claim_support_status_count = sum(
    1
    for record in evidence
    if record.get("claim_support_status") not in VALID_CLAIM_SUPPORT_STATUSES
)

    invalid_conflict_status_count = sum(
    1
    for record in evidence
    if record.get("conflict_status") not in VALID_CONFLICT_STATUSES
)
    unsupported_claim_count = sum(
    1
    for record in evidence
    if record.get("claim_support_status") == "unsupported"
)

    missing_provenance_count = sum(
    1
    for record in evidence
    if any(
        not record.get(field)
        for field in REQUIRED_PROVENANCE_FIELDS
    )
)

    invalid_provenance_count = sum(
    1
    for record in evidence
    if record.get("paper_id")
    and record.get("paper_id") not in unique_identifiers
)
    total_required_fields = len(evidence) * len(REQUIRED_EVIDENCE_FIELDS)

    missing_fields = sum(
        1
        for record in evidence
        for field in REQUIRED_EVIDENCE_FIELDS
        if not record.get(field)
    )

    missing_field_rate = (
        missing_fields / total_required_fields
        if total_required_fields > 0
        else 1.0
    )
    subquestions = subquestions or []

    subquestion_coverage = {}

    for subquestion in subquestions:
        coverage_count = sum(
            1
            for paper in selected_papers
            
            if subquestion in paper.get("supports_subquestions", [])
        )

        subquestion_coverage[subquestion] = coverage_count
    coverage_gaps = [
        f"Subquestion '{subquestion}' has only {count} supporting studies; "
        f"at least {MIN_STUDIES_PER_SUBQUESTION} are required."
        for subquestion, count in subquestion_coverage.items()
        if count < MIN_STUDIES_PER_SUBQUESTION
    ]

    if unique_relevant_count < MIN_RELEVANT_STUDIES:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "gaps": [
                f"At least {MIN_RELEVANT_STUDIES} unique identifiable relevant studies are required."
            ],
        }
    if coverage_gaps:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "gaps": coverage_gaps,
        }
    if missing_field_rate > MAX_MISSING_FIELD_RATE:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "gaps": [
                f"Missing evidence field rate is {missing_field_rate:.2%}; "
                f"maximum allowed is {MAX_MISSING_FIELD_RATE:.0%}."
            ],
        }
    if missing_provenance_count > 0:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "missing_provenance_count": missing_provenance_count,
            "gaps": [
                f"{missing_provenance_count} evidence record(s) are missing provenance."
            ],
        }
    if invalid_provenance_count > 0:
            return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "missing_provenance_count": missing_provenance_count,
            "invalid_provenance_count": invalid_provenance_count,
            "gaps": [
                f"{invalid_provenance_count} evidence record(s) reference "
                "papers that are not in the selected evidence set."
            ],
        }
    if invalid_conflict_status_count > 0:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "missing_provenance_count": missing_provenance_count,
            "invalid_provenance_count": invalid_provenance_count,
            "invalid_conflict_status_count": invalid_conflict_status_count,
            "gaps": [
                f"{invalid_conflict_status_count} evidence record(s) have "
                "a missing or invalid conflict status."
            ],
        }
    if invalid_claim_support_status_count > 0:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "missing_provenance_count": missing_provenance_count,
            "invalid_provenance_count": invalid_provenance_count,
            "invalid_conflict_status_count": invalid_conflict_status_count,
            "invalid_claim_support_status_count": invalid_claim_support_status_count,
            "gaps": [
                f"{invalid_claim_support_status_count} evidence record(s) have "
                "a missing or invalid claim support status."
            ],
        }
    if unsupported_claim_count > 0:
        return {
            "sufficient": False,
            "relevant_studies": relevant_count,
            "unique_relevant_studies": unique_relevant_count,
            "unidentified_papers": unidentified_papers_count,
            "required_studies": MIN_RELEVANT_STUDIES,
            "subquestion_coverage": subquestion_coverage,
            "missing_field_rate": missing_field_rate,
            "missing_provenance_count": missing_provenance_count,
            "invalid_provenance_count": invalid_provenance_count,
            "invalid_conflict_status_count": invalid_conflict_status_count,
            "invalid_claim_support_status_count": invalid_claim_support_status_count,
            "unsupported_claim_count": unsupported_claim_count,
            "gaps": [
                f"{unsupported_claim_count} evidence record(s) contain "
                "unsupported claims."
            ],
        }
    return {
        "sufficient": True,
        "relevant_studies": relevant_count,
        "unique_relevant_studies": unique_relevant_count,
        "unidentified_papers": unidentified_papers_count,
        "required_studies": MIN_RELEVANT_STUDIES,
        "subquestion_coverage": subquestion_coverage,
        "missing_field_rate": missing_field_rate,
        "missing_provenance_count": missing_provenance_count,
        "invalid_provenance_count": invalid_provenance_count,
        "invalid_conflict_status_count": invalid_conflict_status_count,
        "invalid_claim_support_status_count": invalid_claim_support_status_count,
        "unsupported_claim_count": unsupported_claim_count,
        "gaps": [],
    }