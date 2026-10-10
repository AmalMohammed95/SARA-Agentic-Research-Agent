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
def test_duplicate_studies_do_not_satisfy_minimum_requirement():
    selected_papers = [
        {"doi": "10.1000/paper1"},
        {"doi": "10.1000/paper1"},
        {"doi": "10.1000/paper2"},
        {"doi": "10.1000/paper3"},
        {"doi": "10.1000/paper4"},
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
    )

    assert result["sufficient"] is False
    assert result["relevant_studies"] == 5
    assert result["unique_relevant_studies"] == 4
    assert result["required_studies"] == 5
def test_high_missing_field_rate_is_insufficient():
    selected_papers = [
        {"doi": f"10.1000/paper{i}"}
        for i in range(1, 6)
    ]

    evidence = [
        {
            "paper_id": f"10.1000/paper{i}",
            "objective": "Study objective",
            "methodology": "",
            "dataset_sample": "",
            "findings": "Study findings",
            "limitations": "",
            "supported_subquestions": [],
            "conflict_status": "none",
            "claim_support_status": "supported",
        }
        for i in range(1, 6)
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        evidence=evidence,
    )

    assert result["sufficient"] is False
    assert result["missing_field_rate"] > 0.20
def test_invalid_provenance_is_insufficient():
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
            "supported_subquestions": [],
            "conflict_status": "none",
            "claim_support_status": "supported",
        }
        for i in range(1, 6)
    ]

    evidence[0]["paper_id"] = "10.1000/not-selected"

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        evidence=evidence,
    )

    assert result["sufficient"] is False
    assert result["invalid_provenance_count"] == 1
def test_not_available_counts_as_missing_evidence(monkeypatch):
    from sara import evidence as evidence_module

    monkeypatch.setattr(
        evidence_module, "MIN_RELEVANT_STUDIES", 1
    )

    paper = {
        "id": "W_TEST_001",
        "title": "Test Study",
    }

    record = {
        "paper_id": "W_TEST_001",
        "objective": "NOT_AVAILABLE",
        "methodology": "NOT_AVAILABLE",
        "dataset_sample": "NOT_AVAILABLE",
        "findings": "NOT_AVAILABLE",
        "limitations": "NOT_AVAILABLE",
        "supported_subquestions": [],
        "conflict_status": "none",
        "claim_support_status": "unsupported",
    }

    result = evidence_module.evaluate_evidence_sufficiency(
        selected_papers=[paper],
        subquestions=[],
        evidence=[record],
    )

    assert result["missing_field_rate"] == 1.0
    assert result["sufficient"] is False
def test_duplicate_evidence_does_not_increase_coverage(monkeypatch):
    from sara import evidence as evidence_module

    monkeypatch.setattr(
        evidence_module, "MIN_RELEVANT_STUDIES", 1
    )

    subquestion = "How do research agents support reviews?"

    paper = {
        "id": "W_TEST_002",
        "title": "Research Agents",
    }

    record = {
        "paper_id": "W_TEST_002",
        "objective": "Evaluate research agents.",
        "methodology": "Experimental evaluation.",
        "dataset_sample": "Research articles.",
        "findings": "Agents assisted literature screening.",
        "limitations": "Small evaluation sample.",
        "supported_subquestions": [subquestion],
        "conflict_status": "none",
        "claim_support_status": "supported",
    }

    result = evidence_module.evaluate_evidence_sufficiency(
        selected_papers=[paper],
        subquestions=[subquestion],
        evidence=[record.copy(), record.copy()],
    )

    assert result["subquestion_coverage"][subquestion] == 1
def test_duplicate_records_do_not_inflate_missing_field_rate(
    monkeypatch,
):
    from sara import evidence as evidence_module

    monkeypatch.setattr(
        evidence_module, "MIN_RELEVANT_STUDIES", 1
    )

    paper = {
        "id": "W_TEST_003",
        "title": "Evidence Quality Study",
    }

    record = {
        "paper_id": "W_TEST_003",
        "objective": "Evaluate research agents.",
        "methodology": "NOT_AVAILABLE",
        "dataset_sample": "NOT_AVAILABLE",
        "findings": "NOT_AVAILABLE",
        "limitations": "NOT_AVAILABLE",
        "supported_subquestions": [],
        "conflict_status": "none",
        "claim_support_status": "unsupported",
    }

    result = evidence_module.evaluate_evidence_sufficiency(
        selected_papers=[paper],
        subquestions=[],
        evidence=[record.copy(), record.copy()],
    )

    assert result["missing_field_rate"] == 0.8
    assert 0.0 <= result["missing_field_rate"] <= 1.0
def test_deduplicate_papers_by_openalex_id():
    from sara.evidence import deduplicate_papers

    papers = [
        {
            "doi": "https://doi.org/10.1234/example",
            "id": "https://openalex.org/W123",
            "title": "Research Agents",
        },
        {
            "doi": None,
            "id": "https://openalex.org/W123",
            "title": "Research Agents",
        },
        {
            "doi": "https://doi.org/10.5678/another",
            "id": "https://openalex.org/W456",
            "title": "Another Study",
        },
    ]

    result = deduplicate_papers(papers)

    assert len(result) == 2
    assert result[0]["id"] == "https://openalex.org/W123"
    assert result[1]["id"] == "https://openalex.org/W456"
def test_duplicate_paper_across_search_turns():
    from sara.evidence import is_duplicate_paper

    existing_papers = [
        {
            "doi": "https://doi.org/10.1234/example",
            "id": "https://openalex.org/W123",
        }
    ]

    incoming_paper = {
        "doi": None,
        "id": "https://openalex.org/W123",
    }

    assert is_duplicate_paper(incoming_paper, existing_papers)

    different_paper = {
        "doi": "https://doi.org/10.5678/another",
        "id": "https://openalex.org/W456",
    }

    assert not is_duplicate_paper(different_paper, existing_papers)
def test_missing_evidence_markers_are_counted_correctly():
    selected_papers = [
        {"doi": f"10.1000/paper{i}"}
        for i in range(1, 6)
    ]

    evidence = [
        {
            "paper_id": f"10.1000/paper{i}",
            "objective": "- NOT_AVAILABLE",
            "methodology": "NOT_AVAILABLE",
            "dataset_sample": "",
            "findings": None,
            "limitations": "UNKNOWN",
            "supported_subquestions": [],
            "claim_support_status": "supported",
            "conflict_status": "none",
        }
        for i in range(1, 6)
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        evidence=evidence,
    )

    assert result["sufficient"] is False
    assert result["missing_field_rate"] == 1.0

def test_evidence_record_matches_openalex_id_when_doi_exists():
    selected_papers = [
        {
            "doi": f"10.1000/paper{i}",
            "id": f"https://openalex.org/W{i}",
        }
        for i in range(1, 6)
    ]

    evidence = [
        {
            "paper_id": f"https://openalex.org/W{i}",
            "objective": "Evaluate a research method",
            "methodology": "Experimental evaluation",
            "dataset_sample": "100 research papers",
            "findings": "Reported experimental results",
            "limitations": "Reported study limitations",
            "supported_subquestions": [],
            "claim_support_status": "supported",
            "conflict_status": "none",
        }
        for i in range(1, 6)
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        evidence=evidence,
    )

    assert result["missing_evidence_record_count"] == 0
    assert result["missing_field_rate"] == 0.0
    assert result["unique_relevant_studies"] == 5
def test_subquestion_coverage_does_not_double_count_same_paper():
    question = "How are LLM agents used in literature reviews?"

    selected_papers = [
        {
            "doi": "10.1000/paper1",
            "id": "https://openalex.org/W1",
        }
    ]

    evidence = [
        {
            "paper_id": paper_id,
            "objective": "Study objective",
            "methodology": "Study methodology",
            "dataset_sample": "Study sample",
            "findings": "Study findings",
            "limitations": "Study limitations",
            "supported_subquestions": [question],
            "claim_support_status": "supported",
            "conflict_status": "none",
        }
        for paper_id in (
            "10.1000/paper1",
            "https://openalex.org/W1",
        )
    ]

    result = evaluate_evidence_sufficiency(
        selected_papers=selected_papers,
        subquestions=[question],
        evidence=evidence,
    )

    assert result["subquestion_coverage"][question] == 1