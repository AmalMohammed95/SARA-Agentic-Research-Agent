"""Regression test for independent scholarly-provider concurrency."""
import threading
from unittest.mock import patch

from sara.tools import search_scholarly


def test_search_providers_run_concurrently_and_keep_source_order():
    both_started = threading.Barrier(2, timeout=2)

    def openalex(query, max_results=10):
        both_started.wait()
        return [{"id": "openalex:1", "doi": None, "title": "First", "abstract": "A"}]

    def scholar(query, max_results=10):
        both_started.wait()
        return [{"id": "scholar:2", "doi": None, "title": "Second", "abstract": "B"}]

    with patch("sara.tools.search_openalex", side_effect=openalex), patch(
        "sara.tools.search_semantic_scholar", side_effect=scholar
    ):
        result = search_scholarly("topic")

    assert [paper["title"] for paper in result] == ["First", "Second"]
