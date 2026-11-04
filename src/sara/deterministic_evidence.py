"""Auditable extractive-only abstract processing; never generates scientific facts."""
import json
import re
from .source_first import abstract_sentences

PATTERNS = {
    'objective': r'\b(aims? to|objective(?:s)? (?:is|are|of)|purpose (?:is|of)|we (?:aim|propose|introduce|investigate|examine|evaluate|study|present|provide|develop|assess|analyze|analyse)|this (?:paper|study|work|survey) (?:proposes|introduces|investigates|examines|evaluates|studies|presents|provides|analyzes|analyses|surveys))\b',
    'methodology': r'\b(we (?:use|employ|apply|compare|evaluate|test)|using|via|through|experiment(?:s|al)?|benchmark(?:ed|ing)?|framework|taxonomy|protocol|metric(?:s)?|human (?:judg|evaluat)|correlation|methodolog)\w*\b',
    'dataset_sample': r'\b(dataset(?:s)?|data set(?:s)?|sample(?:s)?|corpus|participants|annotated|conversations|instances|benchmark dataset|[0-9][0-9,]*\s+(?:tasks?|cases?|examples?|episodes?|trials?|participants?|conversations?|queries?|images?))\b',
    'findings': r'\b(we (?:find|found|show|demonstrate|observe)|results? (?:show|indicate|demonstrate|reveal|suggest)|our (?:results|findings|analysis) (?:show|reveal|indicat|suggest|found|demonstrat)\w*|outperform\w*|achiev\w*|improv\w*)\b',
    'limitations': r'\b(limitations?|challenges?|critical gaps?|(?:we|this (?:paper|study)) (?:identify|highlight|discuss) (?:important |critical )?(?:gaps?|challenges?|limitations?)|future work|weakness(?:es)?|constraints?|shortcomings?|failure modes?|bias(?:es)?)\b',
}

_EXPLICIT_SAMPLE = re.compile(
    r'\b(?:[0-9][0-9,]*\s+(?:human[- ]annotated\s+)?(?:tasks?|cases?|examples?|episodes?|trials?|participants?|conversations?|queries?|images?|trajector(?:y|ies)|apps?|papers?|studies?|records?|samples?|benchmarks?|datasets?)|\b(?:dataset|corpus|sample)\s+(?:compris(?:e|es)|consist(?:s)? of|contain(?:s)?|with)\s+[0-9]|\b(?:using|on|from|with)\s+(?:the\s+)?[A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3}\s+(?:dataset|corpus))\b',
    re.I,
)


def extract_abstract_json(abstract: str) -> str:
    """Return verbatim abstract sentences only; missing fields remain empty.

    Questions and entailment are handled independently by source-first verification.
    """
    sentences = abstract_sentences(abstract)
    result = {}
    for field, pattern in PATTERNS.items():
        matches = [s for s in sentences if re.search(pattern, s, re.I)]
        if field == 'methodology':
            matches.sort(key=lambda text: (
                bool(re.search(r'\b(?:we (?:use|employ|apply|compare|test|propose)|taxonomy|protocol|experimental setup)\b', text, re.I)),
                bool(re.search(r'\b(?:methodology|method|framework|benchmark)\b', text, re.I)),
            ), reverse=True)
        if field == 'dataset_sample':
            # A generic discussion of datasets does not report a real sample.
            matches = [s for s in matches if _EXPLICIT_SAMPLE.search(s)]
        # A single best exact source sentence is more auditable than merging
        # unrelated sentences into a pseudo-result. Never fill gaps by inference.
        result[field] = matches[0] if matches else ''
    result.update(supported_subquestions=[], supporting_evidence=[], question_evidence={})
    return json.dumps(result, ensure_ascii=False)



def classify_study_type(title: str, abstract: str) -> str:
    """Report study design only when publication metadata explicitly supports it.

    The design label is diagnostic: it never fabricates a missing sample or
    silently removes a required field from the sufficiency calculation.
    """
    import re
    title, abstract = str(title or ''), str(abstract or '')
    if re.search(r'\b(?:systematic review|systematic literature review|meta-analysis)\b', title, re.I):
        return 'systematic_review'
    if re.search(r'\b(?:survey|scoping review|narrative review|literature review)\b', title, re.I):
        return 'narrative_review'
    if re.search(r'\b(?:empirical study|controlled study|randomized trial|case stud(?:y|ies))\b', title, re.I):
        return 'empirical'
    if re.search(r'\b(?:we (?:evaluate|test|experiment)|experiment(?:s)? (?:show|demonstrate)|\d+[\d,]*\s+(?:trials?|tasks?|participants?))\b', abstract, re.I):
        return 'empirical'
    return 'unknown'


def extract_open_text_json(text: str) -> str:
    """Extract independent source-exact paragraphs from a structured open text.

    The extraction is conservative and never infers unreported results. Section
    headings are only weak prioritization; matched spans remain verbatim.
    """
    sections = []
    current = 'unknown'
    for line in str(text or '').splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r'(?:\d+(?:\.\d+)*\s+)?(abstract|introduction|background|methods?|materials and methods|'
                             r'experimental setup|experiments?|evaluation|results?|findings|discussion|'
                             r'limitations?|conclusions?|data|datasets?|study design)', line, re.I)
        if match:
            current = match.group(1).lower()
        elif len(line) >= 35:
            for sentence in abstract_sentences(line):
                if len(sentence) <= 1000:
                    sections.append((current, sentence))
    if not sections:
        return extract_abstract_json(text)
    cues = {
        'objective': r'\b(?:we (?:aim|propose|introduce|study|present|investigate|develop)|this (?:paper|study) (?:presents|proposes|introduces)|our objective)\b',
        'methodology': r'\b(?:we (?:use|used|employ|employed|apply|applied|evaluate|evaluated|conducted|test|tested|compare|compared)|experimental (?:setup|design)|evaluation protocol|methodology)\b',
        'dataset_sample': _EXPLICIT_SAMPLE.pattern,
        'findings': r'\b(?:results? (?:show|showed|indicate|indicated|demonstrate|demonstrated|reveal|revealed)|we (?:find|found|observed)|our findings|outperform\w*|achiev\w*)\b',
        'limitations': r'\b(?:limitations?|shortcomings?|weakness(?:es)?|failure modes?|future work|we identify (?:a )?(?:gap|risk|challenge))\b',
    }
    priority = {
        'objective': ('abstract', 'introduction'),
        'methodology': ('method', 'experimental', 'evaluation', 'study design'),
        'dataset_sample': ('method', 'data', 'dataset', 'experimental', 'evaluation'),
        'findings': ('results', 'finding', 'discussion'),
        'limitations': ('limitation', 'discussion', 'conclusion'),
    }
    result = {}
    used = set()
    for field in ('dataset_sample', 'findings', 'limitations', 'objective', 'methodology'):
        matches = []
        for index, (section, sentence) in enumerate(sections):
            if sentence in used or not re.search(cues[field], sentence, re.I):
                continue
            if field == 'dataset_sample' and not _EXPLICIT_SAMPLE.search(sentence):
                continue
            if field == 'limitations' and re.search(r'\b(?:we propose|we introduce|this paper introduces)\b', sentence, re.I):
                continue
            pref = any(section.startswith(key) for key in priority[field])
            matches.append((not pref, index, sentence))
        matches.sort()
        result[field] = matches[0][2] if matches else ''
        if result[field]:
            used.add(result[field])
    result.update(supported_subquestions=[], supporting_evidence=[], question_evidence={})
    return json.dumps(result, ensure_ascii=False)
