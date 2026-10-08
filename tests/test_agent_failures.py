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
def test_empty_replanned_keywords_fail_safely(monkeypatch):
    class EmptyReplanningKeywordsModelClient:
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

            return (
                "REVISED_KEYWORDS:\n"
            )

    def fake_execute_tool(tool_name, arguments):
        return {
            "status": "COMPLETED",
            "result": [],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        EmptyReplanningKeywordsModelClient,
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
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "No valid search keywords are available."
def test_replanning_can_repeat_same_search_keywords(monkeypatch):
    class RepeatingReplanningModelClient:
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

            return (
                "REVISED_KEYWORDS:\n"
                "- LLM agents academic research\n"
            )

    search_queries = []

    def fake_execute_tool(tool_name, arguments):
        search_queries.append(arguments["query"])

        return {
            "status": "COMPLETED",
            "result": [],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        RepeatingReplanningModelClient,
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

    assert search_queries == [
        "LLM agents academic research",
    ]
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert (
        result["reason"]
        == (
            "Evidence is insufficient and replanning "
            "repeated the current search keywords."
        )
    )
def test_no_search_results_across_turns(monkeypatch):
    class NoResultsModelClient:
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

            return (
                "REVISED_KEYWORDS:\n"
                f"- revised academic research query {self.calls}\n"
            )

    search_queries = []

    def fake_execute_tool(tool_name, arguments):
        search_queries.append(arguments["query"])
        return {
            "status": "COMPLETED",
            "result": [],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        NoResultsModelClient,
    )
    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?",
        max_turns=3,
    )

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert len(search_queries) == 3
    assert result["reason"] == (
        "Evidence is insufficient because repeated searches "
        "returned no papers."
    )
def test_repeated_search_results_without_progress(monkeypatch):
    class NoProgressModelClient:
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

            return (
                "REVISED_KEYWORDS:\n"
                f"- alternative academic research query {self.calls}\n"
            )

    search_queries = []

    repeated_paper = {
        "id": "https://openalex.org/W123456789",
        "title": "Unrelated Academic Research Paper",
        "year": 2024,
        "doi": "https://doi.org/10.1000/example",
        "abstract": "This paper studies an unrelated academic topic.",
    }

    def fake_execute_tool(tool_name, arguments):
        search_queries.append(arguments["query"])
        return {
            "status": "COMPLETED",
            "result": [repeated_paper],
        }

    monkeypatch.setattr(
        agent_module,
        "OllamaModelClient",
        NoProgressModelClient,
    )
    monkeypatch.setattr(
        agent_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = agent_module.run_agent(
        "How are LLM agents used in academic research?",
        max_turns=3,
    )

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert len(search_queries) == 3
    assert result["reason"] == (
        "Evidence is insufficient because repeated searches "
        "produced no new papers."
    )


def test_agent_deduplicates_papers_across_turns(monkeypatch):
    class FakeModel:
        def generate(self, prompt):
            if "research planning component" in prompt:
                return (
                    "OBJECTIVE:\n"
                    "Study research agents.\n"
                    "SUBQUESTIONS:\n"
                    "- How do research agents support reviews?\n"
                    "KEYWORDS:\n"
                    "- research agents\n"
                )

            if "DECISION:" in prompt or "semantic" in prompt.lower():
                return (
                    "DECISION: INCLUDE\n"
                    "REASON: Relevant to the research question."
                )

            if "replan" in prompt.lower() or "revis" in prompt.lower():
                return (
                    "REVISED_KEYWORDS:\n"
                    "- research agents literature reviews\n"
                )

            raise RuntimeError("Simulated extraction failure")

    search_calls = []

    def fake_execute_tool(tool_name, arguments):
        search_calls.append(arguments)

        if len(search_calls) == 1:
            paper = {
                "id": "W123",
                "doi": "10.1000/example",
                "title": "Research Agents",
                "year": 2025,
                "abstract": "Research agents support literature reviews.",
            }
        else:
            paper = {
                "id": "W123",
                "doi": None,
                "title": "Research Agents",
                "year": 2025,
                "abstract": "Research agents support literature reviews.",
            }

        return {
            "status": "COMPLETED",
            "result": [paper],
        }

    monkeypatch.setattr(
        agent_module, "OllamaModelClient", FakeModel
    )
    monkeypatch.setattr(
        agent_module, "execute_tool", fake_execute_tool
    )

    result = agent_module.run_agent(
        "How do research agents support reviews?",
        max_turns=2,
    )
    print("\nSTATUS:", result["status"])
    print("REASON:", result["reason"])
    print("TURNS:", result["turns"])
    print("SEARCH CALLS:", len(search_calls))

    for event in result["trace"]:
        print(
            "TRACE:",
            event.get("action"),
            event.get("status"),
            event.get("details"),
        )

    assert len(search_calls) == 2
    assert len(result["selected_papers"]) == 1
    assert len(result["evidence"]) == 1
