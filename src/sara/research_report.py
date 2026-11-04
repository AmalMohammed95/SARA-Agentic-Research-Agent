"""Conservative audit of sourced claims, separate from metadata completion."""
from collections import Counter

FIELDS = ('objective', 'methodology', 'dataset_sample', 'findings', 'limitations')


def build_evidence_audit(selected_papers, evidence, decision):
    indexed = {}
    for paper in selected_papers:
        for key in (paper.get('doi'), paper.get('id')):
            if key:
                indexed[str(key)] = paper
    supported, unverified = [], []
    sources = Counter()
    for rec in evidence:
        if rec.get('extraction_status') != 'completed':
            continue
        key = str(rec.get('paper_id') or '')
        if key not in indexed:
            continue
        scope = rec.get('evidence_source_scope') or 'abstract_only'
        sources[scope] += 1
        valid = (rec.get('claim_support_status') == 'supported' and
                 bool(rec.get('supporting_evidence')) and bool(rec.get('source_spans')) and
                 bool(rec.get('supported_subquestions')))
        item = {'paper_id': key, 'title': indexed[key].get('title', ''),
                'source_scope': scope, 'source_url': rec.get('evidence_source_url'),
                'supported_questions': list(rec.get('supported_subquestions') or []) if valid else [],
                'quotes': list(rec.get('supporting_evidence') or []) if valid else [],
                'field_availability': rec.get('field_availability', {})}
        (supported if valid else unverified).append(item)
    coverage = decision.get('subquestion_coverage') or {}
    return {
        'report_type': 'PRELIMINARY_EVIDENCE_AUDIT',
        'research_coverage_met': bool(coverage) and all(v >= 2 for v in coverage.values()) and
            decision.get('unique_relevant_studies', 0) >= decision.get('required_studies', 5),
        'metadata_quality_met': decision.get('missing_field_rate', 1.0) <= .2,
        'ready_for_synthesis': bool(decision.get('sufficient')),
        'requires_human_review': True,
        'source_distribution': dict(sources),
        'subquestion_coverage': coverage,
        'missing_metadata_by_field': decision.get('missing_by_field', {}),
        'missing_metadata_rate': decision.get('missing_field_rate'),
        'supported_quote_records': supported,
        'unverified_records': unverified,
        'limitations': ['Model judgments are provisional, not independent fact verification.',
                        'Full text was not accessed for all papers unless individually indicated.',
                        'No missing metadata was inferred or manufactured.',
                        'Human source review is required before academic reliance.'],
    }
