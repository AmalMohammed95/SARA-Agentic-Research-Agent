from sara.topic_guard import requires_agent_scope, anchor_agent_query, anchor_agent_subquestions
QUESTION = 'What methods evaluate reliability of LLM agents in academic research?'
def test_agent_scope_detection():
    assert requires_agent_scope(QUESTION)
    assert not requires_agent_scope('How reliable are LLM outputs?')
def test_search_preserves_agent_topic():
    assert anchor_agent_query('methods for evaluating LLM reliability', QUESTION) == 'LLM agents methods for evaluating LLM reliability'
    assert anchor_agent_query('LLM agent evaluation benchmarks', QUESTION) == 'LLM agent evaluation benchmarks'
def test_subquestions_keep_agent_scope():
    assert anchor_agent_subquestions(['What validation methods are used?', 'How are LLM agents evaluated?'], QUESTION) == ['What validation methods are used for LLM agents?', 'How are LLM agents evaluated?']
