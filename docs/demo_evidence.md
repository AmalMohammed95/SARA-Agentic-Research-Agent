# SARA V3 — COSC726 Demonstration Evidence

## 1. Real Planning and Replanning
Run ID: 9c469714-4587-408f-8775-31e0a386e0e8

- Three agent iterations.
- Two validated and applied replanning attempts.
- Revised search queries were executed.
- Eight studies retrieved in the third iteration.
- Final status: INSUFFICIENT_EVIDENCE.
- Demonstrates bounded planning, replanning, evidence evaluation, and safe termination.

## 2. Human Oversight
Controlled review using an isolated copy of an existing review record.

- Before: WAITING_FOR_APPROVAL
- Human decision: REQUEST_REVISION
- After: WAITING_FOR_REVISION
- Reviewer recorded.
- One audit event recorded.
- Original review record unchanged.

## 3. Adversarial and Security Tests
Command: python -m pytest tests/test_security_adversarial.py -v

Result: 18 passed.

Coverage:
- Unauthorized tool rejection.
- Invalid argument rejection.
- Untrusted abstract handling.
- Safe handling of simulated network failure.

## 4. Synthesis Integration Tests
Command: python -m pytest tests/test_synthesis_integration.py -v

Result: 4 passed.

Coverage:
- Structurally valid synthesis routed to human approval.
- Invalid citation escalated.
- Model failure handled safely.
- Review request persisted.

These tests use mocked model, tool, and evidence-sufficiency components.

## 5. Evidence Limitations
- No live end-to-end research run has yet demonstrated complete
  evidence sufficiency and successful scientific synthesis.
- A structurally valid synthesis is not equivalent to a
  scientifically verified research report.
- Adversarial unit tests do not establish comprehensive
  prompt-injection resistance.
- Human approval remains necessary for research outputs.
