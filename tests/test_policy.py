from sara.policy import validate_tool_call


def test_valid_openalex_tool_call_is_allowed():
    result = validate_tool_call(
        "search_openalex",
        {
            "query": "large language models in academic research",
            "max_results": 5,
        },
    )

    assert result["allowed"] is True
    assert result["reason"] == "Tool call passed validation."
def test_unknown_tool_is_rejected():
    result = validate_tool_call(
        "delete_files",
        {},
    )

    assert result["allowed"] is False
    assert result["reason"] == "Tool 'delete_files' is not allowed."
def test_empty_openalex_query_is_rejected():
    result = validate_tool_call(
        "search_openalex",
        {
            "query": "",
            "max_results": 5,
        },
    )

    assert result["allowed"] is False
    assert result["reason"] == "OpenAlex search query must not be empty."
def test_invalid_max_results_is_rejected():
    result = validate_tool_call(
        "search_openalex",
        {
            "query": "large language models",
            "max_results": 21,
        },
    )

    assert result["allowed"] is False
    assert result["reason"] == (
        "max_results must be an integer between 1 and 20."
    )