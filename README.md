# SARA: Smart Academic Research Agent

SARA (Smart Academic Research Agent) is a bounded Agentic AI system designed to support structured academic literature review tasks.

## Problem Definition

Academic literature reviews require researchers to perform several connected tasks, including formulating search queries, retrieving relevant scholarly papers, screening results, extracting evidence, identifying evidence gaps, and deciding whether additional research is required.

A simple Large Language Model response is not sufficient for this task because the system must interact with external scholarly sources, maintain research state, evaluate the available evidence, revise its search strategy when necessary, and stop or request human review when reliable evidence cannot be obtained.

## Goal

SARA helps researchers conduct structured literature reviews by planning academic searches, retrieving and screening scholarly papers, extracting and organizing evidence, evaluating evidence sufficiency, and revising the research strategy when necessary, while preserving provenance, operating within bounded autonomy, and escalating uncertain or unsupported cases for human review.
## Success Contract

SARA is considered successful when it:

- retrieves scholarly information relevant to the research question;
- screens papers using explicit inclusion and exclusion criteria;
- preserves the provenance of retrieved evidence;
- links supported findings to verifiable scholarly evidence;
- uses only registered tools with validated arguments;
- identifies insufficient, missing, uncertain, or conflicting evidence;
- performs additional search or replanning only within defined limits;
- terminates with an explicit and meaningful status;
- requests human review when reliable autonomous completion is not possible;
- records observable actions, tool usage, evidence, and final status for later evaluation.

The system will later be evaluated using multiple dimensions, including task success, retrieval and screening quality, evidence support, tool correctness, termination behaviour, latency, and resource usage.
## PEAS Analysis

### Performance
- Relevant scholarly evidence is retrieved for the research question.
- Papers are screened according to defined inclusion and exclusion criteria.
- Extracted findings remain linked to their scholarly sources.
- Evidence gaps and uncertainty are identified.
- The agent replans only when justified and within defined limits.
- The system terminates safely with an explicit status.
- Cases requiring academic judgement or unsupported conclusions are escalated for human review.

### Environment
- Researcher or student using SARA.
- Academic research questions and sub-questions.
- Public scholarly metadata and abstracts.
- Scholarly search services such as OpenAlex and, where available, Semantic Scholar.
- Local Large Language Model served through Ollama.
- Local application state, research memory, logs, and evaluation data.

### Actuators
SARA can:
- formulate and revise academic search queries;
- call authorised scholarly search tools;
- screen retrieved papers;
- extract and organise evidence;
- update research state;
- identify evidence gaps;
- request additional searches within a defined budget;
- produce supported research findings;
- stop safely or request human review.

### Sensors
SARA can observe:
- the user's research question;
- research sub-questions and search criteria;
- scholarly search results;
- paper metadata and available abstracts;
- tool success or failure responses;
- screening and extraction results;
- current research state;
- evidence coverage and identified gaps;
- previous actions within the current research run.
## System Architecture

SARA follows a modular Agentic AI architecture that separates research coordination, model interaction, scholarly retrieval, evidence processing, execution control, and human oversight.

The system is organized into the following components:

| Component | Source File | Responsibility |
|---|---|---|
| Agent Controller | `agent.py` | Coordinates the research workflow and agent execution loop. |
| Baseline | `baseline.py` | Provides a baseline implementation for comparison. |
| Model Interface | `model.py` | Handles communication with the language model. |
| Behaviour Specification | `prompts.py` | Defines model instructions and behavioural constraints. |
| Scholarly Tools | `tools.py` | Provides access to scholarly information sources. |
| Policy Validation | `policy.py` | Checks proposed tool actions against execution rules. |
| Tool Executor | `executor.py` | Manages the execution of permitted tool calls. |
| Structured Schemas | `schemas.py` | Defines and validates structured information. |
| Screening | `screening.py` | Supports relevance screening of retrieved papers. |
| Evidence Extraction | `extraction.py` | Processes evidence extracted from scholarly sources. |
| Evidence Evaluation | `evidence.py` | Evaluates evidence sufficiency, provenance, and identified gaps. |
| Replanning | `replanning.py` | Supports revision of research plans when necessary. |
| Research State | `state.py` | Maintains information about the current research workflow. |
| Synthesis | `synthesis.py` | Organizes research findings into a structured output. |
| Human Oversight | `human_review.py` | Supports human review of findings requiring oversight. |
| Review Persistence | `review_store.py` | Stores and retrieves review information. |
| Observability | `tracing.py` | Records observable execution events for inspection and evaluation. |

### Architectural Principles

SARA is designed around the following principles:

- **Bounded autonomy:** Agent execution is constrained by predefined limits.
- **Controlled tool use:** Model-proposed tool actions are subject to application-level validation.
- **Evidence provenance:** Research findings should remain traceable to their scholarly sources.
- **Human oversight:** Findings requiring human judgement can be submitted for review.
- **Modular design:** Research processing, model interaction, validation, and execution responsibilities are separated.
- **Observable execution:** Execution events are recorded to support debugging and evaluation.

The language model is treated as a component of the agentic system rather than as the complete agent.
## Agent Loop and Planning

SARA implements a bounded research-agent loop coordinated by `run_agent()` in `agent.py`.

The agent processes a research question through iterative research activities, including scholarly search, evidence processing, evidence sufficiency assessment, and conditional replanning.

### Execution Limits

The implementation defines the following execution controls:

| Parameter | Value | Purpose |
|---|---|---|
| Default maximum agent turns | 3 | Limits the number of research iterations. |
| Maximum replanning attempts | 2 | Prevents unlimited research-plan revisions. |
| Maximum extractions per turn | 5 | Restricts the number of evidence extraction operations within a turn. |
| Search results per request | 10 | Limits the number of results requested in the identified search call. |

The main execution loop uses the condition `while turn < max_turns`, ensuring that the number of iterations does not exceed the configured turn limit.

The implementation also validates that `max_turns` is a positive integer before entering the loop.

### Replanning Control

Replanning is controlled through the `can_replan()` function in `replanning.py`.

Another replanning attempt is permitted only when:

- The current execution has remaining turns.
- The number of replanning attempts is below the configured maximum of two.

The replanning module also provides `build_replanning_context()`, which accepts the current search keywords and identified evidence gaps.

These controls limit repeated research attempts and prevent unrestricted replanning.

### Bounded Autonomy

SARA does not rely on an unrestricted execution loop. Its research iterations and replanning attempts are subject to explicit application-level limits.

This design supports predictable execution and reduces the risk of uncontrolled repeated searches.
## Termination States and Failure Handling

SARA implements explicit execution states and controlled failure-handling mechanisms to prevent unrestricted agent execution and unsupported research conclusions.

### Terminal States

SARA explicitly defines seven terminal states in the `TERMINAL_STATES` collection in `agent.py`.

| Terminal State | Description |
|---|---|
| `COMPLETED` | The agent has successfully completed the research workflow. |
| `BLOCKED` | Execution is blocked by an applicable constraint or policy. |
| `ESCALATED` | The workflow has been escalated for further review. |
| `WAITING_FOR_APPROVAL` | The workflow is paused pending human approval. |
| `INSUFFICIENT_EVIDENCE` | Available evidence is insufficient to support reliable completion. |
| `BUDGET_EXHAUSTED` | The execution budget has been exhausted. |
| `FAILED_SAFELY` | The agent has stopped safely following an error or validation failure. |

The `REPLANNING` state is transitional and is not included in `TERMINAL_STATES`.

The implementation checks the agent's final status against this collection. If execution ends without a recognized terminal status, it assigns `BUDGET_EXHAUSTED` and records the corresponding stopping reason.

These explicit states allow the system to distinguish successful completion, insufficient evidence, human oversight, blocked execution, and operational failure.
### Failure Handling

The agent implements several safety controls:

- Rejects empty research questions and invalid execution limits.
- Stops safely when the initial research plan fails validation.
- Stops when no valid search keywords remain.
- Handles unsuccessful scholarly search operations.
- Identifies insufficient evidence and unavailable search alternatives.
- Restricts repeated replanning through predefined limits.
- Escalates findings when synthesis validation fails.
- Supports human approval before finalizing findings requiring review.
- Records stopping reasons to explain why execution ended.

### Budget Exhaustion

The main agent loop is bounded by the configured maximum number of turns.

If execution ends without reaching a recognized terminal state, the agent assigns `BUDGET_EXHAUSTED` and records the reason as:

`Maximum number of agent turns reached.`

### Safe Research Behaviour

SARA distinguishes between insufficient scholarly evidence and operational failure.

The system is designed to avoid treating unsupported or incomplete research findings as verified conclusions. Where automated validation cannot establish an acceptable result, the agent can stop safely or initiate human oversight.

These mechanisms support controlled execution, traceability, and responsible use of Agentic AI in academic research.
## Tools, Permissions, and Execution Safety

SARA implements a controlled tool-execution architecture that separates language-model decisions from authorized tool execution.

### Registered Tools

The current implementation permits one external scholarly retrieval tool:

| Tool | Source | Purpose |
|---|---|---|
| `search_openalex` | `tools.py` | Retrieves scholarly publication information from OpenAlex. |

The tool is explicitly registered in the `ALLOWED_TOOLS` collection in `policy.py`.

### Tool Validation

Before a proposed tool call is executed, SARA applies the `validate_tool_call()` function.

The validation process checks:

- Whether the requested tool belongs to the allowed-tool collection.
- Whether the supplied arguments are structured as a dictionary.
- Whether the OpenAlex search query is non-empty.
- Whether `max_results` is an integer between 1 and 20.

Requests that fail validation are rejected.

### Controlled Execution

The `execute_tool()` function in `executor.py` applies the policy validation layer before executing an authorized tool.

If validation fails, the executor returns a `REJECTED` status rather than executing the requested operation.

This separation ensures that the language model cannot directly invoke arbitrary tools through the application's controlled execution interface.

### Security and Safety Principles

The tool-execution design follows these principles:

- **Allowlist-based access:** Only explicitly registered tools may be executed.
- **Argument validation:** Tool inputs must satisfy defined constraints.
- **Separation of responsibilities:** Tool authorization is handled independently of model-generated decisions.
- **Controlled scholarly retrieval:** The authorized external retrieval capability is limited to OpenAlex search.
- **Explicit rejection:** Invalid or unauthorized requests are rejected before execution.

These controls reduce the risk of unauthorized tool use and support bounded agent autonomy.
## Memory, State, and Observability

SARA separates the working state of an individual research run from the persistent storage of human review records.

### Research State Management

The `AgentState` dataclass in `state.py` maintains the working state of a single SARA research execution.

It stores:

- Research question and unique execution identifier.
- Current iteration, replanning attempts, and per-paper extraction attempts.
- Research subquestions and search keywords.
- Retrieved, selected, and excluded scholarly papers.
- Extracted evidence and identified research gaps.
- Current execution status and stopping reason.

The initial execution status is `INITIALIZED`.

This state represents observable research progress rather than private language-model reasoning. It provides working memory within an individual research run; persistent storage of the complete agent state across runs has not been established by the inspected implementation.

### Execution Tracing

The `tracing.py` module provides two functions:

- `create_run_id()` generates a unique identifier for a research execution.
- `create_trace_event()` constructs structured events for observing agent execution.

Run identifiers and structured trace events support the inspection and evaluation of research workflows.

### Persistent Human Review Records

The `review_store.py` module implements JSON-based persistence for human review requests and decisions.

The module provides:

- `save_review()` to save a review record.
- `load_review()` to retrieve a previously saved review.
- `decide_review()` to apply a human review decision and save the updated record.

By default, review records are stored in the `data/reviews` directory, with each record associated with a run identifier.

### Review Record Validation

The review storage module validates run identifiers before constructing file paths.

It also verifies that a loaded review record matches the requested run identifier.

These checks support consistent review retrieval and reduce the risk of invalid file-path construction.

### Observability and Auditability

SARA provides structured execution tracing and persistent review records as separate mechanisms.

Together, these components support research workflow inspection, human oversight, and subsequent evaluation.
## Installation and Usage

### Requirements

- Python with a virtual environment
- Ollama installed locally
- Ollama model: `qwen2.5:7b`
- Internet access for OpenAlex research searches

### Installation (Windows PowerShell)

From the project root directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:7b
```

Ensure the Ollama service is running and the model is available locally.

### Run the Application

```powershell
streamlit run app.py
```

In the Streamlit interface, enter a research question, select the maximum number of agent turns (1–3), and click **Run Research Agent**.

### Run Automated Tests

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -q
```

The latest local test run completed successfully: **84 passed**. This verifies the automated test suite, not the scientific sufficiency of every research result.
## Evaluation and Limitations

### Evaluation Design

SARA is evaluated against a non-agentic academic search baseline using a frozen set of five research questions (E01–E05), stored in `evaluation/research_questions.csv`.

The comparison considers execution status, runtime, evidence support, and research workflow behavior. The baseline performs a simpler search and screening process, whereas SARA uses bounded agentic execution, evidence verification, and explicit termination conditions.

### Recorded Evaluation Results

The following results were recorded for evaluation case E01:

**Research question:** How is deep learning used for leukemia detection in peripheral blood smear images?

| Metric | Baseline | SARA |
|---|---|---|
| Execution status | COMPLETED | INSUFFICIENT_EVIDENCE |
| Duration (seconds) | 1.328 | 2695.436 |
| Execution exception | None | None |

The baseline retrieved and included five papers. SARA completed its bounded execution without a reported exception but did not satisfy its evidence-sufficiency criteria.

These results represent one recorded evaluation case and should not be interpreted as a complete five-case performance comparison.

### Limitations

- **Execution cost:** Local CPU-based LLM inference can substantially increase execution time.
- **Evidence sufficiency:** Retrieved papers and extracted claims may not satisfy strict evidence-verification requirements.
- **Evaluation coverage:** The documented E01 result does not establish performance across all five frozen evaluation cases.
- **External dependency:** Academic search requires access to OpenAlex, while local model execution depends on Ollama availability.
- **Model sensitivity:** Extraction quality and agent decisions may vary with the local language model.

### Testing and Reproducibility

The latest automated test run completed with **84 passing tests**.

To run the tests:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -q
```

Evaluation artifacts are stored in the `evaluation/` directory. The recorded E01 comparison is available in `evaluation/comparison_results_batch_v1.json`.

Passing software tests demonstrates that the tested components behave as expected; it does not independently establish research accuracy, evidence sufficiency, or scientific superiority.

### Evaluation Conclusion

SARA demonstrates an implemented agentic research workflow with bounded execution, evidence verification, human oversight, and explicit failure handling. The recorded E01 experiment highlights a trade-off between research workflow complexity, strict evidence requirements, and execution cost.

Further evaluation across the frozen research questions is required before making broader claims about comparative performance.