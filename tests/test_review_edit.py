"""Regression tests for explicit human editing and review audit records."""
import pytest
from sara.human_review import create_review_request, apply_review_decision
from sara.review_store import save_review, load_review, decide_review

ORIGINAL = 'SUMMARY:\nOriginal [S1]\nCOMPARISON:\nOriginal [S1]\nEVIDENCE_GAPS:\nNone [S1]\nLIMITATIONS:\nLimited [S1]'
EDITED = 'SUMMARY:\nRevised [S1]\nCOMPARISON:\nRevised [S1]\nEVIDENCE_GAPS:\nSome [S1]\nLIMITATIONS:\nLimited [S1]'

@pytest.fixture
def pending():
    return create_review_request('review-42', {'text': ORIGINAL, 'citations': {'S1':'paper-42'}})

def test_review_stores_original(pending):
    assert pending['synthesis']['text'] == ORIGINAL
    assert pending['synthesis']['citations']['S1'] == 'paper-42'

def test_edit_preserves_original(pending):
    out = apply_review_decision(pending, 'EDIT', 'Researcher', 'Clarify limitations', edited_text=EDITED)
    assert out['status'] == 'COMPLETED'
    assert out['decision'] == 'EDIT'
    assert out['synthesis']['text'] == ORIGINAL
    assert out['edited_synthesis'] == EDITED
    assert out['audit_events'][0]['edited'] is True
    assert out['reviewed_at']

def test_edit_persists(tmp_path, pending):
    save_review(pending, tmp_path)
    out = decide_review('review-42', 'EDIT', 'Researcher', 'Correction', directory=tmp_path, edited_text=EDITED)
    assert load_review('review-42', tmp_path) == out

def test_edit_requires_reason(pending):
    with pytest.raises(ValueError):
        apply_review_decision(pending, 'EDIT', 'Researcher', edited_text=EDITED)

def test_edit_requires_text(pending):
    with pytest.raises(ValueError):
        apply_review_decision(pending, 'EDIT', 'Researcher', 'Correction', edited_text=' ')

def test_edit_rejects_unknown_citation(pending):
    with pytest.raises(ValueError):
        apply_review_decision(pending, 'EDIT', 'Researcher', 'Correction', edited_text=EDITED.replace('[S1]', '[S999]'))

def test_edit_rejects_missing_sections(pending):
    with pytest.raises(ValueError):
        apply_review_decision(pending, 'EDIT', 'Researcher', 'Correction', edited_text='SUMMARY:\nRevised [S1]')

def test_edit_cannot_repeat(tmp_path, pending):
    save_review(pending, tmp_path)
    decide_review('review-42', 'EDIT', 'Researcher', 'Correction', directory=tmp_path, edited_text=EDITED)
    with pytest.raises(ValueError):
        decide_review('review-42', 'APPROVE', 'Other', directory=tmp_path)

def test_non_edit_rejects_edited_text(pending):
    with pytest.raises(ValueError):
        apply_review_decision(pending, 'APPROVE', 'Researcher', edited_text=EDITED)

def test_approval_audit(pending):
    out = apply_review_decision(pending, 'APPROVE', 'Researcher')
    assert out['audit_events'][0]['decision'] == 'APPROVE'
    assert out['edited_synthesis'] is None
