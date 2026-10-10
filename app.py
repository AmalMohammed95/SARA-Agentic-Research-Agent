
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

if "result" not in st.session_state:
    st.session_state.result = None

with st.form("research_form"):
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
    else:
        with st.spinner("Searching and evaluating research evidence..."):
            try:
                st.session_state.result = run_agent(
                    question.strip(),
                    max_turns=max_turns,
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
                        ["APPROVE", "REJECT", "REQUEST_REVISION"],
                    )
                    reason = st.text_area("Reason")
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
                        )
                        st.success(
                            f"Review decision recorded: {updated['status']}"
                        )
                        st.rerun()
                    except (ValueError, OSError) as exc:
                        st.error(str(exc))

            else:
                st.info(
                    f"Decision: {review.get('decision')} "
                    f"by {review.get('reviewer')}"
                )
