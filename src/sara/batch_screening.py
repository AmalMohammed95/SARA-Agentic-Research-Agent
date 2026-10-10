import json

from .prompts import (
    BATCH_SEMANTIC_SCREENING_PROMPT,
    SEMANTIC_SCREENING_PROMPT,
)
from .schemas import (
    validate_batch_semantic_screening,
    parse_batch_semantic_screening,
    validate_semantic_screening,
    parse_semantic_screening,
)


def screen_papers_in_batches(
    papers,
    research_question,
    model_client,
    batch_size=5,
):
    """Screen papers in batches, falling back to individual screening."""
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer.")

    results = []

    for start in range(0, len(papers), batch_size):
        batch = papers[start:start + batch_size]

        paper_items = [
            {
                "paper_id": paper.get("doi") or paper.get("id"),
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
            }
            for paper in batch
        ]

        expected_ids = [item["paper_id"] for item in paper_items]
        parsed_by_id = None

        # Batch decisions require unique, nonempty identifiers.
        if (
            all(isinstance(pid, str) and pid.strip() for pid in expected_ids)
            and len(set(expected_ids)) == len(expected_ids)
        ):
            prompt = BATCH_SEMANTIC_SCREENING_PROMPT.format(
                research_question=research_question,
                papers_json=json.dumps(paper_items, ensure_ascii=False),
            )

            try:
                response = model_client.generate(prompt)
                validation = validate_batch_semantic_screening(
                    response, expected_ids
                )

                if validation["valid"]:
                    parsed = parse_batch_semantic_screening(response)
                    parsed_by_id = {
                        item["paper_id"]: item for item in parsed
                    }
            except Exception:
                parsed_by_id = None

        if parsed_by_id is not None:
            for paper, item in zip(batch, paper_items):
                decision = parsed_by_id[item["paper_id"]]
                results.append({
                    "paper": paper,
                    "decision": decision["decision"],
                    "reason": decision["reason"],
                    "status": decision["decision"],
                })
            continue

        # Fall back to the original single-paper screening rules.
        for paper in batch:
            prompt = SEMANTIC_SCREENING_PROMPT.format(
                research_question=research_question,
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
            )

            try:
                response = model_client.generate(prompt)
                validation = validate_semantic_screening(response)

                if not validation["valid"]:
                    results.append({
                        "paper": paper,
                        "decision": "EXCLUDE",
                        "reason": "Invalid semantic screening response.",
                        "status": "INVALID",
                    })
                    continue

                parsed = parse_semantic_screening(response)
                results.append({
                    "paper": paper,
                    "decision": parsed["decision"],
                    "reason": parsed["reason"],
                    "status": parsed["decision"],
                })
            except Exception as exc:
                results.append({
                    "paper": paper,
                    "decision": "EXCLUDE",
                    "reason": "Semantic screening model call failed.",
                    "status": "FAILED_SAFELY",
                    "error": str(exc),
                })

    return results
