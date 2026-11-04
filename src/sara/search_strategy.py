"""Bounded, auditable search expansion. This module never generates evidence."""
import re
import os

_RELIABILITY_TERMS = re.compile(r"\b(?:reliab\w*|robust\w*|consisten\w*|benchmark\w*|evaluat\w*|verif\w*)\b", re.I)
_AGENT_TERMS = re.compile(r"\b(?:llm[- ]based\s+)?agents?\b", re.I)


def reliability_search_variants(research_question: str) -> list[str]:
    """Expand agent-reliability searches across independent evaluation dimensions.

    These are *search phrases*, not subquestions, results, or evidence claims.
    For other research subjects, return no domain-specific expansions.
    """
    if not (_AGENT_TERMS.search(research_question or '') and _RELIABILITY_TERMS.search(research_question or '')):
        return []
    if not re.search(r"\b(?:llms?|large language models?)\b", research_question, re.I):
        return []
    return [
        'LLM agent reliability evaluation benchmark metrics',
        'LLM agent reliability human evaluator agreement',
        'LLM agent evaluation robustness failure modes',
    ]


def choose_turn_queries(keywords: list[str], research_question: str, used: set[str],
                        limit: int = 1) -> list[str]:
    """Choose at most `limit` distinct queries, preserving the planner's first query.

    Each chosen query is recorded in `used`. Excludes empty/duplicate search strings.
    The fixed expansion is an opt-in convenience, never an invented literature result.
    """
    if type(limit) is not int or not 1 <= limit <= 3:
        raise ValueError('Search-query limit must be between 1 and 3')
    variants = reliability_search_variants(research_question)
    if os.getenv("SARA_DIVERSIFIED_SEARCH", "0") == "1" and limit == 3 and variants:
        # Same bounded query set across repeated benchmark runs; each phrase
        # targets a different dimension, without rewriting the original RQ.
        candidates = [*variants, *keywords]
    else:
        candidates = ([*keywords[:1], *variants, *keywords[1:]]
                      if limit > 1 else list(keywords))
    queries = []
    for raw in candidates:
        if not isinstance(raw, str):
            continue
        phrase = ' '.join(raw.split())
        if not phrase or len(phrase) > 250 or phrase.casefold() in used:
            continue
        used.add(phrase.casefold())
        queries.append(phrase)
        if len(queries) == limit:
            break
    return queries
