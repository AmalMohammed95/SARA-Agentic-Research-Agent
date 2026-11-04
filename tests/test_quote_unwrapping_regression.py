import json
from sara.extraction import unwrap_evidence_quote, verify_supporting_evidence, verify_question_evidence


def test_wrapped_quote_verifies_against_source():
    quote = "A baseline judge with screenshots performed well."
    wrapped = json.dumps({"How was it evaluated?": quote})
    assert unwrap_evidence_quote(wrapped) == quote
    assert verify_supporting_evidence("The study found: " + quote, [wrapped])["verified"]


def test_question_mapping_unwraps_quote_for_semantic_judge():
    question = "How was it evaluated?"
    quote = "Repeated trials measured failure rates."
    wrapped = json.dumps({question: quote})
    result = verify_question_evidence(quote, {question: wrapped}, [question])
    assert result["verified_mapping"] == {question: quote}


def test_multiple_json_values_are_not_silently_accepted():
    wrapped = json.dumps({"a": "true quote", "b": "fabricated"})
    assert unwrap_evidence_quote(wrapped) == wrapped
    assert not verify_supporting_evidence("true quote", [wrapped])["verified"]


def test_no_substring_fabrication():
    wrapped = json.dumps({"q": "The system achieved 99% accuracy."})
    assert not verify_supporting_evidence("The system achieved 89% accuracy.", [wrapped])["verified"]
