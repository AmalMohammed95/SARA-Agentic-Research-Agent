"""Regression cases from SARA's Nov 2026 runs: do not fake success/deficits."""
import json

from sara.evidence import evaluate_evidence_sufficiency
from sara.extraction import create_empty_evidence_record
from sara.semantic_verification import verify_semantic_batch, verify_semantic_candidates


def _papers(n):
    return [{'doi': f'10.1000/p{i}', 'abstract': 'A valid scientific abstract.'} for i in range(n)]


def _supported(paper, questions=None):
    result = create_empty_evidence_record(paper)
    result.update({
        'extraction_status': 'completed',
        'claim_support_status': 'supported',
        'objective': 'Question investigated.',
        'methodology': 'Methods were compared.',
        'dataset_sample': '100 examples.',
        'findings': 'A reproducible result.',
        'limitations': 'Limited sample.',
        'supported_subquestions': questions or [],
        'supporting_evidence': ['A reproducible result.'],
    })
    return result


def test_selected_but_not_extracted_is_pending_not_unsupported():
    papers = _papers(9)
    records = [_supported(p) for p in papers[:5]]
    records += [create_empty_evidence_record(p) for p in papers[5:]]
    decision = evaluate_evidence_sufficiency(papers, evidence=records)
    assert decision['processed_studies_count'] == 5
    assert decision['pending_studies_count'] == 4
    assert decision['missing_field_rate'] == 0.0
    assert decision['unsupported_claim_count'] == 0
    assert not decision['sufficient']
    assert 'pending extraction' in ' '.join(decision['gaps'])


def test_missing_record_does_not_silently_allow_completion():
    papers = _papers(6)
    decision = evaluate_evidence_sufficiency(papers, evidence=[_supported(p) for p in papers[:5]])
    assert decision['missing_evidence_record_count'] == 1
    assert decision['pending_studies_count'] == 1
    assert decision['sufficient'] is False


def test_failed_extraction_is_not_a_false_unsupported_claim():
    papers = _papers(5)
    records = [_supported(p) for p in papers[:4]]
    failed = create_empty_evidence_record(papers[4])
    failed['extraction_status'] = 'failed'
    records.append(failed)
    decision = evaluate_evidence_sufficiency(papers, evidence=records)
    assert decision['failed_studies_count'] == 1
    assert decision['unsupported_claim_count'] == 0
    assert decision['processed_studies_count'] == 4
    assert decision['sufficient'] is False


def test_legacy_unsupported_claim_still_counted():
    papers = _papers(5)
    records = [_supported(p) for p in papers]
    records[0]['claim_support_status'] = 'unsupported'
    decision = evaluate_evidence_sufficiency(papers, evidence=records)
    assert decision['unsupported_claim_count'] == 1


def test_completed_unverified_not_allowed_to_claim_coverage():
    papers = _papers(5)
    q = 'Which evaluations measure reliability?'
    records = [_supported(p, [q]) for p in papers]
    records[0]['supporting_evidence'] = []
    records[0]['claim_support_status'] = 'insufficient_data'
    decision = evaluate_evidence_sufficiency(papers, [q], records)
    assert decision['unverified_evidence_count'] == 1
    assert decision['subquestion_coverage'][q] == 4
    assert decision['sufficient'] is False


def test_explicitly_processed_claim_without_source_quote_cannot_inflate_coverage():
    papers = _papers(5)
    q = 'How is evidence checked?'
    records = [_supported(p, [q]) for p in papers]
    records[0]['supporting_evidence'] = []
    decision = evaluate_evidence_sufficiency(papers, [q], records)
    assert decision['subquestion_coverage'][q] == 4


class FakeModel:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt):
        return self.response


def test_semantic_verification_returns_exact_supported_quote():
    abstract = 'The CNN achieved test accuracy of 95%. The SVM achieved 88% accuracy.'
    q = 'What test accuracy did the CNN achieve?'
    quote = 'The CNN achieved test accuracy of 95%.'
    output = json.dumps({'results': [{'question': q, 'verdict': 'SUPPORTED'}]})
    decision = verify_semantic_batch(FakeModel(output), abstract, {q: quote})
    assert decision['supported_quotes'] == {q: [quote]}


def test_semantic_verification_never_returns_unverified_quote():
    q = 'What test accuracy did the CNN achieve?'
    decision = verify_semantic_batch(FakeModel('irrelevant'), 'The CNN achieved 95%.',
                                     {q: 'The CNN achieved 99%.'})
    assert decision['supported_quotes'] == {}
    assert decision['model_calls'] == 0


def test_multi_candidate_verifier_returns_only_accepted_source_spans():
    abstract = 'The CNN achieved test accuracy of 95%. The SVM achieved 88% accuracy.'
    q = 'What test accuracy did the CNN achieve?'
    output = json.dumps({'results': [
        {'id': '0', 'verdict': 'SUPPORTED'},
        {'id': '1', 'verdict': 'UNSUPPORTED'},
    ]})
    decision = verify_semantic_candidates(FakeModel(output), abstract, {
        q: ['The CNN achieved test accuracy of 95%.', 'The SVM achieved 88% accuracy.']
    })
    assert decision['supported_quotes'] == {q: ['The CNN achieved test accuracy of 95%.']}


def test_abstract_quote_positions_are_real_source_characters():
    from sara.extraction import locate_abstract_quotes
    abstract = 'Background. The agent used\n repeated benchmarks to test reliability.'
    spans = locate_abstract_quotes(abstract, ['The agent used repeated benchmarks to test reliability.'])
    assert len(spans) == 1
    span = spans[0]
    assert abstract[span['start_char']:span['end_char']] == span['quote']
    assert '\n' in span['quote']


def test_abstract_quote_positions_reject_hallucinated_quote():
    from sara.extraction import locate_abstract_quotes
    assert locate_abstract_quotes('The agent failed.', ['The agent succeeded.']) == []


def test_synthesis_requires_source_spans_for_new_pipeline_records():
    from sara.synthesis import prepare_synthesis_evidence
    papers = _papers(1)
    record = _supported(papers[0], ['How is reliability tested?'])
    assert prepare_synthesis_evidence(papers, [record]) == []
    record['source_spans'] = [{
        'source': 'abstract', 'quote': 'A reproducible result.',
        'start_char': 0, 'end_char': 22,
    }]
    assert len(prepare_synthesis_evidence(papers, [record])) == 1
