"""Per-question source grounding; never infer direct support from topical similarity."""
from .extraction import verify_supporting_evidence, normalize_supported_subquestions


def verify_question_evidence(abstract, mapping, proposed, original):
    mapping = mapping if isinstance(mapping, dict) else {}
    valid = []
    rejected = {}
    for question in normalize_supported_subquestions(proposed, original):
        quote = mapping.get(question, "")
        if isinstance(quote, str) and quote and verify_supporting_evidence(abstract, [quote])["verified"]:
            valid.append(question)
        else:
            rejected[question] = "missing_or_unverified_verbatim_quote"
    return {"verified_subquestions": valid, "rejected_subquestions": rejected}
