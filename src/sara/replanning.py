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