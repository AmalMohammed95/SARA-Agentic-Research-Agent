import json
from sara.deterministic_evidence import extract_abstract_json
from sara.research_priority import rank_papers

def test_extractive_no_invented_fields():
    abstract = ('We evaluate LLM agents using a benchmark of 120 tasks. '
                'Results show that agents fail on 30 tasks. '
                'Limitations include dataset bias.')
    result = json.loads(extract_abstract_json(abstract))
    assert result['dataset_sample'] in abstract
    assert result['limitations'] in abstract
    assert result['supporting_evidence'] == []
    assert result['supported_subquestions'] == []
    assert result['question_evidence'] == {}
    assert all(not v or v in abstract for k,v in result.items() if isinstance(v,str))

def test_prioritize_agent_evaluation():
    papers=[{'id':'1','title':'LLM Judges Survey','abstract':'A general survey.'},
            {'id':'2','title':'Reliability Evaluation of LLM Agents','abstract':'We benchmark agent reliability.'}]
    assert rank_papers(papers,['How is agent reliability evaluated?'])[0]['id']=='2'
