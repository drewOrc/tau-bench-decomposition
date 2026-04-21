"""Task decomposers for τ-bench."""

from .base import Decomposer, DecompositionResult, SubGoal
from .rule_based import RuleBasedDecomposer

try:
    from .tiny_lm import TinyLMDecomposer
except ImportError:
    TinyLMDecomposer = None  # type: ignore

try:
    from .same_model import SameModelDecomposer
except ImportError:
    SameModelDecomposer = None  # type: ignore

__all__ = [
    "Decomposer",
    "DecompositionResult",
    "SubGoal",
    "RuleBasedDecomposer",
    "TinyLMDecomposer",
    "SameModelDecomposer",
]
