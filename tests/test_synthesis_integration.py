
"""Integration tests for SARA's synthesis stage."""

import pytest
import sara.agent as agent_module


@pytest.fixture
def synthesis_ready(monkeypatch):
    """Make evidence sufficient without network or real LLM calls."""

    monkeypatch.setattr(
        agent_module,
        "evaluate_evidence_sufficiency",
        lambda **kwargs: {
            "sufficient": True,
            "gaps": [],
        },
    )

    monkeypatch.setattr(
        agent_module,
        "prepare_synthesis_evidence",
        lambda papers, evidence: [
            {
                "paper_id": "paper-1",
                "claim_support_status": "supported",
                "findings": "An observed research finding.",
                "supporting_evidence": ["An observed research finding."],
            }
        ],
    )

    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        lambda name, arguments: {
            "status": "COMPLETED",
            "result": [],
        },
    )


PLAN = (
    "OBJECTIVE:\n"
    "Study research agents.\n"
    "SUBQUESTIONS:\n"
    "- How do research agents work?\n"
    "KEYWORDS:\n"
    "- research agents\n"
)


def make_synthesis(citation):
    return (
        "SUMMARY:\n"
        f"Research agents were studied [{citation}].\n\n"
        "COMPARISON:\n"
        "The available studies were compared.\n\n"
        "EVIDENCE_GAPS:\n"
        "Additional evidence may be needed.\n\n"
        "LIMITATIONS:\n"
        "Only abstract-level evidence was used.\n"
    )


def test_agent_completes_valid_synthesis(synthesis_ready, monkeypatch):
    class FakeModel:
        def generate(self, prompt):
            if "research planning component" in prompt:
                return PLAN
            return make_synthesis("S1")

    monkeypatch.setattr(agent_module, "OllamaModelClient", FakeModel)

    result = agent_module.run_agent("How do research agents work?", max_turns=1)

    assert result["status"] == "WAITING_FOR_APPROVAL"
    assert result["review_request"]["decision"] is None
    assert result["synthesis"] is not None
    assert result["synthesis"]["citations"]["S1"] == "paper-1"
    assert result["synthesis"]["requires_human_review"] is True


def test_agent_escalates_invalid_citation(synthesis_ready, monkeypatch):
    class FakeModel:
        def generate(self, prompt):
            if "research planning component" in prompt:
                return PLAN
            return make_synthesis("S99")

    monkeypatch.setattr(agent_module, "OllamaModelClient", FakeModel)

    result = agent_module.run_agent("How do research agents work?", max_turns=1)

    assert result["status"] == "ESCALATED"
    assert result["synthesis"] is None


def test_agent_handles_synthesis_model_failure(synthesis_ready, monkeypatch):
    class FakeModel:
        def generate(self, prompt):
            if "research planning component" in prompt:
                return PLAN
            raise RuntimeError("Simulated Ollama failure")

    monkeypatch.setattr(agent_module, "OllamaModelClient", FakeModel)

    result = agent_module.run_agent("How do research agents work?", max_turns=1)

    assert result["status"] == "FAILED_SAFELY"
    assert result["synthesis"] is None
def test_agent_persists_human_review(
    synthesis_ready, monkeypatch, tmp_path
):
    from sara.review_store import load_review

    class FakeModel:
        def generate(self, prompt):
            if "research planning component" in prompt:
                return PLAN
            return make_synthesis("S1")

    monkeypatch.setattr(
        agent_module, "OllamaModelClient", FakeModel
    )

    # Isolate review files from the real project directory.
    from sara.review_store import save_review

    review_dir = tmp_path / "reviews"

    monkeypatch.setattr(
        agent_module,
        "save_review",
        lambda review: save_review(review, review_dir),
    )

    result = agent_module.run_agent(
        "How do research agents work?",
        max_turns=1,
    )

    assert result["status"] == "WAITING_FOR_APPROVAL"

    saved = load_review(result["run_id"], review_dir)

    assert saved["status"] == "WAITING_FOR_APPROVAL"
    assert saved["decision"] is None
    assert saved["run_id"] == result["run_id"]
