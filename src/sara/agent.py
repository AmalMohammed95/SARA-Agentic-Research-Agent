"""
Bounded agent loop for SARA.

The agent operates within explicit execution limits and must
terminate in a defined state rather than running indefinitely.
"""

from .state import AgentState
from .tracing import create_run_id, create_trace_event
from .evidence import evaluate_evidence_sufficiency
from .replanning import can_replan, build_replanning_context
from .model import OllamaModelClient
from .prompts import RESEARCH_PLANNING_PROMPT, REPLANNING_PROMPT
from .schemas import (
    validate_research_plan,
    parse_research_plan,
    validate_replanning_response,
    parse_revised_keywords,
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
    """
    Run a bounded SARA agent loop.

    Args:
        research_question: The academic research question.
        max_turns: Maximum number of agent turns allowed.

    Returns:
        Structured information about the run and its final state.
    """

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

    while turn < max_turns:
        turn += 1
        state.iteration = turn

        planning_prompt = RESEARCH_PLANNING_PROMPT.format(
            research_question=state.research_question,
        )

        planning_response = model_client.generate(planning_prompt)
        planning_validation = validate_research_plan(planning_response)

        trace.append(
            create_trace_event(
                run_id=run_id,
                turn=turn,
                action="validate_research_plan",
                status="VALID" if planning_validation["valid"] else "INVALID",
                details=planning_validation,
            )
        )

        if planning_validation["valid"]:
            parsed_plan = parse_research_plan(planning_response)
            state.subquestions = parsed_plan["subquestions"]
            state.keywords = parsed_plan["keywords"]

        trace_event = create_trace_event(
            run_id=run_id,
            turn=turn,
            action="agent_turn",
            status="RUNNING",
            details={"iteration": state.iteration},
        )
        trace.append(trace_event)

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
                status="SUFFICIENT"
                if evidence_check["sufficient"]
                else "INSUFFICIENT",
                details=evidence_check,
            )
        )

        state.gaps = evidence_check["gaps"]

        if not evidence_check["sufficient"]:
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
                replanning_response = model_client.generate(
                    replanning_prompt
                )

                replanning_validation = validate_replanning_response(
                    replanning_response
                )
                trace.append(
                    create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="validate_replanning_response",
                        status="VALID"
                        if replanning_validation["valid"]
                        else "INVALID",
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
                            details={
                                "revised_keywords": revised_keywords,
                            },
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

                state.status = "INSUFFICIENT_EVIDENCE"
                state.stopping_reason = (
                    "Evidence is insufficient and another replanning attempt is allowed."
                )
            else:
                state.status = "INSUFFICIENT_EVIDENCE"
                state.stopping_reason = (
                    "Evidence is insufficient and the replanning limit has been reached."
                )

            break

        # Decision-making and tool execution will be added
        # incrementally in later steps.

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
        
    }