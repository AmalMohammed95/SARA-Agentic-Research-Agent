"""Structured output validation for SARA."""
import re

REQUIRED_PLANNING_SECTIONS = ("OBJECTIVE:", "SUBQUESTIONS:", "KEYWORDS:")
REQUIRED_EXTRACTION_SECTIONS = (
    "OBJECTIVE:", "METHODOLOGY:", "DATASET_SAMPLE:", "FINDINGS:",
    "LIMITATIONS:", "SUPPORTED_SUBQUESTIONS:", "SUPPORTING_EVIDENCE:",
)


def validate_research_plan(response: str) -> dict:
    if not response or not response.strip():
        return {"valid": False, "missing_sections": list(REQUIRED_PLANNING_SECTIONS), "reason": "Model response is empty."}
    missing = [s for s in REQUIRED_PLANNING_SECTIONS if s not in response]
    return {"valid": not missing, "missing_sections": missing,
            "reason": "Required planning sections are missing." if missing else "Research plan structure is valid."}


def parse_research_plan(response: str) -> dict:
    if not all(s in response for s in REQUIRED_PLANNING_SECTIONS):
        return {"objective": "", "subquestions": [], "keywords": []}
    objective = response.split("OBJECTIVE:", 1)[1].split("SUBQUESTIONS:", 1)[0].strip()
    questions = response.split("SUBQUESTIONS:", 1)[1].split("KEYWORDS:", 1)[0]
    keywords = response.split("KEYWORDS:", 1)[1]
    def bullets(value):
        return [line.strip()[1:].strip().strip('"').strip("'") for line in value.splitlines() if line.strip().startswith("-")]
    return {"objective": objective, "subquestions": bullets(questions), "keywords": bullets(keywords)}


def validate_replanning_response(response: str) -> dict:
    if not response or not response.strip():
        return {"valid": False, "reason": "Replanning response is empty."}
    if "REVISED_KEYWORDS:" not in response:
        return {"valid": False, "reason": "Missing REVISED_KEYWORDS section."}
    return {"valid": True, "reason": "Replanning response has the required structure."}


def parse_revised_keywords(response: str) -> list[str]:
    if "REVISED_KEYWORDS:" not in response:
        return []
    return [v for line in response.split("REVISED_KEYWORDS:", 1)[1].splitlines()
            if line.strip().startswith("-")
            if (v := line.strip()[1:].strip().strip('"').strip("'"))]


def _missing(value: str) -> bool:
    """Detect absence markers, not actual study limitations or findings."""
    if not isinstance(value, str):
        return True
    v = value.strip().lstrip("-*• ").strip("`'\"“”‘’ ").strip()
    if not v:
        return True
    normalized = re.sub(r"[\s_\-/]+", " ", v).upper().rstrip(". :;")
    if normalized in {"NOT AVAILABLE", "N A", "NA", "NONE", "NULL", "UNKNOWN", "NOT REPORTED", "NOT SPECIFIED", "NOT PROVIDED", "UNAVAILABLE", "NOT APPLICABLE", "NOT KNOWN", "NOT MENTIONED", "NOT STATED", "NOT DISCLOSED", "NOT IDENTIFIED", "NO DATA", "NO INFORMATION"}:
        return True
    # Only statements explicitly saying that source information is absent.
    absence_patterns = (
        r"^(?:the )?(?:abstract|paper|study|source) (?:does not|doesn't|did not) (?:explicitly )?(?:mention|report|state|specify|provide|describe|identify|discuss)\b",
        r"^(?:not|no) (?:available|applicable|reported|provided|specified|mentioned|stated|disclosed)\b",
        r"^(?:no|not any) (?:explicit )?(?:limitations?|datasets?|samples?|findings?|results?|methods?|methodology) (?:are |is )?(?:mentioned|reported|specified|provided|available|stated)\b",
        r"^(?:limitations?|datasets?|samples?|findings?|results?|methods?|methodology) (?:are |is )?not (?:mentioned|reported|specified|provided|available|stated)\b",
    )
    return any(re.search(p, v, flags=re.IGNORECASE) for p in absence_patterns)


def validate_evidence_extraction(response: str) -> dict:
    if not response or not response.strip():
        return {"valid": False, "missing_sections": list(REQUIRED_EXTRACTION_SECTIONS)}
    missing = [s for s in REQUIRED_EXTRACTION_SECTIONS if s not in response]
    return {"valid": not missing, "missing_sections": missing}


def parse_evidence_extraction(response: str) -> dict:
    """Parse only correctly headed sections; do not invent missing evidence."""
    headers = [s[:-1] for s in REQUIRED_EXTRACTION_SECTIONS]
    chunks = {h: [] for h in headers}
    current = None
    for line in (response or "").splitlines():
        match = re.match(r"^\s*(" + "|".join(re.escape(h) for h in headers) + r"):\s*(.*)$", line)
        if match:
            current = match.group(1)
            if match.group(2).strip():
                chunks[current].append(match.group(2))
        elif current is not None:
            chunks[current].append(line)

    result = {}
    for field in ("objective", "methodology", "dataset_sample", "findings", "limitations"):
        value = "\n".join(chunks[field.upper()]).strip()
        result[field] = "" if _missing(value) else value

    for field in ("supported_subquestions", "supporting_evidence"):
        values = []
        seen = set()
        for line in chunks[field.upper()]:
            line = line.strip()
            if not line.startswith("-"):
                continue
            value = line[1:].strip().strip("`'\"“”‘’ ")
            if _missing(value) or re.search(r"\(\s*(?:NOT[_ ]AVAILABLE|N/?A|UNKNOWN)\s*\)\s*$", value, re.I):
                continue
            if value not in seen:
                values.append(value)
                seen.add(value)
        result[field] = values
    return result


def validate_extraction_quality(extraction: dict) -> dict:
    fields = ("objective", "methodology", "dataset_sample", "findings", "limitations")
    populated = [field for field in fields if not _missing(extraction.get(field, ""))]
    return {"usable": bool(populated), "populated_fields": populated,
            "populated_field_count": len(populated), "total_fields": len(fields)}


def validate_semantic_screening(response: str) -> dict:
    if not response or not response.strip():
        return {"valid": False, "reason": "Semantic screening response is empty."}
    if "DECISION:" not in response or "REASON:" not in response:
        return {"valid": False, "reason": "Required semantic screening sections are missing."}
    decision = response.split("DECISION:", 1)[1].split("REASON:", 1)[0].strip().upper()
    if decision not in {"INCLUDE", "EXCLUDE"}:
        return {"valid": False, "reason": "Semantic screening decision must be INCLUDE or EXCLUDE."}
    if not response.split("REASON:", 1)[1].strip():
        return {"valid": False, "reason": "Semantic screening reason must not be empty."}
    return {"valid": True, "reason": "Semantic screening response is valid."}


def parse_semantic_screening(response: str) -> dict:
    return {"decision": response.split("DECISION:", 1)[1].split("REASON:", 1)[0].strip().upper(),
            "reason": response.split("REASON:", 1)[1].strip()}


def validate_batch_semantic_screening(
    response: str,
    expected_ids: list[str],
) -> dict:
    """Validate a complete batch of semantic screening decisions."""
    import json

    if not response or not response.strip():
        return {"valid": False, "reason": "Empty batch response."}

    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return {"valid": False, "reason": "Invalid JSON response."}

    if isinstance(data, dict):
        results = data.get("results")
    elif isinstance(data, list):
        results = data
    else:
        return {
        "valid": False,
        "reason": "Expected a JSON object or array.",
    }

    if not isinstance(results, list):
        return {"valid": False, "reason": "Missing results list."}

    if not expected_ids or len(expected_ids) != len(set(expected_ids)):
        return {"valid": False, "reason": "Invalid expected paper IDs."}

    if len(results) != len(expected_ids):
        return {"valid": False, "reason": "Incorrect number of results."}

    seen_ids = set()

    for item in results:
        if not isinstance(item, dict):
            return {"valid": False, "reason": "Invalid result item."}

        paper_id = item.get("paper_id")
        decision = item.get("decision")
        reason = item.get("reason")

        if not isinstance(paper_id, str) or paper_id not in expected_ids:
            return {"valid": False, "reason": "Unexpected paper ID."}

        if paper_id in seen_ids:
            return {"valid": False, "reason": "Duplicate paper ID."}

        seen_ids.add(paper_id)

        if decision not in {"INCLUDE", "EXCLUDE"}:
            return {"valid": False, "reason": "Invalid screening decision."}

        if not isinstance(reason, str) or not reason.strip():
            return {"valid": False, "reason": "Missing screening reason."}

    if seen_ids != set(expected_ids):
        return {"valid": False, "reason": "Missing paper decisions."}

    return {"valid": True, "reason": "Valid batch screening response."}


def parse_batch_semantic_screening(response: str) -> list[dict]:
    """Parse batch screening results from a JSON response."""
    import json

    data = json.loads(response)

    if isinstance(data, list):
        return data

    return data["results"]
