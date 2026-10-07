import sara.executor as executor_module


def test_openalex_exception_fails_safely(monkeypatch):
    def failing_search_openalex(query, max_results=5):
        raise RuntimeError("Simulated OpenAlex failure")

    monkeypatch.setattr(
        executor_module,
        "search_openalex",
        failing_search_openalex,
    )

    result = executor_module.execute_tool(
        "search_openalex",
        {
            "query": "LLM agents academic research",
            "max_results": 5,
        },
    )

    assert result["status"] == "FAILED_SAFELY"
    assert result["tool"] == "search_openalex"
    assert result["result"] is None
    assert "Simulated OpenAlex failure" in result["reason"]