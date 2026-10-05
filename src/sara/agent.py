"""
Bounded agent loop for SARA.

The agent operates within explicit execution limits and must
terminate in a defined state rather than running indefinitely.
"""

from .extraction import (
    create_empty_evidence_record,
    verify_supporting_evidence,
)
from .screening import screen_papers
from .executor import execute_tool
from .state import AgentState
from .tracing import create_run_id, create_trace_event
from .evidence import evaluate_evidence_sufficiency
from .replanning import can_replan, build_replanning_context
from .model import OllamaModelClient
from .prompts import (
    RESEARCH_PLANNING_PROMPT,
    REPLANNING_PROMPT,
    EVIDENCE_EXTRACTION_PROMPT,
)
from .schemas import (
    validate_research_plan,
    parse_research_plan,
    validate_replanning_response,
    parse_revised_keywords,
    validate_evidence_extraction,
    parse_evidence_extraction,
)


TERMINAL_STATES = {
    "COMPLETED",
    "BLOCKED",
    "ESCALATED",
    "WAITING_FOR_APPROVAL",
    "INSUFFICIENT_EVIDENCE",
    "BUDGET_EXHAUSTED",
    "FAILED_SAFELY",
}


def run_agent(research_question: str, max_turns: int = 3) -> dict:
    """Run a bounded SARA agent loop."""

    if not research_question or not research_question.strip():
        return {
            "status": "FAILED_SAFELY",
            "turns": 0,
            "reason": "Research question must not be empty.",
        }

    if not isinstance(max_turns, int) or max_turns < 1:
        return {
            "status": "FAILED_SAFELY",
            "turns": 0,
            "reason": "max_turns must be a positive integer.",
        }

    run_id = create_run_id()
    state = AgentState(
        research_question=research_question.strip(),
        run_id=run_id,
    )
    trace = []
    model_client = OllamaModelClient()
    turn = 0

    # Initial planning happens once. Replanning updates state.keywords and the
    # next loop iteration uses those revised keywords directly.
    planning_prompt = RESEARCH_PLANNING_PROMPT.format(
        research_question=state.research_question,
    )
    planning_response = model_client.generate(planning_prompt)
    planning_validation = validate_research_plan(planning_response)

    trace.append(
        create_trace_event(
            run_id=run_id,
            turn=0,
            action="validate_research_plan",
            status="VALID" if planning_validation["valid"] else "INVALID",
            details=planning_validation,
        )
    )

    if not planning_validation["valid"]:
        state.status = "FAILED_SAFELY"
        state.stopping_reason = "Initial research plan failed validation."
        return {
            "status": state.status,
            "run_id": state.run_id,
            "turns": state.iteration,
            "reason": state.stopping_reason,
            "replanning_attempts": state.replanning_attempts,
            "trace": trace,
            "gaps": state.gaps,
            "evidence": state.evidence,
        }

    parsed_plan = parse_research_plan(planning_response)
    state.subquestions = parsed_plan["subquestions"]
    state.keywords = parsed_plan["keywords"]

    while turn < max_turns:
        turn += 1
        state.iteration = turn

        if not state.keywords:
            state.status = "FAILED_SAFELY"
            state.stopping_reason = "No valid search keywords are available."
            break

        search_query = state.keywords[0]
        search_result = execute_tool(
            "search_openalex",
            {
                "query": search_query,
                "max_results": 5,
            },
        )

        trace.append(
            create_trace_event(
                run_id=run_id,
                turn=turn,
                action="search_openalex",
                status=search_result["status"],
                details={
                    "query": search_query,
                    "results_count": len(search_result["result"] or []),
                },
            )
        )

        if search_result["status"] != "COMPLETED":
            state.status = "FAILED_SAFELY"
            state.stopping_reason = "OpenAlex search did not complete successfully."
            break

        new_retrieved_papers = search_result["result"] or []

        included_papers, excluded_papers = screen_papers(
            new_retrieved_papers,
            search_query,
        )

        # Accumulate retrieved papers across turns without duplicates.
        existing_retrieved_ids = {
            paper.get("doi") or paper.get("id")
            for paper in state.retrieved_papers
        }

        for paper in new_retrieved_papers:
            paper_id = paper.get("doi") or paper.get("id")
            if paper_id not in existing_retrieved_ids:
                state.retrieved_papers.append(paper)
                existing_retrieved_ids.add(paper_id)

        # Accumulate selected papers across turns without duplicates.
        existing_selected_ids = {
            paper.get("doi") or paper.get("id")
            for paper in state.selected_papers
        }

        for paper in included_papers:
            paper_id = paper.get("doi") or paper.get("id")
            if paper_id not in existing_selected_ids:
                state.selected_papers.append(paper)
                existing_selected_ids.add(paper_id)

                # Create an evidence record only for newly selected papers.
                state.evidence.append(
                    create_empty_evidence_record(paper)
                )

        # Preserve exclusions from previous turns.
        existing_excluded_ids = {
            paper.get("doi") or paper.get("id")
            for paper in state.excluded_papers
        }

        for paper in excluded_papers:
            paper_id = paper.get("doi") or paper.get("id")
            if paper_id not in existing_excluded_ids:
                state.excluded_papers.append(paper)
                existing_excluded_ids.add(paper_id)
        paper_with_abstract = next(
            (
                paper
                for paper in included_papers
                if paper.get("abstract")
            ),
            None,
        )

        if paper_with_abstract:
            extraction_prompt = EVIDENCE_EXTRACTION_PROMPT.format(
                title=paper_with_abstract.get("title", ""),
                abstract=paper_with_abstract.get("abstract", ""),
                subquestions=state.subquestions,
            )
            extraction_response = model_client.generate(extraction_prompt)
            extraction_validation = validate_evidence_extraction(
                extraction_response
            )

            trace.append(
                create_trace_event(
                    run_id=run_id,
                    turn=turn,
                    action="validate_evidence_extraction",
                    status=(
                        "VALID"
                        if extraction_validation["valid"]
                        else "INVALID"
                    ),
                    details={
                        "paper_id": (
                            paper_with_abstract.get("doi")
                            or paper_with_abstract.get("id")
                        ),
                        "title": paper_with_abstract.get("title", ""),
                        "validation": extraction_validation,
                    },
                )
            )

            if extraction_validation["valid"]:
                parsed_extraction = parse_evidence_extraction(
                    extraction_response
                )
                trace.append(
                    create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="parse_evidence_extraction",
                        status="COMPLETED",
                        details={
                            "paper_id": (
                                paper_with_abstract.get("doi")
                                or paper_with_abstract.get("id")
                            ),
                            "extraction": parsed_extraction,
                        },
                    )
                )

                extracted_record = create_empty_evidence_record(
                    paper_with_abstract
                )
                extracted_record.update(parsed_extraction)

                grounding_result = verify_supporting_evidence(
                    paper_with_abstract.get("abstract", ""),
                    parsed_extraction.get("supporting_evidence", []),
                )
                if grounding_result["verified"]:
                    extracted_record["claim_support_status"] = "supported"

                trace.append(
                    create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="verify_supporting_evidence",
                        status=(
                            "VERIFIED"
                            if grounding_result["verified"]
                            else "UNVERIFIED"
                        ),
                        details={
                            "paper_id": (
                                paper_with_abstract.get("doi")
                                or paper_with_abstract.get("id")
                            ),
                            "title": paper_with_abstract.get("title", ""),
                            "grounding": grounding_result,
                        },
                    )
                )

                validated_subquestions = [
                    subquestion
                    for subquestion in extracted_record[
                        "supported_subquestions"
                    ]
                    if subquestion in state.subquestions
                ]
                extracted_record[
                    "supported_subquestions"
                ] = validated_subquestions

                for index, evidence_record in enumerate(state.evidence):
                    if (
                        evidence_record["paper_id"]
                        == extracted_record["paper_id"]
                    ):
                        state.evidence[index] = extracted_record
                        break

        trace.append(
            create_trace_event(
                run_id=run_id,
                turn=turn,
                action="screen_papers",
                status="COMPLETED",
                details={
                    "turn_retrieved": len(new_retrieved_papers),
                    "turn_selected": len(included_papers),
                    "turn_excluded": len(excluded_papers),
                    "total_retrieved": len(state.retrieved_papers),
                    "total_selected": len(state.selected_papers),
                    "total_excluded": len(state.excluded_papers),
                },
            )
        )

        trace.append(
            create_trace_event(
                run_id=run_id,
                turn=turn,
                action="agent_turn",
                status="RUNNING",
                details={"iteration": state.iteration},
            )
        )

        evidence_check = evaluate_evidence_sufficiency(
            selected_papers=state.selected_papers,
            subquestions=state.subquestions,
            evidence=state.evidence,
        )
        trace.append(
            create_trace_event(
                run_id=run_id,
                turn=turn,
                action="evaluate_evidence",
                status=(
                    "SUFFICIENT"
                    if evidence_check["sufficient"]
                    else "INSUFFICIENT"
                ),
                details=evidence_check,
            )
        )
        state.gaps = evidence_check["gaps"]

        if evidence_check["sufficient"]:
            state.status = "COMPLETED"
            state.stopping_reason = "Evidence sufficiency criteria were met."
            break

        if can_replan(state.replanning_attempts):
            state.replanning_attempts += 1
            replanning_context = build_replanning_context(
                current_keywords=state.keywords,
                gaps=state.gaps,
            )
            replanning_prompt = REPLANNING_PROMPT.format(
                research_question=state.research_question,
                current_keywords=replanning_context["current_keywords"],
                evidence_gaps=replanning_context["evidence_gaps"],
            )
            replanning_response = model_client.generate(replanning_prompt)
            replanning_validation = validate_replanning_response(
                replanning_response
            )

            trace.append(
                create_trace_event(
                    run_id=run_id,
                    turn=turn,
                    action="validate_replanning_response",
                    status=(
                        "VALID"
                        if replanning_validation["valid"]
                        else "INVALID"
                    ),
                    details=replanning_validation,
                )
            )

            if replanning_validation["valid"]:
                revised_keywords = parse_revised_keywords(
                    replanning_response
                )
                state.keywords = revised_keywords
                trace.append(
                    create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="apply_revised_keywords",
                        status="COMPLETED",
                        details={"revised_keywords": revised_keywords},
                    )
                )
                trace.append(
                    create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="replanning_requested",
                        status="ALLOWED",
                        details={
                            "attempt": state.replanning_attempts,
                            "gaps": state.gaps,
                            "context": replanning_context,
                        },
                    )
                )
                state.status = "REPLANNING"
                state.stopping_reason = None
                continue

            state.status = "INSUFFICIENT_EVIDENCE"
            state.stopping_reason = (
                "Evidence is insufficient and replanning failed validation."
            )
            break

        state.status = "INSUFFICIENT_EVIDENCE"
        state.stopping_reason = (
            "Evidence is insufficient and the replanning limit has been reached."
        )
        break

    if state.status not in TERMINAL_STATES:
        state.status = "BUDGET_EXHAUSTED"
        state.stopping_reason = "Maximum number of agent turns reached."

    return {
        "status": state.status,
        "run_id": state.run_id,
        "turns": state.iteration,
        "reason": state.stopping_reason,
        "replanning_attempts": state.replanning_attempts,
        "trace": trace,
        "gaps": state.gaps,
        "evidence": state.evidence,
    }
