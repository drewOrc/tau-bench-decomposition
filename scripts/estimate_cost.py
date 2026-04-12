"""Estimate API cost for τ-bench baseline reproduction.

Produces a breakdown by model, environment, and seed count so you
know the bill before you start running experiments.

Usage:
    python scripts/estimate_cost.py
    python scripts/estimate_cost.py --seeds 3 --envs retail airline
    python scripts/estimate_cost.py --agent-model claude-sonnet-4-5-20250929
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

# ── Pricing (per 1M tokens, as of 2026-04) ──────────────────────

PRICING = {
    # Anthropic
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 0.80, "output":  4.00},
    # OpenAI
    "gpt-4o-mini":               {"input": 0.15, "output":  0.60},
    "gpt-4o":                    {"input": 2.50, "output": 10.00},
}

# ── Task-level token estimates ───────────────────────────────────
#
# These are rough estimates from τ-bench paper analysis and community
# reports. Each "task" is a multi-turn conversation between the agent
# and the user simulator, typically 4-8 turns for retail, 6-12 for
# airline.
#
# Numbers below are PER TASK (all turns combined).

@dataclass
class TaskProfile:
    name: str
    n_tasks: int
    avg_agent_input_tokens: int    # tokens the agent reads (system + history + tools)
    avg_agent_output_tokens: int   # tokens the agent generates (reasoning + tool calls)
    avg_user_input_tokens: int     # tokens the user sim reads
    avg_user_output_tokens: int    # tokens the user sim generates

PROFILES = {
    "retail": TaskProfile(
        name="τ-retail",
        n_tasks=115,
        avg_agent_input_tokens=4500,    # ~6 turns × 750 tok/turn avg
        avg_agent_output_tokens=800,    # ~6 turns × 130 tok/turn avg
        avg_user_input_tokens=2000,     # ~6 turns × 330 tok/turn avg
        avg_user_output_tokens=300,     # ~6 turns × 50 tok/turn avg
    ),
    "airline": TaskProfile(
        name="τ-airline",
        n_tasks=50,
        avg_agent_input_tokens=6000,    # ~8 turns × 750 tok/turn avg (harder tasks)
        avg_agent_output_tokens=1200,   # ~8 turns × 150 tok/turn avg
        avg_user_input_tokens=2800,     # ~8 turns × 350 tok/turn avg
        avg_user_output_tokens=400,     # ~8 turns × 50 tok/turn avg
    ),
}


def cost_per_task(
    profile: TaskProfile,
    agent_model: str,
    user_model: str,
) -> dict:
    """Return cost breakdown for one task."""
    ap = PRICING[agent_model]
    up = PRICING[user_model]

    agent_cost = (
        profile.avg_agent_input_tokens * ap["input"]
        + profile.avg_agent_output_tokens * ap["output"]
    ) / 1_000_000

    user_cost = (
        profile.avg_user_input_tokens * up["input"]
        + profile.avg_user_output_tokens * up["output"]
    ) / 1_000_000

    return {
        "agent_cost": agent_cost,
        "user_cost": user_cost,
        "total": agent_cost + user_cost,
    }


def estimate(
    envs: list[str],
    n_seeds: int,
    agent_model: str,
    user_model: str,
) -> dict:
    """Full experiment cost estimate."""
    results = {}
    grand_total = 0.0

    for env in envs:
        profile = PROFILES[env]
        per_task = cost_per_task(profile, agent_model, user_model)
        env_total = per_task["total"] * profile.n_tasks * n_seeds

        results[env] = {
            "tasks": profile.n_tasks,
            "seeds": n_seeds,
            "total_runs": profile.n_tasks * n_seeds,
            "cost_per_task": {
                "agent": f"${per_task['agent_cost']:.5f}",
                "user_sim": f"${per_task['user_cost']:.5f}",
                "total": f"${per_task['total']:.5f}",
            },
            "env_total": f"${env_total:.2f}",
        }
        grand_total += env_total

    return {
        "models": {
            "agent": agent_model,
            "user_simulator": user_model,
        },
        "environments": results,
        "grand_total": f"${grand_total:.2f}",
        "budget_check": "WITHIN $130 budget" if grand_total <= 130 else f"OVER BUDGET by ${grand_total - 130:.2f}",
    }


def main():
    p = argparse.ArgumentParser(description="Estimate τ-bench experiment costs")
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--envs", nargs="+", default=["retail", "airline"],
                   choices=["retail", "airline"])
    p.add_argument("--agent-model", default="claude-sonnet-4-5-20250929")
    p.add_argument("--user-model", default="gpt-4o-mini")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    args = p.parse_args()

    result = estimate(args.envs, args.seeds, args.agent_model, args.user_model)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Pretty print
    print("=" * 60)
    print("τ-bench Cost Estimate")
    print("=" * 60)
    print(f"Agent model:     {result['models']['agent']}")
    print(f"User simulator:  {result['models']['user_simulator']}")
    print(f"Seeds:           {args.seeds}")
    print()

    for env, data in result["environments"].items():
        print(f"── {env.upper()} {'─' * 45}")
        print(f"   Tasks:          {data['tasks']}")
        print(f"   Total runs:     {data['total_runs']} ({data['tasks']} × {data['seeds']} seeds)")
        print(f"   Per task:       agent {data['cost_per_task']['agent']}"
              f"  +  user_sim {data['cost_per_task']['user_sim']}"
              f"  =  {data['cost_per_task']['total']}")
        print(f"   Env total:      {data['env_total']}")
        print()

    print(f"{'=' * 60}")
    print(f"GRAND TOTAL:       {result['grand_total']}")
    print(f"Budget ($130):     {result['budget_check']}")
    print(f"{'=' * 60}")

    # Decomposer add-on estimate
    print()
    print("── DECOMPOSER ADD-ON (if baseline passes) ─────────────────")
    haiku_input = PRICING["claude-haiku-4-5-20251001"]["input"]
    haiku_output = PRICING["claude-haiku-4-5-20251001"]["output"]
    # Decomposer adds ~500 input + ~200 output tokens per task
    decomp_per_task = (500 * haiku_input + 200 * haiku_output) / 1_000_000
    compound_tasks = 47 + 25  # retail compound + airline compound estimate
    decomp_total = decomp_per_task * compound_tasks * args.seeds
    print(f"   Decomposer model: claude-haiku-4-5-20251001")
    print(f"   Compound tasks:   ~{compound_tasks} (retail 47 + airline ~25)")
    print(f"   Per task:         ${decomp_per_task:.6f}")
    print(f"   Add-on total:     ${decomp_total:.2f}")
    print(f"   Combined total:   ${float(result['grand_total'].replace('$','')) + decomp_total:.2f}")
    print()

    # Failure modes
    print("── FAILURE MODES TO WATCH ─────────────────────────────────")
    print("   1. API rate limits: Anthropic 4000 RPM / OpenAI varies")
    print("      → Use --concurrency 4-6, not higher")
    print("   2. gpt-4o-mini version drift: user sim behavior may")
    print("      differ from paper's snapshot")
    print("      → Record model version string in logs")
    print("   3. τ-bench repo breaking changes: check Issues + recent")
    print("      commits before cloning")
    print("      → Pin to a specific commit hash after smoke test")
    print("   4. Tool schema changes: τ-bench tools might have updated")
    print("      → Compare tool definitions with paper's Table 1")
    print("   5. Compound task annotation: 47/115 retail compound is")
    print("      our count; verify with actual task metadata")
    print("      → Run: grep -c 'actions.*actions' in task definitions")
    print("   6. Cost overrun: if avg turns >> estimate, bill explodes")
    print("      → Run 3-task smoke test first (--task-ids 0 1 2)")
    print("      → Check actual cost vs estimate before full run")
    print("   7. Timeout: some airline tasks take 15+ turns")
    print("      → Set per-task timeout, log incomplete tasks separately")


if __name__ == "__main__":
    main()
