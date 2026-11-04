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
    "not_assessed",
    "insufficient_data",
)
def get_paper_identifier(paper: dict) -> str | None:
    """
    Return the best available persistent identifier for a paper.
    DOI is preferred, followed by the paper ID.
    """
    return paper.get("doi") or paper.get("id")
def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """
    Remove duplicate papers using DOI or OpenAlex ID.
    Preserve the first occurrence.
    """
    unique_papers = []
    seen_dois = set()
    seen_ids = set()

    for paper in papers:
        doi = paper.get("doi")
        paper_id = paper.get("id")

        normalized_doi = (
            str(doi).strip().lower()
            if doi
            else None
        )

        normalized_id = (
            str(paper_id).strip().lower()
            if paper_id
            else None
        )

        if (
            normalized_doi
            and normalized_doi in seen_dois
        ) or (
            normalized_id
            and normalized_id in seen_ids
        ):
            continue

        unique_papers.append(paper)

        if normalized_doi:
            seen_dois.add(normalized_doi)

        if normalized_id:
            seen_ids.add(normalized_id)

    return unique_papers
def is_duplicate_paper(paper: dict, existing_papers: list[dict]) -> bool:
    """
    Check whether a paper shares a DOI or OpenAlex ID
    with an existing paper.
    """
    doi = str(paper.get("doi") or "").strip().lower()
    paper_id = str(paper.get("id") or "").strip().lower()

    for existing in existing_papers:
        existing_doi = str(existing.get("doi") or "").strip().lower()
        existing_id = str(existing.get("id") or "").strip().lower()

        if doi and existing_doi and doi == existing_doi:
            return True

        if paper_id and existing_id and paper_id == existing_id:
            return True

    return False
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
    selected_papers = deduplicate_papers(selected_papers)
    unique_identifiers = {
        get_paper_identifier(paper)
        for paper in selected_papers
        if get_paper_identifier(paper) is not None
    }
    accepted_identifiers = {
        identifier
        for paper in selected_papers
        for identifier in (paper.get("doi"), paper.get("id"))
        if identifier is not None
    }
    unique_relevant_count = len(unique_identifiers)

    unidentified_papers_count = sum(
    1
    for paper in selected_papers
    if get_paper_identifier(paper) is None
)
    evidence = evidence or []

    evidence_paper_ids = {
        record.get("paper_id")
        for record in evidence
        if record.get("paper_id") in accepted_identifiers
    }

    missing_evidence_record_count = sum(
        1
        for paper in selected_papers
        if not any(
            identifier in evidence_paper_ids
            for identifier in (paper.get("doi"), paper.get("id"))
            if identifier is not None
        )
    )
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
    # A selected paper awaiting extraction is NOT an unsupported scientific claim.
    unsupported_claim_count = sum(
        1 for record in evidence
        if record.get("claim_support_status") == "unsupported"
        and record.get("extraction_status") not in ("pending", "failed")
    )

    unverified_evidence_count = sum(
        1 for record in evidence
        if record.get("extraction_status") == "completed"
        and record.get("claim_support_status") in ("not_assessed", "insufficient_data")
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
    and record.get("paper_id") not in accepted_identifiers
)
    total_required_fields = (
    len(unique_identifiers) * len(REQUIRED_EVIDENCE_FIELDS)
)

    missing_markers = {
   
        "",
        "NOT_AVAILABLE",
        "N/A",
        "NONE",
        "NULL",
        "UNKNOWN",
        "NOT_APPLICABLE",
        "NOT APPLICABLE",
        "NOT REPORTED",
        "NOT PROVIDED",
        "NOT SPECIFIED",
        "UNAVAILABLE",
        "NO INFORMATION",
    }

    def is_missing(value):
        if value is None:
            return True

        if isinstance(value, (list, tuple, dict, set)):
            return len(value) == 0

        if isinstance(value, str):
            normalized = value.strip().upper()

            # Handle common LLM formatting variations.
            normalized = normalized.lstrip("-*• ").strip()
            normalized = normalized.strip("`'\"").strip()

            return normalized in missing_markers or normalized.startswith((
                "NOT AVAILABLE:", "NOT REPORTED:", "UNKNOWN:",
            ))

        return False
   

   

    

    evidence_by_paper = {}

    for record in evidence:
        paper_id = record.get("paper_id")

        if paper_id not in accepted_identifiers:
            continue

        if paper_id not in evidence_by_paper:
            evidence_by_paper[paper_id] = []

        evidence_by_paper[paper_id].append(record)

    # Keep the denominator honest: only completed extractions have five
    # assessable fields. Unprocessed/failed studies are separate blocking gaps,
    # never silently ignored in the sufficiency decision.
    missing_fields = 0
    applicable_field_count = 0
    not_applicable_field_count = 0
    missing_by_field = {field: 0 for field in REQUIRED_EVIDENCE_FIELDS}
    processed_studies_count = 0
    pending_studies_count = 0
    failed_studies_count = 0

    for paper in selected_papers:
        paper_ids = {paper.get("doi"), paper.get("id")} - {None}
        matching_records = [
            record for paper_id in paper_ids
            for record in evidence_by_paper.get(paper_id, [])
        ]
        if not matching_records or all(
            record.get("extraction_status") == "pending"
            for record in matching_records
        ):
            pending_studies_count += 1
            continue
        completed_records = [
            record for record in matching_records
            if record.get("extraction_status", "completed") == "completed"
        ]
        if not completed_records:
            failed_studies_count += 1
            continue
        processed_studies_count += 1
        for field in REQUIRED_EVIDENCE_FIELDS:
            # Design-aware applicability never changes the 20% ceiling.
            # An explicit non-empirical study designation may remove the
            # sample field from the denominator, never infer its value.
            if field == "dataset_sample" and any(
                record.get("study_type") == "narrative_review"
                and record.get("dataset_sample") == "NOT_APPLICABLE"
                for record in completed_records
            ):
                not_applicable_field_count += 1
                continue
            applicable_field_count += 1
            if all(is_missing(record.get(field)) for record in completed_records):
                missing_fields += 1
                missing_by_field[field] += 1

    processed_required_fields = applicable_field_count
    # No processed evidence is 100% unavailable for reporting purposes; the
    # pending/failed flags prevent sufficiency independently.
    missing_field_rate = (
        missing_fields / processed_required_fields
        if processed_required_fields else 1.0
    )
    subquestions = subquestions or []
    subquestion_coverage = {}


    for subquestion in subquestions:
        supporting_studies = 0

        for paper in selected_papers:
            paper_ids = {
                paper.get("doi"),
                paper.get("id"),
            }
            paper_ids.discard(None)

            has_support = any(
                record.get("paper_id") in paper_ids
                and record.get("claim_support_status") == "supported"
                and subquestion in record.get(
                    "supported_subquestions", []
                )
                and (
                    record.get("extraction_status") is None  # legacy records
                    or bool(record.get("supporting_evidence"))
                )
                for record in evidence
            )

            if has_support:
                supporting_studies += 1

        subquestion_coverage[subquestion] = supporting_studies

    coverage_gaps = [
        f"Subquestion '{subquestion}' has only {count} supporting studies; "
        f"at least {MIN_STUDIES_PER_SUBQUESTION} are required."
        for subquestion, count in subquestion_coverage.items()
        if count < MIN_STUDIES_PER_SUBQUESTION
    ]

    
    gaps = []
    if pending_studies_count:
        gaps.append(
            f"{pending_studies_count} selected study/studies are pending extraction; "
            "they are not unsupported claims."
        )
    if failed_studies_count:
        gaps.append(
            f"{failed_studies_count} selected study/studies failed extraction "
            "or validation; their content was not assessed."
        )
    if missing_evidence_record_count > 0:
        gaps.append(
            f"{missing_evidence_record_count} selected study/studies "
            "have no matching evidence record."
        )

    if unique_relevant_count < MIN_RELEVANT_STUDIES:
        gaps.append(
            f"At least {MIN_RELEVANT_STUDIES} unique identifiable "
            "relevant studies are required."
        )

    gaps.extend(coverage_gaps)

    if missing_field_rate > MAX_MISSING_FIELD_RATE:
        gaps.append(
            f"Missing evidence field rate is {missing_field_rate:.2%}; "
            f"maximum allowed is {MAX_MISSING_FIELD_RATE:.0%}."
        )

    if missing_provenance_count > 0:
        gaps.append(
            f"{missing_provenance_count} evidence record(s) "
            "are missing provenance."
        )

    if invalid_provenance_count > 0:
        gaps.append(
            f"{invalid_provenance_count} evidence record(s) reference "
            "papers that are not in the selected evidence set."
        )

    if invalid_conflict_status_count > 0:
        gaps.append(
            f"{invalid_conflict_status_count} evidence record(s) have "
            "a missing or invalid conflict status."
        )

    if invalid_claim_support_status_count > 0:
        gaps.append(
            f"{invalid_claim_support_status_count} evidence record(s) have "
            "a missing or invalid claim support status."
        )

    if unverified_evidence_count:
        gaps.append(
            f"{unverified_evidence_count} completed evidence record(s) "
            "do not have verified support; these are not asserted claims."
        )

    if unsupported_claim_count > 0:
        gaps.append(
            f"{unsupported_claim_count} evidence record(s) contain "
            "unsupported claims."
        )

    return {
        "sufficient": not gaps,
        "relevant_studies": relevant_count,
        "unique_relevant_studies": unique_relevant_count,
        "unidentified_papers": unidentified_papers_count,
        "required_studies": MIN_RELEVANT_STUDIES,
        "subquestion_coverage": subquestion_coverage,
        "missing_field_rate": missing_field_rate,
        "missing_fields_count": missing_fields,
        "processed_studies_count": processed_studies_count,
        "pending_studies_count": pending_studies_count,
        "failed_studies_count": failed_studies_count,
        "assessed_required_fields": processed_required_fields,
        "not_applicable_fields_count": not_applicable_field_count,
        "missing_by_field": missing_by_field,
        "abstract_only_records": sum(
            record.get("evidence_source_scope") == "abstract_only"
            and record.get("extraction_status") == "completed"
            for record in evidence
        ),
        "verified_supported_records": sum(
            record.get("claim_support_status") == "supported"
            and bool(record.get("supporting_evidence"))
            and bool(record.get("source_spans"))
            for record in evidence
        ),
        "missing_evidence_record_count": missing_evidence_record_count,
        "missing_provenance_count": missing_provenance_count,
        "invalid_provenance_count": invalid_provenance_count,
        "invalid_conflict_status_count": invalid_conflict_status_count,
        "invalid_claim_support_status_count": (
            invalid_claim_support_status_count
        ),
        "unsupported_claim_count": unsupported_claim_count,
        "unverified_evidence_count": unverified_evidence_count,
        "gaps": gaps,
    }
