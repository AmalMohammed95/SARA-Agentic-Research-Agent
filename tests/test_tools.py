import sara.tools as tools_module


def test_empty_openalex_query_returns_empty_list(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Network should not be called.")

    monkeypatch.setattr(
        tools_module.urllib.request,
        "urlopen",
        fail_if_called,
    )

    result = tools_module.search_openalex("")

    assert result == []
def test_openalex_successful_response_is_parsed(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return (
                b'{"results": ['
                b'{'
                b'"id": "W123456",'
                b'"title": "LLM Agents in Academic Research",'
                b'"publication_year": 2025,'
                b'"doi": "10.1000/test-paper",'
                b'"abstract_inverted_index": {'
                b'"LLM": [0],'
                b'"agents": [1],'
                b'"support": [2],'
                b'"research": [3]'
                b'}'
                b'}'
                b']}'
            )

    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(
        tools_module.urllib.request,
        "urlopen",
        fake_urlopen,
    )

    result = tools_module.search_openalex(
        "LLM agents academic research",
        max_results=5,
    )

    assert len(result) == 1
    assert result[0]["id"] == "W123456"
    assert result[0]["title"] == "LLM Agents in Academic Research"
    assert result[0]["year"] == 2025
    assert result[0]["doi"] == "10.1000/test-paper"
    assert result[0]["abstract"] == "LLM agents support research"
def test_openalex_network_failure_returns_empty_list(monkeypatch):
    def failing_urlopen(*args, **kwargs):
        raise RuntimeError("Simulated network failure")

    monkeypatch.setattr(
        tools_module.urllib.request,
        "urlopen",
        failing_urlopen,
    )

    result = tools_module.search_openalex(
        "LLM agents academic research",
        max_results=5,
    )

    assert result == []