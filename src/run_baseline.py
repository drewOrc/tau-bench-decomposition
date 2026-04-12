"""Wrapper script to run τ-bench baseline with our conventions.

Runs `python -m tau_bench.run` with fixed seeds and standardized log paths,
so results land in `results/baseline/seed{seed}/` and can be merged across
seeds by `merge_seeds.py` (same pattern as cost-aware-hybrid-router).

Usage:
    # From tau-bench-decomposition/
    python src/run_baseline.py \\
        --env retail \\
        --model claude-sonnet-4-5-20250929 \\
        --seeds 42 43 44 \\
        --concurrency 6

    # Smoke test (3 tasks only)
    python src/run_baseline.py --env retail --task-ids 0 1 2 --seeds 42
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List


VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor" / "tau-bench-clean"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def build_cmd(
    env: str,
    model: str,
    model_provider: str,
    user_model: str,
    user_model_provider: str,
    seed: int,
    concurrency: int,
    log_dir: Path,
    task_ids: List[int] | None,
    strategy: str,
) -> List[str]:
    cmd = [
        sys.executable,
        "run.py",
        "--env", env,
        "--model", model,
        "--model-provider", model_provider,
        "--user-model", user_model,
        "--user-model-provider", user_model_provider,
        "--agent-strategy", strategy,
        "--temperature", "0.0",
        "--task-split", "test",
        "--log-dir", str(log_dir),
        "--max-concurrency", str(concurrency),
        "--seed", str(seed),
        "--user-strategy", "llm",
    ]
    if task_ids:
        cmd.append("--task-ids")
        cmd.extend(str(t) for t in task_ids)
    return cmd


def run_single_seed(seed: int, args: argparse.Namespace) -> int:
    log_dir = RESULTS_DIR / args.tag / f"seed{seed}"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_cmd(
        env=args.env,
        model=args.model,
        model_provider=args.model_provider,
        user_model=args.user_model,
        user_model_provider=args.user_model_provider,
        seed=seed,
        concurrency=args.concurrency,
        log_dir=log_dir,
        task_ids=args.task_ids,
        strategy=args.strategy,
    )
    print(f"\n>>> seed={seed}\n{' '.join(shlex.quote(c) for c in cmd)}\n")
    return subprocess.call(cmd, cwd=str(VENDOR_DIR))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", choices=["retail", "airline"], default="retail")
    p.add_argument("--model", default="claude-sonnet-4-5-20250929")
    p.add_argument("--model-provider", default="anthropic")
    p.add_argument("--user-model", default="gpt-4o-mini")
    p.add_argument("--user-model-provider", default="openai")
    p.add_argument("--strategy", default="tool-calling",
                   choices=["tool-calling", "act", "react", "few-shot"])
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--task-ids", type=int, nargs="+", default=None,
                   help="Run only specific task IDs (smoke test)")
    p.add_argument("--tag", default="baseline",
                   help="Subdir under results/ (e.g. 'baseline' or 'decomposer')")
    args = p.parse_args()

    if not VENDOR_DIR.exists():
        print(f"ERROR: vendor not found at {VENDOR_DIR}")
        print("Run: git clone https://github.com/sierra-research/tau-bench vendor/tau-bench")
        return 1

    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        if key not in os.environ:
            print(f"WARN: {key} not set")

    codes = []
    for seed in args.seeds:
        codes.append(run_single_seed(seed, args))
    print("\nExit codes:", codes)
    return max(codes) if codes else 0


if __name__ == "__main__":
    sys.exit(main())
