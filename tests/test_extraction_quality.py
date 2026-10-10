
from sara.agent import validate_extraction_quality
from sara.agent import verify_supporting_evidence
from sara.schemas import parse_evidence_extraction

def test_missing_markers_are_not_substantive():
    extraction = {
        "objective": "NOT_AVAILABLE",
        "methodology": "N/A",
        "dataset_sample": "",
        "findings": "UNKNOWN",
        "limitations": "NONE",
    }

    result = validate_extraction_quality(extraction)

    assert result["usable"] is False
    assert result["populated_field_count"] == 0


def test_real_academic_information_is_usable():
    extraction = {
        "objective": "Evaluate automated literature screening.",
        "methodology": "Systematic literature review.",
        "dataset_sample": "NOT_AVAILABLE",
        "findings": "",
        "limitations": "",
    }

    result = validate_extraction_quality(extraction)

    assert result["usable"] is True
    assert result["populated_field_count"] == 2
    assert result["populated_fields"] == [
        "objective",
        "methodology",
    ]
def test_verify_supporting_evidence_with_quotation_marks():
    abstract = (
        "The proposed framework improves the accuracy "
        "of automated literature screening."
    )

    supporting_evidence = [
        '"improves the accuracy of automated literature screening"'
    ]

    result = verify_supporting_evidence(
        abstract=abstract,
        supporting_evidence=supporting_evidence,
    )

    assert result["verified"] is True
    assert len(result["verified_quotes"]) == 1
    assert result["unverified_quotes"] == []
def test_missing_evidence_marker_is_not_verified():
    abstract = (
        "This study evaluates automated literature screening."
    )

    result = verify_supporting_evidence(
        abstract=abstract,
        supporting_evidence=["- NOT_AVAILABLE"],
    )

    assert result["verified"] is False
    assert result["verified_quotes"] == []
def test_extraction_quality_rejects_formatted_missing_markers():
    extraction = {
        "objective": "- NOT_AVAILABLE",
        "methodology": "NOT_AVAILABLE",
        "dataset_sample": "",
        "findings": "* NOT_AVAILABLE",
        "limitations": "UNKNOWN",
    }

    result = validate_extraction_quality(extraction)

    assert result["usable"] is False
    assert result["populated_field_count"] == 0
    assert result["populated_fields"] == []
    assert result["total_fields"] == 5
def test_parse_evidence_extraction_normalizes_missing_fields():
    response = (
        "OBJECTIVE:\n"
        "- NOT_AVAILABLE\n"
        "METHODOLOGY:\n"
        "* NOT_AVAILABLE\n"
        "DATASET_SAMPLE:\n"
        "NOT_AVAILABLE\n"
        "FINDINGS:\n"
        "- NOT_AVAILABLE\n"
        "LIMITATIONS:\n"
        "UNKNOWN\n"
        "SUPPORTED_SUBQUESTIONS:\n"
        "- NOT_AVAILABLE\n"
        "SUPPORTING_EVIDENCE:\n"
        "- NOT_AVAILABLE\n"
    )

    result = parse_evidence_extraction(response)

    assert result["objective"] == ""
    assert result["methodology"] == ""
    assert result["dataset_sample"] == ""
    assert result["findings"] == ""
    assert result["limitations"] == ""
    assert result["supported_subquestions"] == []
    assert result["supporting_evidence"] == []
def test_parse_evidence_extraction_rejects_missing_list_items():
    response = (
        "OBJECTIVE:\n"
        "Evaluate research agents.\n"
        "METHODOLOGY:\n"
        "Literature analysis.\n"
        "DATASET_SAMPLE:\n"
        "NOT_AVAILABLE\n"
        "FINDINGS:\n"
        "NOT_AVAILABLE\n"
        "LIMITATIONS:\n"
        "NOT_AVAILABLE\n"
        "SUPPORTED_SUBQUESTIONS:\n"
        "- UNKNOWN\n"
        "- N/A\n"
        "- NOT_AVAILABLE\n"
        "SUPPORTING_EVIDENCE:\n"
        "- UNKNOWN\n"
        "- N/A\n"
        "- NOT_AVAILABLE\n"
    )

    result = parse_evidence_extraction(response)

    assert result["supported_subquestions"] == []
    assert result["supporting_evidence"] == []