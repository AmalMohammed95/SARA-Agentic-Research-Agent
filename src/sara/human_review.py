
"""
Human-in-the-loop review for SARA.

Review decisions are explicit, deterministic, and auditable.
No approval is assumed automatically.
"""

from datetime import datetime, timezone
import re


VALID_DECISIONS = {"APPROVE", "EDIT", "REJECT", "REQUEST_REVISION"}


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
        "synthesis": {"text": synthesis["text"], "citations": dict(synthesis["citations"])},
        "edited_synthesis": None,
        "audit_events": [],
    }


def apply_review_decision(
    review_request: dict,
    decision: str,
    reviewer: str,
    reason: str = "",
    edited_text: str | None = None,
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

    if decision == "EDIT":
        if not isinstance(edited_text, str) or not edited_text.strip():
            raise ValueError("Edited synthesis text is required.")
        synthesis = review_request.get("synthesis")
        if not isinstance(synthesis, dict) or not isinstance(synthesis.get("citations"), dict):
            raise ValueError("Original synthesis and citations are required for editing.")
        from .synthesis import validate_synthesis
        validation = validate_synthesis(edited_text, synthesis["citations"])
        if not validation.get("valid"):
            raise ValueError(f"Edited synthesis failed citation checks: {validation.get('reason')}")
    elif edited_text is not None:
        raise ValueError("Edited text is only allowed for EDIT decisions.")

    status_map = {
        "APPROVE": "COMPLETED",
        "EDIT": "COMPLETED",
        "REJECT": "ESCALATED",
        "REQUEST_REVISION": "WAITING_FOR_REVISION",
    }

    timestamp = datetime.now(timezone.utc).isoformat()
    audit_event = {"decision": decision, "reviewer": reviewer.strip(),
                   "reason": reason.strip(), "timestamp": timestamp,
                   "edited": decision == "EDIT"}
    return {
        **review_request,
        "edited_synthesis": (edited_text if decision == "EDIT" else review_request.get("edited_synthesis")),
        "audit_events": [*review_request.get("audit_events", []), audit_event],
        "status": status_map[decision],
        "decision": decision,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "reviewed_at": timestamp,
    }
