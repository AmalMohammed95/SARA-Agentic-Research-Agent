import json

import sara.agent as agent_module


def test_agent_uses_batch_screening_and_traces_each_paper(monkeypatch):
    class MockModelClient:
        calls = []

        def generate(self, prompt):
            self.calls.append(prompt)

            if "Papers (JSON):" in prompt:
                return json.dumps({
                    "results": [
                        {
                            "paper_id": "W100",
                            "decision": "INCLUDE",
                            "reason": "Directly relevant to the question.",
                        },
                        {
                            "paper_id": "W200",
                            "decision": "EXCLUDE",
                            "reason": "Not directly relevant.",
                        },
                    ]
                })

            if "SUBQUESTIONS:" in prompt or "research plan" in prompt.lower():
                return (
                    "OBJECTIVE:\nStudy academic research agents.\n"
                    "SUBQUESTIONS:\n"
                    "- How are research agents used?\n"
                    "KEYWORDS:\n"
                    "- academic research agents\n"
                )

            raise RuntimeError("Stop after semantic screening")

    def fake_execute_tool(tool_name, arguments):
        return {
            "status": "COMPLETED",
            "result": [
                {
                    "id": "W100",
                    "title": "Research Agents",
                    "abstract": "Research agents support academic workflows.",
                    "year": 2025,
                },
                {
                    "id": "W200",
                    "title": "Unrelated Topic",
                    "abstract": "This paper studies another topic.",
                    "year": 2025,
                },
            ],
        }

    model = MockModelClient()

    monkeypatch.setattr(
        agent_module, "OllamaModelClient", lambda: model
    )
    monkeypatch.setattr(
        agent_module, "execute_tool", fake_execute_tool
    )

    result = agent_module.run_agent(
        "How are research agents used?",
        max_turns=1,
    )

    screening_events = [
        event for event in result["trace"]
        if event["action"] == "semantic_screening"
    ]

    assert len(screening_events) == 2

    assert {
        event["status"] for event in screening_events
    } == {"INCLUDE", "EXCLUDE"}

    batch_calls = [
        prompt for prompt in model.calls
        if "Papers (JSON):" in prompt
    ]

    assert len(batch_calls) == 1
