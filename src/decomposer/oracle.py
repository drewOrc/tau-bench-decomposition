"""Oracle decomposer for ceiling analysis.

Loads pre-defined gold-standard sub-goals from a JSON file, keyed by task
index. Returns perfect sub-goals that a human would extract from the user's
first utterance, based on ground-truth action analysis.

This is NOT a real decomposer — it's an experimental upper bound ("if the
agent had perfect sub-goal knowledge, how much would it help?"). Zero API
cost, sub-millisecond latency.

Usage:
    from decomposer.oracle import OracleDecomposer
    d = OracleDecomposer()              # loads data/oracle_subgoals.json
    result = d.decompose("...", domain="retail", task_index=3)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Decomposer, DecompositionResult, SubGoal

# Default path relative to project root
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "oracle_subgoals.json"


class OracleDecomposer(Decomposer):
    """Looks up gold-standard sub-goals by task_index."""

    name = "oracle"

    def __init__(self, json_path: Optional[Path] = None) -> None:
        path = json_path or _DEFAULT_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Oracle sub-goals file not found: {path}\n"
                "Create it with gold-standard annotations first."
            )
        with open(path) as f:
            raw: Dict[str, Any] = json.load(f)

        # Parse into {int_task_id: List[SubGoal]}
        self._goals: Dict[int, List[SubGoal]] = {}
        for key, entry in raw.items():
            if key.startswith("_"):
                continue  # skip metadata keys like "_meta"
            task_id = int(key)
            sub_goals: List[SubGoal] = []
            for sg in entry["sub_goals"]:
                sub_goals.append(
                    SubGoal(
                        action_type=sg["action_type"],
                        entity=sg["entity"],
                        constraint=sg.get("constraint"),
                        raw_span=None,
                        confidence=1.0,
                    )
                )
            self._goals[task_id] = sub_goals

        self._covered_task_ids = set(self._goals.keys())

    @property
    def covered_task_ids(self) -> set:
        """Task indices that have gold sub-goals."""
        return self._covered_task_ids

    def decompose(
        self,
        user_utterance: str,
        domain: str = "retail",
        **kwargs: Any,
    ) -> DecompositionResult:
        """Return gold sub-goals for the given task_index.

        Args:
            user_utterance: First user message (logged but not parsed).
            domain: "retail" or "airline".
            **kwargs: Must include ``task_index`` (int) for oracle lookup.

        Returns:
            DecompositionResult with gold sub-goals, or empty if task_index
            is not in the oracle data.
        """
        t0 = time.perf_counter()
        task_index: Optional[int] = kwargs.get("task_index")

        if task_index is None:
            raise ValueError(
                "OracleDecomposer requires task_index kwarg. "
                "Got None — ensure agent.solve() passes task_index to "
                "decomposer.decompose()."
            )

        # Thread-safe: self._goals is read-only after __init__ (no mutation).
        sub_goals = self._goals.get(task_index, [])
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return DecompositionResult(
            sub_goals=sub_goals,
            source="oracle",
            raw_input=user_utterance,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
        )


if __name__ == "__main__":
    d = OracleDecomposer()
    print(f"Loaded oracle sub-goals for {len(d.covered_task_ids)} tasks: "
          f"{sorted(d.covered_task_ids)}")

    # Demo: task 19 (return water bottle + exchange pet bed + office chair)
    result = d.decompose(
        "I want to return the water bottle and exchange the pet bed...",
        domain="retail",
        task_index=19,
    )
    print(f"\nTask 19 ({len(result.sub_goals)} sub-goals):")
    print(result.to_system_hint())
    print(f"latency: {result.latency_ms:.3f}ms, cost: ${result.cost_usd}")

    # Demo: task not in oracle (returns empty sub-goals)
    result2 = d.decompose("Some other task", domain="retail", task_index=999)
    print(f"\nTask 999: {len(result2.sub_goals)} sub-goals (expected 0)")

    # Demo: missing task_index raises ValueError
    try:
        d.decompose("No task index")
    except ValueError as e:
        print(f"\nCorrectly raised ValueError: {e}")
