"""V2 regression tests for logged failures in source processing and trace accounting."""
import json
from sara.source_first import abstract_sentences, source_candidates
from sara.deterministic_evidence import extract_abstract_json


def test_glued_sentences_keep_verbatim_source_and_split():
    abstract = (
        'This paper introduces a taxonomy for agent reliability evaluation.'
        'We compare reliability metrics over 150 agent tasks.'
        'Results show improved consistency in repeated trials.'
    )
    sentences = abstract_sentences(abstract)
    assert len(sentences) == 3
    assert all(part in abstract for part in sentences)
    assert 'We compare reliability metrics over 150 agent tasks.' in sentences


def test_not_confuse_a_survey_with_an_empirical_sample():
    abstract = ('This survey organizes approaches using datasets and benchmarks. '
                'We propose a taxonomy for evaluation frameworks.')
    extraction = json.loads(extract_abstract_json(abstract))
    assert extraction['dataset_sample'] == ''
    assert 'taxonomy' in extraction['methodology']


def test_explicit_numeric_sample_is_extracted():
    abstract = ('We evaluate 931 human-annotated trajectories from six mobile benchmarks. '
                'Results show that reliability differs across judges.')
    extraction = json.loads(extract_abstract_json(abstract))
    assert '931 human-annotated trajectories' in extraction['dataset_sample']


def test_verbatim_methods_candidate_does_not_return_whole_glued_abstract():
    abstract = ('Agent deployment has numerous challenges for practitioners.'
                'We measure reliability with repeated trials and failure rates.')
    out = source_candidates(abstract, 'What methods measure the reliability of LLM agents?')
    assert out[0] == 'We measure reliability with repeated trials and failure rates.'


def test_decimal_does_not_split_inside_number():
    abstract = ('We compare GPT-4.1 and other agent models on tasks.'
                'Results show variation in reliability across settings.')
    sentences = abstract_sentences(abstract)
    assert len(sentences) == 2
    assert 'GPT-4.1' in sentences[0]
