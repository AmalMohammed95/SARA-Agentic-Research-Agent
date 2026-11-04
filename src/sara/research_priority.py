"""Bounded prioritization of papers with transparent, deterministic ranking."""
import re

def rank_papers(papers, questions, attempts=None):
    attempts = attempts or {}
    terms = set()
    for q in questions:
        terms.update(re.findall(r"[a-z]{5,}", str(q).lower()))
    terms -= {"which", "their", "these", "those", "about", "agents", "academic", "research"}
    def score(p):
        text = (str(p.get("title") or "") + " " + str(p.get("abstract") or "")).lower()
        title = str(p.get("title") or "").lower()
        overlap = sum(bool(re.search(r"\b" + re.escape(t) + r"\b", text)) for t in terms)
        agent = bool(re.search(r"\b(?:llm[- ]based |llm |multi[- ]?)?agents?\b", title))
        assessment = bool(re.search(r"evaluat|benchmark|reliab|robust|failure|assess", title))
        return (-int(agent and assessment), -overlap,
                attempts.get(p.get("doi") or p.get("id"), 0),
                str(p.get("doi") or p.get("id") or p.get("title")))
    return sorted(papers, key=score)
