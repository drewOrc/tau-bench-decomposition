"""Run τ-bench with a pre-decomposition agent (Phase C).

Mirrors run_baseline.py but swaps in ToolCallingAgentWithDecomposer.
We reimplement the task loop (rather than calling tau_bench.run.run())
because run() hard-codes agent_factory() with no hook for custom agents.

Usage:
    # Smoke test (1 task, rule-based decomposer)
    python src/run_decomposer.py --env retail --task-ids 0 --seeds 42 \
        --decomposer rule-based

    # Full run with rule-based decomposer
    python src/run_decomposer.py --env retail --seeds 42 43 44 \
        --decomposer rule-based --concurrency 2

    # Full run with tiny-LM decomposer (Haiku 4.5)
    python src/run_decomposer.py --env retail --seeds 42 43 44 \
        --decomposer tiny-lm --concurrency 2

    # Ablation: decomposer runs but output not injected
    python src/run_decomposer.py --env retail --seeds 42 43 44 \
        --decomposer rule-based --inject-as none --tag decomposer-rule-ablation

    # Oracle decomposer (ceiling analysis, auto-selects annotated tasks)
    python src/run_decomposer.py --env retail --seeds 42 43 44 \
        --decomposer oracle --concurrency 2
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import litellm
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)
litellm.num_retries = 5

# Make our src/ and vendor importable
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "vendor" / "tau-bench-clean"))

RESULTS_DIR = PROJECT_ROOT / "results"


def build_decomposer(name: str):
    """Instantiate a decomposer by name."""
    if name == "rule-based":
        from decomposer.rule_based import RuleBasedDecomposer
        return RuleBasedDecomposer()
    elif name == "tiny-lm":
        from decomposer.tiny_lm import TinyLMDecomposer
        return TinyLMDecomposer()
    elif name == "oracle":
        from decomposer.oracle import OracleDecomposer
        return OracleDecomposer()
    else:
        raise ValueError(f"Unknown decomposer: {name}. Use 'rule-based', 'tiny-lm', or 'oracle'.")


def run_single_seed(seed: int, args: argparse.Namespace) -> dict:
    """Run all tasks for a single seed with decomposer agent."""
    from tau_bench.envs import get_env
    from tau_bench.types import EnvRunResult
    from agent_with_decomposer import ToolCallingAgentWithDecomposer

    random.seed(seed)
    log_dir = RESULTS_DIR / args.tag / args.env / f"seed{seed}"
    log_dir.mkdir(parents=True, exist_ok=True)

    time_str = datetime.now().strftime("%m%d%H%M%S")
    ckpt_path = log_dir / f"tool-calling-{args.model.split('/')[-1]}-{args.temperature}_decomp-{args.decomposer}_{time_str}.json"

    # Create env to get tools_info and wiki
    env = get_env(
        args.env,
        user_strategy="llm",
        user_model=args.user_model,
        user_provider=args.user_model_provider,
        task_split="test",
    )

    # Build decomposer and agent
    decomposer = build_decomposer(args.decomposer)
    agent = ToolCallingAgentWithDecomposer(
        tools_info=env.tools_info,
        wiki=env.wiki,
        model=args.model,
        provider=args.model_provider,
        decomposer=decomposer,
        domain=args.env,
        temperature=args.temperature,
        inject_as=args.inject_as,
    )

    # Determine task indices
    if args.task_ids:
        idxs = args.task_ids
    else:
        idxs = list(range(len(env.tasks)))

    print(f"\n{'='*60}")
    print(f">>> seed={seed} | env={args.env} | model={args.model}")
    print(f">>> decomposer={args.decomposer} | inject_as={args.inject_as}")
    print(f">>> {len(idxs)} tasks | log_dir={log_dir}")
    print(f"{'='*60}\n")

    lock = threading.Lock()
    t0 = time.time()

    def _run(idx: int):
        isolated_env = get_env(
            args.env,
            user_strategy="llm",
            user_model=args.user_model,
            user_provider=args.user_model_provider,
            task_split="test",
            task_index=idx,
        )
        print(f"Running task {idx}")
        try:
            res = agent.solve(env=isolated_env, task_index=idx)
            result = EnvRunResult(
                task_id=idx,
                reward=res.reward,
                info=res.info,
                traj=res.messages,
                trial=0,
            )
        except Exception as e:
            result = EnvRunResult(
                task_id=idx,
                reward=0.0,
                info={"error": str(e), "traceback": traceback.format_exc()},
                traj=[],
                trial=0,
            )
        status = "✅" if result.reward >= 0.999 else "❌"
        print(f"{status} task_id={idx} reward={result.reward}")

        # Checkpoint incrementally
        with lock:
            data = []
            if ckpt_path.exists():
                with open(ckpt_path) as f:
                    data = json.load(f)
            with open(ckpt_path, "w") as f:
                json.dump(data + [result.model_dump()], f, indent=2)
        return result

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(_run, idxs))

    wall_time = time.time() - t0

    # Compute metrics
    rewards = [r.reward for r in results]
    n_pass = sum(1 for r in rewards if r >= 0.999)
    n_tasks = len(rewards)
    pass_1 = n_pass / n_tasks if n_tasks else 0.0

    # Decomposer cost stats
    decomp_costs = []
    decomp_latencies = []
    for r in results:
        d = r.info.get("decomposition", {}) if isinstance(r.info, dict) else {}
        if d:
            decomp_costs.append(d.get("cost_usd", 0.0))
            decomp_latencies.append(d.get("latency_ms", 0.0))

    summary = {
        "seed": seed,
        "env": args.env,
        "model": args.model,
        "model_provider": args.model_provider,
        "user_model": args.user_model,
        "strategy": "tool-calling",
        "temperature": args.temperature,
        "decomposer": args.decomposer,
        "inject_as": args.inject_as,
        "wall_time_s": round(wall_time, 1),
        "num_tasks": n_tasks,
        "pass_1": round(pass_1, 4),
        "n_pass": n_pass,
        "mean_reward": round(sum(rewards) / n_tasks, 4) if n_tasks else 0.0,
        "decomposer_total_cost_usd": round(sum(decomp_costs), 6),
        "decomposer_mean_latency_ms": round(
            sum(decomp_latencies) / len(decomp_latencies), 1
        ) if decomp_latencies else 0.0,
    }

    summary_path = log_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Save final checkpoint (overwrite incremental)
    with open(ckpt_path, "w") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)

    print(f"\n>>> seed={seed} done in {wall_time:.1f}s")
    print(f">>> pass^1 = {pass_1*100:.1f}% ({n_pass}/{n_tasks})")
    print(f">>> decomposer cost: ${sum(decomp_costs):.4f}")
    print(f">>> summary → {summary_path}")

    return summary


def main() -> int:
    p = argparse.ArgumentParser(description="Run τ-bench with decomposer agent")
    p.add_argument("--env", choices=["retail", "airline"], default="retail")
    p.add_argument("--model", default="gpt-4o",
                   help="Agent model (default: gpt-4o)")
    p.add_argument("--model-provider", default="openai")
    p.add_argument("--user-model", default="gpt-4o",
                   help="User simulator model (default: gpt-4o)")
    p.add_argument("--user-model-provider", default="openai")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--concurrency", type=int, default=1,
                   help="Parallel tasks per seed (default: 1)")
    p.add_argument("--task-ids", type=int, nargs="+", default=None,
                   help="Run only specific task IDs (for smoke test)")
    p.add_argument("--decomposer", default="rule-based",
                   choices=["rule-based", "tiny-lm", "oracle"],
                   help="Decomposer type (default: rule-based)")
    p.add_argument("--inject-as", default="system",
                   choices=["system", "user_prefix", "none"],
                   help="Where to inject sub-goals (default: system)")
    p.add_argument("--tag", default=None,
                   help="Results subdirectory (auto-generated if not set)")
    args = p.parse_args()

    # Auto-generate tag if not specified
    if args.tag is None:
        inject_suffix = f"-{args.inject_as}" if args.inject_as != "system" else ""
        args.tag = f"decomposer-{args.decomposer}{inject_suffix}"

    # Oracle mode: auto-select covered tasks if --task-ids not specified
    if args.decomposer == "oracle" and args.task_ids is None:
        if args.env != "retail":
            print("ERROR: oracle sub-goals only cover retail tasks. "
                  "Pass --task-ids explicitly for other envs.")
            return 1
        from decomposer.oracle import OracleDecomposer
        _oracle = OracleDecomposer()
        args.task_ids = sorted(_oracle.covered_task_ids)
        print(f"Oracle mode: auto-selected {len(args.task_ids)} tasks with "
              f"gold sub-goals: {args.task_ids}")
        del _oracle

    # Validate API keys
    missing = set()
    if "openai" in args.model_provider and not os.environ.get("OPENAI_API_KEY"):
        missing.add("OPENAI_API_KEY")
    if "openai" in args.user_model_provider and not os.environ.get("OPENAI_API_KEY"):
        missing.add("OPENAI_API_KEY")
    if args.decomposer == "tiny-lm" and not os.environ.get("ANTHROPIC_API_KEY"):
        missing.add("ANTHROPIC_API_KEY")
    if missing:
        print(f"ERROR: Missing API keys: {missing}")
        print("Set them in .env or export them.")
        return 1

    print(f"Config: model={args.model}, decomposer={args.decomposer}, "
          f"inject_as={args.inject_as}")
    print(f"Seeds: {args.seeds}, concurrency={args.concurrency}")
    print(f"Tag: {args.tag}")
    if args.task_ids:
        print(f"Task IDs: {args.task_ids} (smoke test mode)")

    summaries = []
    for seed in args.seeds:
        try:
            s = run_single_seed(seed, args)
            summaries.append(s)
        except Exception as e:
            print(f"\n!!! seed={seed} FAILED: {e}")
            traceback.print_exc()
            summaries.append({"seed": seed, "error": str(e)})

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    for s in summaries:
        if "error" in s:
            print(f"  seed={s['seed']}: FAILED — {s['error']}")
        else:
            print(f"  seed={s['seed']}: pass^1={s['pass_1']*100:.1f}% "
                  f"({s['n_pass']}/{s['num_tasks']}) "
                  f"decomp_cost=${s.get('decomposer_total_cost_usd', 0):.4f} "
                  f"in {s['wall_time_s']}s")

    return 0 if all("error" not in s for s in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
