import json
from sara.source_enrichment import enrich_papers, obtain_open_text
from sara.deterministic_evidence import extract_open_text_json
from sara.research_report import build_evidence_audit


def test_open_access_text_fallback_is_honest():
    def broken(_):
        raise OSError('not available')
    paper = {'doi': 'https://doi.org/10.48550/arxiv.2407.01231', 'abstract': 'Study abstract'}
    result = enrich_papers([paper], fetch=broken)
    assert result[0]['abstract'] == paper['abstract']
    assert result[0]['source_scope'] == 'abstract_only'
    assert result[0]['source_url'] is None


def test_unapproved_hosts_never_called():
    calls = []
    def fake(url):
        calls.append(url)
        return b''
    result = obtain_open_text({'doi':'https://evil.test/paper', 'abstract':'x'}, fetch=fake)
    assert result['source_scope'] == 'abstract_only'
    assert calls == []


def test_rich_source_extraction_is_verbatim_without_duplication():
    sample = '''Methods
We evaluated 120 tasks using repeated trials of LLM agents.
Results
Results showed higher agreement across repeated agent runs.
Limitations
A limitation is that the evaluation relies on a single dataset.
Introduction
We introduce an evaluation protocol for agent reliability.'''
    result = json.loads(extract_open_text_json(sample))
    spans = [result[k] for k in ('objective','methodology','dataset_sample','findings','limitations') if result[k]]
    assert len(spans) == len(set(spans))
    assert all(span in sample for span in spans)
    assert result['findings'].startswith('Results showed')
    assert result['limitations'].startswith('A limitation')


def test_audit_does_not_claim_completion_when_metadata_missing():
    papers = [{'doi':'p1','title':'Example'}]
    records = [{'paper_id':'p1','extraction_status':'completed',
                'claim_support_status':'supported','supporting_evidence':['Quoted source.'],
                'source_spans':[{'quote':'Quoted source.'}],
                'supported_subquestions':['q'],'evidence_source_scope':'abstract_only'}]
    check = {'subquestion_coverage':{'q':3},'unique_relevant_studies':6,
             'required_studies':5,'missing_field_rate':.42,'sufficient':False}
    audit = build_evidence_audit(papers, records, check)
    assert audit['research_coverage_met'] is True
    assert audit['metadata_quality_met'] is False
    assert audit['ready_for_synthesis'] is False
    assert audit['requires_human_review'] is True
