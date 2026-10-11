from unittest.mock import patch
from sara.tools import search_scholarly, search_semantic_scholar
from sara.policy import validate_tool_call
from sara.executor import execute_tool


def test_merges_doi_and_keeps_better_abstract():
    first = [{"id": "openalex:1", "doi": "https://doi.org/10.1/ABC", "title": "A", "year": 2025, "abstract": "short"}]
    second = [{"id": "ss:1", "doi": "https://doi.org/10.1/abc", "title": "A", "year": 2025, "abstract": "long and meaningful abstract"}]
    with patch("sara.tools.search_openalex", return_value=first), patch("sara.tools.search_semantic_scholar", return_value=second):
        result = search_scholarly("leukemia", 10)
    assert len(result) == 1
    assert result[0]["abstract"] == "long and meaningful abstract"
    assert set(result[0]["sources"]) == {"openalex", "semantic_scholar"}


def test_partial_provider_failure():
    paper = {"id": "openalex:1", "doi": None, "title": "A", "year": 2025, "abstract": "evidence"}
    with patch("sara.tools.search_openalex", return_value=[paper]), patch("sara.tools.search_semantic_scholar", side_effect=TimeoutError):
        assert len(search_scholarly("topic")) == 1


def test_both_providers_fail_safely():
    with patch("sara.tools.search_openalex", side_effect=TimeoutError), patch("sara.tools.search_semantic_scholar", side_effect=TimeoutError):
        result = execute_tool("search_scholarly", {"query": "topic", "max_results": 10})
    assert result["status"] == "FAILED_SAFELY"


def test_tool_policy():
    assert validate_tool_call("search_scholarly", {"query": "topic", "max_results": 10})["allowed"]
    assert not validate_tool_call("search_scholarly", {"query": "topic", "max_results": True})["allowed"]
    assert not validate_tool_call("unregistered_tool", {"query": "topic"})["allowed"]


def test_semantic_scholar_parsing():
    import io, json
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"data": [{"paperId": "123", "title": "Title", "year": 2024, "abstract": "Evidence", "externalIds": {"DOI": "10.1/example"}}]}).encode()
    with patch("sara.tools.urllib.request.urlopen", return_value=Response()):
        papers = search_semantic_scholar("topic")
    assert papers[0]["doi"] == "https://doi.org/10.1/example"
    assert papers[0]["abstract"] == "Evidence"
