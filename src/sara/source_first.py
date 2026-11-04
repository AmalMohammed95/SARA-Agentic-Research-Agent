"""Source-anchored candidate retrieval for scientific evidence review.

Only source-exact sentences are returned. Ranking prioritizes sentences that
actually describe the requested evidence type; this is retrieval, *not* proof
of entailment. Every candidate still requires independent verification.
"""
import re

_STOP = frozenset('what which how are is the a an of in for to do does and or with by from on used use researchers studies study agents llm llms methods common evaluating evaluation assess assessing academic research'.split())

# Intent-specific cues improve retrieval when a question and an abstract use
# different terms (e.g. "validation" vs "human agreement"). These lists only
# rank source passages; they never authorize scientific claims.
_INTENT_CUES = {
    'methods': ('benchmark', 'metric', 'repeat', 'trial', 'failure rate', 'success rate',
                'evaluation protocol', 'task completion', 'experiment', 'measure',
                'test set', 'accuracy', 'robustness', 'human rating', 'rubric'),
    'validation': ('human judg', 'human evaluat', 'human annotat', 'human rat',
                   'agreement', 'correlation', 'calibrat', 'reproduc', 'gold standard',
                   'ground truth', 'reference label', 'benchmark', 'inter-rater'),
    'challenges': ('limitation', 'challenge', 'bias', 'failure', 'contaminat',
                   'robustness', 'unreliab', 'shortcoming', 'cost', 'scalab',
                   'generaliz', 'risk', 'uncertain'),
}


def abstract_sentences(abstract: str) -> list[str]:
    if not isinstance(abstract, str) or not abstract.strip():
        return []
    # Scholarly metadata can remove whitespace between sentences ("...methods.We").
    # Keep the original character spans for exact source verification.
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“])|(?<=[.!?])(?=[A-Z][a-z])', abstract.strip())
    return [s.strip() for s in parts if len(s.strip()) >= 35]


def _tokens(value: str) -> set[str]:
    return {w for w in re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', value.lower()) if len(w) > 2 and w not in _STOP}


def _intent(question: str) -> str | None:
    q = question.lower()
    if re.search(r'\b(validat\w*|human judg\w*|reproduc\w*|calibrat\w*|agreement)\b', q):
        return 'validation'
    if re.search(r'\b(challenge\w*|limitation\w*|difficult\w*|weakness\w*|failure modes?|risks?)\b', q):
        return 'challenges'
    if re.search(r'\b(method\w*|measur\w*|assess\w*|evaluat\w*|metric\w*|benchmark\w*)\b', q):
        return 'methods'
    return None


def source_candidates(abstract: str, question: str, limit: int = 3) -> list[str]:
    """Return up to ``limit`` relevant verbatim sentences, best first.

    Do not send zero-signal passages for semantic verification: that wastes
    model calls and may invite spurious topic-level endorsements.
    """
    terms = _tokens(question)
    intent = _intent(question)
    cues = _INTENT_CUES.get(intent, ())
    ranked = []
    for index, sentence in enumerate(abstract_sentences(abstract)):
        overlap = len(terms & _tokens(sentence))
        cue_count = sum(cue in sentence.lower() for cue in cues)
        score = overlap + min(cue_count, 3) * 2
        if score:
            ranked.append((-score, -cue_count, index, sentence))
    ranked.sort()
    return [sentence for _, _, _, sentence in ranked[:max(0, limit)]]


def build_multi_source_mapping(abstract: str, questions: list[str], existing: dict) -> tuple[dict, dict]:
    """Provide up to three distinct source-exact candidates for each question."""
    from .extraction import verify_supporting_evidence
    existing = existing if isinstance(existing, dict) else {}
    mapping, diagnostics = {}, {}
    for question in questions:
        candidates = []
        quote = existing.get(question)
        if isinstance(quote, str) and verify_supporting_evidence(abstract, [quote])['verified']:
            candidates.append(quote)
        for candidate in source_candidates(abstract, question, limit=3):
            if candidate not in candidates:
                candidates.append(candidate)
        candidates = candidates[:3]
        if candidates:
            mapping[question] = candidates
            diagnostics[question] = ('model_quote_exact' if isinstance(quote, str) and quote in candidates else 'source_sentence_candidate_unverified_semantics')
        else:
            diagnostics[question] = 'no_source_candidate'
    return mapping, diagnostics


def build_source_first_mapping(abstract: str, questions: list[str], existing: dict) -> tuple[dict, dict]:
    """Backward-compatible single best candidate API."""
    multi, diagnostics = build_multi_source_mapping(abstract, questions, existing)
    return {q: quotes[0] for q, quotes in multi.items()}, diagnostics
