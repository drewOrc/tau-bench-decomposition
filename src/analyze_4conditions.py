"""Compare 4 conditions on the 22-task complex subset.

Conditions: baseline, rule-based, oracle, tiny-lm
Tasks: 22 complex retail tasks with oracle sub-goals

Usage:
    python src/analyze_4conditions.py
"""

import json
import glob
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUBSET_22 = [3, 19, 20, 21, 22, 23, 28, 30, 31, 32, 35, 36, 37, 38, 39, 41, 42, 46, 49, 54, 55, 64]
SEEDS = [42, 43, 44]

CONDITIONS = {
    "baseline": {
        "dir": "baseline",
        "full_run": True,  # need to extract 22-task subset
    },
    "rule-based": {
        "dir": "decomposer-rule-based",
        "full_run": True,  # need to extract 22-task subset
    },
    "oracle": {
        "dir": "decomposer-oracle",
        "full_run": False,  # already 22-task only
    },
    "tiny-lm": {
        "dir": "decomposer-tiny-lm",
        "full_run": False,  # already 22-task only
    },
}


def load_rewards_by_task(path: str) -> dict[int, float]:
    """Load checkpoint JSON, return {task_id: reward}."""
    with open(path) as f:
        data = json.load(f)
    return {r["task_id"]: r["reward"] for r in data}


def find_checkpoint(result_dir: str, seed: int) -> str | None:
    """Find the best checkpoint file for a condition/seed."""
    base = PROJECT_ROOT / "results" / result_dir / "retail" / f"seed{seed}"
    # Prefer merged_checkpoint, then latest tool-calling file
    merged = base / "merged_checkpoint.json"
    if merged.exists():
        return str(merged)
    ckpts = sorted(glob.glob(str(base / "tool-calling-*.json")))
    return ckpts[-1] if ckpts else None


def main():
    # ---- Load data ----
    # condition -> seed -> {task_id: reward}
    all_data: dict[str, dict[int, dict[int, float]]] = {}

    for cond_name, cond_info in CONDITIONS.items():
        all_data[cond_name] = {}
        for seed in SEEDS:
            ckpt = find_checkpoint(cond_info["dir"], seed)
            if ckpt is None:
                print(f"WARNING: No checkpoint for {cond_name}/seed{seed}")
                continue
            rewards = load_rewards_by_task(ckpt)
            if cond_info["full_run"]:
                # Extract subset
                rewards = {tid: rewards[tid] for tid in SUBSET_22 if tid in rewards}
            all_data[cond_name][seed] = rewards

    # ---- Summary table ----
    print("=" * 70)
    print("4-CONDITION COMPARISON ON 22-TASK COMPLEX SUBSET")
    print("=" * 70)
    print()
    print(f"{'Condition':<15} {'Seed 42':>10} {'Seed 43':>10} {'Seed 44':>10} {'Mean':>10} {'Std':>8}")
    print("-" * 63)

    condition_means = {}
    condition_per_seed = {}

    for cond_name in CONDITIONS:
        rates = []
        seed_strs = []
        for seed in SEEDS:
            rewards = all_data[cond_name].get(seed, {})
            if not rewards:
                seed_strs.append(f"{'N/A':>10}")
                continue
            n_tasks = len(rewards)
            n_pass = sum(1 for r in rewards.values() if r >= 0.999)
            rate = n_pass / n_tasks * 100 if n_tasks else 0
            rates.append(rate)
            seed_strs.append(f"{n_pass}/{n_tasks}={rate:.1f}%")

        mean_rate = sum(rates) / len(rates) if rates else 0
        std_rate = (sum((r - mean_rate) ** 2 for r in rates) / len(rates)) ** 0.5 if len(rates) > 1 else 0
        condition_means[cond_name] = mean_rate
        condition_per_seed[cond_name] = rates

        print(f"{cond_name:<15} {seed_strs[0]:>10} {seed_strs[1]:>10} {seed_strs[2]:>10} {mean_rate:>9.1f}% {std_rate:>7.1f}pp")

    # ---- Deltas from baseline ----
    print()
    print("Deltas from baseline:")
    baseline_mean = condition_means.get("baseline", 0)
    for cond_name in CONDITIONS:
        if cond_name == "baseline":
            continue
        delta = condition_means[cond_name] - baseline_mean
        print(f"  {cond_name}: {delta:+.1f}pp")

    # ---- Per-task analysis ----
    print()
    print("=" * 70)
    print("PER-TASK PASS RATES (across 3 seeds)")
    print("=" * 70)
    print()
    header = f"{'Task':>6}"
    for cond_name in CONDITIONS:
        header += f"  {cond_name:>12}"
    header += "  delta(oracle)"
    print(header)
    print("-" * (6 + 14 * len(CONDITIONS) + 16))

    for tid in SUBSET_22:
        row = f"{tid:>6}"
        task_rates = {}
        for cond_name in CONDITIONS:
            passes = 0
            total = 0
            for seed in SEEDS:
                rewards = all_data[cond_name].get(seed, {})
                if tid in rewards:
                    total += 1
                    if rewards[tid] >= 0.999:
                        passes += 1
            rate = passes / total if total else 0
            task_rates[cond_name] = rate
            row += f"  {passes}/{total}={rate*100:4.0f}%"

        baseline_rate = task_rates.get("baseline", 0)
        oracle_rate = task_rates.get("oracle", 0)
        delta = oracle_rate - baseline_rate
        marker = "⬆" if delta > 0.01 else ("⬇" if delta < -0.01 else "=")
        row += f"  {delta*100:+5.0f}pp {marker}"
        print(row)

    # ---- Statistical tests (oracle vs baseline, tiny-lm vs baseline) ----
    print()
    print("=" * 70)
    print("STATISTICAL TESTS (pooled across seeds)")
    print("=" * 70)

    try:
        from scipy.stats import wilcoxon

        for test_cond in ["oracle", "tiny-lm"]:
            if test_cond not in all_data or not all_data[test_cond]:
                continue
            print(f"\n--- {test_cond} vs baseline ---")

            # Pooled: one observation per (task, seed)
            baseline_vec = []
            test_vec = []
            for seed in SEEDS:
                bl_rewards = all_data["baseline"].get(seed, {})
                test_rewards = all_data[test_cond].get(seed, {})
                for tid in SUBSET_22:
                    if tid in bl_rewards and tid in test_rewards:
                        baseline_vec.append(1 if bl_rewards[tid] >= 0.999 else 0)
                        test_vec.append(1 if test_rewards[tid] >= 0.999 else 0)

            n = len(baseline_vec)
            bl_pass = sum(baseline_vec)
            test_pass = sum(test_vec)
            print(f"  Pooled observations: {n}")
            print(f"  Baseline pass: {bl_pass}/{n} = {bl_pass/n*100:.1f}%")
            print(f"  {test_cond} pass: {test_pass}/{n} = {test_pass/n*100:.1f}%")

            # McNemar's test
            # a: both pass, b: baseline pass + test fail, c: baseline fail + test pass, d: both fail
            a = sum(1 for i in range(n) if baseline_vec[i] == 1 and test_vec[i] == 1)
            b = sum(1 for i in range(n) if baseline_vec[i] == 1 and test_vec[i] == 0)
            c = sum(1 for i in range(n) if baseline_vec[i] == 0 and test_vec[i] == 1)
            d = sum(1 for i in range(n) if baseline_vec[i] == 0 and test_vec[i] == 0)
            print(f"  McNemar contingency: a={a} b={b} c={c} d={d}")
            if b + c > 0:
                mcnemar_chi2 = (abs(b - c) - 1) ** 2 / (b + c)
                from scipy.stats import chi2
                p_mcnemar = 1 - chi2.cdf(mcnemar_chi2, df=1)
                print(f"  McNemar's chi2={mcnemar_chi2:.3f}, p={p_mcnemar:.4f}")
            else:
                print(f"  McNemar: no discordant pairs")

            # Per-seed pass rates for Wilcoxon
            bl_rates = condition_per_seed.get("baseline", [])
            test_rates = condition_per_seed.get(test_cond, [])
            if len(bl_rates) == len(test_rates) == 3:
                diffs = [test_rates[i] - bl_rates[i] for i in range(3)]
                print(f"  Per-seed diffs: {[f'{d:+.1f}pp' for d in diffs]}")
                if any(d != 0 for d in diffs):
                    try:
                        stat, p = wilcoxon(bl_rates, test_rates)
                        print(f"  Wilcoxon signed-rank: stat={stat:.3f}, p={p:.4f}")
                    except Exception as e:
                        print(f"  Wilcoxon: {e}")

            # Effect size (Cohen's d)
            if len(bl_rates) > 1 and len(test_rates) > 1:
                import math
                mean_bl = sum(bl_rates) / len(bl_rates)
                mean_test = sum(test_rates) / len(test_rates)
                var_bl = sum((r - mean_bl) ** 2 for r in bl_rates) / (len(bl_rates) - 1)
                var_test = sum((r - mean_test) ** 2 for r in test_rates) / (len(test_rates) - 1)
                pooled_std = math.sqrt((var_bl + var_test) / 2)
                d = (mean_test - mean_bl) / pooled_std if pooled_std > 0 else float("inf")
                print(f"  Cohen's d = {d:.2f}")

    except ImportError:
        print("scipy not installed — skipping statistical tests")

    # ---- Decomposer cost summary ----
    print()
    print("=" * 70)
    print("DECOMPOSER COST SUMMARY")
    print("=" * 70)
    for cond_name in ["rule-based", "oracle", "tiny-lm"]:
        costs = []
        for seed in SEEDS:
            summary_path = PROJECT_ROOT / "results" / CONDITIONS[cond_name]["dir"] / "retail" / f"seed{seed}" / "summary.json"
            try:
                with open(summary_path) as f:
                    s = json.load(f)
                costs.append(s.get("decomposer_total_cost_usd", 0))
            except:
                costs.append(None)
        cost_strs = [f"${c:.4f}" if c is not None else "N/A" for c in costs]
        total = sum(c for c in costs if c is not None)
        print(f"  {cond_name:<15} seeds: {cost_strs}  total: ${total:.4f}")


if __name__ == "__main__":
    main()
