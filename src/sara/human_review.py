
"""
Human-in-the-loop review for SARA.

Review decisions are explicit, deterministic, and auditable.
No approval is assumed automatically.
"""

from datetime import datetime, timezone


VALID_DECISIONS = {"APPROVE", "REJECT", "REQUEST_REVISION"}


def create_review_request(
    run_id: str,
    synthesis: dict | None,
) -> dict:
    """Create a pending review request for a synthesis."""

    if not run_id or not isinstance(synthesis, dict):
        raise ValueError("A run ID and synthesis are required.")

    if not synthesis.get("text") or not synthesis.get("citations"):
        raise ValueError("Synthesis text and citations are required.")

    return {
        "run_id": run_id,
        "status": "WAITING_FOR_APPROVAL",
        "decision": None,
        "reviewer": None,
        "reason": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": None,
    }


def apply_review_decision(
    review_request: dict,
    decision: str,
    reviewer: str,
    reason: str = "",
) -> dict:
    """Apply an explicit human decision to a pending review."""

    if review_request.get("status") != "WAITING_FOR_APPROVAL":
        raise ValueError("Review request is not pending.")

    decision = decision.strip().upper()

    if decision not in VALID_DECISIONS:
        raise ValueError("Invalid review decision.")

    if not reviewer or not reviewer.strip():
        raise ValueError("Reviewer identity is required.")

    if decision != "APPROVE" and not reason.strip():
        raise ValueError("A reason is required for rejection or revision.")

    status_map = {
        "APPROVE": "COMPLETED",
        "REJECT": "ESCALATED",
        "REQUEST_REVISION": "WAITING_FOR_REVISION",
    }

    return {
        **review_request,
        "status": status_map[decision],
        "decision": decision,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
