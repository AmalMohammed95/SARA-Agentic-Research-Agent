"""
Bounded replanning utilities for SARA.

This module controls when the agent is allowed to replan after
detecting insufficient evidence or research gaps.
"""

MAX_REPLANNING_ATTEMPTS = 2
def can_replan(replanning_attempts: int) -> bool:
    """
    Return True when another replanning attempt is allowed.
    """
    return replanning_attempts < MAX_REPLANNING_ATTEMPTS
def build_replanning_context(
    current_keywords: list[str],
    gaps: list[str],
) -> dict:
    """
    Build structured context for a new research search plan.

    The function does not execute a search. It prepares the
    observable information needed for the next planning step.
    """
    return {
        "current_keywords": current_keywords,
        "evidence_gaps": gaps,
    }