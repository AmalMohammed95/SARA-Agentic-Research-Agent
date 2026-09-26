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