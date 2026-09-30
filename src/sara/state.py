"""
State management for SARA.

This module defines the working state maintained during a single
agent run. It stores observable research progress and evidence,
not private model reasoning.
"""

from dataclasses import dataclass, field


@dataclass
class AgentState:
    """
    Working state for a single SARA research run.
    """

    research_question: str
    run_id: str

    iteration: int = 0

    subquestions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    retrieved_papers: list[dict] = field(default_factory=list)
    selected_papers: list[dict] = field(default_factory=list)
    excluded_papers: list[dict] = field(default_factory=list)

    evidence: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    status: str = "INITIALIZED"
    stopping_reason: str | None = None