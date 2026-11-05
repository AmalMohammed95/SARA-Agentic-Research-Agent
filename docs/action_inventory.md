# SARA V3 - Tool Catalogue and Action Inventory

## 1. Purpose

This document records the tool permissions, execution boundaries,
and human oversight actions in SARA V3.

It describes the inspected implementation in policy.py and executor.py.

## 2. Tool Catalogue

| Tool | Purpose | Arguments | Permission | Side Effects |
|---|---|---|---|---|
| search_openalex | Retrieve scholarly search results from OpenAlex | query: non-empty string; max_results: integer 1-20, default 5 | Read | External network request |
| search_scholarly | Retrieve scholarly search results through Semantic Scholar | query: non-empty string; max_results: integer 1-20, default 5 | Read | External network request |

Both tools are registered in the ALLOWED_TOOLS allowlist.

The inspected executor does not authorize arbitrary shell execution,
local file deletion, database modification, or external message sending.

Tool-specific timeouts, retries, and rate limits require separate
inspection of tools.py and related retrieval modules; they are not
established by policy.py and executor.py alone.

## 3. Execution and Validation Boundary

The controlled execution sequence is:

1. The agent proposes a tool request.
2. validate_tool_call() checks the tool name and arguments.
3. Unauthorized requests are rejected.
4. execute_tool() dispatches the validated request.
5. Results or execution failures are returned as structured data.

Tool requests may return:

- COMPLETED: The validated tool execution returned successfully.
- REJECTED: Tool name or arguments failed policy validation.
- FAILED_SAFELY: Tool execution raised an exception or could not be dispatched.

COMPLETED describes tool execution, not scientific correctness
or the relevance of the retrieved results.

## 4. Action Inventory

| Action | Consequence | Reversible? | Oversight |
|---|---|---|---|
| Receive a research question | Starts a research workflow | Yes | User initiated |
| Generate a research plan | Changes proposed research direction | Yes | Automated, bounded |
| Submit scholarly search queries | Uses external retrieval services | Request cannot be undone; local results can be discarded | Automated, policy validated |
| Screen retrieved papers | Influences selected evidence | Yes, through review or rerun | Automated, subject to evaluation |
| Extract and verify evidence | Produces preliminary research evidence | Yes, through correction or exclusion | Automated validation; human review when needed |
| Replan research | Changes search strategy | Yes | Automated, bounded |
| Produce a research report | Creates a research output | Yes, through revision | Human review may be required |
| Approve, reject, or request revision | Changes a human-review decision record | Decision is controlled and not freely repeatable | Explicit human decision |

Human-review operations are application workflows, not tools
registered in ALLOWED_TOOLS.

## 5. Authority Boundaries

- The LLM is a decision component, not an execution authority.
- Only allowlisted tools can execute through the controlled executor.
- Tool arguments are checked before dispatch.
- Scholarly retrieval does not grant permission to modify local records.
- Retrieved academic content is external data, not trusted instructions.
- Human-review decisions require the appropriate review workflow.

## 6. Verified Controls

The project's offline adversarial test suite demonstrated:

- Rejection of unauthorized tool names.
- Rejection of invalid tool arguments.
- Preservation of a malicious abstract as source data at the tool boundary.
- Safe reporting of simulated network failure.

The 18 tests in test_security_adversarial.py passed.

These tests do not establish comprehensive end-to-end
prompt-injection resistance.

## 7. Limitations

- The inspected tool layer does not establish full user-level access control.
- External services may fail or enforce rate limits.
- Tool authorization does not guarantee scientific evidence quality.
- Complete timeout and retry policies must be verified separately.
- Human oversight is not a substitute for independent source validation.

## 8. Implementation References

- src/sara/policy.py
- src/sara/executor.py
- src/sara/tools.py
- src/sara/human_review.py
- src/sara/review_store.py
- tests/test_policy.py
- tests/test_security_adversarial.py
- tests/test_human_review.py

This inventory is limited to the capabilities established by
the inspected architecture and existing test evidence.
