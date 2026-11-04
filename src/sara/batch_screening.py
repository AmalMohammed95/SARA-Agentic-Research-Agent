import json
import re
import os

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
    # Conservative: only bypass LLM when the title directly says that agent
    # reliability/robustness is being evaluated. Generic "agent evaluation" is
    # NOT enough, and chatbot/LLM-judge-only papers remain ambiguous.
    fast_enabled = os.getenv("SARA_FAST_SCREENING", "1") == "1"
    def obvious_agent_evaluation(paper):
        title = str(paper.get("title") or "")
        abstract = str(paper.get("abstract") or "")
        agent = re.search(r"\b(?:LLM[- ]based |LLM |language model )?agents?\b", title, re.I)
        reliability = re.search(r"\b(?:reliab\w*|robust\w*|failure\w*|consisten\w*)\b", title, re.I)
        evaluation = re.search(r"\b(?:evaluat\w*|benchmark\w*|assess\w*|measur\w*)\b", title, re.I)
        strict = os.getenv("SARA_STRICT_FAST_SCREENING", "0") == "1"
        corroborated = bool(re.search(
            r"\b(?:agents?|agentic)\b.*\b(?:evaluat\w*|benchmark\w*|reliab\w*|robust\w*)\b"
            r"|\b(?:evaluat\w*|benchmark\w*|reliab\w*|robust\w*)\b.*\b(?:agents?|agentic)\b",
            abstract, re.I | re.S))
        return bool(agent and evaluation and len(abstract.strip()) >= 100 and (
            not strict or (reliability and corroborated)
        ))

    for start in range(0, len(papers), batch_size):
        original_batch = papers[start:start + batch_size]
        batch = []
        for paper in original_batch:
            if fast_enabled and obvious_agent_evaluation(paper):
                results.append({
                    "paper": paper, "decision": "INCLUDE",
                    "reason": "Explicit agent evaluation topic in title; evidence remains subject to verification.",
                    "status": "INCLUDE",
                })
            else:
                batch.append(paper)
        if not batch:
            continue

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
                validation = validate_batch_semantic_screening(response, expected_ids)

                print(
                    f"[BATCH SCREENING] papers={len(batch)} "
                    f"valid={validation['valid']} "
                    f"reason={validation.get('reason', 'OK')}",
                    flush=True,
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

        # Bound the expensive individual fallback after malformed batch output.
        # Remaining papers fail closed, not silently included as relevant.
        try:
            fallback_limit = max(0, min(len(batch), int(os.getenv(
                "SARA_SCREENING_FALLBACK_LIMIT", str(len(batch))))))
        except ValueError:
            fallback_limit = len(batch)
        for index, paper in enumerate(batch):
            if index >= fallback_limit:
                results.append({
                    "paper": paper,
                    "decision": "EXCLUDE",
                    "reason": "Batch screening failed; individual verification deferred by the call budget.",
                    "status": "BUDGET_EXHAUSTED",
                })
                continue
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
