"""LLM-as-judge failure classifier for τ-bench trajectories.

Reads raw τ-bench result JSON, filters failures, and labels each with one of:
  user_fault | called_wrong_tool | wrong_argument | wrong_value |
  partial_resolve | other

Output: JSONL at data/annotations/failures_labeled_{domain}_seed{seed}.jsonl

Judge model: Claude Haiku 4.5 (cheap, structured output).
Expected cost: ~$0.01 per trajectory × ~40 failures × 3 seeds ≈ $1.5 total.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

JUDGE_SYSTEM = """You are a fault analyst for an AI agent evaluation benchmark called τ-bench.
You will be given:
  1. The user instruction (what the user was trying to do)
  2. The ground truth action sequence (correct tool calls)
  3. The actual trajectory (agent's messages and tool calls)

The trajectory has already been graded as FAILED.

Your job: classify the PRIMARY fault into ONE category.

CATEGORIES:
- user_fault: User simulator gave info not in instruction OR was inconsistent.
- called_wrong_tool: Agent called the wrong tool or skipped a required one.
- wrong_argument: Correct tool but wrong arguments (wrong ID/value/filter).
- wrong_value: Agent told user incorrect info that diverged the conversation.
- partial_resolve: Only completed some of the requested actions.
- other: Timeout, refusal, loop, tool error, or unclassifiable.

Return JSON only:
{"category": "...", "rationale": "<one sentence>", "first_error_turn": <int>}
"""


def format_case(
    instruction: str,
    gt_actions: List[Dict[str, Any]],
    traj: List[Dict[str, Any]],
) -> str:
    traj_stripped = [m for m in traj if m.get("role") != "system"]
    traj_text = "\n".join(
        f"{m['role'].upper()}: {m.get('content') or m.get('tool_calls') or ''}"
        for m in traj_stripped
    )
    return (
        f"--- User instruction ---\n{instruction}\n\n"
        f"--- Ground truth action sequence ---\n{json.dumps(gt_actions, indent=2)}\n\n"
        f"--- Actual trajectory ---\n{traj_text}\n\n"
        "Classify the PRIMARY fault. Return JSON only."
    )


def call_judge(client, instruction: str, gt_actions: List, traj: List) -> Dict[str, Any]:
    prompt = format_case(instruction, gt_actions, traj)
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
        temperature=0.0,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        out = json.loads(text[start : end + 1]) if start >= 0 else {"category": "other"}
    out["_tokens"] = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return out


def get_tasks(domain: str) -> List:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor" / "tau-bench"))
    if domain == "retail":
        from tau_bench.envs.retail.tasks_test import TASKS_TEST as tasks
    elif domain == "airline":
        import tau_bench.envs.airline.tasks_test as at
        tasks = at.TASKS
    else:
        raise ValueError(domain)
    return tasks


def is_compound(task, domain: str) -> bool:
    reads = {
        "retail": {"get_order_details", "get_product_details", "find_user_id_by_name_zip",
                   "get_user_details", "find_user_id_by_email", "list_all_product_types", "calculate"},
        "airline": {"get_reservation_details", "search_direct_flight", "search_onestop_flight",
                    "get_user_details", "calculate", "list_all_airports"},
    }[domain]
    n_writes = sum(1 for a in task.actions if a.name not in reads)
    return n_writes >= 2, n_writes


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", required=True, help="Path to tau-bench results JSON")
    p.add_argument("--domain", required=True, choices=["retail", "airline"])
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True, help="Output JSONL path")
    p.add_argument("--max-n", type=int, default=None, help="Limit annotations")
    args = p.parse_args()

    try:
        from anthropic import Anthropic
    except ImportError:
        print("pip install anthropic"); return 1
    client = Anthropic()

    with open(args.results) as f:
        results = json.load(f)
    failures = [r for r in results if float(r.get("reward", 1.0)) < 1e-3]
    if args.max_n:
        failures = failures[: args.max_n]
    print(f"{len(failures)} failures to label from {args.results}")

    tasks = get_tasks(args.domain)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    total_tokens = {"in": 0, "out": 0}
    with open(args.out, "w") as fout:
        for r in failures:
            tid = r["task_id"]
            task = tasks[tid]
            compound, n_writes = is_compound(task, args.domain)
            label = call_judge(client, task.instruction, [a.model_dump() for a in task.actions], r.get("traj", []))
            total_tokens["in"] += label["_tokens"]["in"]
            total_tokens["out"] += label["_tokens"]["out"]
            rec = {
                "task_id": tid, "seed": args.seed, "domain": args.domain,
                "reward": r.get("reward", 0.0),
                "n_ground_truth_writes": n_writes, "is_compound": compound,
                "llm_label": {k: v for k, v in label.items() if k != "_tokens"},
            }
            fout.write(json.dumps(rec) + "\n")
            print(f"  task {tid}: {label.get('category')} (compound={compound})")
    cost = (total_tokens["in"] * 1.0 + total_tokens["out"] * 5.0) / 1_000_000
    print(f"Done. Tokens: {total_tokens}. Cost: ${cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
