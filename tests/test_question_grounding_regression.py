import json
from sara.question_grounding import verify_question_evidence
from sara.json_extraction import validate_json_extraction


def test_one_bad_quote_does_not_invalidate_other_question():
    questions = ["How is reliability measured?", "How are results validated?"]
    abstract = "Reliability was measured by repeated trials and failure rates."
    check = verify_question_evidence(abstract, {
        questions[0]: "Reliability was measured by repeated trials and failure rates.",
        questions[1]: "Human validators confirmed everything.",
    }, questions, questions)
    assert check["verified_subquestions"] == [questions[0]]
    assert questions[1] in check["rejected_subquestions"]


def test_schema_rejects_missing_question_evidence():
    raw = {"objective": "x", "methodology": "", "dataset_sample": "", "findings": "", "limitations": "", "supported_subquestions": ["Q"], "supporting_evidence": ["x"]}
    assert "question_evidence" in __import__("sara.json_extraction", fromlist=["EXTRACTION_SCHEMA"]).EXTRACTION_SCHEMA["required"]


def test_unsupported_question_cannot_be_credited_from_unrelated_quote():
    assert verify_question_evidence("A benchmark measured latency.", {"Q": "A benchmark measured latency."}, ["Q"], ["Q"])["verified_subquestions"] == ["Q"]
    assert not verify_question_evidence("A benchmark measured latency.", {"Q": "Accuracy was 99%."}, ["Q"], ["Q"])["verified_subquestions"]
