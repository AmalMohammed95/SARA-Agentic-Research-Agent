"""Auditable extractive-only abstract processing; never generates scientific facts."""
import json
import re
from .source_first import abstract_sentences

PATTERNS = {
    'objective': r'\b(aims? to|objective(?:s)? (?:is|are|of)|purpose (?:is|of)|we (?:aim|propose|introduce|investigate|examine|evaluate|study|present|provide|develop|assess|analyze|analyse)|this (?:paper|study|work|survey) (?:proposes|introduces|investigates|examines|evaluates|studies|presents|provides|analyzes|analyses|surveys))\b',
    'methodology': r'\b(we (?:use|employ|apply|compare|evaluate|test)|using|via|through|experiment(?:s|al)?|benchmark(?:ed|ing)?|framework|taxonomy|protocol|metric(?:s)?|human (?:judg|evaluat)|correlation|methodolog)\w*\b',
    'dataset_sample': r'\b(dataset(?:s)?|data set(?:s)?|sample(?:s)?|corpus|participants|annotated|conversations|instances|benchmark dataset|[0-9][0-9,]*\s+(?:tasks?|cases?|examples?|episodes?|trials?|participants?|conversations?|queries?|images?))\b',
    'findings': r'\b(we (?:find|found|show|demonstrate|observe)|results? (?:show|indicate|demonstrate|reveal|suggest)|our (?:results|findings)|outperform\w*|achiev\w*|improv\w*)\b',
    'limitations': r'\b(limitations?|challenges?|critical gaps?|(?:we|this (?:paper|study)) (?:identify|highlight|discuss) (?:important |critical )?(?:gaps?|challenges?|limitations?)|future work|weakness(?:es)?|constraints?|shortcomings?|failure modes?|bias(?:es)?)\b',
}

def extract_abstract_json(abstract: str) -> str:
    """Return verbatim abstract sentences only; missing fields remain empty.

    Questions and entailment are handled independently by source-first verification.
    """
    sentences = abstract_sentences(abstract)
    result = {}
    for field, pattern in PATTERNS.items():
        matches = [s for s in sentences if re.search(pattern, s, re.I)]
        result[field] = ' '.join(matches[:2]) if matches else ''
    result.update(supported_subquestions=[], supporting_evidence=[], question_evidence={})
    return json.dumps(result, ensure_ascii=False)
