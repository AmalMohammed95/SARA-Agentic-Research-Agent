SARA: Smart Academic Research Agent
SARA (Smart Academic Research Agent) is a bounded Agentic AI system designed to support structured academic literature review tasks.
Marker Navigation — Clean-Machine Run Order
Follow the sections below in the order required by the COSC726 submission brief. The detailed architecture and safety rationale are retained in the rest of this document.
What it does: Introduction and Problem Definition.
Prerequisites: Requirements under Installation and Usage.
Install: Installation (Windows PowerShell), beginning with `git clone`.
Configure: `.env.example` discussion and Optional Semantic Scholar API Configuration; provider selection is explained under Run the Application.
Run: Run the Application (SARA V3).
Test: Run Automated Tests (no model inference or API keys needed).
Worked example: Worked Example — Leukemia Detection (E01 topic).
Reproduce evaluation: Reproducing the Recorded Evaluation Analysis and Separate V3 Evaluation Snapshot.
Approval gate: Human Approval Gate, including controlled tests.
Repository map: Repository Map.
Limitations: Limitations and Evaluation Conclusion.
Problem Definition
Academic literature reviews require researchers to perform several connected tasks, including formulating search queries, retrieving relevant scholarly papers, screening results, extracting evidence, identifying evidence gaps, and deciding whether additional research is required.
A simple Large Language Model response is not sufficient for this task because the system must interact with external scholarly sources, maintain research state, evaluate the available evidence, revise its search strategy when necessary, and stop or request human review when reliable evidence cannot be obtained.
Goal
SARA helps researchers conduct structured literature reviews by planning academic searches, retrieving and screening scholarly papers, extracting and organizing evidence, evaluating evidence sufficiency, and revising the research strategy when necessary, while preserving provenance, operating within bounded autonomy, and escalating uncertain or unsupported cases for human review.
Success Contract
SARA is considered successful when it:
retrieves scholarly information relevant to the research question;
screens papers using explicit inclusion and exclusion criteria;
preserves the provenance of retrieved evidence;
links supported findings to verifiable scholarly evidence;
uses only registered tools with validated arguments;
identifies insufficient, missing, uncertain, or conflicting evidence;
performs additional search or replanning only within defined limits;
terminates with an explicit and meaningful status;
requests human review when reliable autonomous completion is not possible;
records observable actions, tool usage, evidence, and final status for later evaluation.
The system was evaluated on five frozen research questions using baseline and SARA workflows; execution status, evidence diagnostics, runtime, and tested control behavior are reported below. Scientific accuracy was not independently validated.
PEAS Analysis
Performance
Relevant scholarly evidence is retrieved for the research question.
Papers are screened according to defined inclusion and exclusion criteria.
Extracted findings remain linked to their scholarly sources.
Evidence gaps and uncertainty are identified.
The agent replans only when justified and within defined limits.
The system terminates safely with an explicit status.
Cases requiring academic judgement or unsupported conclusions are escalated for human review.
Environment
Researcher or student using SARA.
Academic research questions and sub-questions.
Public scholarly metadata and abstracts.
Scholarly search services such as OpenAlex and, where available, Semantic Scholar.
Language model provided through Ollama (default) or Google Gemini (configured provider).
Local application state, research memory, logs, and evaluation data.
Actuators
SARA can:
formulate and revise academic search queries;
call authorised scholarly search tools;
screen retrieved papers;
extract and organise evidence;
update research state;
identify evidence gaps;
request additional searches within a defined budget;
produce supported research findings;
stop safely or request human review.
Sensors
SARA can observe:
the user's research question;
research sub-questions and search criteria;
scholarly search results;
paper metadata and available abstracts;
tool success or failure responses;
screening and extraction results;
current research state;
evidence coverage and identified gaps;
previous actions within the current research run.
System Architecture
SARA follows a modular Agentic AI architecture that separates research coordination, model interaction, scholarly retrieval, evidence processing, execution control, and human oversight.
The system is organized into the following components:
Component	Source File	Responsibility
Agent Controller	`agent.py`	Coordinates the research workflow and agent execution loop.
Baseline	`baseline.py`	Provides a baseline implementation for comparison.
Model Interface	`model.py`	Handles communication with the language model.
Behaviour Specification	`prompts.py`	Defines model instructions and behavioural constraints.
Scholarly Tools	`tools.py`	Provides access to scholarly information sources.
Policy Validation	`policy.py`	Checks proposed tool actions against execution rules.
Tool Executor	`executor.py`	Manages the execution of permitted tool calls.
Structured Schemas	`schemas.py`	Defines and validates structured information.
Screening	`screening.py`	Supports relevance screening of retrieved papers.
Evidence Extraction	`extraction.py`	Processes evidence extracted from scholarly sources.
Evidence Evaluation	`evidence.py`	Evaluates evidence sufficiency, provenance, and identified gaps.
Search Strategy	`search_strategy.py`	Supports research-query selection and search diversification.
Source-First Processing	`source_first.py`	Supports evidence processing grounded in available source material.
Source Enrichment	`source_enrichment.py`	Retrieves additional accessible scholarly text where available.

Deterministic Evidence	`deterministic_evidence.py`	Extracts source-grounded evidence using deterministic processing.
Evidence Orchestration	`evidence_orchestrator.py`	Coordinates evidence-processing operations.
Research Report	`research_report.py`	Builds structured research and evidence-audit output.
Topic Guard	`topic_guard.py`	Supports preservation of research-topic scope.
Replanning	`replanning.py`	Supports revision of research plans when necessary.
Research State	`state.py`	Maintains information about the current research workflow.
Synthesis	`synthesis.py`	Organizes research findings into a structured output.
Human Oversight	`human_review.py`	Supports human review of findings requiring oversight.
Review Persistence	`review_store.py`	Stores and retrieves review information.
Observability	`tracing.py`	Records observable execution events for inspection and evaluation.
Architectural Principles
SARA is designed around the following principles:
Bounded autonomy: Agent execution is constrained by predefined limits.
Controlled tool use: Model-proposed tool actions are subject to application-level validation.
Evidence provenance: Research findings should remain traceable to their scholarly sources.
Human oversight: Findings requiring human judgement can be submitted for review.
Modular design: Research processing, model interaction, validation, and execution responsibilities are separated.
Observable execution: Execution events are recorded to support debugging and evaluation.
The language model is treated as a component of the agentic system rather than as the complete agent.
Agent Loop and Planning
SARA implements a bounded research-agent loop coordinated by `run_agent()` in `agent.py`.
The agent processes a research question through iterative research activities, including scholarly search, evidence processing, evidence sufficiency assessment, and conditional replanning.
Execution Limits
The implementation defines the following execution controls:
Parameter	Value	Purpose
Default maximum agent turns	3	Limits the number of research iterations.
Maximum replanning attempts	2	Prevents unlimited research-plan revisions.
Evidence extraction limit	5 by default; 20 in extractive mode; configurable up to 30	Controls the bounded number of evidence extractions. V3 evaluation used 24.
Search results per query	10 by default; maximum 10	Limits retrieved results per query. V3 evaluation used 8.
The main execution loop uses the condition `while turn < max_turns`, ensuring that the number of iterations does not exceed the configured turn limit.
The implementation also validates that `max_turns` is a positive integer before entering the loop.
Replanning Control
Replanning is controlled through the `can_replan()` function in `replanning.py`.
Another replanning attempt is permitted only when:
The current execution has remaining turns.
The number of replanning attempts is below the configured maximum of two.
The replanning module also provides `build_replanning_context()`, which accepts the current search keywords and identified evidence gaps.
These controls limit repeated research attempts and prevent unrestricted replanning.
Bounded Autonomy
SARA does not rely on an unrestricted execution loop. Its research iterations and replanning attempts are subject to explicit application-level limits.
This design supports predictable execution and reduces the risk of uncontrolled repeated searches.
Termination States and Failure Handling
SARA implements explicit execution states and controlled failure-handling mechanisms to prevent unrestricted agent execution and unsupported research conclusions.
Terminal States
SARA explicitly defines seven terminal states in the `TERMINAL_STATES` collection in `agent.py`.
Terminal State	Description
`COMPLETED`	The agent has successfully completed the research workflow.
`BLOCKED`	Execution is blocked by an applicable constraint or policy.
`ESCALATED`	The workflow has been escalated for further review.
`WAITING_FOR_APPROVAL`	The workflow is paused pending human approval.
`INSUFFICIENT_EVIDENCE`	Available evidence is insufficient to support reliable completion.
`BUDGET_EXHAUSTED`	The execution budget has been exhausted.
`FAILED_SAFELY`	The agent has stopped safely following an error or validation failure.
The `REPLANNING` state is transitional and is not included in `TERMINAL_STATES`.
The implementation checks the agent's final status against this collection. If execution ends without a recognized terminal status, it assigns `BUDGET_EXHAUSTED` and records the corresponding stopping reason.
These explicit states allow the system to distinguish successful completion, insufficient evidence, human oversight, blocked execution, and operational failure.
Failure Handling
The agent implements several safety controls:
Rejects empty research questions and invalid execution limits.
Stops safely when the initial research plan fails validation.
Stops when no valid search keywords remain.
Handles unsuccessful scholarly search operations.
Identifies insufficient evidence and unavailable search alternatives.
Restricts repeated replanning through predefined limits.
Escalates findings when synthesis validation fails.
Supports human approval before finalizing findings requiring review.
Records stopping reasons to explain why execution ended.
Budget Exhaustion
The main agent loop is bounded by the configured maximum number of turns.
If execution ends without reaching a recognized terminal state, the agent assigns `BUDGET_EXHAUSTED` and records the reason as:
`Maximum number of agent turns reached.`
Safe Research Behaviour
SARA distinguishes between insufficient scholarly evidence and operational failure.
The system is designed to avoid treating unsupported or incomplete research findings as verified conclusions. Where automated validation cannot establish an acceptable result, the agent can stop safely or initiate human oversight.
These mechanisms support controlled execution, traceability, and responsible use of Agentic AI in academic research.
Tools, Permissions, and Execution Safety
SARA implements a controlled tool-execution architecture that separates language-model decisions from authorized tool execution.
Registered Tools
SARA uses a controlled scholarly search interface that integrates
OpenAlex and Semantic Scholar.
Tool	Source File	Purpose
`search_scholarly`	`tools.py`	Searches OpenAlex and Semantic Scholar, combines results, removes duplicates, and preserves source provenance.
`search_openalex`	`tools.py`	Retrieves scholarly metadata and abstracts from OpenAlex.
Both tools are validated through the allowlist in `policy.py`
before execution by `executor.py`.
Semantic Scholar access is optional and may be affected by
HTTP 429 rate limits. SARA can continue using OpenAlex when
Semantic Scholar is unavailable.
Tool Validation
Before a proposed tool call is executed, SARA applies the `validate_tool_call()` function.
The validation process checks:
Whether the requested tool belongs to the allowed-tool collection.
Whether the supplied arguments are structured as a dictionary.
Whether the scholarly search query is non-empty before executing the authorized search tools.
Whether `max_results` is an integer between 1 and 20.
Requests that fail validation are rejected.
Controlled Execution
The `execute_tool()` function in `executor.py` applies the policy validation layer before executing an authorized tool.
If validation fails, the executor returns a `REJECTED` status rather than executing the requested operation.
This separation ensures that the language model cannot directly invoke arbitrary tools through the application's controlled execution interface.
Security and Safety Principles
The tool-execution design follows these principles:
Allowlist-based access: Only explicitly registered tools may be executed.
Argument validation: Tool inputs must satisfy defined constraints.
Separation of responsibilities: Tool authorization is handled independently of model-generated decisions.
Controlled scholarly retrieval: The authorized external retrieval capability is limited to scholarly searches through OpenAlex and Semantic Scholar, subject to the configured tool allowlist and execution policies.
Explicit rejection: Invalid or unauthorized requests are rejected before execution.
These controls reduce the risk of unauthorized tool use and support bounded agent autonomy.
Memory, State, and Observability
SARA separates the working state of an individual research run from the persistent storage of human review records.
Research State Management
The `AgentState` dataclass in `state.py` maintains the working state of a single SARA research execution.
It stores:
Research question and unique execution identifier.
Current iteration, replanning attempts, and per-paper extraction attempts.
Research subquestions and search keywords.
Retrieved, selected, and excluded scholarly papers.
Extracted evidence and identified research gaps.
Current execution status and stopping reason.
The initial execution status is `INITIALIZED`.
This state represents observable research progress rather than private language-model reasoning. It provides working memory within an individual research run; persistent storage of the complete agent state across runs has not been established by the inspected implementation.
Execution Tracing
The `tracing.py` module provides two functions:
`create_run_id()` generates a unique identifier for a research execution.
`create_trace_event()` constructs structured events for observing agent execution.
Run identifiers and structured trace events support the inspection and evaluation of research workflows.
Persistent Human Review Records
The `review_store.py` module implements JSON-based persistence for human review requests and decisions.
The module provides:
`save_review()` to save a review record.
`load_review()` to retrieve a previously saved review.
`decide_review()` to apply a human review decision and save the updated record.
By default, review records are stored in the `data/reviews` directory, with each record associated with a run identifier.
Review Record Validation
The review storage module validates run identifiers before constructing file paths.
It also verifies that a loaded review record matches the requested run identifier.
These checks support consistent review retrieval and reduce the risk of invalid file-path construction.
Observability and Auditability
SARA provides structured execution tracing and persistent review records as separate mechanisms.
Together, these components support research workflow inspection, human oversight, and subsequent evaluation.
Installation and Usage
Requirements
SARA was developed and tested in the following local environment:
Python 3.13.7
Windows with PowerShell
Git for cloning the repository
Ollama installed and running locally
Ollama model: `qwen2.5:7b` (approximately 4.7 GB)
Internet access for scholarly retrieval through OpenAlex
and Semantic Scholar
SARA supports Ollama (the default local provider) and Google Gemini (optional).
Model selection is configured using SARA_MODEL_PROVIDER or the V3 launcher. Gemini requires GEMINI_API_KEY. Local Ollama inference does not require an API key.
A Semantic Scholar API key is optional. The repository includes
an `.env.example` file documenting the supported key name.
Installation (Windows PowerShell)
On a new Windows machine, install Python 3.13.7, Git, and Ollama first (see Requirements). Open PowerShell, then use these commands from a directory where you want the project to live:
```powershell
git clone --branch v2 --single-branch https://github.com/AmalMohammed95/SARA-Agentic-Research-Agent.git
cd SARA-Agentic-Research-Agent
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen2.5:7b
```
The execution-policy adjustment applies only to the current PowerShell session. If your organization prohibits policy changes, ask the administrator for an approved setup method. The `ollama pull` step requires a model download (about 4.7 GB) on a machine that does not have the model yet.
The local `.env` file is a template and is not loaded automatically by SARA. The `RUN_SARA_V3.ps1` launcher sets the supported provider and V3 processing options in the PowerShell process. For Gemini, you must separately set `GEMINI_API_KEY` in the same session. Never commit `.env` or real API keys to GitHub.
Optional Semantic Scholar API Configuration
SARA can search OpenAlex without an API key.
For Semantic Scholar, an API key is optional. The supported
environment variable is `SEMANTIC_SCHOLAR_API_KEY`.
To set the key for the current Windows PowerShell session:
```powershell
$env:SEMANTIC_SCHOLAR_API_KEY = "YOUR_API_KEY"
```
Replace `YOUR_API_KEY` with your actual key.
The `.env.example` file documents this variable. The current
implementation reads the environment variable directly and does
not automatically load values from a `.env` file.
If no key is provided, SARA attempts Semantic Scholar requests
without authentication. Requests may be rate-limited, and
OpenAlex remains available as an alternative source.
Run the Application (SARA V3)
Ensure Ollama is running and the `qwen2.5:7b` model is installed.
From the project root, run:
```powershell
.\RUN_SARA_V3.ps1 -Provider ollama
```
The V3 launcher configures the model provider, evidence extraction,
verification settings, and PYTHONPATH automatically.
The Streamlit interface should open at:
http://localhost:8501
Enter a research question, choose the maximum number of agent
turns (1–3), and click Run Research Agent.
For the optional Gemini provider, install the additional Google Gen AI SDK (it is not included in the base `requirements.txt`), configure `GEMINI_API_KEY` securely in the same PowerShell session, and run:
```powershell
python -m pip install google-genai
$env:GEMINI_API_KEY = "YOUR_API_KEY"
```
The Ollama path above is the verified no-key clean-machine setup. Hosted Gemini requires an accessible API account and quota; `google-genai` should be version-pinned before claiming identical hosted-environment reproducibility.
```powershell
.\RUN_SARA_V3.ps1 -Provider gemini
```
If PowerShell blocks the launcher, the execution policy can be
adjusted for the current session only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Never commit API keys or the local .env file to GitHub.
Run Automated Tests
```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -q
```
The latest local test run completed successfully: 247 passed. This verifies the automated test suite, not the scientific sufficiency of every research result.
Worked Example — Leukemia Detection (E01 topic)
This example demonstrates how SARA processes a real academic
research question using its bounded agentic workflow.
Research Question:
What deep learning approaches are used for leukemia detection
in peripheral blood smear images?
Execution Steps:
Launch SARA using the V3 launcher.
Open the Streamlit interface at http://localhost:8501.
Enter the research question above.
Set Maximum Agent Turns to 3.
Click "Run Research Agent".
Inspect the research plan, retrieved papers, evidence,
execution trace, and final status.
Previously Recorded Separate Live Execution:
A real execution on November 5, 2026 demonstrated:
Three bounded research turns.
Two applied search-strategy revisions.
Eight scholarly publications retrieved in the final turn.
Seven publications selected for further processing.
Six publications processed.
Final status: INSUFFICIENT_EVIDENCE.
Interpretation:
SARA demonstrated controlled replanning and scholarly retrieval,
but the evidence did not satisfy all acceptance criteria.
The system terminated safely instead of presenting incomplete
research findings as verified conclusions.
Important:
This is a previously recorded demonstration, not a guarantee
of identical results in a new live run.
Retrieved publications, execution time, and final status may
vary depending on scholarly APIs, model responses, and the
execution environment.
A working run should display the research workflow and
an explicit execution status rather than an application error.
Human Approval Gate
SARA implements a Human-in-the-Loop (HITL) approval mechanism
to prevent automatic acceptance of research findings.
When the Approval Gate Is Triggered
When sufficient evidence is available and a synthesis passes
structural citation validation, the workflow may enter:
`WAITING_FOR_APPROVAL`
The Streamlit interface then displays the Human Review section.
Reviewer Actions
Enter the reviewer name.
Inspect the proposed synthesis and citations.
Select a decision:
APPROVE → COMPLETED
EDIT → COMPLETED
REJECT → ESCALATED
REQUEST_REVISION → WAITING_FOR_REVISION
Provide a reason where required.
For EDIT, provide a revised synthesis.
Click "Submit review decision".
Audit and Persistence
Review decisions are saved as JSON records in `data/reviews`.
Each decision records the reviewer identity, decision, reason,
timestamp, and audit information.
The relevant implementation files are:
`src/sara/human_review.py`
`src/sara/review_store.py`
`app.py`
Reproducing the Controlled Approval Tests
From the project root, run:
```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_human_review.py tests/test_review_store.py -q
```
These tests use controlled review records and do not require
a live scholarly search or LLM inference.
Important Limitation
The five recorded live research cases terminated with
INSUFFICIENT_EVIDENCE and did not reach the approval gate.
Therefore, the approval mechanism is demonstrated through
controlled tests rather than a scientifically successful
live research workflow.
Repository Map
The SARA repository is organized as follows:
File / Directory	Description
`app.py`	Streamlit application and user interface.
`src/sara/`	Core agent implementation, models, tools, policies, evidence processing, synthesis, and human review.
`tests/`	Automated unit, integration, security, and failure-handling tests.
`evaluation/`	Frozen research questions, baseline comparison scripts, recorded results, and evaluation analysis.
`docs/`	Architecture and technical documentation.
`data/reviews/`	Persistent human-review records and audit information.
`RUN_SARA_V3.ps1`	PowerShell launcher for the V3 configuration.
`requirements.txt`	Python package dependencies.
`.env.example`	Template for environment configuration.
`README.md`	Installation, execution, testing, evaluation, and reproducibility instructions.
The main agent controller is implemented in
`src/sara/agent.py`.
The project separates research processing, tool validation,
evidence assessment, human oversight, and evaluation
to support modularity, testing, and reproducibility.
Evaluation and Limitations

Evaluation Design
SARA was evaluated against a non-agentic academic search baseline using a frozen set of five research questions (E01–E05), stored in `evaluation/research_questions.csv`.
The evaluation compares execution status, runtime, evidence support, and research workflow behavior. The baseline follows a simpler search and screening process, while SARA incorporates bounded agentic execution, evidence verification, limited replanning, and explicit termination conditions.
The evaluation records are treated as frozen experimental artifacts. Reported execution outcomes are distinguished from scientific validity and evidence quality.
Recorded Evaluation Results
The frozen evaluation includes five paired experiments, producing ten execution records: five baseline runs and five SARA runs.
Metric	Baseline	SARA
Evaluation cases	5 (E01–E05)	5 (E01–E05)
Recorded execution status	5 COMPLETED	5 INSUFFICIENT_EVIDENCE
Mean runtime (seconds)	1.50	2002.48
Top-level execution crashes	0	0
Bounded replanning	Not applicable	2 replanning attempts per run
All five baseline executions reached the `COMPLETED` state. However, this status indicates workflow completion and does not establish that the resulting claims are scientifically valid or adequately supported.
All five SARA executions terminated with `INSUFFICIENT_EVIDENCE`. This indicates that SARA did not satisfy its configured evidence-sufficiency conditions within the permitted execution limits. These outcomes demonstrate explicit stopping behavior, not successful completion of the research tasks.
The evaluation also identified limitations involving incomplete evidence fields, unsupported claims, and insufficient retrieval coverage, including a sparse-retrieval case in E05.
The substantial runtime difference reflects the computational cost of SARA's local LLM-based workflow and additional verification steps. The recorded results do not establish that SARA is more accurate or scientifically superior to the baseline.
Separate V3 Evaluation Snapshot (Gemini)
The later V3 evaluation used the same five frozen questions (E01--E05) but a different provider and workflow configuration. Its saved, concise results are in `evaluation/comparison_results_v3_summary.json`. This is a separate descriptive snapshot, not a controlled speed comparison with the earlier Ollama batch.
V3 Metric	Baseline	SARA
Recorded cases	5	5
Completed baseline workflows	5	Not equivalent to SARA completion
`INSUFFICIENT_EVIDENCE` final statuses	0	5
Mean recorded runtime	1.65 s	206.12 s
The mean V3 SARA missing-field rate was approximately 43.92%, exceeding the system's 20% acceptance threshold. No V3 case met the complete evidence-sufficiency criteria. These diagnostics do not establish independently verified claim accuracy. The raw experimental records were not included in the public repository; the tracked summary permits inspection of the recorded statuses and runtimes.
To inspect the V3 summary without making any model or API requests, run the following from PowerShell in the repository root:
```powershell
$v3 = Get-Content evaluation/comparison_results_v3_summary.json -Raw | ConvertFrom-Json
$v3.results | Group-Object system, status | Select-Object Name, Count
$v3.results | Group-Object system | ForEach-Object {
    '{0}: {1} runs; mean {2:N2} seconds' -f $_.Name, $_.Count, (($_.Group | Measure-Object -Property duration_seconds -Average).Average)
}
```
Expected: five baseline `COMPLETED`, five SARA `INSUFFICIENT_EVIDENCE`; mean duration about 1.65 s for the baseline and 206.12 s for SARA.
Limitations
Execution cost: Local CPU-based LLM inference substantially increases execution time compared with the simpler baseline.
Evidence sufficiency: None of the five evaluated SARA runs satisfied the configured evidence-sufficiency criteria.
Evidence quality: Missing extraction fields and unsupported claims limit the reliability of automatically generated research findings.
Retrieval coverage: Scholarly search may return insufficient relevant evidence for some research questions, as observed in E05.
External dependencies: Scholarly retrieval requires internet connectivity. Semantic Scholar may impose HTTP 429 rate limits, and SARA's local model execution depends on Ollama availability.
Model sensitivity: Extraction quality, reasoning behavior, and agent decisions may vary with the local language model.
Evaluation scope: Five frozen research questions provide a bounded experimental comparison, not evidence of general performance across all research domains.
Reference validation: Automated evidence checks do not replace independent expert assessment against a hand-checked reference set.
Testing and Reproducibility
The latest complete automated test run reported 247 passing tests.
To run the automated tests:
```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -q
```
The frozen research questions are stored in `evaluation/research_questions.csv`, and the recorded comparison results are stored in `evaluation/comparison_results_batch_v1.json`.
Reproducing the Recorded Evaluation Analysis
The frozen evaluation contains five research questions (E01–E05)
and ten recorded executions: five baseline runs and five SARA runs.
To regenerate the evaluation summary from the saved results,
run the following command from the project root:
```powershell
python evaluation/analyze_results.py
```
The script reads:
`evaluation/research_questions.csv`
`evaluation/comparison_results_batch_v1.json`
It writes the summary to:
`evaluation/evaluation_summary.json`
This command analyzes previously recorded results. It does not
rerun the research agent, call scholarly APIs, or invoke Ollama.
Reproducing the recorded analysis is different from repeating
the live experiments, which may take substantially longer and
produce different results.
Rerunning the Live Evaluation
The evaluation runner is available at `evaluation/run_comparison.py`.
To run a specific evaluation case:
```powershell
python evaluation/run_comparison.py E01
```
To run all evaluation cases:
```powershell
python evaluation/run_comparison.py
```
Important: These commands are provided for documentation and
should not be executed against the frozen evaluation artifacts
without first creating a separate working copy of the project.
The runner reads and writes
`evaluation/comparison_results_batch_v1.json`. It skips recorded
case-system pairs whose status is not `EXCEPTION`, and it may rerun
and replace records that previously ended with `EXCEPTION`.
Therefore, these commands do not necessarily rerun all experiments
when existing results are present. A fresh evaluation requires an
isolated copy of the project with a separate results file.
Live evaluation requires Ollama and scholarly API connectivity,
may take considerable time, and may produce different outcomes.
The evaluation results should be interpreted as recorded experimental observations. Repeating live experiments may produce different outcomes because of model variability, scholarly API responses, and execution environment differences.
Passing automated software tests demonstrates that the tested components meet their specified checks. It does not independently establish scientific accuracy, evidence sufficiency, or research superiority.
Evaluation Conclusion
SARA implements an agentic academic research workflow with controlled scholarly retrieval, bounded execution, evidence verification, limited replanning, human oversight, and explicit failure handling.
Across the five frozen evaluation cases, SARA consistently terminated without a top-level crash but did not obtain sufficient verified evidence to complete the research tasks. The baseline completed its simpler workflow substantially faster, although completion alone does not establish scientific correctness.
These findings highlight a measurable trade-off between agentic workflow controls, evidence requirements, and computational cost. Further improvements in retrieval coverage, evidence extraction, and independent reference-based validation are necessary before claims of improved research quality can be supported.