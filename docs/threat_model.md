# SARA V3 — Threat Model and Responsible Engineering

## 1. Scope

This document describes the security boundaries, relevant threats,
existing controls, and residual risks of the SARA academic research agent.

SARA retrieves scholarly information, uses language models for research
processing, validates tool requests, maintains execution state, and
supports human review.

## 2. Protected Assets

- Integrity of retrieved academic evidence and source provenance.
- Accuracy of research outputs and reported verification status.
- Model provider credentials and service configuration.
- Locally stored human-review records.
- Execution traces and research questions.
- Availability of scholarly retrieval and model services.

## 3. Threat Actors and Sources

- Malicious content embedded in retrieved scholarly text.
- Users attempting unauthorized tool execution.
- Invalid or manipulated model-generated tool arguments.
- Unauthorized access to locally stored review information.
- External service failures, rate limits, and malformed responses.

## 4. Trust Boundaries

1. User input enters the agent through the application interface.
2. Model-generated decisions cross into application-controlled validation.
3. Tool requests pass through policy validation before execution.
4. External scholarly content enters as untrusted source data.
5. Evidence must be checked before being treated as supported.
6. Human-review records cross a local persistence boundary.

The language model is not granted direct authority to execute
arbitrary system commands through SARA's controlled tool executor.

## 5. Threats, Controls, and Evidence

| Threat | Existing control | Verification |
|---|---|---|
| Unauthorized tool request | Tool allowlist and policy validation | Tested |
| Invalid tool arguments | Argument validation before dispatch | Tested |
| Network failure | Explicit FAILED_SAFELY response | Tested |
| Malicious abstract content | Treated as data by the tool executor | Partially tested |
| Unsupported research claims | Evidence validation and insufficient-evidence states | Tested within defined scenarios |
| Repeated or unproductive execution | Bounded turns and progress controls | Tested within defined scenarios |
| Invalid human-review decision | Decision validation and duplicate-decision prevention | Tested |
| Credential exposure | Requires secure environment configuration and operational controls | Not independently audited |
| Unauthorized review-file access | Local storage requires operating-system access controls | Not independently tested |
| End-to-end prompt injection | No complete end-to-end resistance demonstrated | Not established |

## 6. Privacy Considerations

SARA processes research questions and retrieved scholarly materials.
Human-review records are stored locally in JSON files.

Hosted model use may transmit prompt content to the configured model
provider. Deployment must therefore consider applicable provider
policies and avoid submitting confidential information without authorization.

The inspected implementation does not establish complete multi-user
isolation, encryption-at-rest, or a formal data-retention and deletion policy.
These protections must not be claimed as verified.

## 7. Residual Risks

- Prompt injection may influence model decisions despite tool restrictions.
- Retrieved information may be incomplete, misleading, or incorrectly classified.
- Source availability and external API quotas may affect research coverage.
- Local review storage requires appropriate filesystem permissions.
- Scientific correctness has not been independently established for every
  extracted claim.
- Repeated-run consistency and comprehensive adversarial coverage
  remain unverified.

## 8. Human Oversight and Safe Failure

SARA provides human-review workflows supporting approval, rejection,
and revision requests.

The system distinguishes successful execution from insufficient evidence
and operational failures.

A status of INSUFFICIENT_EVIDENCE is not a claim that the research
question has no answer. It indicates that the available evidence did
not satisfy the configured acceptance requirements.

## 9. Verification Evidence

- tests/test_security_adversarial.py: 18 tests passed.
- tests/test_human_review.py, tests/test_agent_failures.py,
  tests/test_policy.py: 28 tests passed in an isolated test environment.
- The frozen E01-E05 SARA V3 benchmark recorded five
  INSUFFICIENT_EVIDENCE outcomes without recorded exceptions.

The automated tests establish behavior only within their tested
scenarios. They do not establish comprehensive security assurance.

## 10. Risk Treatment

For the COSC726 capstone, the approach is to retain bounded autonomy,
document residual risks, avoid unsupported security claims, and require
human review where scientific evidence or consequential decisions
cannot be accepted automatically.

Production deployment would require additional access-control,
privacy, credential-handling, and end-to-end adversarial assessments.
