"""Conservative guard against losing agent-specific scope during planning.

This does not infer evidence or change the sufficiency thresholds.
"""
import re

_AGENT = re.compile(r"\b(?:agents?|agentic|multi[- ]agent)\b", re.I)
_LLM = re.compile(r"\b(?:llms?|large language models?)\b", re.I)


def requires_agent_scope(research_question: str) -> bool:
    return bool(_AGENT.search(research_question or "") and _LLM.search(research_question or ""))


def anchor_agent_query(query: str, research_question: str) -> str:
    """Keep a generated query specific to LLM agents when that is the subject."""
    query = (query or "").strip()
    if requires_agent_scope(research_question) and not _AGENT.search(query):
        return ("LLM agents " + query).strip()
    return query


def anchor_agent_subquestions(subquestions: list[str], research_question: str) -> list[str]:
    """Qualify broad generated questions without asserting they are answered."""
    if not requires_agent_scope(research_question):
        return subquestions
    result = []
    for question in subquestions:
        if not isinstance(question, str):
            result.append(question)
            continue
        q = question.strip()
        if q and not _AGENT.search(q):
            q = q.rstrip(' ?') + ' for LLM agents?'
        result.append(q)
    return result


def flag_scope_drift(subquestions: list[str], research_question: str) -> list[str]:
    """Diagnostics only: suspicious questions require human review, not auto-approval."""
    if not requires_agent_scope(research_question):
        return []
    return [q for q in subquestions if isinstance(q, str)
            and re.search(r"\bpeer[- ]review (?:process|procedure|workflow)", q, re.I)]

# Planning failures must be corrected before retrieval, not compensated for
# by extracting evidence against an unrelated research subquestion.
_DRIFT = re.compile(
    r"\bpeer[- ]reviews?\b|\bliterature reviews?\b|\bpublication process\b",
    re.I,
)
_RELIABILITY = re.compile(r"\breliab|\brobust|\bconsisten|\breproducib|\bvalid|\bevaluat|\bbenchmark|\bassess|\bverif|\btest", re.I)


def repair_reliability_plan(subquestions: list[str], research_question: str) -> tuple[list[str], list[str]]:
    """Conservatively repair off-topic questions for agent reliability research.

    Repairs are explicitly reported; the original question remains unchanged.
    This does not assert evidence or bypass subsequent evidence verification.
    """
    if not (requires_agent_scope(research_question) and _RELIABILITY.search(research_question)):
        return subquestions, []
    repaired, warnings = [], []
    for question in subquestions:
        if isinstance(question, str) and _DRIFT.search(question):
            warnings.append(question)
            repaired.append('How are LLM agent reliability evaluations validated against human judgments and reproducible benchmarks?')
        else:
            repaired.append(question)
    # Avoid redundant coverage questions; ensure distinct research dimensions.
    fallback = [
        'What methods and benchmarks measure the reliability of LLM agents?',
        'How are LLM agent reliability evaluations validated against human judgments and reproducible benchmarks?',
        'What limitations and failure modes affect the reliability evaluation of LLM agents?',
    ]
    seen = set()
    for index, question in enumerate(repaired):
        key = str(question).strip().casefold()
        if key in seen or not key:
            replacement = next((q for q in fallback if q.casefold() not in seen), fallback[index % len(fallback)])
            warnings.append(str(question))
            repaired[index] = replacement
            key = replacement.casefold()
        seen.add(key)
    return repaired, warnings


_STABLE_RELIABILITY_DIMENSIONS = [
    'Which evaluation metrics and benchmarks assess the reliability of LLM agents?',
    'How is consistency and robustness of LLM agents tested across repeated tasks?',
    'Which limitations and reproducibility challenges affect reliability evaluation of LLM agents?',
]


def stable_reliability_subquestions(research_question: str) -> list[str]:
    """Return transparent, reproducible dimensions for broad agent-reliability evaluation.

    Never alter a narrow question such as one specifically about finance or a
    named benchmark. This is an experimental fixed plan, not a scientific fact.
    """
    q = (research_question or '').lower()
    broad = (requires_agent_scope(research_question)
             and bool(re.search(r'\breliab\w*\b', q))
             and bool(re.search(r'\b(?:evaluat\w*|assess\w*|measur\w*|method\w*)\b', q))
             and bool(re.match(r'^\s*(?:what|how|which)\b', q)))
    narrow = bool(re.search(r'\b(?:financial|finance|healthcare|clinical|mobile|voice|trading|medical|security patch|named benchmark)\b', q))
    return list(_STABLE_RELIABILITY_DIMENSIONS) if broad and not narrow else []
