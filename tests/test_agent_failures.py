import sara.agent as agent_module


class FailingModelClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("Simulated model failure")


def test_initial_planning_model_failure_is_safe(monkeypatch):
    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        FailingModelClient,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?"
    )

    assert result["status"] == "FAILED_SAFELY"
    assert result["turns"] == 0
    assert "Initial planning model call failed" in result["reason"]
    assert "Simulated model failure" in result["reason"]

    assert len(result["trace"]) == 1
    assert result["trace"][0]["action"] == "research_planning"
    assert result["trace"][0]["status"] == "FAILED_SAFELY"
def test_semantic_screening_model_failure_is_safe(monkeypatch):
    class PlanningThenFailingModelClient:
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1

            if self.calls == 1:
                return (
                    "OBJECTIVE:\n"
                    "Study LLM agents in academic research.\n"
                    "SUBQUESTIONS:\n"
                    "- How are LLM agents used in academic research?\n"
                    "KEYWORDS:\n"
                    "- LLM agents academic research\n"
                )

            raise RuntimeError("Simulated semantic screening failure")

    def fake_execute_tool(tool_name, arguments):
        return {
            "status": "COMPLETED",
            "result": [
                {
                    "id": "W123456",
                    "doi": "10.1000/test-paper",
                    "title": "LLM Agents in Academic Research",
                    "year": 2025,
                    "abstract": (
                        "This study examines the use of LLM agents "
                        "in academic research workflows."
                    ),
                }
            ],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        PlanningThenFailingModelClient,
    )
    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?",
        max_turns=1,
    )

    failure_events = [
        event
        for event in result["trace"]
        if (
            event["action"] == "semantic_screening"
            and event["status"] == "FAILED_SAFELY"
        )
    ]

    assert len(failure_events) == 1
    assert (
        failure_events[0]["details"]["error"]
        == "Simulated semantic screening failure"
    )
def test_evidence_extraction_model_failure_is_safe(monkeypatch):
    class ExtractionFailingModelClient:
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1

            if self.calls == 1:
                return (
                    "OBJECTIVE:\n"
                    "Study LLM agents in academic research.\n"
                    "SUBQUESTIONS:\n"
                    "- How are LLM agents used in academic research?\n"
                    "KEYWORDS:\n"
                    "- LLM agents academic research\n"
                )

            if self.calls == 2:
                return (
                    "DECISION: INCLUDE\n"
                    "REASON: The paper directly addresses the "
                    "research question."
                )

            raise RuntimeError("Simulated evidence extraction failure")

    def fake_execute_tool(tool_name, arguments):
        return {
            "status": "COMPLETED",
            "result": [
                {
                    "id": "W123456",
                    "doi": "10.1000/test-paper",
                    "title": "LLM Agents in Academic Research",
                    "year": 2025,
                    "abstract": (
                        "This study examines the use of LLM agents "
                        "in academic research workflows."
                    ),
                }
            ],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        ExtractionFailingModelClient,
    )
    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?",
        max_turns=1,
    )

    failure_events = [
        event
        for event in result["trace"]
        if (
            event["action"] == "evidence_extraction"
            and event["status"] == "FAILED_SAFELY"
        )
    ]

    assert len(failure_events) == 1
    assert (
        failure_events[0]["details"]["error"]
        == "Simulated evidence extraction failure"
    )
def test_replanning_model_failure_is_safe(monkeypatch):
    class ReplanningFailingModelClient:
        def __init__(self):
            self.calls = 0

        def generate(self, prompt: str) -> str:
            self.calls += 1

            if self.calls == 1:
                return (
                    "OBJECTIVE:\n"
                    "Study LLM agents in academic research.\n"
                    "SUBQUESTIONS:\n"
                    "- How are LLM agents used in academic research?\n"
                    "KEYWORDS:\n"
                    "- LLM agents academic research\n"
                )

            raise RuntimeError("Simulated replanning failure")

    def fake_execute_tool(tool_name, arguments):
        return {
            "status": "COMPLETED",
            "result": [],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        ReplanningFailingModelClient,
    )
    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?",
        max_turns=2,
    )

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["replanning_attempts"] == 1
    assert (
        result["reason"]
        == (
            "Evidence is insufficient and the replanning "
            "model call failed safely."
        )
    )

    failure_events = [
        event
        for event in result["trace"]
        if (
            event["action"] == "replanning"
            and event["status"] == "FAILED_SAFELY"
        )
    ]

    assert len(failure_events) == 1
    assert (
        failure_events[0]["details"]["error"]
        == "Simulated replanning failure"
    )