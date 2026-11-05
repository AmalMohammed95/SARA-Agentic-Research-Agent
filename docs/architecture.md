# SARA V3 - System Architecture

```mermaid
flowchart TD
    U["Researcher"] --> UI["Streamlit UI"]
    UI --> AC["Agent Controller and Planning"]

    AC <--> ST["Research State"]
    AC --> MC["Model Interface"]
    MC --> LLM["Gemini / Ollama"]

    AC --> PV["Policy Validation"]
    PV --> EX["Controlled Tool Executor"]
    EX --> SR["Scholarly Retrieval"]

    SR --> SC["Paper Screening"]
    SC --> EN["Source Enrichment"]
    EN --> EV["Evidence Extraction and Orchestration"]
    EV --> VA["Evidence Verification"]
    VA --> D{"Sufficient evidence?"}

    D -->|Yes| RP["Research Report"]
    D -->|Replan within budget| AC
    D -->|Stop safely| FS["Insufficient Evidence"]

    RP --> HR["Human Review"]
    FS --> HR

    AC -.-> TR["Execution Tracing"]
    VA -.-> TR
    HR -.-> TR
```

## Architecture Notes

- The model is a decision component, not the entire agent.
- Tool requests pass through policy validation.
- Scholarly information enters as untrusted source data.
- Evidence verification preserves provenance and uncertainty.
- The research workflow follows bounded execution limits.
- Human oversight and safe termination are supported.
- State and traces provide execution observability.

This is a logical architecture diagram, not an exact function-call graph.
