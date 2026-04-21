"""Same-model decomposer (gpt-4o as both planner and executor).

Uses litellm to call the same model that serves as the executor,
isolating whether the quality gap is model-size or task-inherent.
"""

from __future__ import annotations

import json
import time
from typing import List, Optional

import litellm

from .base import Decomposer, DecompositionResult, SubGoal
from .tiny_lm import SYSTEM_PROMPT


class SameModelDecomposer(Decomposer):
    name = "same-model-gpt4o"

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str = "openai",
        max_tokens: int = 400,
    ) -> None:
        self.model = model
        self.provider = provider
        self.max_tokens = max_tokens

    def _parse_response(self, text: str) -> List[SubGoal]:
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            if t.startswith("json"):
                t = t[4:].strip()
        try:
            data = json.loads(t)
        except json.JSONDecodeError:
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
                    confidence=0.9,
                )
            )
        return sub_goals

    def decompose(
        self, user_utterance: str, domain: str = "retail", **kwargs
    ) -> DecompositionResult:
        t0 = time.perf_counter()
        resp = litellm.completion(
            model=self.model,
            custom_llm_provider=self.provider,
            max_tokens=self.max_tokens,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"[domain={domain}]\n{user_utterance}"},
            ],
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        text = resp.choices[0].message.content or ""
        sub_goals = self._parse_response(text)
        cost = resp._hidden_params.get("response_cost") or 0.0
        return DecompositionResult(
            sub_goals=sub_goals,
            source=self.name,
            raw_input=user_utterance,
            cost_usd=cost,
            latency_ms=elapsed_ms,
        )
