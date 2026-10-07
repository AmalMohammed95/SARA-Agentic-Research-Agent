
"""Persistent human review storage for SARA."""

import json
import re
from pathlib import Path

from .human_review import apply_review_decision


def _review_path(run_id: str, directory: str | Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
        raise ValueError("Invalid run ID.")

    return Path(directory) / f"{run_id}.json"


def save_review(
    review: dict,
    directory: str | Path = "data/reviews",
) -> Path:
    """Save a review request or decision to JSON."""

    path = _review_path(review["run_id"], directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(review, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)

    return path


def load_review(
    run_id: str,
    directory: str | Path = "data/reviews",
) -> dict:
    """Load a previously saved review."""

    path = _review_path(run_id, directory)

    if not path.is_file():
        raise FileNotFoundError(f"Review not found: {run_id}")

    review = json.loads(path.read_text(encoding="utf-8"))

    if review.get("run_id") != run_id:
        raise ValueError("Review run ID mismatch.")

    return review


def decide_review(
    run_id: str,
    decision: str,
    reviewer: str,
    reason: str = "",
    directory: str | Path = "data/reviews",
) -> dict:
    """Apply a human decision and persist the result."""

    review = load_review(run_id, directory)

    updated_review = apply_review_decision(
        review,
        decision,
        reviewer,
        reason,
    )

    save_review(updated_review, directory)
    return updated_review
