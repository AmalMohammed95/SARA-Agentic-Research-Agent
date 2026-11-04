import json
from sara.deterministic_evidence import extract_abstract_json
from sara.extraction import verify_supporting_evidence
from sara.batch_screening import screen_papers_in_batches

class RejectModel:
    def generate(self, prompt, **kwargs):
        return 'DECISION: EXCLUDE\nREASON: Ambiguous evidence.'

def test_extraction_never_invents_text():
    abstract = ('We evaluate the reliability of LLM agents using a benchmark of 100 tasks. '
                'Our results show failures under changing conditions. '
                'A limitation is the small sample size.')
    result = json.loads(extract_abstract_json(abstract))
    for field in ('objective', 'methodology', 'dataset_sample', 'findings', 'limitations'):
        for sentence in result[field].split('. '):
            assert not sentence or sentence.rstrip('.') in abstract
    assert result['supported_subquestions'] == []
    assert result['question_evidence'] == {}

def test_absent_fields_are_not_invented():
    result = json.loads(extract_abstract_json('We introduce a new agent system.'))
    assert result['dataset_sample'] == ''
    assert result['findings'] == ''
    assert result['limitations'] == ''

def test_strict_fast_screening_does_not_auto_include_generic_evaluation(monkeypatch):
    monkeypatch.setenv('SARA_STRICT_FAST_SCREENING', '1')
    paper = {'id':'p1','title':'Evaluation and Benchmarking of LLM Agents',
             'abstract':'We evaluate many different agent tasks. ' * 6}
    out = screen_papers_in_batches([paper], 'reliability of agents', RejectModel())
    assert out[0]['decision'] == 'EXCLUDE'
