"""Rule-based decomposer (Option A).

Cheap baseline. Uses regex on action verbs + entity mentions.
Zero API cost, sub-millisecond latency.

This is intentionally simple. If it works, it's the strongest possible argument
for "cheap decomposer is enough". If it flops, we fall back to tiny_lm.py.
"""

from __future__ import annotations

import re
import time
from typing import Dict, List

from .base import Decomposer, DecompositionResult, SubGoal


# Action verb → canonical sub-goal type, per domain.
# These patterns are designed to be high-precision, low-recall.
RETAIL_VERBS: Dict[str, List[str]] = {
    "RETURN":   [r"\breturn(ing|ed)?\b", r"\brefund\b"],
    "EXCHANGE": [r"\bexchange(d|ing)?\b", r"\bswap\b", r"\breplace\b"],
    "CANCEL":   [r"\bcancel(led|ing)?\b"],
    "MODIFY":   [r"\bmodif(y|ied|ying)\b", r"\bchange\b", r"\bupdate\b"],
    "ADDRESS":  [r"\baddress\b", r"\bshipping\b"],
    "INFO":     [r"\btracking\b", r"\bprice\b", r"\bstatus\b"],
}

AIRLINE_VERBS: Dict[str, List[str]] = {
    "BOOK":     [r"\bbook(ing|ed)?\b", r"\breserv(e|ing|ation)\b"],
    "CANCEL":   [r"\bcancel(led|ing)?\b"],
    "CHANGE":   [r"\bchange\b", r"\breschedul(e|ing|ed)\b", r"\bswitch\b"],
    "BAGGAGE":  [r"\bbaggage\b", r"\bluggage\b", r"\bbags?\b"],
    "REFUND":   [r"\brefund\b", r"\bcertificate\b"],
    "UPDATE":   [r"\bupdate\b", r"\bmodif(y|ied|ying)\b"],
}

# Entity patterns: order IDs, reservation IDs, product names
ORDER_ID_PAT = re.compile(r"#?W\d{7,}")
RESERVATION_ID_PAT = re.compile(r"\b[A-Z0-9]{6,7}\b")
ITEM_MENTION_PAT = re.compile(
    r"\b(water bottle|desk lamp|pet bed|office chair|thermostat|keyboard|"
    r"headphones|speaker|tablet|monitor|lamp|t-?shirt|backpack|watch|camera|"
    r"phone case|sneakers|jacket|mug|blender|vacuum)\b", re.IGNORECASE,
)
FLIGHT_CITY_PAT = re.compile(
    r"\b(NYC|LAX|SFO|SF|LA|JFK|EWR|BOS|ORD|DFW|DEN|SEA|MIA|ATL|PHX|MSP|IAH|LAS|DTW|PHL|CLT|BWI)\b"
)
CHEAPEST_PAT = re.compile(r"\bcheap(est)?\b", re.IGNORECASE)
PREF_PAT = re.compile(r"\bprefer(s|red)?\b", re.IGNORECASE)


def _find_entities(text: str, domain: str) -> List[str]:
    entities: List[str] = []
    if domain == "retail":
        entities.extend(ORDER_ID_PAT.findall(text))
        entities.extend(m.group(0).lower() for m in ITEM_MENTION_PAT.finditer(text))
    elif domain == "airline":
        entities.extend(RESERVATION_ID_PAT.findall(text))
        entities.extend(m.group(0).upper() for m in FLIGHT_CITY_PAT.finditer(text))
    # dedupe preserving order
    seen: set = set()
    uniq: List[str] = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq


def _find_constraint(text: str) -> str:
    c = []
    if CHEAPEST_PAT.search(text):
        c.append("cheapest")
    if PREF_PAT.search(text):
        # Extract "prefer X" phrase
        m = re.search(r"prefer(?:s|red)?\s+([^.,;\n]+)", text, re.IGNORECASE)
        if m:
            c.append(f"prefers {m.group(1).strip()[:40]}")
    return "; ".join(c) if c else ""


class RuleBasedDecomposer(Decomposer):
    name = "rule-based"

    def decompose(
        self, user_utterance: str, domain: str = "retail", **kwargs
    ) -> DecompositionResult:
        t0 = time.perf_counter()
        verbs = RETAIL_VERBS if domain == "retail" else AIRLINE_VERBS
        text = user_utterance
        sub_goals: List[SubGoal] = []

        # Split on sentence-ish boundaries so each sub-goal comes from one clause.
        clauses = re.split(r"(?:\.|\band\b|\bthen\b|,\s+also)", text, flags=re.IGNORECASE)
        constraint_global = _find_constraint(text)
        for clause in clauses:
            clause = clause.strip()
            if len(clause) < 6:
                continue
            matched_verb = None
            for verb_type, patterns in verbs.items():
                if any(re.search(p, clause, re.IGNORECASE) for p in patterns):
                    matched_verb = verb_type
                    break
            if not matched_verb:
                continue
            entities = _find_entities(clause, domain)
            entity_str = ", ".join(entities) if entities else "(entity unclear)"
            sub_goals.append(
                SubGoal(
                    action_type=matched_verb,
                    entity=entity_str,
                    constraint=constraint_global or None,
                    raw_span=clause[:120],
                    confidence=0.7 if entities else 0.4,
                )
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return DecompositionResult(
            sub_goals=sub_goals,
            source="rule-based",
            raw_input=user_utterance,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
        )


if __name__ == "__main__":
    # Quick smoke test
    d = RuleBasedDecomposer()
    sample = (
        "You want to return the water bottle, and exchange the pet bed and "
        "office chair to the cheapest version. You prefer battery > USB > AC."
    )
    r = d.decompose(sample, domain="retail")
    print(r.to_system_hint())
    print(f"latency: {r.latency_ms:.2f}ms, cost: ${r.cost_usd}")
