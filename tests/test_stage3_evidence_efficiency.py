"""Acceptance regressions for stage-3 quote retrieval and bounded verification."""
import json

from sara.source_first import build_multi_source_mapping, source_candidates
from sara.semantic_verification import verify_semantic_with_budget
from sara.deterministic_evidence import extract_abstract_json


class CountModel:
    def __init__(self):
        self.calls = 0
    def generate(self, prompt):
        self.calls += 1
        pairs = json.loads(prompt.split('Pairs (JSON): ', 1)[1])
        return json.dumps({'results': [
            {'question': p['question'], 'verdict': 'SUPPORTED'} for p in pairs
        ]})


def test_methods_retrieval_prefers_actual_metrics_to_generic_reliability():
    abstract = ('Reliability is an important concern for LLM agents in academia. '
                'We measure task success rates and run repeated trials across environments.')
    got = source_candidates(abstract, 'What methods measure the reliability of agents?')
    assert got[0].startswith('We measure task success')


def test_validation_retrieval_finds_human_agreement_without_exact_question_wording():
    abstract = ('Our research investigates the deployment of LLM agents. '
                'We compare agent ratings with human annotators and measure inter-rater agreement.')
    got = source_candidates(abstract, 'How are agent reliability evaluations validated against human judgments?')
    assert got[0].startswith('We compare agent ratings')


def test_challenge_retrieval_prefers_stated_limitation():
    abstract = ('Our survey describes reliability for LLM agents in business. '
                'A key limitation is benchmark contamination and distribution shift.')
    got = source_candidates(abstract, 'What challenges and limitations arise in agent reliability evaluation?')
    assert 'key limitation' in got[0]


def test_unrelated_abstract_yields_no_misleading_source_candidates():
    abstract = 'The dolphins have beautiful fins and prefer cold ocean currents.'
    mapping, diagnostics = build_multi_source_mapping(
        abstract, ['How do researchers validate LLM agent reliability?'], {})
    assert mapping == {}
    assert list(diagnostics.values()) == ['no_source_candidate']


def test_quote_mapping_is_verbatim_but_not_yet_verified_semantically():
    abstract = 'We evaluate agent reliability using repeated trials and measured failure rates.'
    q = 'What methods are used to evaluate agent reliability?'
    mapping, origin = build_multi_source_mapping(abstract, [q], {})
    assert all(quote in abstract for quote in mapping[q])
    assert origin[q] == 'source_sentence_candidate_unverified_semantics'


def test_budget_exhaustion_fails_closed_without_calling_model():
    model = CountModel()
    abstract = 'We tested reliability with repeated trials and recorded failure rates.'
    q = 'How is reliability tested?'
    result = verify_semantic_with_budget(model, abstract, {q: [abstract]}, 0)
    assert result['verdicts'][q] == 'UNCERTAIN'
    assert result['supported_quotes'] == {}
    assert result['model_calls'] == 0
    assert model.calls == 0


def test_budget_available_performs_one_call():
    model = CountModel()
    abstract = 'We tested reliability with repeated trials and recorded failure rates.'
    q = 'How is reliability tested?'
    result = verify_semantic_with_budget(model, abstract, {q: [abstract]}, 1)
    assert result['verdicts'][q] == 'SUPPORTED'
    assert result['supported_quotes'][q] == [abstract]
    assert model.calls == 1


def test_sample_size_extracted_only_when_source_says_it():
    a = 'We compare 240 tasks using a robustness benchmark. Results show 12 failures.'
    result = json.loads(extract_abstract_json(a))
    assert result['dataset_sample'] in a
    assert result['dataset_sample'].startswith('We compare 240 tasks')
    assert json.loads(extract_abstract_json('We introduce a conceptual taxonomy.'))['dataset_sample'] == ''


def test_budget_not_used_when_no_evidence_candidates():
    model = CountModel()
    result = verify_semantic_with_budget(model, '', {}, 0)
    assert result['model_calls'] == 0
    assert result['error'] is None
