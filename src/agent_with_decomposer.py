"""τ-bench ToolCallingAgent wrapped with a pre-decomposition step.

This is a drop-in subclass of tau_bench.agents.tool_calling_agent.ToolCallingAgent
that runs a Decomposer on the FIRST user observation (turn 0), then injects the
resulting sub-goal list into the system prompt BEFORE the main tool-calling loop.

Key design decisions:
  1. Decomposition happens ONCE, upfront. It does not re-run on each user turn.
     Rationale: τ-bench's user simulator is instructed to reveal info incrementally,
     so later user turns may add info, but the initial framing is enough for
     most compound tasks. Cost stays bounded.
  2. The sub-goal list is injected as an appended system message, not a user
     message. We do not want it to look like the user said it.
  3. We log the DecompositionResult (cost, latency, source, sub-goals) into
     SolveResult.info under key "decomposition" so downstream analysis can
     correlate decomposer quality with task reward.

Usage:
    from agent_with_decomposer import ToolCallingAgentWithDecomposer
    from decomposer import RuleBasedDecomposer

    agent = ToolCallingAgentWithDecomposer(
        tools_info=env.tools_info,
        wiki=env.wiki,
        model="claude-sonnet-4-5-20250929",
        provider="anthropic",
        decomposer=RuleBasedDecomposer(),
        domain="retail",
    )
    result = agent.solve(env, task_index=0)
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make vendor tau-bench importable regardless of cwd
_VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "tau-bench-clean"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from tau_bench.agents.tool_calling_agent import ToolCallingAgent, message_to_action
from tau_bench.envs.base import Env
from tau_bench.types import SolveResult, RESPOND_ACTION_NAME
from litellm import completion

from decomposer.base import Decomposer, DecompositionResult


class ToolCallingAgentWithDecomposer(ToolCallingAgent):
    """ToolCallingAgent that runs a pre-decomposition pass on turn 0."""

    def __init__(
        self,
        tools_info: List[Dict[str, Any]],
        wiki: str,
        model: str,
        provider: str,
        decomposer: Decomposer,
        domain: str = "retail",
        temperature: float = 0.0,
        inject_as: str = "system",  # "system" | "user_prefix" | "none"
    ):
        super().__init__(
            tools_info=tools_info,
            wiki=wiki,
            model=model,
            provider=provider,
            temperature=temperature,
        )
        self.decomposer = decomposer
        self.domain = domain
        self.inject_as = inject_as

    def solve(
        self, env: Env, task_index: Optional[int] = None, max_num_steps: int = 30
    ) -> SolveResult:
        total_cost = 0.0
        env_reset_res = env.reset(task_index=task_index)
        obs = env_reset_res.observation
        info = env_reset_res.info.model_dump()
        reward = 0.0

        decomp: DecompositionResult = self.decomposer.decompose(
            obs, domain=self.domain, task_index=task_index
        )
        hint = decomp.to_system_hint()
        total_cost += decomp.cost_usd

        system_content = self.wiki
        user_content = obs
        if hint:
            if self.inject_as == "system":
                system_content = f"{self.wiki}\n\n{hint}"
            elif self.inject_as == "user_prefix":
                user_content = f"{hint}\n\n{obs}"
            # "none" = do nothing, used for ablation (decomp runs but not injected)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        # Mirrors ToolCallingAgent.solve() loop
        for _ in range(max_num_steps):
            res = completion(
                messages=messages,
                model=self.model,
                custom_llm_provider=self.provider,
                tools=self.tools_info,
                temperature=self.temperature,
            )
            next_message = res.choices[0].message.model_dump()
            total_cost += res._hidden_params.get("response_cost") or 0.0
            action = message_to_action(next_message)
            env_response = env.step(action)
            reward = env_response.reward
            info = {**info, **env_response.info.model_dump()}
            if action.name != RESPOND_ACTION_NAME:
                next_message["tool_calls"] = next_message["tool_calls"][:1]
                messages.extend(
                    [
                        next_message,
                        {
                            "role": "tool",
                            "tool_call_id": next_message["tool_calls"][0]["id"],
                            "name": next_message["tool_calls"][0]["function"]["name"],
                            "content": env_response.observation,
                        },
                    ]
                )
            else:
                messages.extend(
                    [
                        next_message,
                        {"role": "user", "content": env_response.observation},
                    ]
                )
            if env_response.done:
                break

        info["decomposition"] = {
            "source": decomp.source,
            "n_sub_goals": len(decomp.sub_goals),
            "sub_goals": [asdict(sg) for sg in decomp.sub_goals],
            "cost_usd": decomp.cost_usd,
            "latency_ms": decomp.latency_ms,
            "inject_as": self.inject_as,
        }

        return SolveResult(
            reward=reward,
            info=info,
            messages=messages,
            total_cost=total_cost,
        )


if __name__ == "__main__":
    # Smoke test: instantiate, no env call
    from decomposer import RuleBasedDecomposer

    agent = ToolCallingAgentWithDecomposer(
        tools_info=[],
        wiki="You are a customer service agent.",
        model="claude-sonnet-4-5-20250929",
        provider="anthropic",
        decomposer=RuleBasedDecomposer(),
        domain="retail",
    )
    print(f"Agent created: model={agent.model}, decomposer={agent.decomposer.name}")
    print(f"Inject mode: {agent.inject_as}")
