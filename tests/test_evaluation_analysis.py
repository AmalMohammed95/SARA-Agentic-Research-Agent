import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from evaluation.analyze_results import summarize


def _fixture(tmp_path, records):
    questions = tmp_path / "questions.csv"
    questions.write_text("case_id,research_question,category\nE01,First,specific\nE02,Second,broad\n", encoding="utf-8")
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"results": records}), encoding="utf-8")
    return questions, results


def test_missing_runs_are_not_counted_as_failures(tmp_path):
    paths = _fixture(tmp_path, [{"case_id": "E01", "system": "SARA", "status": "INSUFFICIENT_EVIDENCE", "duration_seconds": 3}])
    result = summarize(*paths)
    assert result["expected_pairs"] == 4
    assert result["recorded_pairs"] == 1
    assert result["missing_pairs"] == 3
    assert result["status_counts"]["SARA"] == {"INSUFFICIENT_EVIDENCE": 1}
    assert result["rows"][0]["recorded"] is False


def test_duplicate_results_are_rejected(tmp_path):
    row = {"case_id": "E01", "system": "Baseline", "status": "COMPLETED"}
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(*_fixture(tmp_path, [row, row]))


def test_unknown_case_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown"):
        summarize(*_fixture(tmp_path, [{"case_id": "E99", "system": "SARA", "status": "COMPLETED"}]))


def test_missing_status_rejected(tmp_path):
    with pytest.raises(ValueError, match="Missing status"):
        summarize(*_fixture(tmp_path, [{"case_id": "E01", "system": "SARA"}]))


def test_real_recorded_case_has_consistent_counts():
    result = summarize(
        ROOT / "evaluation" / "research_questions.csv",
        ROOT / "evaluation" / "comparison_results_batch_v1.json"
    )

    assert result["total_cases"] == 5
    assert result["expected_pairs"] == 10

    assert result["recorded_pairs"] == 10
    assert result["missing_pairs"] == 0

    assert result["status_counts"]["Baseline"] == {
        "COMPLETED": 5
    }

    assert result["status_counts"]["SARA"] == {
        "INSUFFICIENT_EVIDENCE": 5
    }