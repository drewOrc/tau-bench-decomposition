"""Run τ-bench baseline via Python API (bypasses broken CLI argparse).

τ-bench's run.py uses litellm enum objects as argparse choices, which
breaks string comparison. We import tau_bench.run.run() directly with a
RunConfig Pydantic model, giving us full control over parameters.

Usage:
    # Activate venv first!
    # Smoke test (1 task)
    python src/run_baseline.py --env retail --task-ids 0 --seeds 42

    # Full baseline (gpt-4o FC, 3 seeds)
    python src/run_baseline.py --env retail --seeds 42 43 44 --concurrency 2

    # Airline baseline
    python src/run_baseline.py --env airline --seeds 42 43 44 --concurrency 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
import litellm
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Enable litellm retry on rate limit (429) errors.
# tau-bench's litellm calls default to num_retries=None (no retry),
# which makes every 429 a fatal task failure. With retries, litellm
# waits the suggested duration and tries again.
litellm.num_retries = 5

RESULTS_DIR = PROJECT_ROOT / "results"


def run_single_seed(seed: int, args: argparse.Namespace) -> dict:
    """Run τ-bench for a single seed and return summary dict."""
    from tau_bench.run import run
    from tau_bench.types import RunConfig

    log_dir = RESULTS_DIR / args.tag / args.env / f"seed{seed}"
    log_dir.mkdir(parents=True, exist_ok=True)

    config = RunConfig(
        model=args.model,
        model_provider=args.model_provider,
        user_model=args.user_model,
        user_model_provider=args.user_model_provider,
        agent_strategy=args.strategy,
        temperature=args.temperature,
        env=args.env,
        task_split="test",
        task_ids=args.task_ids,
        log_dir=str(log_dir),
        max_concurrency=args.concurrency,
        seed=seed,
        user_strategy="llm",
    )

    print(f"\n{'='*60}")
    print(f">>> seed={seed} | env={args.env} | model={args.model}")
    print(f">>> log_dir={log_dir}")
    if args.task_ids:
        print(f">>> task_ids={args.task_ids}")
    print(f"{'='*60}\n")

    t0 = time.time()
    results = run(config)
    wall_time = time.time() - t0

    # Compute pass^1 from returned results
    rewards = [r.reward for r in results]
    n_pass = sum(1 for r in rewards if r >= 0.999)
    n_tasks = len(rewards)
    pass_1 = n_pass / n_tasks if n_tasks else 0.0

    summary = {
        "seed": seed,
        "env": args.env,
        "model": args.model,
        "model_provider": args.model_provider,
        "user_model": args.user_model,
        "strategy": args.strategy,
        "temperature": args.temperature,
        "wall_time_s": round(wall_time, 1),
        "num_tasks": n_tasks,
        "pass_1": round(pass_1, 4),
        "n_pass": n_pass,
        "mean_reward": round(sum(rewards) / n_tasks, 4) if n_tasks else 0.0,
    }

    # Save per-seed summary
    summary_path = log_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n>>> seed={seed} done in {wall_time:.1f}s")
    print(f">>> pass^1 = {pass_1*100:.1f}% ({n_pass}/{n_tasks})")
    print(f">>> summary → {summary_path}")

    return summary


def main() -> int:
    p = argparse.ArgumentParser(description="Run τ-bench baseline via Python API")
    p.add_argument("--env", choices=["retail", "airline"], default="retail")
    p.add_argument("--model", default="gpt-4o",
                   help="Agent model (default: gpt-4o for paper reproduction)")
    p.add_argument("--model-provider", default="openai")
    p.add_argument("--user-model", default="gpt-4o",
                   help="User simulator model (gpt-4o matches paper setup)")
    p.add_argument("--user-model-provider", default="openai")
    p.add_argument("--strategy", default="tool-calling",
                   choices=["tool-calling", "act", "react", "few-shot"])
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--concurrency", type=int, default=1,
                   help="Parallel tasks per seed (default: 1 for smoke test)")
    p.add_argument("--task-ids", type=int, nargs="+", default=None,
                   help="Run only specific task IDs (for smoke test)")
    p.add_argument("--tag", default="baseline",
                   help="Subdir under results/ (e.g. 'baseline', 'decomposer')")
    args = p.parse_args()

    # Validate API keys
    missing = []
    if "openai" in args.model_provider and not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if "openai" in args.user_model_provider and not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if "anthropic" in args.model_provider and not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"ERROR: Missing API keys: {set(missing)}")
        print("Set them in .env or export them.")
        return 1

    print(f"Config: model={args.model}, provider={args.model_provider}, "
          f"user={args.user_model}, strategy={args.strategy}")
    print(f"Seeds: {args.seeds}, concurrency={args.concurrency}")
    if args.task_ids:
        print(f"Task IDs: {args.task_ids} (smoke test mode)")

    summaries = []
    for seed in args.seeds:
        try:
            s = run_single_seed(seed, args)
            summaries.append(s)
        except Exception as e:
            print(f"\n!!! seed={seed} FAILED: {e}")
            summaries.append({"seed": seed, "error": str(e)})

    # Print final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    for s in summaries:
        if "error" in s:
            print(f"  seed={s['seed']}: FAILED — {s['error']}")
        else:
            print(f"  seed={s['seed']}: pass^1={s['pass_1']*100:.1f}% "
                  f"({s['n_pass']}/{s['num_tasks']}) in {s['wall_time_s']}s")

    return 0 if all("error" not in s for s in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
