"""Stage 2 offline regression checks for search expansion and screening budget."""
import json
import pytest

from sara.search_strategy import choose_turn_queries, reliability_search_variants
from sara.batch_screening import screen_papers_in_batches
from sara.deterministic_evidence import extract_abstract_json

QUESTION = 'What methods are used to evaluate the reliability of LLM agents in academic research?'


def test_reliability_queries_expand_with_nonoverlapping_evaluation_method():
    used = set()
    queries = choose_turn_queries(['LLM agents reliability methods', 'agent benchmark'], QUESTION, used, 2)
    assert queries[0] == 'LLM agents reliability methods'
    assert 'benchmark' in queries[1]
    assert len(queries) == len(set(queries)) == 2
    queries2 = choose_turn_queries(['LLM agents reliability methods', 'agent benchmark'], QUESTION, used, 2)
    assert len(queries2) == 2
    assert all(query not in queries for query in queries2)


def test_general_question_is_not_forced_into_llm_agent_queries():
    used = set()
    assert not reliability_search_variants('How is urban flood risk modeled?')
    assert choose_turn_queries(['urban flood risk', 'urban flood model'], 'How is urban flood risk modeled?', used, 2) == [
        'urban flood risk', 'urban flood model',
    ]


def test_query_canonicalization_and_limits():
    used = set()
    assert choose_turn_queries(['  Agent    evaluation ', 'agent evaluation', 'benchmark design'], QUESTION, used, 1) == [
        'Agent evaluation',
    ]
    assert choose_turn_queries(['agent evaluation', 'benchmark design'], QUESTION, used, 1) == [
        'benchmark design',
    ]
    with pytest.raises(ValueError):
        choose_turn_queries(['x'], QUESTION, set(), 0)
    with pytest.raises(ValueError):
        choose_turn_queries(['x'], QUESTION, set(), 4)


class ExcludeModel:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return 'DECISION:\nEXCLUDE\nREASON:\nInsufficient agent-specific evidence.'


def test_strict_fast_screen_requires_abstract_corroboration(monkeypatch):
    monkeypatch.setenv('SARA_FAST_SCREENING', '1')
    monkeypatch.setenv('SARA_STRICT_FAST_SCREENING', '1')
    paper = {'id': 'A', 'title': 'Reliability Evaluation of LLM Agents',
             'abstract': 'We discuss educational standards and school administration procedures. ' * 4}
    model = ExcludeModel()
    decision = screen_papers_in_batches([paper], QUESTION, model)
    assert model.calls >= 1
    assert decision[0]['decision'] == 'EXCLUDE'


def test_strict_fast_screen_accepts_obviously_relevant_but_not_evidence(monkeypatch):
    monkeypatch.setenv('SARA_FAST_SCREENING', '1')
    monkeypatch.setenv('SARA_STRICT_FAST_SCREENING', '1')
    class NoCall:
        def generate(self, prompt):
            raise AssertionError('Should not call model for obvious relevance')
    paper = {'id': 'A', 'title': 'Reliability Evaluation of LLM Agents',
             'abstract': 'We benchmark LLM agents to evaluate robustness and reliability on realistic tasks. ' * 3}
    result = screen_papers_in_batches([paper], QUESTION, NoCall())
    assert result[0]['decision'] == 'INCLUDE'
    assert 'verification' in result[0]['reason']


def test_batch_fallback_budget_fails_closed(monkeypatch):
    monkeypatch.setenv('SARA_FAST_SCREENING', '0')
    monkeypatch.setenv('SARA_SCREENING_FALLBACK_LIMIT', '1')
    class LimitedModel:
        calls = 0
        def generate(self, prompt):
            self.calls += 1
            if self.calls == 1:
                return 'malformed batch'
            return 'DECISION:\nINCLUDE\nREASON:\nRelevant study.'
    model = LimitedModel()
    papers = [
        {'id': 'P1', 'title': 'A', 'abstract': 'abstract A'},
        {'id': 'P2', 'title': 'B', 'abstract': 'abstract B'},
        {'id': 'P3', 'title': 'C', 'abstract': 'abstract C'},
    ]
    result = screen_papers_in_batches(papers, QUESTION, model)
    assert model.calls == 2  # 1 batch + 1 individual; never 4
    assert len(result) == 3
    assert result[0]['decision'] == 'INCLUDE'
    assert [r['status'] for r in result[1:]] == ['BUDGET_EXHAUSTED'] * 2


def test_extraction_captures_source_verbatim_survey_objective():
    abstract = ('This survey provides a taxonomy of agent evaluation benchmarks. '
                'We identify critical gaps in evaluating agents. '
                'Our results show that the tested agents vary in robustness.')
    extracted = json.loads(extract_abstract_json(abstract))
    assert 'taxonomy' in extracted['objective']
    assert 'gaps' in extracted['limitations']
    for k in ('objective', 'methodology', 'dataset_sample', 'findings', 'limitations'):
        assert not extracted[k] or extracted[k] in abstract


def test_two_search_requests_in_one_turn_are_traced_and_deduplicated(monkeypatch):
    from sara import agent as agent_module
    monkeypatch.setenv('SARA_SEARCH_QUERIES_PER_TURN', '2')
    monkeypatch.setenv('SARA_FAST_SCREENING', '0')
    class PlanModel:
        def generate(self, prompt, **kwargs):
            return ("OBJECTIVE:\nExamine agent evaluation.\nSUBQUESTIONS:\n"
                    "- How are LLM agents evaluated?\n"
                    "- How are their results validated?\n"
                    "- What are their limitations?\nKEYWORDS:\n"
                    "- LLM agents reliability methods\n"
                    "- agent benchmark\n")
    calls = []
    def search(_tool, arguments):
        calls.append(arguments['query'])
        return {'status': 'COMPLETED', 'result': [
            {'id': 'P1', 'title': 'Agent evaluation', 'year': 2026,
             'abstract': 'We evaluate many agent tasks with human raters.'},
        ]}
    monkeypatch.setattr(agent_module, 'OllamaModelClient', PlanModel)
    monkeypatch.setattr(agent_module, 'execute_tool', search)
    monkeypatch.setattr(agent_module, 'screen_papers_in_batches', lambda **kwargs: [
        {'paper': p, 'decision': 'EXCLUDE', 'reason': 'No direct evidence', 'status': 'EXCLUDE'}
        for p in kwargs['papers']
    ])
    result = agent_module.run_agent(QUESTION, max_turns=1)
    assert len(calls) == 2 and calls[0] != calls[1]
    assert len(result['excluded_papers']) == 1
    assert any(event['action'] == 'search_query_summary' and
               event['details']['unique_results'] == 1 for event in result['trace'])


def test_unassessed_screening_is_deferred_not_wrongly_excluded(monkeypatch):
    from sara import agent as agent_module
    monkeypatch.setenv('SARA_SEARCH_QUERIES_PER_TURN', '1')
    class PlanModel:
        def generate(self, prompt, **kwargs):
            return ("OBJECTIVE:\nResearch methods.\nSUBQUESTIONS:\n"
                    "- How are methods used?\nKEYWORDS:\n- research agents\n")
    def search(_tool, _args):
        return {'status': 'COMPLETED', 'result': [
            {'id': 'P1', 'title': 'Agent research', 'year': 2026,
             'abstract': 'We evaluate agents for research.'},
        ]}
    monkeypatch.setattr(agent_module, 'OllamaModelClient', PlanModel)
    monkeypatch.setattr(agent_module, 'execute_tool', search)
    monkeypatch.setattr(agent_module, 'screen_papers_in_batches', lambda **kwargs: [
        {'paper': p, 'decision': 'EXCLUDE', 'reason': 'Screening call budget exhausted',
         'status': 'BUDGET_EXHAUSTED'} for p in kwargs['papers']
    ])
    result = agent_module.run_agent('How are research agents used?', 1)
    assert [p['id'] for p in result['deferred_papers']] == ['P1']
    assert not result['excluded_papers']
    assert not result['selected_papers']
