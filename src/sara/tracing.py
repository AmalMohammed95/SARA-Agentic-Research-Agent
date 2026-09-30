"""
Tracing and observability utilities for SARA.

This module records observable execution events without storing
private chain-of-thought or hidden model reasoning.
"""

from datetime import datetime, timezone
from uuid import uuid4


def create_run_id() -> str:
    """
    Create a unique identifier for a SARA execution run.
    """
    return str(uuid4())


def create_trace_event(
    run_id: str,
    turn: int,
    action: str,
    status: str,
    details: dict | None = None,
) -> dict:
    """
    Create a structured observable trace event.

    Args:
        run_id: Unique identifier for the complete agent run.
        turn: Current agent turn number.
        action: Observable action performed or proposed.
        status: Resulting status of the action.
        details: Optional structured information about the event.

    Returns:
        A structured trace event.
    """

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "turn": turn,
        "action": action,
        "status": status,
        "details": details or {},
    }