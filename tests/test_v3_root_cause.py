"""Regression tests for the reproducibility, provenance and model-call failures.

Tests use synthetic abstracts and fake model responses; these are NOT external
scientific validation or proof that Gemini's labels are correct.
"""
import json
import re

from sara.deterministic_evidence import classify_study_type, extract_abstract_json
from sara.evidence_orchestrator import prepare_work, review_papers
from sara.topic_guard import stable_reliability_subquestions


Q1 = 'Which evaluation metrics and benchmarks assess the reliability of LLM agents?'
Q2 = 'How is consistency and robustness of LLM agents tested across repeated tasks?'
Q3 = 'Which limitations and reproducibility challenges affect reliability evaluation of LLM agents?'
QUESTIONS = [Q1, Q2, Q3]


class FakeAllSupported:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        payload = json.loads(prompt.split('UNTRUSTED PAIRS (JSON): ', 1)[1])
        return json.dumps({'results': [{'id': p['id'], 'verdict': 'SUPPORTED'} for p in payload]})


class FakeMalformed:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return '{"results": [{"id":"0","verdict":"SUPPORTED"}]}'


def papers(n=8):
    return [{
        'paper_id': f'doi:{i}',
        'title': 'LLM agent reliability evaluation',
        'abstract': (
            'We evaluate LLM agent reliability using repeated tasks and failure rate metrics. '
            'We test consistency and robustness across repeated runs of the agents. '
            'The limitation is benchmark contamination affecting reproducibility of agent reliability studies.'
        ),
    } for i in range(n)]


def test_batching_reduces_calls_versus_one_per_paper():
    fake = FakeAllSupported()
    review = review_papers(fake, papers(9), QUESTIONS, max_calls=3, batch_size=3)
    assert review['model_calls'] == 3
    assert fake.calls == 3
    assert review['reviewed_papers'] == 9
    assert review['unreviewed_papers'] == 0
    assert all(review['supported'][f'doi:{i}'] for i in range(9))


def test_strict_quote_source_provenance():
    fake = FakeAllSupported()
    samples = papers(1)
    results = review_papers(fake, samples, QUESTIONS, max_calls=1)
    assert results['supported']
    abstract = samples[0]['abstract']
    for quotes in results['supported']['doi:0'].values():
        assert all(quote in abstract for quote in quotes)


def test_malformed_partial_batch_not_accepted():
    fake = FakeMalformed()
    result = review_papers(fake, papers(3), QUESTIONS, max_calls=1, batch_size=3)
    assert fake.calls == 1
    assert result['supported'] == {}
    assert result['reviewed_papers'] == 0
    assert result['unreviewed_papers'] == 3
    assert result['batches'][0]['status'] == 'UNVERIFIED'


def test_budget_zero_cannot_create_support():
    fake = FakeAllSupported()
    result = review_papers(fake, papers(5), QUESTIONS, max_calls=0)
    assert fake.calls == 0
    assert result['supported'] == {}
    assert result['unreviewed_papers'] == 5
    assert result['budget_exhausted']


def test_budget_partial_is_explicit():
    fake = FakeAllSupported()
    result = review_papers(fake, papers(5), QUESTIONS, max_calls=1, batch_size=2)
    assert result['reviewed_papers'] == 2
    assert result['unreviewed_papers'] == 3
    assert result['budget_exhausted']


def test_reproducible_plan_for_broad_question():
    question = 'What methods are used to evaluate the reliability of LLM agents in academic research?'
    assert stable_reliability_subquestions(question) == QUESTIONS
    assert stable_reliability_subquestions(question) == QUESTIONS


def test_narrow_research_question_not_rewritten():
    assert stable_reliability_subquestions(
        'What methods evaluate reliability of LLM agents in finance?'
    ) == []


def test_review_type_not_fabricated_as_empirical_sample():
    title = 'A Survey of LLM Agent Evaluation'
    abstract = ('This survey reviews datasets and benchmark methods. '
                'Our analysis reveals persistent gaps in reliability evaluation.')
    assert classify_study_type(title, abstract) == 'narrative_review'
    data = json.loads(extract_abstract_json(abstract))
    assert data['dataset_sample'] == ''
    assert data['findings'].startswith('Our analysis reveals')


def test_candidate_retrieval_has_no_fabricated_quote():
    work = prepare_work(papers(1), QUESTIONS)
    assert work
    for source_quote in [q for candidates in work[0]['candidates'].values() for q in candidates]:
        assert source_quote in work[0]['abstract']


def test_invalid_call_budget_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        review_papers(FakeAllSupported(), papers(1), QUESTIONS, max_calls=-1)
    with pytest.raises(ValueError):
        review_papers(FakeAllSupported(), papers(1), QUESTIONS, batch_size=0)


def test_gemini_agent_uses_batched_verification_without_fabricated_support(monkeypatch):
    """End-to-end state machine test with synthetic studies and fake Gemini."""
    import sara.agent as agent

    question = 'What methods are used to evaluate the reliability of LLM agents in academic research?'
    synthetic_abstract = (
        'We evaluate the reliability of LLM agents using repeated tasks and failure-rate metrics. '
        'We test reliability and consistency across 100 agent trials on a benchmark dataset. '
        'Results show a 12 percent failure rate during repeated agent trials. '
        'Limitations include benchmark contamination affecting reproducibility of agent evaluations.'
    )
    works = [
        {'id': f'https://openalex.org/W{i}', 'doi': f'https://doi.org/10.1000/sara{i}',
         'title': f'LLM Agent Reliability Evaluation Study {i}',
         'year': 2026, 'abstract': synthetic_abstract}
        for i in range(6)
    ]

    class FakeGemini:
        def generate(self, prompt):
            if 'research planning component' in prompt:
                return ('OBJECTIVE:\nEvaluate agent reliability.\n'
                        'SUBQUESTIONS:\n- How are LLM agents evaluated?\n'
                        'KEYWORDS:\n- LLM agent reliability evaluation\n')
            if 'UNTRUSTED PAIRS (JSON):' in prompt:
                pairs = json.loads(prompt.split('UNTRUSTED PAIRS (JSON): ', 1)[1])
                return json.dumps({'results': [{'id': p['id'], 'verdict': 'SUPPORTED'}
                                               for p in pairs]})
            if 'academic synthesis component' in prompt:
                raise RuntimeError('Synthetic fixture never authorizes a factual synthesis')
            raise AssertionError('Unexpected model invocation: ' + prompt[:100])

    monkeypatch.setenv('SARA_MODEL_PROVIDER', 'gemini')
    monkeypatch.setenv('SARA_EXTRACTIVE_MODE', '1')
    monkeypatch.setenv('SARA_SEMANTIC_VERIFICATION', '1')
    monkeypatch.setenv('SARA_BATCH_SEMANTIC_VERIFICATION', '1')
    monkeypatch.setenv('SARA_STABLE_RELIABILITY_PLAN', '1')
    monkeypatch.setenv('SARA_MAX_SEMANTIC_CALLS', '2')
    monkeypatch.setenv('SARA_MAX_EXTRACTIONS', '10')
    monkeypatch.setenv('SARA_FAST_SCREENING', '1')
    monkeypatch.setenv('SARA_STRICT_FAST_SCREENING', '0')
    monkeypatch.setattr(agent, 'GeminiModelClient', FakeGemini)
    monkeypatch.setattr(agent, 'execute_tool', lambda *_: {'status': 'COMPLETED', 'result': works})

    result = agent.run_agent(question, max_turns=1)
    events = [e for e in result['trace'] if e['action'] == 'batch_semantic_verification']
    assert len(events) == 1
    assert events[0]['details']['model_calls'] == 2  # Six papers, three per call
    assert events[0]['details']['reviewed_papers'] == 6
    assert any(e['action'] == 'stable_research_plan' for e in result['trace'])
    assert not any(e['action'] == 'verify_semantic_evidence' for e in result['trace'])
    assert len(result['evidence']) == 6
    for record in result['evidence']:
        assert record['claim_support_status'] == 'supported'
        assert record['supporting_evidence']
        assert record['study_type'] in ('empirical', 'unknown')
        assert record['evidence_source_scope'] == 'abstract_only'
        assert all(s['quote'] in synthetic_abstract for s in record['source_spans'])
    check = next(e['details'] for e in result['trace'] if e['action'] == 'evaluate_evidence')
    assert all(count >= 2 for count in check['subquestion_coverage'].values())


def test_no_metric_candidate_from_generic_topic_sentence():
    work = prepare_work([{'paper_id': 'p', 'abstract':
        'LLM agent evaluation is an important area of academic research.'}],
        ['Which quantitative benchmark metrics measure agent reliability?'])
    # General background cannot support a metric-specific empirical claim.
    assert work == []


def test_not_applicable_sample_is_design_aware_not_missing(monkeypatch):
    from sara.evidence import evaluate_evidence_sufficiency
    rec = {
        'paper_id': 'doi:1', 'study_type': 'narrative_review',
        'objective': 'We survey agent evaluation methods.',
        'methodology': 'We organize studies in a taxonomy.',
        'dataset_sample': 'NOT_APPLICABLE',
        'findings': 'Our analysis reveals gaps.',
        'limitations': 'We identify limitations.',
        'conflict_status': 'none', 'claim_support_status': 'supported',
        'extraction_status': 'completed',
        'supported_subquestions': [Q1],
        'supporting_evidence': ['Our analysis reveals gaps.'],
        'source_spans': [{'source':'abstract','quote':'Our analysis reveals gaps.',
                          'start_char':0,'end_char':26}],
    }
    check = evaluate_evidence_sufficiency(
        [{'id': 'doi:1'}], [Q1], [rec]
    )
    assert check['not_applicable_fields_count'] == 1
    assert check['assessed_required_fields'] == 4
    assert check['missing_field_rate'] == 0
    # Sufficiency remains blocked by 5-study and 2-per-question thresholds.
    assert not check['sufficient']


def test_unknown_study_type_cannot_avoid_missing_sample():
    from sara.evidence import evaluate_evidence_sufficiency
    rec = {'paper_id': 'p', 'study_type': 'unknown',
           'objective': 'o', 'methodology': 'm', 'dataset_sample': 'NOT_APPLICABLE',
           'findings': 'f', 'limitations': 'l', 'extraction_status': 'completed',
           'claim_support_status': 'not_assessed', 'conflict_status': 'none'}
    result = evaluate_evidence_sufficiency([{'id':'p'}], [], [rec])
    assert result['missing_field_rate'] == 0.2
    assert result['not_applicable_fields_count'] == 0


def test_diversified_search_uses_distinct_dimensions(monkeypatch):
    from sara.search_strategy import choose_turn_queries
    monkeypatch.setenv('SARA_DIVERSIFIED_SEARCH', '1')
    query = 'What methods evaluate reliability of LLM agents in academic research?'
    selected = choose_turn_queries(['Generic agent literature'], query, set(), limit=3)
    assert len(selected) == 3
    assert 'benchmark metrics' in selected[0]
    assert 'human evaluator agreement' in selected[1]
    assert 'failure modes' in selected[2]
