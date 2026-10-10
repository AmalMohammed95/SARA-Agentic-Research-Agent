import pytest

from sara.schemas import (
    validate_batch_semantic_screening,
    parse_batch_semantic_screening,
)


def test_valid_batch_screening():
    response = """{
        "results": [
            {"paper_id": "P1", "decision": "INCLUDE", "reason": "Directly relevant."},
            {"paper_id": "P2", "decision": "EXCLUDE", "reason": "Not directly relevant."}
        ]
    }"""

    expected_ids = ["P1", "P2"]

    validation = validate_batch_semantic_screening(response, expected_ids)
    assert validation["valid"] is True

    parsed = parse_batch_semantic_screening(response)
    assert len(parsed) == 2
    assert parsed[0]["paper_id"] == "P1"


@pytest.mark.parametrize(
    "response",
    [
        '{"results": [{"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant."}]}',
        '{"results": [{"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant."}, {"paper_id": "P1", "decision": "EXCLUDE", "reason": "Irrelevant."}]}',
        '{"results": [{"paper_id": "P1", "decision": "MAYBE", "reason": "Uncertain."}, {"paper_id": "P2", "decision": "EXCLUDE", "reason": "Irrelevant."}]}',
        "not valid json",
    ],
)
def test_invalid_batch_screening(response):
    validation = validate_batch_semantic_screening(
        response, ["P1", "P2"]
    )
    assert validation["valid"] is False


def test_batch_json_array_is_accepted():
    response = """[
        {"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant."},
        {"paper_id": "P2", "decision": "EXCLUDE", "reason": "Not relevant."}
    ]"""

    validation = validate_batch_semantic_screening(
        response, ["P1", "P2"]
    )

    assert validation["valid"] is True

    parsed = parse_batch_semantic_screening(response)

    assert len(parsed) == 2
    assert parsed[0]["paper_id"] == "P1"
    assert parsed[1]["decision"] == "EXCLUDE"


def test_batch_json_array_rejects_duplicate_ids():
    response = """[
        {"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant."},
        {"paper_id": "P1", "decision": "EXCLUDE", "reason": "Not relevant."}
    ]"""

    validation = validate_batch_semantic_screening(
        response, ["P1", "P2"]
    )

    assert validation["valid"] is False
