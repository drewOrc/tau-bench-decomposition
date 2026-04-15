"""Base interface for task decomposers.

A decomposer takes a user utterance (usually the first user message of an
episode, but can be called incrementally) and returns a structured list of
sub-goals that the agent should aim to achieve.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SubGoal:
    """One unit of work the agent should complete."""

    action_type: str          # e.g. "RETURN", "EXCHANGE", "CANCEL", "MODIFY", "BOOK"
    entity: str               # e.g. order id, item name, flight reservation id
    constraint: Optional[str] = None  # user preference or filter
    raw_span: Optional[str] = None    # original text span that produced this
    confidence: float = 1.0           # 0..1 for ranking if desired

    def to_bullet(self) -> str:
        c = f" [{self.constraint}]" if self.constraint else ""
        return f"- {self.action_type}: {self.entity}{c}"


@dataclass
class DecompositionResult:
    sub_goals: List[SubGoal] = field(default_factory=list)
    source: str = ""          # "rule-based" | "tiny-lm" | ...
    raw_input: str = ""
    cost_usd: float = 0.0     # 0 for rule-based
    latency_ms: float = 0.0

    def to_system_hint(self) -> str:
        """Format sub-goals as a system prompt snippet."""
        if not self.sub_goals:
            return ""
        lines = ["<sub_goals>",
                 "The user's request likely contains these sub-goals. "
                 "Verify with the user and address each before finishing:"]
        for sg in self.sub_goals:
            lines.append(sg.to_bullet())
        lines.append("</sub_goals>")
        return "\n".join(lines)


class Decomposer(ABC):
    """Abstract decomposer."""

    name: str = "base"

    @abstractmethod
    def decompose(self, user_utterance: str, domain: str = "retail", **kwargs) -> DecompositionResult:
        ...

    def refresh(
        self,
        prior: DecompositionResult,
        new_user_utterance: str,
        domain: str = "retail",
    ) -> DecompositionResult:
        """Default: re-run from scratch on concatenated input.

        Subclasses can override for incremental updates.
        """
        combined = prior.raw_input + "\n" + new_user_utterance if prior.raw_input else new_user_utterance
        return self.decompose(combined, domain=domain)
