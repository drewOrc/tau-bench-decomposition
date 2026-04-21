"""LLM-as-judge failure classifier for τ-bench trajectories.

Reads baseline result JSONs, filters failures (reward < 1.0), and labels each
with our extended failure taxonomy (7 categories, decomposition relevance, user
behavior). Uses the annotation schema from data/annotation_schema.json.

Judge model: gpt-4o-mini (cheap, good at structured output).
Expected cost: ~$0.005 per trajectory × ~180 failures ≈ $1 total.

Usage:
    # Annotate all retail failures (3 seeds)
    python src/annotate_failures.py --domain retail --seeds 42 43 44

    # Annotate single seed, dry-run first 5
    python src/annotate_failures.py --domain retail --seeds 42 --max-n 5

    # Annotate airline
    python src/annotate_failures.py --domain airline --seeds 42 43 44
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import litellm
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)
litellm.num_retries = 3

RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data" / "annotations"

JUDGE_SYSTEM = """You are a fault analyst for τ-bench, an AI agent benchmark for multi-turn tool-calling tasks.

You will receive a FAILED trajectory: the user instruction, the agent's conversation with tool calls, and the ground truth actions the agent should have taken.

Classify the failure using these fields (return JSON only, no markdown):

1. "primary_failure": one of:
   - "wrong_argument": Agent called the right tool but with wrong parameters (wrong ID, wrong value, wrong filter).
   - "wrong_decision": Agent made a wrong strategic choice or violated domain policy (e.g., policy says exchange must be one call, agent split into two).
   - "wrong_info": Agent gave user incorrect information (wrong price, wrong status, missing info).
   - "partial_resolve": User had multiple sub-tasks; agent only completed some.
   - "user_led_astray": The user simulator steered the conversation toward a wrong outcome (e.g., user asked to cancel instead of modify, user gave up too early).
   - "ambiguous_task": The task instruction allows multiple reasonable interpretations; the agent's path was defensible but didn't match ground truth.

2. "secondary_failure": same options as above, or null if only one issue.

3. "user_behavior": one of:
   - "cooperative": User gave clear info when asked, followed agent's lead.
   - "underspecified": User gave vague or incomplete answers requiring agent to guess.
   - "contradictory": User gave conflicting information.
   - "premature_stop": User ended conversation before task was complete.

4. "decomposition_relevant": true if listing sub-goals before execution could have prevented this failure. Typically true for partial_resolve and some wrong_decision cases where the agent forgot a step.

5. "n_subtasks": Number of distinct actions the user requested (e.g., "change address for 3 orders" = 3, "cancel order" = 1).

6. "n_subtasks_completed": How many the agent actually completed successfully.

7. "policy_violation": true if the agent violated an explicit rule in the system prompt policy.

8. "confidence": 0.0-1.0, your confidence in this classification.

9. "rationale": One sentence explaining your classification.

Return ONLY a JSON object with these 9 fields. No markdown, no explanation outside JSON."""


def load_tasks(domain: str):
    """Load task definitions from tau-bench."""
    if domain == "retail":
        from tau_bench.envs.retail.tasks_test import TASKS_TEST as tasks
    elif domain == "airline":
        from tau_bench.envs.airline.tasks_test import TASKS as tasks
    else:
        raise ValueError(f"Unknown domain: {domain}")
    return tasks


def format_trajectory(traj: list) -> str:
    """Format trajectory into readable text for the judge."""
    lines = []
    for i, turn in enumerate(traj):
        role = turn.get("role", "unknown").upper()
        if role == "SYSTEM":
            # Truncate system prompt to first 500 chars
            content = str(turn.get("content", ""))[:500] + "..."
            lines.append(f"[{i}] {role}: {content}")
        elif role == "ASSISTANT":
            tool_calls = turn.get("tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {}).get("name", "?")
                    args = tc.get("function", {}).get("arguments", "")
                    if isinstance(args, str):
                        args_str = args[:200]
                    else:
                        args_str = json.dumps(args)[:200]
                    lines.append(f"[{i}] AGENT TOOL_CALL: {fn}({args_str})")
            else:
                content = str(turn.get("content", ""))[:300]
                lines.append(f"[{i}] AGENT: {content}")
        elif role == "TOOL":
            content = str(turn.get("content", ""))[:200]
            lines.append(f"[{i}] TOOL_RESULT: {content}")
        elif role == "USER":
            content = str(turn.get("content", ""))[:300]
            lines.append(f"[{i}] USER: {content}")
    return "\n".join(lines)


def call_judge(instruction: str, gt_actions: list, traj: list, model: str) -> dict:
    """Call LLM judge to classify a failure."""
    traj_text = format_trajectory(traj)
    try:
        gt_text = json.dumps(gt_actions, indent=2, default=str)[:2000]
    except (TypeError, ValueError):
        gt_text = str(gt_actions)[:2000]

    user_prompt = (
        f"--- User Instruction ---\n{instruction}\n\n"
        f"--- Ground Truth Actions ---\n{gt_text}\n\n"
        f"--- Actual Trajectory ({len(traj)} turns) ---\n{traj_text}\n\n"
        "Classify the failure. Return JSON only."
    )

    resp = litellm.completion(
        model=model,
        temperature=0.0,
        max_tokens=400,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = resp.choices[0].message.content.strip()
    # Clean markdown wrapper if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                result = {
                    "primary_failure": "unknown",
                    "rationale": f"Judge returned unparseable: {text[:100]}",
                    "confidence": 0.0,
                }
        else:
            result = {
                "primary_failure": "unknown",
                "rationale": f"Judge returned unparseable: {text[:100]}",
                "confidence": 0.0,
            }

    result["_usage"] = {
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
    }
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="LLM-as-judge failure annotation")
    p.add_argument("--domain", required=True, choices=["retail", "airline"])
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--tag", default="baseline")
    p.add_argument("--judge-model", default="gpt-4o-mini",
                   help="Model for LLM-as-judge (default: gpt-4o-mini)")
    p.add_argument("--max-n", type=int, default=None,
                   help="Limit number of annotations per seed (for testing)")
    p.add_argument("--include-passes", action="store_true",
                   help="Also annotate passing tasks (for validation)")
    args = p.parse_args()

    tasks = load_tasks(args.domain)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    total_tokens = {"input": 0, "output": 0}
    all_annotations = []

    for seed in args.seeds:
        seed_dir = RESULTS_DIR / args.tag / args.domain / f"seed{seed}"
        files = sorted(
            p for p in seed_dir.glob("*.json")
            if p.name not in ("summary.json", "metrics_merged.json")
        )
        if not files:
            print(f"WARNING: No results found in {seed_dir}")
            continue

        with open(files[-1]) as f:
            results = json.load(f)

        # Filter to failures (or all if include-passes)
        if args.include_passes:
            to_annotate = results
        else:
            to_annotate = [r for r in results if r.get("reward", 1.0) < 0.999]

        if args.max_n:
            to_annotate = to_annotate[:args.max_n]

        print(f"\nseed {seed}: {len(to_annotate)} tasks to annotate "
              f"(from {len(results)} total)")

        for i, r in enumerate(to_annotate):
            tid = r["task_id"]
            task = tasks[tid]
            gt_actions = [a.model_dump() for a in task.actions]
            traj = r.get("traj", [])

            try:
                label = call_judge(
                    instruction=task.instruction,
                    gt_actions=gt_actions,
                    traj=traj,
                    model=args.judge_model,
                )
            except Exception as e:
                print(f"  ERROR on task {tid}: {e}")
                label = {
                    "primary_failure": "unknown",
                    "rationale": f"Judge call failed: {str(e)[:100]}",
                    "confidence": 0.0,
                    "_usage": {"input_tokens": 0, "output_tokens": 0},
                }

            total_tokens["input"] += label.get("_usage", {}).get("input_tokens", 0)
            total_tokens["output"] += label.get("_usage", {}).get("output_tokens", 0)

            # Build annotation record
            annotation = {
                "task_id": tid,
                "seed": seed,
                "domain": args.domain,
                "reward": r.get("reward", 0.0),
                "annotation": {
                    "primary_failure": label.get("primary_failure", "unknown"),
                    "secondary_failure": label.get("secondary_failure"),
                    "user_behavior": label.get("user_behavior", "cooperative"),
                    "decomposition_relevant": label.get("decomposition_relevant", False),
                    "n_subtasks": label.get("n_subtasks", 1),
                    "n_subtasks_completed": label.get("n_subtasks_completed", 0),
                    "policy_violation": label.get("policy_violation", False),
                    "tool_error_count": sum(
                        1 for t in traj
                        if t.get("role") == "tool"
                        and "error" in str(t.get("content", "")).lower()
                    ),
                    "turn_count": len(traj),
                    "confidence": label.get("confidence", 0.5),
                    "rationale": label.get("rationale", ""),
                },
            }
            all_annotations.append(annotation)

            status = label.get("primary_failure", "?")
            decomp = "D" if label.get("decomposition_relevant") else "-"
            print(f"  [{i+1}/{len(to_annotate)}] task {tid}: {status} [{decomp}] "
                  f"(conf={label.get('confidence', '?')})")

    # Save annotations
    out_path = DATA_DIR / f"{args.tag}_{args.domain}_annotations.jsonl"
    with open(out_path, "w") as f:
        for ann in all_annotations:
            f.write(json.dumps(ann) + "\n")

    # Cost estimate (gpt-4o-mini: $0.15/M input, $0.60/M output)
    cost = (total_tokens["input"] * 0.15 + total_tokens["output"] * 0.60) / 1_000_000
    print(f"\n{'='*60}")
    print(f"Done. {len(all_annotations)} annotations saved to {out_path}")
    print(f"Tokens: input={total_tokens['input']:,}, output={total_tokens['output']:,}")
    print(f"Estimated cost: ${cost:.4f}")
    print(f"{'='*60}")

    # Print summary
    from collections import Counter
    cats = Counter(a["annotation"]["primary_failure"] for a in all_annotations)
    decomp_count = sum(1 for a in all_annotations if a["annotation"]["decomposition_relevant"])
    print(f"\nFailure category distribution:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} ({count/len(all_annotations)*100:.1f}%)")
    print(f"\nDecomposition-relevant: {decomp_count}/{len(all_annotations)} "
          f"({decomp_count/len(all_annotations)*100:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
