"""

Bounded agent loop for SARA.



The agent operates within explicit execution limits and must

terminate in a defined state rather than running indefinitely.

"""


from .deterministic_evidence import extract_abstract_json
from .topic_guard import anchor_agent_query, anchor_agent_subquestions, flag_scope_drift, repair_reliability_plan
from .batch_screening import screen_papers_in_batches
from .batch_extraction import extract_batch
from .json_extraction import (
    EXTRACTION_SCHEMA, json_extraction_prompt,
    validate_json_extraction, parse_json_extraction,
)
from .extraction import (
    create_empty_evidence_record,
    verify_supporting_evidence,
    normalize_supported_subquestions,
    verify_question_evidence,
    unwrap_evidence_quote,
    locate_abstract_quotes,
)
from .semantic_verification import verify_semantic_batch, verify_semantic_candidates, verify_semantic_with_budget
from .source_first import build_source_first_mapping, build_multi_source_mapping
from .screening import screen_agent_papers
from .search_strategy import choose_turn_queries

from .executor import execute_tool

from .state import AgentState

from .tracing import create_run_id, create_trace_event

from .evidence import evaluate_evidence_sufficiency

from .replanning import can_replan, build_replanning_context

from .model import OllamaModelClient, GeminiModelClient
import os

from .human_review import create_review_request

from .review_store import save_review

from sara.evidence import deduplicate_papers, is_duplicate_paper

from .synthesis import (

    prepare_synthesis_evidence,

    build_synthesis_prompt,

    validate_synthesis,

)

from .prompts import (

    RESEARCH_PLANNING_PROMPT,

    REPLANNING_PROMPT,

    EVIDENCE_EXTRACTION_PROMPT,

    SEMANTIC_SCREENING_PROMPT,

)

from .schemas import (

    validate_research_plan,

    parse_research_plan,

    validate_replanning_response,

    parse_revised_keywords,

    validate_evidence_extraction,

    parse_evidence_extraction,

    validate_extraction_quality,

    validate_semantic_screening,

    parse_semantic_screening,

)

def filter_unseen_papers(retrieved_papers: list[dict], previously_seen: list[dict]) -> list[dict]:
    """Avoid repeated LLM screening for papers already retrieved in prior turns."""
    return [
        paper for paper in retrieved_papers
        if not is_duplicate_paper(paper, previously_seen)
    ]


MAX_EXTRACTIONS_PER_TURN = 5  # Legacy default; configurable higher bounded limit



TERMINAL_STATES = {

    "COMPLETED",

    "BLOCKED",

    "ESCALATED",

    "WAITING_FOR_APPROVAL",

    "INSUFFICIENT_EVIDENCE",

    "BUDGET_EXHAUSTED",

    "FAILED_SAFELY",

}



def select_search_query(keywords, used_queries):

    valid_keywords = [

        keyword.strip()

        for keyword in keywords

        if isinstance(keyword, str) and keyword.strip()

    ]



    for keyword in valid_keywords:

        if keyword.lower() not in used_queries:

            used_queries.add(keyword.lower())

            return keyword



    return None



def run_agent(research_question: str, max_turns: int = 3) -> dict:

    """Run a bounded SARA agent loop."""



    if not research_question or not research_question.strip():

        return {

            "status": "FAILED_SAFELY",

            "turns": 0,

            "reason": "Research question must not be empty.",

        }



    if not isinstance(max_turns, int) or max_turns < 1:

        return {

            "status": "FAILED_SAFELY",

            "turns": 0,

            "reason": "max_turns must be a positive integer.",

        }



    run_id = create_run_id()

    state = AgentState(

        research_question=research_question.strip(),

        run_id=run_id,

    )

    trace = []
    # Zero/unset keeps prior behavior; the reliable run profile bounds reviews.
    try:
        max_semantic_calls = max(0, int(os.getenv("SARA_MAX_SEMANTIC_CALLS", "0")))
    except ValueError:
        max_semantic_calls = 0
    semantic_calls_used = 0


    model_provider = os.getenv("SARA_MODEL_PROVIDER", "ollama").lower()

    if model_provider == "gemini":
        model_client = GeminiModelClient()
    elif model_provider == "ollama":
        model_client = OllamaModelClient()
    else:
        raise ValueError(
            f"Unsupported model provider: {model_provider}"
        )


    turn = 0

    synthesis_result = None

    review_request = None



    # Initial planning happens once. Replanning updates state.keywords and the

    # next loop iteration uses those revised keywords directly.

    planning_prompt = RESEARCH_PLANNING_PROMPT.format(

        research_question=state.research_question,

    )

    try:

        planning_response = model_client.generate(planning_prompt)

    except Exception as exc:

        state.status = "FAILED_SAFELY"

        state.stopping_reason = (

            f"Initial planning model call failed: {exc}"

        )



        trace.append(

            create_trace_event(

                run_id=run_id,

                turn=0,

                action="research_planning",

                status="FAILED_SAFELY",

                details={"error": str(exc)},

            )

        )



        return {

            "status": state.status,

            "run_id": state.run_id,

            "turns": state.iteration,

            "reason": state.stopping_reason,

            "replanning_attempts": state.replanning_attempts,

            "trace": trace,

            "gaps": state.gaps,

            "evidence": state.evidence,

        }



    planning_validation = validate_research_plan(planning_response)



    trace.append(

        create_trace_event(

            run_id=run_id,

            turn=0,

            action="validate_research_plan",

            status="VALID" if planning_validation["valid"] else "INVALID",

            details=planning_validation,

        )

    )



    if not planning_validation["valid"]:

        state.status = "FAILED_SAFELY"

        state.stopping_reason = "Initial research plan failed validation."

        return {

            "status": state.status,

            "run_id": state.run_id,

            "turns": state.iteration,

            "reason": state.stopping_reason,

            "replanning_attempts": state.replanning_attempts,

            "trace": trace,

            "gaps": state.gaps,

            "evidence": state.evidence,

        }



    parsed_plan = parse_research_plan(planning_response)

    state.subquestions = anchor_agent_subquestions(parsed_plan["subquestions"], research_question)
    state.subquestions, repaired_questions = repair_reliability_plan(state.subquestions, research_question)

    state.keywords = [anchor_agent_query(k, research_question) for k in parsed_plan["keywords"]]

    # Log planning drift without silently rewriting the research question.
    drift = repaired_questions + flag_scope_drift(state.subquestions, research_question)
    if drift:
        trace.append(create_trace_event(
            run_id=run_id, turn=0, action="research_scope_warning",
            status="REVIEW_REQUIRED", details={"questions": drift},
        ))







    used_search_queries = set()



    while turn < max_turns:

        turn += 1

        state.iteration = turn



        if not state.keywords:

            state.status = "FAILED_SAFELY"

            state.stopping_reason = "No valid search keywords are available."

            break



        # A single turn may search two complementary phrases when enabled.
        # Every request and failure is traced separately. No query is repeated.
        try:
            query_limit = max(1, min(3, int(os.getenv("SARA_SEARCH_QUERIES_PER_TURN", "1"))))
        except ValueError:
            query_limit = 1
        search_queries = choose_turn_queries(
            [anchor_agent_query(k, research_question) for k in state.keywords],
            research_question, used_search_queries, limit=query_limit,
        )
        if not search_queries:
            state.status = "INSUFFICIENT_EVIDENCE"
            state.stopping_reason = "No unused search queries remain."
            break

        retrieved_batch = []
        completed_queries = 0
        for query in search_queries:
            search_result = execute_tool(
                "search_scholarly", {"query": query, "max_results": 10},
            )
            trace.append(create_trace_event(
                run_id=run_id, turn=turn, action="search_scholarly",
                status=search_result["status"],
                details={"query": query,
                         "results_count": len(search_result["result"] or [])},
            ))
            if search_result["status"] == "COMPLETED":
                completed_queries += 1
                retrieved_batch.extend(search_result["result"] or [])

        trace.append(create_trace_event(
            run_id=run_id, turn=turn, action="search_query_summary",
            status="COMPLETED" if completed_queries else "FAILED_SAFELY",
            details={"requested": len(search_queries), "completed": completed_queries,
                     "failed": len(search_queries) - completed_queries,
                     "unique_results": len(deduplicate_papers(retrieved_batch))},
        ))
        if not completed_queries:
            state.status = "FAILED_SAFELY"
            state.stopping_reason = "All scholarly searches failed."
            break

        new_retrieved_papers = deduplicate_papers(retrieved_batch)

        # Papers seen in an earlier turn have already been screened.
        # Screen only genuinely new records; retain the accumulated
        # selected/excluded evidence from prior turns unchanged.
        unseen_papers = filter_unseen_papers(
            new_retrieved_papers, state.retrieved_papers
        )
        # Screening deferred by the model-call budget is NOT an exclusion.
        # Retry a bounded number in subsequent turns; never report it as irrelevant.
        for deferred in state.deferred_papers:
            if not is_duplicate_paper(deferred, unseen_papers):
                unseen_papers.append(deferred)
        state.deferred_papers = []

        included_papers, excluded_papers = screen_agent_papers(

            unseen_papers,

        )



        # Semantic screening of deterministically eligible papers.

        semantically_included = []

        semantically_excluded = []
        semantically_deferred = []


        from .research_priority import rank_papers
        included_papers = rank_papers(included_papers, state.subquestions)
        screening_results = screen_papers_in_batches(
            papers=included_papers,
            research_question=state.research_question,
            model_client=model_client,
            batch_size=5,
        )

        for result in screening_results:
            paper = result["paper"]
            decision = result["decision"]
            reason = result["reason"]
            status = result["status"]

            if status == "BUDGET_EXHAUSTED":
                semantically_deferred.append(paper)
            elif decision == "INCLUDE":
                semantically_included.append(
                    {
                        **paper,
                        "screening_status": "semantically_relevant",
                        "screening_reason": reason,
                    }
                )
            else:
                semantically_excluded.append(
                    {
                        **paper,
                        "exclusion_reason": reason,
                    }
                )

            trace_details = {
                "paper_id": paper.get("doi") or paper.get("id"),
                "title": paper.get("title", ""),
                "reason": reason,
            }

            if result.get("error"):
                trace_details["error"] = result["error"]

            trace.append(
                create_trace_event(
                    run_id=run_id,
                    turn=turn,
                    action="semantic_screening",
                    status=status,
                    details=trace_details,
                )
            )

        included_papers = semantically_included

        excluded_papers.extend(semantically_excluded)
        state.deferred_papers.extend(semantically_deferred)





        # Accumulate retrieved papers across turns without duplicates.

        existing_retrieved_ids = {

            paper.get("doi") or paper.get("id")

            for paper in state.retrieved_papers

        }

        previous_retrieved_count = len(state.retrieved_papers)



        for paper in new_retrieved_papers:

            paper_id = paper.get("doi") or paper.get("id")



            if not is_duplicate_paper(

                paper, state.retrieved_papers

            ):

                state.retrieved_papers.append(paper)

                existing_retrieved_ids.add(paper_id)



        # Accumulate selected papers across turns without duplicates.

        existing_selected_ids = {

            paper.get("doi") or paper.get("id")

            for paper in state.selected_papers

        }



        newly_selected_papers = []



        for paper in included_papers:

            paper_id = paper.get("doi") or paper.get("id")



            if not is_duplicate_paper(

                    paper, state.selected_papers

                ):

                state.selected_papers.append(paper)

                newly_selected_papers.append(paper)

                existing_selected_ids.add(paper_id)



                # Create evidence only for a newly selected paper.

                state.evidence.append(

                    create_empty_evidence_record(paper)

                )



        # Preserve exclusions from previous turns without duplicates.

        existing_excluded_ids = {

            paper.get("doi") or paper.get("id")

            for paper in state.excluded_papers

        }



        for paper in excluded_papers:

            paper_id = paper.get("doi") or paper.get("id")



            if paper_id not in existing_excluded_ids:

                state.excluded_papers.append(paper)

                existing_excluded_ids.add(paper_id)



        # Extract evidence from at most two pending selected papers per turn.

        # Retry incomplete or unsupported records, at most twice per paper.
        # Never treat missing fields as verified evidence.
        pending_evidence_ids = {
            record["paper_id"]
            for record in state.evidence
            if record.get("extraction_status") in ("pending", "failed")
            or record.get("claim_support_status") != "supported"
            or any(
                not record.get(field)
                for field in ("objective", "methodology", "findings", "limitations")
            )
        }

        papers_with_abstract = [

            paper

            for paper in state.selected_papers

            if (

                (paper.get("doi") or paper.get("id"))

                in pending_evidence_ids

                and paper.get("abstract")

                and state.extraction_attempts.get(

                    paper.get("doi") or paper.get("id"), 0

                ) < (1 if os.getenv("SARA_EXTRACTIVE_MODE", "0") == "1" else 2)

            )

                ]

        from .research_priority import rank_papers
        papers_with_abstract = rank_papers(papers_with_abstract, state.subquestions,
            state.extraction_attempts)

        pending_count = len(papers_with_abstract)
        papers_with_abstract = papers_with_abstract[:max(1, min(30, int(os.getenv("SARA_MAX_EXTRACTIONS", str(MAX_EXTRACTIONS_PER_TURN)))))]
        trace.append(create_trace_event(
            run_id=run_id, turn=turn, action="extraction_queue",
            status="SCHEDULED", details={"pending": pending_count,
            "scheduled": len(papers_with_abstract),
            "deferred": max(0, pending_count - len(papers_with_abstract)),
            "mode": "extractive" if os.getenv("SARA_EXTRACTIVE_MODE", "0") == "1" else "generative"},
        ))



        # Opt-in: batch two papers, with fail-closed individual fallback.
        # On CPU this is an experiment, not an assumed speedup.
        batch_responses = {}
        if (
            os.environ.get("SARA_BATCH_EXTRACTION", "0") == "1"
            and os.environ.get("SARA_JSON_EXTRACTION", "0") != "1"
        ):
            for start in range(0, len(papers_with_abstract), 2):
                group = papers_with_abstract[start:start + 2]
                if len(group) < 2:
                    continue
                try:
                    batch_responses.update(
                        extract_batch(model_client, group, state.subquestions)
                    )
                except Exception as exc:
                    trace.append(create_trace_event(
                        run_id=run_id, turn=turn, action="batch_evidence_extraction",
                        status="FALLBACK", details={"error": str(exc)},
                    ))

        for paper_with_abstract in papers_with_abstract:

            paper_id = (

                paper_with_abstract.get("doi")

                or paper_with_abstract.get("id")

            )



            state.extraction_attempts[paper_id] = (

                state.extraction_attempts.get(paper_id, 0) + 1

            )
            # Mark this as attempted, without inventing an unsupported claim.
            for rec in state.evidence:
                if rec.get("paper_id") == paper_id and rec.get("extraction_status") != "completed":
                    rec["extraction_status"] = "failed"  # until validation succeeds
                    break

            extraction_prompt = EVIDENCE_EXTRACTION_PROMPT.format(

                title=paper_with_abstract.get("title", ""),

                abstract=paper_with_abstract.get("abstract", ""),

                subquestions=state.subquestions,

            )
            use_json_extraction = (
                os.environ.get("SARA_JSON_EXTRACTION", "0") == "1"
                and isinstance(model_client, OllamaModelClient)
                and paper_id not in batch_responses
            )


            deterministic_extraction = os.getenv("SARA_EXTRACTIVE_MODE", "0") == "1"
            if deterministic_extraction:
                use_json_extraction = True
            try:
                extraction_response = (extract_abstract_json(
                    paper_with_abstract.get("abstract", "")
                ) if deterministic_extraction else batch_responses.get(paper_id))

                if extraction_response is None:
                    # Structured JSON extraction for Ollama.
                    if use_json_extraction:
                        extraction_prompt = json_extraction_prompt(
                            paper_with_abstract.get("title", ""),
                            paper_with_abstract.get("abstract", ""),
                            state.subquestions,
                        )
                        extraction_response = model_client.generate(
                            extraction_prompt,
                            format=EXTRACTION_SCHEMA,
                        )
                    else:
                        extraction_response = model_client.generate(
                            extraction_prompt
                        )

            except Exception as exc:



                    trace.append(

                        create_trace_event(

                            run_id=run_id,

                            turn=turn,

                            action="evidence_extraction",

                            status="FAILED_SAFELY",

                            details={

                                "paper_id": paper_id,

                                "title": paper_with_abstract.get(

                                    "title", ""

                                ),

                                "error": str(exc),

                            },

                        )

                    )

                    continue



            if deterministic_extraction:
                trace.append(create_trace_event(
                    run_id=run_id, turn=turn, action="extractive_evidence",
                    status="COMPLETED", details={"paper_id": paper_id,
                    "mode": "source_verbatim_no_generation"},
                ))
            is_json_extraction = use_json_extraction

            extraction_validation = (
                validate_json_extraction(extraction_response)
                if is_json_extraction else
                validate_evidence_extraction(extraction_response)
            )



            trace.append(

                create_trace_event(

                    run_id=run_id,

                    turn=turn,

                    action="validate_evidence_extraction",

                    status=(

                        "VALID"

                        if extraction_validation["valid"]

                        else "INVALID"

                    ),

                    details={

                        "paper_id": (

                            paper_with_abstract.get("doi")

                            or paper_with_abstract.get("id")

                        ),

                        "title": paper_with_abstract.get(

                            "title", ""

                        ),

                        "validation": extraction_validation,

                    },

                )

            )



            if not extraction_validation["valid"]:

                continue



            parsed_extraction = (
                parse_json_extraction(extraction_response)
                if is_json_extraction else
                parse_evidence_extraction(extraction_response)
            )



            trace.append(

                create_trace_event(

                    run_id=run_id,

                    turn=turn,

                    action="parse_evidence_extraction",

                    status="COMPLETED",

                    details={

                        "paper_id": (

                            paper_with_abstract.get("doi")

                            or paper_with_abstract.get("id")

                        ),

                        "extraction": parsed_extraction,

                    },

                )

            )

            quality_check = validate_extraction_quality(

                parsed_extraction

            )



            trace.append(

                create_trace_event(

                    run_id=run_id,

                    turn=turn,

                    action="validate_extraction_quality",

                    status=(

                        "USABLE"

                        if quality_check["usable"]

                        else "UNUSABLE"

                    ),

                    details={

                        "paper_id": (

                            paper_with_abstract.get("doi")

                            or paper_with_abstract.get("id")

                        ),

                        "quality": quality_check,

                    },

                )

            )



            if not quality_check["usable"]:

                continue





            extracted_record = create_empty_evidence_record(

                paper_with_abstract

            )

            extracted_record.update(parsed_extraction)
            extracted_record["extraction_status"] = "completed"



            raw_quotes = parsed_extraction.get("supporting_evidence", [])
            cleaned_quotes = [unwrap_evidence_quote(q) for q in raw_quotes]
            grounding_result = verify_supporting_evidence(
                paper_with_abstract.get("abstract", ""), cleaned_quotes,
            )
            validated_subquestions = normalize_supported_subquestions(
                extracted_record["supported_subquestions"],
                state.subquestions,
            )
            if is_json_extraction:
                question_check = verify_question_evidence(
                    paper_with_abstract.get("abstract", ""),
                    parsed_extraction.get("question_evidence", {}),
                    state.subquestions,
                )

                # V6: source-first fallback. Candidate sentences are exact source
                # spans, never evidence until the semantic gate approves them.
                source_mapping, candidate_origins = build_multi_source_mapping(
                    paper_with_abstract.get("abstract", ""),
                    state.subquestions,
                    question_check["verified_mapping"],
                )
                validated_subquestions = []
                trace.append(create_trace_event(
                    run_id=run_id, turn=turn, action="source_first_candidates",
                    status="COMPLETED",
                    details={"paper_id": paper_id, "candidate_origins": candidate_origins},
                ))
                if os.getenv("SARA_SEMANTIC_VERIFICATION", "0") != "1":
                    validated_subquestions = list(question_check["verified_subquestions"])
                trace.append(create_trace_event(
                    run_id=run_id, turn=turn, action="verify_question_grounding",
                    status="COMPLETED",
                    details={
                        "paper_id": paper_id,
                        "verified_subquestions": question_check["verified_subquestions"],
                        "rejected_mapping": question_check["rejected_mapping"],
                    },
                ))
                # Opt-in: one model call per paper for all grounded pairs.
                # A missing/invalid verdict never grants coverage.
                if os.getenv("SARA_SEMANTIC_VERIFICATION", "0") == "1":
                    remaining_semantic_calls = (
                        max(0, max_semantic_calls - semantic_calls_used)
                        if max_semantic_calls else None
                    )
                    semantic_check = verify_semantic_with_budget(
                        model_client,
                        paper_with_abstract.get("abstract", ""),
                        source_mapping,
                        remaining_semantic_calls,
                    )
                    semantic_calls_used += semantic_check["model_calls"]
                    validated_subquestions = [
                        question for question in state.subquestions
                        if semantic_check["verdicts"].get(question) == "SUPPORTED"
                        and question in source_mapping
                    ]
                    trace.append(create_trace_event(
                        run_id=run_id,
                        turn=turn,
                        action="verify_semantic_evidence",
                        status=("UNCERTAIN" if semantic_check["error"] else "COMPLETED"),
                        details={
                            "paper_id": paper_with_abstract.get("doi") or paper_with_abstract.get("id"),
                            "verdicts": semantic_check["verdicts"],
                            "error": semantic_check["error"],
                            "model_calls": semantic_check["model_calls"],
                            "semantic_calls_used": semantic_calls_used,
                            "semantic_calls_budget": max_semantic_calls or "unlimited",
                        },
                    ))


        # Do not count subquestion coverage when source

        # quotations have not passed grounding verification.

            if not grounding_result["verified"]:
                # In structured extraction, each question has its own independently
                # source-verified quote. An unrelated bad quote must not veto it.
                if not is_json_extraction:
                    validated_subquestions = []



            extracted_record[

                "supported_subquestions"

            ] = validated_subquestions



            # Never pass fabricated or semantically rejected quotes to synthesis.
            # Per-question model verdicts must be accompanied by the specific
            # verified source quotations, not just a paper-level SUPPORTED flag.
            if is_json_extraction:
                if os.getenv("SARA_SEMANTIC_VERIFICATION", "0") == "1":
                    accepted_quote_map = semantic_check.get("supported_quotes", {})
                else:
                    accepted_quote_map = {
                        q: [quote] for q, quote in question_check["verified_mapping"].items()
                        if q in validated_subquestions
                    }
                accepted_quotes = [
                    quote for q in validated_subquestions
                    for quote in accepted_quote_map.get(q, [])
                ]
            else:
                accepted_quotes = grounding_result["verified_quotes"] if grounding_result["verified"] else []
            verified_spans = locate_abstract_quotes(
                paper_with_abstract.get("abstract", ""), accepted_quotes,
            )
            extracted_record["source_spans"] = verified_spans
            extracted_record["supporting_evidence"] = [span["quote"] for span in verified_spans]
            extracted_record["question_evidence"] = (
                {q: quotes for q, quotes in accepted_quote_map.items()
                 if q in validated_subquestions and quotes}
                if is_json_extraction else {}
            )
            if not extracted_record["supporting_evidence"]:
                validated_subquestions = []
                extracted_record["supported_subquestions"] = []

            if (

                (grounding_result["verified"] or (
                    is_json_extraction and bool(validated_subquestions)
                ))

                and validated_subquestions

                and "objective" in quality_check["populated_fields"]

                and (

                    "findings" in quality_check["populated_fields"]

                     or "limitations" in quality_check["populated_fields"]

                    )



            ):

                extracted_record[

                    "claim_support_status"

                ] = "supported"



            if extracted_record["claim_support_status"] != "supported":
                extracted_record["claim_support_status"] = "insufficient_data"

            trace.append(

                create_trace_event(

                    run_id=run_id,

                    turn=turn,

                    action="verify_supporting_evidence",

                    status=(

                        "VERIFIED"

                        if grounding_result["verified"]

                        else "UNVERIFIED"

                    ),

                    details={

                        "paper_id": (

                            paper_with_abstract.get("doi")

                            or paper_with_abstract.get("id")

                        ),

                        "title": paper_with_abstract.get(

                            "title", ""

                        ),

                        "grounding": grounding_result,

                    },

                )

            )



            # Replace the corresponding empty evidence record.

            for index, evidence_record in enumerate(state.evidence):

                if (

                    evidence_record["paper_id"]

                    == extracted_record["paper_id"]

                ):

                    # Keep the strongest verified extraction across retries.
                    # Never overwrite a supported record with an unsupported one.
                    fields = ("objective", "methodology", "dataset_sample", "findings", "limitations")
                    def evidence_rank(record):
                        return (
                            record.get("claim_support_status") == "supported",
                            sum(bool(record.get(field)) for field in fields),
                        )

                    if evidence_rank(extracted_record) > evidence_rank(evidence_record):
                        state.evidence[index] = extracted_record

                    break





        trace.append(

            create_trace_event(

                run_id=run_id,

                turn=turn,

                action="screen_papers",

                status="COMPLETED",

                details={

                    "turn_retrieved": len(new_retrieved_papers),

                    "turn_selected": len(included_papers),

                    "turn_excluded": len(excluded_papers),

                    "total_retrieved": len(state.retrieved_papers),

                    "total_selected": len(state.selected_papers),

                    "total_excluded": len(state.excluded_papers),
                    "screening_deferred": len(state.deferred_papers),

                },

            )

        )



        trace.append(

            create_trace_event(

                run_id=run_id,

                turn=turn,

                action="agent_turn",

                status="RUNNING",

                details={"iteration": state.iteration},

            )

        )



        evidence_check = evaluate_evidence_sufficiency(

            selected_papers=state.selected_papers,

            subquestions=state.subquestions,

            evidence=state.evidence,

        )

        trace.append(

            create_trace_event(

                run_id=run_id,

                turn=turn,

                action="evaluate_evidence",

                status=(

                    "SUFFICIENT"

                    if evidence_check["sufficient"]

                    else "INSUFFICIENT"

                ),

                details=evidence_check,

            )

        )

        state.gaps = evidence_check["gaps"]





        if evidence_check["sufficient"]:

            verified_evidence = prepare_synthesis_evidence(

                state.selected_papers,

                state.evidence,

            )



            if not verified_evidence:

                state.status = "FAILED_SAFELY"

                state.stopping_reason = (

                    "Synthesis could not proceed because no "

                    "supported evidence was available."

                )

                break



            try:

                synthesis_prompt, citation_map = build_synthesis_prompt(

                    state.research_question,

                    verified_evidence,

                )



                synthesis_response = model_client.generate(

                    synthesis_prompt

                )



                synthesis_validation = validate_synthesis(

                    synthesis_response,

                    citation_map,

                )



                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="evidence_synthesis",

                        status=(

                            "VALID"

                            if synthesis_validation["valid"]

                            else "INVALID"

                        ),

                        details=synthesis_validation,

                    )

                )



                if not synthesis_validation["valid"]:

                    state.status = "ESCALATED"

                    state.stopping_reason = (

                        "Synthesis requires human review because "

                        "its structure or citations failed validation."

                    )

                    break



                synthesis_result = {

                    "text": synthesis_response,

                    "citations": synthesis_validation["citations"],

                    "validation": "STRUCTURE_AND_CITATIONS_ONLY",

                    "requires_human_review": True,

                }



                review_request = create_review_request(

                    run_id=state.run_id,

                    synthesis=synthesis_result,

                )

                save_review(review_request)



                state.status = "WAITING_FOR_APPROVAL"

                state.stopping_reason = (

                    "Evidence synthesis passed structural citation "

                    "validation and requires explicit human approval."

                )



                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="human_review_requested",

                        status="WAITING_FOR_APPROVAL",

                        details={"run_id": run_id},

                    )

                )



            except Exception as exc:

                state.status = "FAILED_SAFELY"

                state.stopping_reason = (

                    "Evidence synthesis failed safely."

                )



                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="evidence_synthesis",

                        status="FAILED_SAFELY",

                        details={"error": str(exc)},

                    )

                )



            break





        if turn < max_turns and can_replan(state.replanning_attempts):

            state.replanning_attempts += 1

            replanning_context = build_replanning_context(

                current_keywords=state.keywords,

                gaps=state.gaps,

            )

            replanning_prompt = REPLANNING_PROMPT.format(

                research_question=state.research_question,

                current_keywords=replanning_context["current_keywords"],

                evidence_gaps=replanning_context["evidence_gaps"],

            )

            try:

                replanning_response = model_client.generate(

                    replanning_prompt

                )

            except Exception as exc:

                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="replanning",

                        status="FAILED_SAFELY",

                        details={

                            "attempt": state.replanning_attempts,

                            "error": str(exc),

                        },

                    )

                )



                state.status = "INSUFFICIENT_EVIDENCE"

                state.stopping_reason = (

                    "Evidence is insufficient and the replanning "

                    "model call failed safely."

                )

                break

            replanning_validation = validate_replanning_response(

                replanning_response

            )



            trace.append(

                create_trace_event(

                    run_id=run_id,

                    turn=turn,

                    action="validate_replanning_response",

                    status=(

                        "VALID"

                        if replanning_validation["valid"]

                        else "INVALID"

                    ),

                    details=replanning_validation,

                )

            )



            if replanning_validation["valid"]:

                revised_keywords = parse_revised_keywords(

                    replanning_response

                )



                if revised_keywords == state.keywords:

                    state.status = "INSUFFICIENT_EVIDENCE"

                    state.stopping_reason = (

                        "Evidence is insufficient and replanning "

                        "repeated the current search keywords."

                    )

                    break



                state.keywords = [anchor_agent_query(k, research_question) for k in revised_keywords]

                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="apply_revised_keywords",

                        status="COMPLETED",

                        details={"revised_keywords": revised_keywords},

                    )

                )

                trace.append(

                    create_trace_event(

                        run_id=run_id,

                        turn=turn,

                        action="replanning_requested",

                        status="ALLOWED",

                        details={

                            "attempt": state.replanning_attempts,

                            "gaps": state.gaps,

                            "context": replanning_context,

                        },

                    )

                )

                state.status = "REPLANNING"

                state.stopping_reason = None

                continue



            state.status = "INSUFFICIENT_EVIDENCE"

            state.stopping_reason = (

                "Evidence is insufficient and replanning failed validation."

            )

            break



        state.status = "INSUFFICIENT_EVIDENCE"



        if not state.retrieved_papers:

            state.stopping_reason = (

                "Evidence is insufficient because repeated searches "

                "returned no papers."

            )

        elif len(state.retrieved_papers) == previous_retrieved_count:

            state.stopping_reason = (

                "Evidence is insufficient because repeated searches "

                "produced no new papers."

            )

        else:

            state.stopping_reason = (

                "Evidence is insufficient and the replanning limit "

                "has been reached."

            )



        break

    if state.status not in TERMINAL_STATES:

        state.status = "BUDGET_EXHAUSTED"

        state.stopping_reason = "Maximum number of agent turns reached."



    return {

        "status": state.status,

        "run_id": state.run_id,

        "turns": state.iteration,

        "reason": state.stopping_reason,

        "replanning_attempts": state.replanning_attempts,

        "trace": trace,

        "gaps": state.gaps,

        "evidence": state.evidence,

        "selected_papers": state.selected_papers,

        "excluded_papers": state.excluded_papers,
        "deferred_papers": state.deferred_papers,

        "synthesis": synthesis_result,

        "review_request": review_request,

    }
