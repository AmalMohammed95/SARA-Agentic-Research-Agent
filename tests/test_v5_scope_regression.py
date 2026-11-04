from sara.topic_guard import anchor_agent_query, flag_scope_drift
from sara.json_extraction import json_extraction_prompt

def test_query_anchor_keeps_agents():
    assert anchor_agent_query("Metrics for LLM reliability", "How reliable are LLM agents?").startswith("LLM agents ")

def test_existing_agent_query_not_duplicated():
    assert anchor_agent_query("LLM agents reliability", "How reliable are LLM agents?") == "LLM agents reliability"

def test_peer_review_scope_warning():
    q = "What peer review processes evaluate LLM agents?"
    assert flag_scope_drift([q], "How reliable are LLM agents?") == [q]

def test_extraction_prompt_distinguishes_review_types():
    assert "Peer review of manuscripts" in json_extraction_prompt("T", "A", ["Q?"])
