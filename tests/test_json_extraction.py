import json
from sara.json_extraction import (
    EXTRACTION_SCHEMA, json_extraction_prompt,
    validate_json_extraction, parse_json_extraction,
)
from sara.extraction import verify_supporting_evidence, normalize_supported_subquestions

ABSTRACT = ("This study evaluates a convolutional neural network for leukemia detection. "
            "The model was evaluated on 1,000 blood images and achieved 96.5% accuracy.")
QUESTIONS = ["What method was used?", "What accuracy was reported?"]


def _sample():
    return {
        "objective": "Evaluate CNN for leukemia detection",
        "methodology": "Convolutional neural network",
        "dataset_sample": "1,000 blood images",
        "findings": "96.5% accuracy",
        "limitations": "",
        "supported_subquestions": QUESTIONS,
        "supporting_evidence": ["The model was evaluated on 1,000 blood images and achieved 96.5% accuracy."],
    }


def test_json_schema_is_strict():
    assert EXTRACTION_SCHEMA["additionalProperties"] is False
    assert set(EXTRACTION_SCHEMA["required"]) == (
    set(_sample()) | {"question_evidence"}
)


def test_json_extraction_preserves_evidence_and_questions():
    raw = json.dumps(_sample())
    assert validate_json_extraction(raw)["valid"]
    parsed = parse_json_extraction(raw)
    assert verify_supporting_evidence(ABSTRACT, parsed["supporting_evidence"])["verified"]
    assert normalize_supported_subquestions(parsed["supported_subquestions"], QUESTIONS) == QUESTIONS


def test_json_extraction_rejects_missing_and_wrong_types():
    sample = _sample()
    del sample["objective"]
    assert not validate_json_extraction(json.dumps(sample))["valid"]
    sample = _sample()
    sample["supporting_evidence"] = "fabricated"
    assert not validate_json_extraction(json.dumps(sample))["valid"]
    assert not validate_json_extraction("not json")["valid"]


def test_json_extraction_missing_values_are_empty():
    sample = _sample()
    sample["limitations"] = "NOT_AVAILABLE"
    sample["supported_subquestions"] = ["NOT_AVAILABLE"]
    parsed = parse_json_extraction(json.dumps(sample))
    assert parsed["limitations"] == ""
    assert parsed["supported_subquestions"] == []


def test_prompt_requires_verbatim_evidence_and_untrusted_abstract():
    prompt = json_extraction_prompt("Title", ABSTRACT, QUESTIONS)
    assert ABSTRACT in prompt
    assert "verbatim" in prompt
    assert "untrusted" in prompt

def test_grounded_quote_does_not_guarantee_semantic_support():
    abstract = (
        "The study used 1,000 blood images. "
        "The classification accuracy was 96.5%."
    )

    question = "What classification accuracy was reported?"
    irrelevant_quote = "The study used 1,000 blood images."

    grounding = verify_supporting_evidence(
        abstract,
        [irrelevant_quote],
    )

    questions = normalize_supported_subquestions(
        [question],
        [question],
    )

    assert grounding["verified"] is True
    assert questions == [question]

    # The checks above establish textual grounding and question identity,
    # but do not establish that the quote answers the question.
def test_invalid_json_extraction_is_rejected():
    from sara.json_extraction import validate_json_extraction

    invalid_responses = [
        "{invalid json}",
        '{"objective": "test"',
        "This is not JSON",
        "",
    ]

    for response in invalid_responses:
        result = validate_json_extraction(response)
        assert not result["valid"], (
            f"Invalid JSON was accepted: {response!r}"
        )
def test_question_evidence_optional_mapping():
    import json
    from sara.json_extraction import validate_json_extraction

    data = {
        "objective": "Evaluate the model",
        "methodology": "CNN",
        "dataset_sample": "100 images",
        "findings": "Accuracy was 95%",
        "limitations": "",
        "supported_subquestions": ["What is the accuracy?"],
        "supporting_evidence": ["Accuracy was 95%"],
        "question_evidence": {
            "What is the accuracy?": "Accuracy was 95%"
        },
    }

    result = validate_json_extraction(json.dumps(data))
    assert result["valid"]
