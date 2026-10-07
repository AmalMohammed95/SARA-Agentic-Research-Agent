from sara.evidence import evaluate_evidence_sufficiency


def test_fewer_than_five_unique_studies_is_insufficient():
    selected_papers = [
        {"doi": "10.1000/paper1"},
        {"doi": "10.1000/paper2"},
        {"doi": "10.1000/paper3"},
        {"doi": "10.1000/paper4"},
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
    )

    assert result["sufficient"] is False
    assert result["unique_relevant_studies"] == 4
    assert result["required_studies"] == 5
def test_complete_supported_evidence_is_sufficient():
    subquestions = [
        "How are LLM agents used in academic research?",
        "What benefits do LLM agents provide?",
    ]

    selected_papers = [
        {"doi": f"10.1000/paper{i}"}
        for i in range(1, 6)
    ]

    evidence = [
        {
            "paper_id": f"10.1000/paper{i}",
            "objective": "Study objective",
            "methodology": "Study methodology",
            "dataset_sample": "Study sample",
            "findings": "Study findings",
            "limitations": "Study limitations",
            "supported_subquestions": subquestions,
            "conflict_status": "none",
            "claim_support_status": "supported",
        }
        for i in range(1, 6)
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        subquestions=subquestions,
        evidence=evidence,
    )

    assert result["sufficient"] is True
    assert result["unique_relevant_studies"] == 5
    assert result["missing_field_rate"] == 0.0
    assert result["unsupported_claim_count"] == 0
    assert result["gaps"] == []