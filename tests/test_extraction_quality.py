
from sara.agent import validate_extraction_quality


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
