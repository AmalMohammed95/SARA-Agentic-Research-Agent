"""
Bounded agent loop for SARA.

The agent operates within explicit execution limits and must
terminate in a defined state rather than running indefinitely.
"""


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

    turn = 0

    while turn < max_turns:
        turn += 1

        # Decision-making and tool execution will be added
        # incrementally in later steps.

    return {
        "status": "BUDGET_EXHAUSTED",
        "turns": turn,
        "reason": "Maximum number of agent turns reached.",
    }