"""
SARA Non-Agentic Baseline

This module provides a simple fixed workflow that will later be used
as a comparison point for the agentic version of SARA.

The baseline does not perform autonomous planning, replanning,
tool selection, or iterative decision-making.
"""


def run_baseline(research_question: str) -> dict:
    """
    Run the initial non-agentic baseline workflow.

    Args:
        research_question: The academic research question provided by the user.

    Returns:
        A structured dictionary containing the baseline result.
    """

    if not research_question or not research_question.strip():
        return {
            "status": "INVALID_INPUT",
            "research_question": research_question,
            "message": "A research question is required.",
        }

    return {
        "status": "COMPLETED",
        "research_question": research_question.strip(),
        "workflow": "non_agentic_baseline",
        "message": "Baseline request accepted.",
    }


if __name__ == "__main__":
    question = input("Enter a research question: ")

    result = run_baseline(question)

    print("\nSARA Baseline Result")
    print("-" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")