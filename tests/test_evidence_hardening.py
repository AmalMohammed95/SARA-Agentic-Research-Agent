"""Regression tests for placeholder evidence and empty source quotations."""
import pytest
from sara.evidence import evaluate_evidence_sufficiency
from sara.synthesis import prepare_synthesis_evidence


@pytest.mark.parametrize("placeholder", [
    "NOT_APPLICABLE", "not reported", "Not specified", "Unavailable",
    "  - N/A  ", "NOT AVAILABLE: no details",
])
def test_placeholders_are_missing_evidence(placeholder):
    papers = [{"id": f"W{i}"} for i in range(5)]
    records = [{
        "paper_id": f"W{i}", "objective": placeholder,
        "methodology": "Experimental", "dataset_sample": "Sample",
        "findings": "Findings", "limitations": "Limitations",
        "claim_support_status": "supported", "conflict_status": "none",
    } for i in range(5)]
    result = evaluate_evidence_sufficiency(papers, evidence=records)
    assert result["missing_field_rate"] == pytest.approx(0.2)


@pytest.mark.parametrize("quotes", [[], ["N/A"], ["NOT_AVAILABLE"], ["  "]])
def test_synthesis_rejects_empty_or_placeholder_quotes(quotes):
    papers = [{"id": "W1"}]
    evidence = [{"paper_id": "W1", "claim_support_status": "supported",
                 "supporting_evidence": quotes}]
    assert prepare_synthesis_evidence(papers, evidence) == []
