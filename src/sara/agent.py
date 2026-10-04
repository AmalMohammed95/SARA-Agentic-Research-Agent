"""
Bounded agent loop for SARA.

The agent operates within explicit execution limits and must
terminate in a defined state rather than running indefinitely.
"""

from .state import AgentState
from .tracing import create_run_id, create_trace_event
from .evidence import evaluate_evidence_sufficiency
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
    turn = 0

    while turn < max_turns:
        turn += 1
        state.iteration = turn

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
            state.status = "INSUFFICIENT_EVIDENCE"
            state.stopping_reason = "Evidence is insufficient and replanning is not yet implemented."
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
        "trace": trace,
        "gaps": state.gaps,
    }