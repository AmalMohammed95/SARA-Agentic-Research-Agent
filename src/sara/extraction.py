"""
Evidence extraction utilities for SARA.

This module converts selected academic papers into structured
evidence records that can later be validated by the evidence gate.
"""
import re
REQUIRED_EXTRACTION_FIELDS = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)

NOT_APPLICABLE = "NOT_APPLICABLE"

def is_valid_not_applicable(field: str, record: dict) -> bool:
    """Allow N/A only for dataset_sample in non-empirical studies."""
    if field != "dataset_sample":
        return False

    if record.get(field) != NOT_APPLICABLE:
        return False

    return record.get("study_type") in {
        "theoretical",
        "conceptual",
        "narrative_review",
    }



def create_empty_evidence_record(paper: dict) -> dict:
    """
    Create a structured evidence record for a selected paper.

    Missing academic evidence is kept empty rather than invented.
    """
    return {
        "paper_id": paper.get("doi") or paper.get("id"),
        "study_type": "unknown",
        "objective": "",
        "methodology": "",
        "dataset_sample": "",
        "findings": "",
        "limitations": "",
        "supported_subquestions": [],
        "conflict_status": "none",
        "claim_support_status": "not_assessed",
        "extraction_status": "pending",
        "supporting_evidence": [],
        "source_spans": [],
    }
def unwrap_evidence_quote(quote: str) -> str:
    """Unwrap an accidental one-entry JSON mapping without changing its quote."""
    if not isinstance(quote, str):
        return ""
    candidate = quote.strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        import json
        try:
            parsed = json.loads(candidate)
        except ValueError:
            return quote
        if (isinstance(parsed, dict) and len(parsed) == 1
                and all(isinstance(v, str) for v in parsed.values())):
            return next(iter(parsed.values()))
    return quote


def verify_supporting_evidence(
    abstract: str,
    supporting_evidence: list[str],
) -> dict:
    """Verify that extracted evidence quotes occur in the source abstract."""

    if not abstract or not supporting_evidence:
        return {
            "verified": False,
            "verified_quotes": [],
            "unverified_quotes": supporting_evidence,
        }

    normalized_abstract = " ".join(abstract.lower().split())

    verified_quotes = []
    unverified_quotes = []

    for quote in supporting_evidence:
        normalized_quote = " ".join(unwrap_evidence_quote(quote).lower().split())

        # Remove an optional trailing source label.
        normalized_quote = re.sub(
            r"\s*\(abstract\)\s*$",
            "",
            normalized_quote,
        )

        # Remove surrounding quotation marks.
        normalized_quote = normalized_quote.strip().strip(
            "\"'“”‘’"
        ).strip()
        if normalized_quote and normalized_quote in normalized_abstract:
            verified_quotes.append(quote)
        else:
            unverified_quotes.append(quote)

    return {
        "verified": bool(verified_quotes) and not unverified_quotes,
        "verified_quotes": verified_quotes,
        "unverified_quotes": unverified_quotes,
    }

def normalize_supported_subquestions(
    extracted_subquestions: list,
    original_subquestions: list[str],
) -> list[str]:
    """Recover exact original questions with optional trailing explanations."""
    validated = []

    for extracted in extracted_subquestions:
        if not isinstance(extracted, str):
            continue

        if extracted in original_subquestions:
            matched = extracted
        else:
            matches = [
                question
                for question in original_subquestions
                if isinstance(question, str)
                and extracted.startswith(question + " ")
            ]
            matched = matches[0] if len(matches) == 1 else None

        if matched is not None and matched not in validated:
            validated.append(matched)

    return validated
def verify_question_evidence(
    abstract: str,
    question_evidence: dict,
    original_subquestions: list[str],
) -> dict:
    """Verify question-to-quote links against the source abstract."""

    verified_mapping = {}
    rejected_mapping = {}

    if not isinstance(question_evidence, dict):
        return {
            "verified_mapping": {},
            "rejected_mapping": {},
            "verified_subquestions": [],
        }

    for question, quote in question_evidence.items():
        if not isinstance(question, str) or not isinstance(quote, str):
            rejected_mapping[str(question)] = "Invalid mapping type"
            continue

        if question not in original_subquestions:
            rejected_mapping[question] = "Unknown research question"
            continue

        result = verify_supporting_evidence(abstract, [quote])

        if not result["verified"]:
            rejected_mapping[question] = "Quote not found in abstract"
            continue

        verified_mapping[question] = unwrap_evidence_quote(quote)

    return {
        "verified_mapping": verified_mapping,
        "rejected_mapping": rejected_mapping,
        "verified_subquestions": list(verified_mapping),
    }
def verify_semantic_support(question: str, quote: str) -> dict:
    """Conservative, rule-based check for explicit answer evidence."""
    import re

    if not isinstance(question, str) or not isinstance(quote, str):
        return {"status": "UNSUPPORTED", "reason": "Invalid input"}

    question = question.strip().lower()
    quote = quote.strip().lower()

    if not question or not quote:
        return {"status": "UNSUPPORTED", "reason": "Empty input"}

    accuracy_terms = (
        "accuracy",
        "accurate",
        "classification accuracy",
    )

    asks_accuracy = any(term in question for term in accuracy_terms)

    if asks_accuracy:
        has_accuracy_measure = bool(
            re.search(
                r"\b(?:accuracy|accurate)\b.{0,60}?\b\d+(?:\.\d+)?\s*%"
                r"|\b\d+(?:\.\d+)?\s*%.{0,60}?\baccuracy\b",
                quote,
            )
        )

        model_names = (
            "cnn", "svm", "lstm", "gru",
            "random forest", "resnet", "vgg",
            "transformer", "vit",
        )

        mentioned_models = {
            model
            for model in model_names
            if re.search(r"\b" + re.escape(model) + r"\b", quote)
        }
        question_models = {
            model
            for model in model_names
            if re.search(
                r"\b" + re.escape(model) + r"\b",
                question,
            )
        }

        if (
            has_accuracy_measure
            and question_models
            and mentioned_models
            and question_models.isdisjoint(mentioned_models)
        ):
            return {
                "status": "UNSUPPORTED",
                "reason": "Model mismatch between question and quote",
            }
        asks_test_accuracy = bool(
            re.search(r"\b(?:test|testing)\b", question)
        )

        asks_training_accuracy = bool(
            re.search(r"\b(?:train|training)\b", question)
        )

        quote_has_test_accuracy = bool(
            re.search(
                r"\b(?:test|testing)\s+accuracy\b",
                quote,
            )
        )

        quote_has_training_accuracy = bool(
            re.search(
                r"\b(?:train|training)\s+accuracy\b",
                quote,
            )
        )

        if (
            has_accuracy_measure
            and asks_test_accuracy
            and quote_has_training_accuracy
            and not quote_has_test_accuracy
        ):
            return {
                "status": "UNSUPPORTED",
                "reason": "Training accuracy does not establish test accuracy",
            }

        if (
            has_accuracy_measure
            and asks_training_accuracy
            and quote_has_test_accuracy
            and not quote_has_training_accuracy
        ):
            return {
                "status": "UNSUPPORTED",
                "reason": "Test accuracy does not establish training accuracy",
            }
        if has_accuracy_measure and len(mentioned_models) > 1:
            return {
                "status": "UNCERTAIN",
                "reason": "Multiple models mentioned",
            }

        if has_accuracy_measure:
            return {
                "status": "SUPPORTED",
                "reason": "Explicit accuracy percentage found",
            }

        return {
            "status": "UNSUPPORTED",
            "reason": "No explicit accuracy percentage found",
        }

    return {
        "status": "UNCERTAIN",
        "reason": "Semantic support requires further verification",
    }


def locate_abstract_quotes(abstract: str, quotes: list[str]) -> list[dict]:
    """Return source-exact character spans for verified abstract quotations.

    Whitespace variations are located in the original abstract, not reconstructed
    from the model. Invalid or unverifiable quotes are excluded, never repaired
    by hallucinating a position. Offsets are Python string character offsets.
    """
    if not isinstance(abstract, str) or not isinstance(quotes, list):
        return []
    spans, seen = [], set()
    for candidate in quotes:
        if not isinstance(candidate, str):
            continue
        quote = unwrap_evidence_quote(candidate).strip().strip('"\'“”‘’').strip()
        if not quote:
            continue
        # Escape all non-whitespace, but allow whitespace normalization in
        # the original source (e.g. PDF or metadata line wraps).
        expression = r'\s+'.join(re.escape(word) for word in quote.split())
        if not expression:
            continue
        match = re.search(expression, abstract, re.I)
        if match is None:
            continue
        key = (match.start(), match.end())
        if key in seen:
            continue
        spans.append({
            'source': 'abstract',
            'quote': abstract[match.start():match.end()],
            'start_char': match.start(),
            'end_char': match.end(),
        })
        seen.add(key)
    return spans
