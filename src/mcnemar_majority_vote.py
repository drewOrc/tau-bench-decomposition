"""Majority-vote McNemar analysis for tau-bench decomposition.

Reviewer concern: pooling 22 tasks x 3 seeds = 66 observations inflates
effective sample size because within-task outcomes are correlated across seeds.

This script aggregates per-task via majority vote: a task "passes" if it
succeeds on >= 2 of 3 seeds.  This yields n=22 truly independent observations
for McNemar's test.

All pairwise condition comparisons are reported, with contingency tables,
odds ratios, and a comparison to the pooled (n=66) results.

Usage:
    python src/mcnemar_majority_vote.py
"""

from __future__ import annotations

import json
import glob
from pathlib import Path
from scipy.stats import chi2

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUBSET_22 = [
    3, 19, 20, 21, 22, 23, 28, 30, 31, 32,
    35, 36, 37, 38, 39, 41, 42, 46, 49, 54, 55, 64,
]
SEEDS = [42, 43, 44]

CONDITIONS = {
    "baseline":   {"dir": "baseline",             "full_run": True},
    "rule-based": {"dir": "decomposer-rule-based", "full_run": True},
    "oracle":     {"dir": "decomposer-oracle",     "full_run": False},
    "tiny-lm":    {"dir": "decomposer-tiny-lm",    "full_run": False},
    "same-model": {"dir": "decomposer-same-model", "full_run": False},
}

PAIRWISE_COMPARISONS = [
    ("oracle",     "baseline"),
    ("tiny-lm",    "baseline"),
    ("same-model", "baseline"),
    ("oracle",     "tiny-lm"),
    ("oracle",     "same-model"),
    ("same-model", "tiny-lm"),
]

PASS_THRESHOLD = 0.999


def load_rewards_by_task(path: str) -> dict[int, float]:
    """Load checkpoint JSON, return {task_id: reward}."""
    with open(path) as f:
        data = json.load(f)
    return {r["task_id"]: r["reward"] for r in data}


def find_checkpoint(result_dir: str, seed: int) -> str | None:
    """Find the best checkpoint file for a condition/seed."""
    base = PROJECT_ROOT / "results" / result_dir / "retail" / f"seed{seed}"
    merged = base / "merged_checkpoint.json"
    if merged.exists():
        return str(merged)
    ckpts = sorted(glob.glob(str(base / "tool-calling-*.json")))
    return ckpts[-1] if ckpts else None


def majority_vote(
    seed_rewards: dict[int, dict[int, float]],
    task_ids: list[int],
) -> dict[int, int]:
    """For each task, return 1 if it passes on >= 2 of 3 seeds, else 0."""
    result = {}
    for tid in task_ids:
        passes = sum(
            1
            for seed in SEEDS
            if seed in seed_rewards
            and tid in seed_rewards[seed]
            and seed_rewards[seed][tid] >= PASS_THRESHOLD
        )
        result[tid] = 1 if passes >= 2 else 0
    return result


def mcnemar_test(
    vec_a: list[int],
    vec_b: list[int],
) -> tuple[int, int, int, int, float | None, float | None]:
    """McNemar test with continuity correction.

    Contingency table convention:
        a = both pass
        b = A passes, B fails
        c = A fails,  B passes
        d = both fail

    Returns (a, b, c, d, chi2_stat, p_value).
    """
    n = len(vec_a)
    a = sum(1 for i in range(n) if vec_a[i] == 1 and vec_b[i] == 1)
    b = sum(1 for i in range(n) if vec_a[i] == 1 and vec_b[i] == 0)
    c = sum(1 for i in range(n) if vec_a[i] == 0 and vec_b[i] == 1)
    d = sum(1 for i in range(n) if vec_a[i] == 0 and vec_b[i] == 0)

    if b + c > 0:
        chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)
        p_value = 1 - chi2.cdf(chi2_stat, df=1)
    else:
        chi2_stat = None
        p_value = None

    return a, b, c, d, chi2_stat, p_value


def odds_ratio(b: int, c: int) -> str:
    """Odds ratio for discordant pairs.  c/b when b > 0."""
    if b == 0 and c == 0:
        return "undefined (no discordant pairs)"
    if b == 0:
        return f"inf ({c} gained, 0 lost)"
    return f"{c / b:.2f}  (c/b = {c}/{b})"


def pooled_mcnemar(
    data_a: dict[int, dict[int, float]],
    data_b: dict[int, dict[int, float]],
) -> tuple[int, int, int, int, float | None, float | None, int]:
    """McNemar on 22 x 3 = 66 pooled observations."""
    vec_a: list[int] = []
    vec_b: list[int] = []
    for seed in SEEDS:
        ra = data_a.get(seed, {})
        rb = data_b.get(seed, {})
        for tid in SUBSET_22:
            if tid in ra and tid in rb:
                vec_a.append(1 if ra[tid] >= PASS_THRESHOLD else 0)
                vec_b.append(1 if rb[tid] >= PASS_THRESHOLD else 0)
    a, b, c, d, chi2_stat, p_val = mcnemar_test(vec_a, vec_b)
    return a, b, c, d, chi2_stat, p_val, len(vec_a)


def main() -> None:
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
                rewards = {tid: rewards[tid] for tid in SUBSET_22 if tid in rewards}
            all_data[cond_name][seed] = rewards

    mv: dict[str, dict[int, int]] = {}
    for cond_name in CONDITIONS:
        mv[cond_name] = majority_vote(all_data[cond_name], SUBSET_22)

    print("=" * 72)
    print("MAJORITY-VOTE McNEMAR ANALYSIS  (n=22 independent tasks)")
    print("  Vote rule: task passes if reward >= 0.999 on >= 2 of 3 seeds")
    print("=" * 72)

    print("\n--- Per-condition majority-vote pass rates ---\n")
    print(f"{'Condition':<15} {'MV Pass':>8} {'MV Fail':>8} {'Rate':>8}   per-seed raw rates")
    print("-" * 72)

    for cond_name in CONDITIONS:
        n_pass = sum(mv[cond_name][tid] for tid in SUBSET_22)
        n_fail = len(SUBSET_22) - n_pass
        rate = n_pass / len(SUBSET_22) * 100

        # Also show per-seed raw rates for context
        raw_rates = []
        for seed in SEEDS:
            rewards = all_data[cond_name].get(seed, {})
            sp = sum(1 for tid in SUBSET_22 if tid in rewards and rewards[tid] >= PASS_THRESHOLD)
            raw_rates.append(f"{sp}/22")

        print(
            f"{cond_name:<15} {n_pass:>8} {n_fail:>8} {rate:>7.1f}%"
            f"   [{', '.join(raw_rates)}]"
        )

    print("\n--- Per-task majority-vote detail ---\n")
    header = f"{'Task':>6}"
    for cond_name in CONDITIONS:
        header += f"  {cond_name:>11}"
    print(header)
    print("-" * (6 + 13 * len(CONDITIONS)))

    for tid in SUBSET_22:
        row = f"{tid:>6}"
        for cond_name in CONDITIONS:
            # Show seed-level detail: e.g. "2/3 -> P" or "1/3 -> F"
            n_pass_seeds = sum(
                1
                for seed in SEEDS
                if seed in all_data[cond_name]
                and tid in all_data[cond_name][seed]
                and all_data[cond_name][seed][tid] >= PASS_THRESHOLD
            )
            mv_label = "P" if n_pass_seeds >= 2 else "F"
            row += f"  {n_pass_seeds}/3->{mv_label:>1}"
        print(row)

    print("\n" + "=" * 72)
    print("PAIRWISE McNEMAR TESTS  (majority vote, n=22)")
    print("=" * 72)

    for cond_a, cond_b in PAIRWISE_COMPARISONS:
        vec_a = [mv[cond_a][tid] for tid in SUBSET_22]
        vec_b = [mv[cond_b][tid] for tid in SUBSET_22]
        a, b, c, d, chi2_stat, p_val = mcnemar_test(vec_a, vec_b)

        pass_a = sum(vec_a)
        pass_b = sum(vec_b)
        delta = (pass_a - pass_b) / len(SUBSET_22) * 100

        print(f"\n--- {cond_a} vs {cond_b} ---")
        print(f"  {cond_a:<12} pass: {pass_a}/22 = {pass_a / 22 * 100:.1f}%")
        print(f"  {cond_b:<12} pass: {pass_b}/22 = {pass_b / 22 * 100:.1f}%")
        print(f"  Delta ({cond_a} - {cond_b}): {delta:+.1f}pp")
        print()
        print(f"  2x2 contingency table:")
        print(f"                      {cond_b} pass   {cond_b} fail")
        print(f"    {cond_a} pass        a={a:<6}      b={b}")
        print(f"    {cond_a} fail        c={c:<6}      d={d}")
        print(f"  Discordant pairs: b+c = {b + c}")
        print(f"  Odds ratio: {odds_ratio(b, c)}")

        if chi2_stat is not None:
            sig = "SIGNIFICANT *" if p_val < 0.05 else "not significant"
            print(f"  McNemar chi2 = {chi2_stat:.4f},  p = {p_val:.4f}  [{sig}]")
        else:
            print(f"  McNemar: no discordant pairs (cannot compute)")

    print("\n" + "=" * 72)
    print("COMPARISON: MAJORITY-VOTE (n=22) vs POOLED (n=66)")
    print("=" * 72)

    print(f"\n{'Comparison':<28} {'Pooled p':>10} {'MV p':>10} {'Pooled b+c':>12} {'MV b+c':>8} {'Verdict':>14}")
    print("-" * 90)

    for cond_a, cond_b in PAIRWISE_COMPARISONS:
        # Majority-vote
        vec_a_mv = [mv[cond_a][tid] for tid in SUBSET_22]
        vec_b_mv = [mv[cond_b][tid] for tid in SUBSET_22]
        _, b_mv, c_mv, _, chi2_mv, p_mv = mcnemar_test(vec_a_mv, vec_b_mv)

        # Pooled
        _, b_p, c_p, _, chi2_p, p_p, n_p = pooled_mcnemar(
            all_data[cond_a], all_data[cond_b]
        )

        p_mv_str = f"{p_mv:.4f}" if p_mv is not None else "N/A"
        p_p_str = f"{p_p:.4f}" if p_p is not None else "N/A"

        if p_mv is not None and p_p is not None:
            if p_mv < 0.05 and p_p < 0.05:
                verdict = "both sig."
            elif p_mv >= 0.05 and p_p < 0.05:
                verdict = "LOST at n=22"
            elif p_mv < 0.05 and p_p >= 0.05:
                verdict = "GAINED at n=22"
            else:
                verdict = "both n.s."
        else:
            verdict = "N/A"

        label = f"{cond_a} vs {cond_b}"
        print(
            f"{label:<28} {p_p_str:>10} {p_mv_str:>10} {b_p + c_p:>12} {b_mv + c_mv:>8} {verdict:>14}"
        )

    print("\n" + "=" * 72)
    print("INTERPRETATION")
    print("=" * 72)

    # The critical check: oracle vs baseline
    vec_or = [mv["oracle"][tid] for tid in SUBSET_22]
    vec_bl = [mv["baseline"][tid] for tid in SUBSET_22]
    _, b_crit, c_crit, _, _, p_crit = mcnemar_test(vec_or, vec_bl)

    print()
    if p_crit is not None and p_crit < 0.05:
        print(f"  CRITICAL: Oracle vs Baseline remains SIGNIFICANT at n=22")
        print(f"    p = {p_crit:.4f} (majority-vote McNemar, continuity-corrected)")
        print(f"    This addresses the correlated-observations concern: even with")
        print(f"    only 22 independent data points, the oracle effect holds.")
    else:
        p_str = f"{p_crit:.4f}" if p_crit is not None else "N/A"
        print(f"  CRITICAL: Oracle vs Baseline is NOT significant at n=22")
        print(f"    p = {p_str} (majority-vote McNemar, continuity-corrected)")
        print(f"    The pooled p=0.007 was likely inflated by within-task correlation.")
        print(f"    Discordant pairs at n=22: b={b_crit}, c={c_crit}")
        print(f"    The effect may be real but the sample is too small to confirm")
        print(f"    with majority-vote aggregation.")
    print()


if __name__ == "__main__":
    main()
