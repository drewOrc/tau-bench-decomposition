"""Tiny-LM decomposer (Option C).

Uses Claude Haiku 4.5 to parse user utterance into structured sub-goals.
Cost: ~$0.0005 per call. Latency: ~0.5-1.5s.
"""

from __future__ import annotations

import json
import os
import time
from typing import List, Optional

from .base import Decomposer, DecompositionResult, SubGoal


SYSTEM_PROMPT = """You decompose a customer-service user request into sub-goals.

Output STRICT JSON with a single key "sub_goals" mapping to a list.
Each sub-goal object must have:
  - "action_type": one of (RETURN, EXCHANGE, CANCEL, MODIFY, ADDRESS, BOOK, CHANGE, BAGGAGE, REFUND, INFO, OTHER)
  - "entity": the thing being acted on (order id, item name, reservation id, etc.)
  - "constraint": optional user preference (e.g. "cheapest", "prefers USB") or null

Rules:
- Only include sub-goals explicitly mentioned or strongly implied.
- Do not hallucinate entities.
- If the user just wants info, use action_type=INFO.
- If unsure of entity, use "(unclear)".

Example input: "I want to return the water bottle and exchange the pet bed to the cheapest version."
Example output: {"sub_goals":[{"action_type":"RETURN","entity":"water bottle","constraint":null},{"action_type":"EXCHANGE","entity":"pet bed","constraint":"cheapest"}]}

Output ONLY the JSON, no prose."""


class TinyLMDecomposer(Decomposer):
    name = "tiny-lm-haiku"

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: Optional[str] = None,
        max_tokens: int = 400,
    ) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError("pip install anthropic") from e
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens

    def _parse_response(self, text: str) -> List[SubGoal]:
        # Strip any code fence
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            if t.startswith("json"):
                t = t[4:].strip()
        try:
            data = json.loads(t)
        except json.JSONDecodeError:
            # Try to find JSON object inside text
            start = t.find("{")
            end = t.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(t[start : end + 1])
            else:
                return []
        sub_goals: List[SubGoal] = []
        for item in data.get("sub_goals", []):
            sub_goals.append(
                SubGoal(
                    action_type=item.get("action_type", "OTHER"),
                    entity=item.get("entity", "(unclear)"),
                    constraint=item.get("constraint") or None,
                    confidence=0.8,
                )
            )
        return sub_goals

    def decompose(
        self, user_utterance: str, domain: str = "retail", **kwargs
    ) -> DecompositionResult:
        t0 = time.perf_counter()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"[domain={domain}]\n{user_utterance}"}],
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        text = resp.content[0].text if resp.content else ""
        sub_goals = self._parse_response(text)
        # Rough cost: Haiku 4.5 is $1/MTok in, $5/MTok out
        cost = (resp.usage.input_tokens * 1.0 + resp.usage.output_tokens * 5.0) / 1_000_000
        return DecompositionResult(
            sub_goals=sub_goals,
            source=self.name,
            raw_input=user_utterance,
            cost_usd=cost,
            latency_ms=elapsed_ms,
        )


if __name__ == "__main__":
    d = TinyLMDecomposer()
    sample = (
        "You are Yusuf Rossi in 19122. You received your order #W2378156 and "
        "wish to exchange the mechanical keyboard for a similar one but with "
        "clicky switches, and the smart thermostat for one compatible with "
        "Google Home instead of Apple HomeKit."
    )
    r = d.decompose(sample, domain="retail")
    print(r.to_system_hint())
    print(f"latency: {r.latency_ms:.1f}ms, cost: ${r.cost_usd:.5f}")
