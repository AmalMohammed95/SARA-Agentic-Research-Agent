
"""Deterministic tests for SARA evidence-grounded synthesis."""

import pytest

from sara.synthesis import (
    SynthesisValidationError,
    prepare_synthesis_evidence,
    build_synthesis_prompt,
    validate_synthesis,
)


@pytest.fixture
def sample_data():
    papers = [
        {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1000/example",
        }
    ]

    evidence = [
        {
            "paper_id": "https://doi.org/10.1000/example",
            "claim_support_status": "supported",
            "objective": "Evaluate research agents",
            "methodology": "Experimental evaluation",
            "dataset_sample": "Ten tasks",
            "findings": "The agent completed eight tasks",
            "limitations": "Small evaluation sample",
            "supporting_evidence": [
                "The agent completed eight of ten tasks."
            ],
        }
    ]

    return papers, evidence


def test_prepare_supported_evidence(sample_data):
    papers, evidence = sample_data

    result = prepare_synthesis_evidence(papers, evidence)

    assert len(result) == 1
    assert result[0]["claim_support_status"] == "supported"


def test_reject_unsupported_evidence(sample_data):
    papers, evidence = sample_data
    evidence[0]["claim_support_status"] = "unsupported"

    assert prepare_synthesis_evidence(papers, evidence) == []


def test_reject_unknown_paper(sample_data):
    papers, evidence = sample_data
    evidence[0]["paper_id"] = "unknown-paper"

    assert prepare_synthesis_evidence(papers, evidence) == []


def test_build_prompt_and_citation_map(sample_data):
    papers, evidence = sample_data
    verified = prepare_synthesis_evidence(papers, evidence)

    prompt, citation_map = build_synthesis_prompt(
        "How effective are research agents?",
        verified,
    )

    assert "How effective are research agents?" in prompt
    assert "[S1]" in prompt
    assert citation_map["S1"] == evidence[0]["paper_id"]


def test_reject_empty_evidence():
    with pytest.raises(SynthesisValidationError):
        build_synthesis_prompt("Research question", [])


def test_accept_valid_synthesis():
    response = """
SUMMARY:
The agent completed eight tasks [S1].

COMPARISON:
Only one study is available [S1].

EVIDENCE_GAPS:
More studies are needed [S1].

LIMITATIONS:
The evaluation sample was small [S1].
"""

    result = validate_synthesis(
        response,
        {"S1": "paper-123"},
    )

    assert result["valid"] is True
    assert result["citations"]["S1"] == "paper-123"


def test_reject_unknown_citation():
    response = """
SUMMARY:
A finding was reported [S9].

COMPARISON:
No comparison is available.

EVIDENCE_GAPS:
Additional evidence is needed.

LIMITATIONS:
The evidence is limited.
"""

    result = validate_synthesis(
        response,
        {"S1": "paper-123"},
    )

    assert result["valid"] is False
    assert "Unknown citation" in result["reason"]


def test_reject_missing_sections():
    result = validate_synthesis(
        "SUMMARY:\nA finding was reported [S1].",
        {"S1": "paper-123"},
    )

    assert result["valid"] is False
    assert "Missing sections" in result["reason"]
