
"""Tests for persistent human review storage."""

import json

import pytest

from sara.human_review import create_review_request
from sara.review_store import (
    save_review,
    load_review,
    decide_review,
)


@pytest.fixture
def review_directory(tmp_path):
    return tmp_path / "reviews"


@pytest.fixture
def pending_review():
    return create_review_request(
        "run-123",
        {
            "text": "Supported research summary [S1].",
            "citations": {"S1": "paper-123"},
        },
    )


def test_save_and_load_review(review_directory, pending_review):
    path = save_review(pending_review, review_directory)

    assert path.exists()
    assert load_review("run-123", review_directory) == pending_review


def test_approve_review(review_directory, pending_review):
    save_review(pending_review, review_directory)

    result = decide_review(
        "run-123",
        "APPROVE",
        "researcher",
        directory=review_directory,
    )

    assert result["status"] == "COMPLETED"
    assert result["decision"] == "APPROVE"
    assert load_review("run-123", review_directory) == result


def test_reject_review(review_directory, pending_review):
    save_review(pending_review, review_directory)

    result = decide_review(
        "run-123",
        "REJECT",
        "researcher",
        reason="Unsupported conclusion.",
        directory=review_directory,
    )

    assert result["status"] == "ESCALATED"
    assert result["decision"] == "REJECT"


def test_request_revision(review_directory, pending_review):
    save_review(pending_review, review_directory)

    result = decide_review(
        "run-123",
        "REQUEST_REVISION",
        "researcher",
        reason="Clarify limitations.",
        directory=review_directory,
    )

    assert result["status"] == "WAITING_FOR_REVISION"


def test_cannot_review_twice(review_directory, pending_review):
    save_review(pending_review, review_directory)

    decide_review(
        "run-123",
        "APPROVE",
        "researcher",
        directory=review_directory,
    )

    with pytest.raises(ValueError):
        decide_review(
            "run-123",
            "REJECT",
            "researcher",
            reason="Changed decision.",
            directory=review_directory,
        )


def test_reject_invalid_run_id(review_directory):
    with pytest.raises(ValueError):
        load_review("../outside", review_directory)


def test_reject_missing_review(review_directory):
    with pytest.raises(FileNotFoundError):
        load_review("missing-run", review_directory)


def test_reject_mismatched_run_id(review_directory):
    review_directory.mkdir(parents=True)

    path = review_directory / "run-123.json"
    path.write_text(
        json.dumps({"run_id": "another-run"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_review("run-123", review_directory)
