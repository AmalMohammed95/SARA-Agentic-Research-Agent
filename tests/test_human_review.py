
"""Tests for SARA human review decisions."""

import pytest

from sara.human_review import (
    create_review_request,
    apply_review_decision,
)


@pytest.fixture
def pending_review():
    return create_review_request(
        "run-123",
        {
            "text": "Supported research summary [S1].",
            "citations": {"S1": "paper-123"},
        },
    )


def test_review_starts_pending(pending_review):
    assert pending_review["status"] == "WAITING_FOR_APPROVAL"
    assert pending_review["decision"] is None


def test_explicit_approval(pending_review):
    result = apply_review_decision(
        pending_review, "APPROVE", "human-reviewer"
    )
    assert result["status"] == "COMPLETED"
    assert result["decision"] == "APPROVE"
    assert result["reviewer"] == "human-reviewer"


def test_rejection_requires_reason(pending_review):
    with pytest.raises(ValueError):
        apply_review_decision(
            pending_review, "REJECT", "human-reviewer"
        )


def test_explicit_rejection(pending_review):
    result = apply_review_decision(
        pending_review,
        "REJECT",
        "human-reviewer",
        "The synthesis contains an unsupported conclusion.",
    )
    assert result["status"] == "ESCALATED"


def test_revision_request(pending_review):
    result = apply_review_decision(
        pending_review,
        "REQUEST_REVISION",
        "human-reviewer",
        "Clarify the evidence limitations.",
    )
    assert result["status"] == "WAITING_FOR_REVISION"


def test_invalid_decision_rejected(pending_review):
    with pytest.raises(ValueError):
        apply_review_decision(
            pending_review, "AUTO_APPROVE", "agent"
        )


def test_review_cannot_be_applied_twice(pending_review):
    approved = apply_review_decision(
        pending_review, "APPROVE", "human-reviewer"
    )
    with pytest.raises(ValueError):
        apply_review_decision(
            approved, "REJECT", "another-reviewer", "Changed mind."
        )
