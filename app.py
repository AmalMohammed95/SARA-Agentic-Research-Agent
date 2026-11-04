
"""Streamlit interface for SARA."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sara.agent import run_agent
from sara.review_store import load_review, decide_review


st.set_page_config(
    page_title="SARA - Academic Research Agent",
    page_icon="📚",
    layout="wide",
)

st.title("SARA - Smart Academic Research Agent")
st.caption("Evidence-grounded academic research with human oversight")
import os
_json_enabled = os.environ.get("SARA_JSON_EXTRACTION", "0") == "1"
_extractive_enabled = os.environ.get("SARA_EXTRACTIVE_MODE", "0") == "1"
_semantic_enabled = os.environ.get("SARA_SEMANTIC_VERIFICATION", "0") == "1"
_batch_enabled = os.environ.get("SARA_BATCH_SEMANTIC_VERIFICATION", "1") == "1"
st.caption(f"Runtime: Source-only extraction={'ON' if _extractive_enabled else 'OFF'} | "
           f"JSON extraction={'ON' if _json_enabled else 'OFF'} | "
           f"Semantic verification={'ON' if _semantic_enabled else 'OFF'} | "
           f"Cross-paper batching={'ON' if _batch_enabled else 'OFF'}")
if not (_json_enabled or _extractive_enabled) or not _semantic_enabled:
    st.warning("Reliable evidence profile is not fully enabled. Use the included RUN_SARA_V3.ps1 launcher, "
               "or set SARA_EXTRACTIVE_MODE=1 and SARA_SEMANTIC_VERIFICATION=1 before starting Streamlit.")


if "result" not in st.session_state:
    st.session_state.result = None

with st.form("research_form"):
    default_provider = os.environ.get("SARA_MODEL_PROVIDER", "ollama").lower()
    provider = st.selectbox("Model provider", ["gemini", "ollama"],
                            index=0 if default_provider == "gemini" else 1,
                            format_func=lambda value: "Google Gemini API" if value == "gemini" else "Ollama (local)")
    question = st.text_area(
        "Research question",
        placeholder="How are LLM agents used in academic research?",
        height=100,
    )
    max_turns = st.slider("Maximum agent turns", 1, 3, 3)
    submitted = st.form_submit_button("Run Research Agent")

if submitted:
    if not question.strip():
        st.error("Please enter a research question.")
    elif provider == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is unavailable in the Streamlit process. Set it in your terminal and restart Streamlit; do not paste it into the application.")
    else:
        with st.spinner("Searching and evaluating research evidence..."):
            try:
                st.session_state.result = run_agent(
                    question.strip(),
                    max_turns=max_turns,
                    provider=provider,
                )
            except Exception as exc:
                st.session_state.result = None
                st.error(f"Agent execution failed: {exc}")

result = st.session_state.result

if result:
    st.subheader("Execution result")
    st.write("Status:", result["status"])
    st.write("Reason:", result.get("reason"))
    st.write("Run ID:", result.get("run_id"))
    st.write("Turns:", result.get("turns"))

    decisions = [event.get("details", {}) for event in result.get("trace", [])
                 if event.get("action") == "evaluate_evidence"]
    if decisions:
        decision = decisions[-1]
        a, b, c = st.columns(3)
        a.metric("Processed studies", decision.get("processed_studies_count", "—"))
        b.metric("Missing metadata", f"{decision.get('missing_field_rate', 1):.1%}")
        c.metric("Unverified records", decision.get("unverified_evidence_count", "—"))
        st.caption("Abstract-derived evidence is preliminary. A model verdict alone is not proof; "
                   "source spans, research coverage, and human approval remain required.")

    audit = result.get("evidence_audit") or {}
    if audit:
        st.subheader("Preliminary evidence audit")
        st.write("Research coverage:", "MET" if audit.get("research_coverage_met") else "NOT MET")
        st.write("Metadata completeness:", "MET" if audit.get("metadata_quality_met") else "NOT MET")
        st.write("Source coverage:", audit.get("source_distribution"))
        st.warning("Exact-source quotes and model verdicts are preliminary, not independent verification. Human review is required.")
        with st.expander("Preliminary source-supported records"):
            st.json(audit.get("supported_quote_records", []))
        with st.expander("Unverified evidence"):
            st.json(audit.get("unverified_records", []))
        import json
        st.download_button("Export evidence audit (JSON)",
            json.dumps(audit, ensure_ascii=False, indent=2),
            "SARA_evidence_audit.json", mime="application/json")

    with st.expander("Evidence gaps"):
        gaps = result.get("gaps", [])
        if gaps:
            for gap in gaps:
                st.write("-", gap)
        else:
            st.write("No reported gaps.")

    with st.expander("Selected papers"):
        st.json(result.get("selected_papers", []))

    with st.expander("Evidence records"):
        st.json(result.get("evidence", []))

    with st.expander("Execution trace"):
        st.json(result.get("trace", []))

    synthesis = result.get("synthesis")

    if synthesis:
        st.subheader("Research synthesis")
        st.warning(
            "This draft has passed structural citation checks only. "
            "It has not been semantically verified or approved."
        )
        st.text(synthesis["text"])
        st.write("Citations:", synthesis.get("citations", {}))

    if result["status"] == "WAITING_FOR_APPROVAL":
        st.subheader("Human review")

        try:
            review = load_review(result["run_id"])
        except (FileNotFoundError, ValueError) as exc:
            st.error(f"Review request unavailable: {exc}")
        else:
            st.write("Review status:", review["status"])

            if review["status"] == "WAITING_FOR_APPROVAL":
                with st.form("review_form"):
                    reviewer = st.text_input("Reviewer name")
                    decision = st.selectbox(
                        "Decision",
                        ["APPROVE", "EDIT", "REJECT", "REQUEST_REVISION"],
                    )
                    reason = st.text_area("Reason")
                    edited_text = st.text_area(
                        "Edited synthesis (required for EDIT only)",
                        value=review.get("synthesis", {}).get("text", ""),
                        height=240,
                    )
                    review_submitted = st.form_submit_button(
                        "Submit review decision"
                    )

                if review_submitted:
                    try:
                        updated = decide_review(
                            result["run_id"],
                            decision,
                            reviewer,
                            reason,
                            edited_text=edited_text if decision == "EDIT" else None,
                        )
                        st.success(
                            f"Review decision recorded: {updated['status']}"
                        )
                        st.rerun()
                    except (ValueError, OSError) as exc:
                        st.error(str(exc))

            else:
                if review.get("edited_synthesis"):
                    st.subheader("Human-edited synthesis")
                    st.warning("Human edited; citation labels checked structurally, not semantically verified.")
                    st.text(review["edited_synthesis"])
                st.info(
                    f"Decision: {review.get('decision')} "
                    f"by {review.get('reviewer')}"
                )
