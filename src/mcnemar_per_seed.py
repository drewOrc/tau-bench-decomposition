"""Per-seed McNemar tests for oracle vs baseline and oracle vs tiny-lm
on the 22-task complex subset.

Computes:
1. Per-seed 2x2 McNemar contingency tables (baseline vs oracle)
2. Pooled McNemar oracle vs tiny-lm
3. Consistency analysis: is pooled p=0.007 driven by one seed?
"""

from __future__ import annotations

import json
import glob
from pathlib import Path
from scipy.stats import chi2

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SUBSET_22 = [3, 19, 20, 21, 22, 23, 28, 30, 31, 32, 35, 36, 37, 38, 39, 41, 42, 46, 49, 54, 55, 64]
SEEDS = [42, 43, 44]

CONDITIONS = {
    "baseline": {"dir": "baseline", "full_run": True},
    "oracle": {"dir": "decomposer-oracle", "full_run": False},
    "tiny-lm": {"dir": "decomposer-tiny-lm", "full_run": False},
    "same-model": {"dir": "decomposer-same-model", "full_run": False},
}


def load_rewards_by_task(path: str) -> dict[int, float]:
    with open(path) as f:
        data = json.load(f)
    return {r["task_id"]: r["reward"] for r in data}


def find_checkpoint(result_dir: str, seed: int) -> str | None:
    base = PROJECT_ROOT / "results" / result_dir / "retail" / f"seed{seed}"
    merged = base / "merged_checkpoint.json"
    if merged.exists():
        return str(merged)
    ckpts = sorted(glob.glob(str(base / "tool-calling-*.json")))
    return ckpts[-1] if ckpts else None


def mcnemar_test(bl_vec, test_vec, label=""):
    """Compute McNemar test with continuity correction.
    Returns (a, b, c, d, chi2_stat, p_value)
    """
    n = len(bl_vec)
    a = sum(1 for i in range(n) if bl_vec[i] == 1 and test_vec[i] == 1)  # both pass
    b = sum(1 for i in range(n) if bl_vec[i] == 1 and test_vec[i] == 0)  # bl pass, test fail
    c = sum(1 for i in range(n) if bl_vec[i] == 0 and test_vec[i] == 1)  # bl fail, test pass
    d = sum(1 for i in range(n) if bl_vec[i] == 0 and test_vec[i] == 0)  # both fail

    if b + c > 0:
        chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)  # continuity correction
        p_value = 1 - chi2.cdf(chi2_stat, df=1)
    else:
        chi2_stat = None
        p_value = None

    return a, b, c, d, chi2_stat, p_value


def main():
    all_data = {}
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

    print("=" * 70)
    print("1. PER-SEED McNEMAR: ORACLE vs BASELINE (22-task complex subset)")
    print("=" * 70)

    per_seed_discordant = []  # track (b, c) per seed

    for seed in SEEDS:
        bl_rewards = all_data["baseline"].get(seed, {})
        or_rewards = all_data["oracle"].get(seed, {})

        bl_vec = []
        or_vec = []
        for tid in SUBSET_22:
            if tid in bl_rewards and tid in or_rewards:
                bl_vec.append(1 if bl_rewards[tid] >= 0.999 else 0)
                or_vec.append(1 if or_rewards[tid] >= 0.999 else 0)

        a, b, c, d, chi2_stat, p_val = mcnemar_test(bl_vec, or_vec)
        per_seed_discordant.append((b, c))

        bl_pass = sum(bl_vec)
        or_pass = sum(or_vec)
        n = len(bl_vec)

        print(f"\n--- Seed {seed} (n={n} tasks) ---")
        print(f"  Baseline pass: {bl_pass}/{n} = {bl_pass/n*100:.1f}%")
        print(f"  Oracle pass:   {or_pass}/{n} = {or_pass/n*100:.1f}%")
        print(f"  Delta:         {(or_pass - bl_pass)/n*100:+.1f}pp")
        print(f"  McNemar 2x2:   a={a} (both pass), b={b} (bl+/or-), c={c} (bl-/or+), d={d} (both fail)")
        print(f"  Discordant pairs: b+c = {b+c}")
        if chi2_stat is not None:
            print(f"  McNemar chi2 = {chi2_stat:.4f}, p = {p_val:.4f}  {'*' if p_val < 0.05 else 'n.s.'}")
        else:
            print(f"  McNemar: no discordant pairs")

        # Show which tasks flipped
        flipped_bl_to_or = [tid for i, tid in enumerate(SUBSET_22[:n]) if bl_vec[i] == 0 and or_vec[i] == 1]
        flipped_or_to_bl = [tid for i, tid in enumerate(SUBSET_22[:n]) if bl_vec[i] == 1 and or_vec[i] == 0]
        if flipped_bl_to_or:
            print(f"  Tasks gained by oracle (bl fail -> or pass): {flipped_bl_to_or}")
        if flipped_or_to_bl:
            print(f"  Tasks lost by oracle (bl pass -> or fail):   {flipped_or_to_bl}")

    print("\n" + "=" * 70)
    print("1b. POOLED McNEMAR: ORACLE vs BASELINE (all seeds, 66 observations)")
    print("=" * 70)

    bl_vec_pooled = []
    or_vec_pooled = []
    for seed in SEEDS:
        bl_rewards = all_data["baseline"].get(seed, {})
        or_rewards = all_data["oracle"].get(seed, {})
        for tid in SUBSET_22:
            if tid in bl_rewards and tid in or_rewards:
                bl_vec_pooled.append(1 if bl_rewards[tid] >= 0.999 else 0)
                or_vec_pooled.append(1 if or_rewards[tid] >= 0.999 else 0)

    a, b, c, d, chi2_stat, p_val = mcnemar_test(bl_vec_pooled, or_vec_pooled)
    n = len(bl_vec_pooled)
    print(f"\n  Pooled observations: {n}")
    print(f"  Baseline pass: {sum(bl_vec_pooled)}/{n} = {sum(bl_vec_pooled)/n*100:.1f}%")
    print(f"  Oracle pass:   {sum(or_vec_pooled)}/{n} = {sum(or_vec_pooled)/n*100:.1f}%")
    print(f"  McNemar 2x2:   a={a}, b={b}, c={c}, d={d}")
    if chi2_stat is not None:
        print(f"  McNemar chi2 = {chi2_stat:.4f}, p = {p_val:.4f}  {'*' if p_val < 0.05 else 'n.s.'}")

    print("\n" + "=" * 70)
    print("2. POOLED McNEMAR: ORACLE vs TINY-LM (all seeds)")
    print("=" * 70)

    or_vec2 = []
    tl_vec2 = []
    for seed in SEEDS:
        or_rewards = all_data["oracle"].get(seed, {})
        tl_rewards = all_data["tiny-lm"].get(seed, {})
        for tid in SUBSET_22:
            if tid in or_rewards and tid in tl_rewards:
                or_vec2.append(1 if or_rewards[tid] >= 0.999 else 0)
                tl_vec2.append(1 if tl_rewards[tid] >= 0.999 else 0)

    a, b, c, d, chi2_stat, p_val = mcnemar_test(or_vec2, tl_vec2, "oracle vs tiny-lm")
    n = len(or_vec2)
    print(f"\n  Pooled observations: {n}")
    print(f"  Oracle pass:  {sum(or_vec2)}/{n} = {sum(or_vec2)/n*100:.1f}%")
    print(f"  Tiny-LM pass: {sum(tl_vec2)}/{n} = {sum(tl_vec2)/n*100:.1f}%")
    print(f"  McNemar 2x2:  a={a}, b={b}, c={c}, d={d}")
    if chi2_stat is not None:
        print(f"  McNemar chi2 = {chi2_stat:.4f}, p = {p_val:.4f}  {'*' if p_val < 0.05 else 'n.s.'}")

    # Also per-seed for oracle vs tiny-lm
    print("\n  Per-seed breakdown (oracle vs tiny-lm):")
    for seed in SEEDS:
        or_rewards = all_data["oracle"].get(seed, {})
        tl_rewards = all_data["tiny-lm"].get(seed, {})
        ov, tv = [], []
        for tid in SUBSET_22:
            if tid in or_rewards and tid in tl_rewards:
                ov.append(1 if or_rewards[tid] >= 0.999 else 0)
                tv.append(1 if tl_rewards[tid] >= 0.999 else 0)
        a, b, c, d, chi2_stat, p_val = mcnemar_test(ov, tv)
        n = len(ov)
        p_str = f"p={p_val:.4f}" if p_val is not None else "no discordant"
        print(f"    Seed {seed}: or={sum(ov)}/{n}, tl={sum(tv)}/{n}, a={a} b={b} c={c} d={d}, {p_str}")

    print("\n" + "=" * 70)
    print("3. CONSISTENCY ANALYSIS: Is pooled p=0.007 driven by one seed?")
    print("=" * 70)

    print("\n  Per-seed discordant pair ratios (oracle vs baseline):")
    total_b = 0
    total_c = 0
    for i, seed in enumerate(SEEDS):
        b, c = per_seed_discordant[i]
        total_b += b
        total_c += c
        direction = "oracle gains" if c > b else ("baseline gains" if b > c else "tied")
        print(f"    Seed {seed}: b={b} (bl+/or-), c={c} (bl-/or+)  -> net {c-b:+d} ({direction})")

    print(f"\n  Total across seeds: b={total_b}, c={total_c}")
    print(f"  If effect is consistent, each seed should contribute similar c-b ratios.")

    # Check if removing any single seed kills significance
    print("\n  Leave-one-seed-out sensitivity:")
    for leave_out in SEEDS:
        bl_vec_loo = []
        or_vec_loo = []
        for seed in SEEDS:
            if seed == leave_out:
                continue
            bl_rewards = all_data["baseline"].get(seed, {})
            or_rewards = all_data["oracle"].get(seed, {})
            for tid in SUBSET_22:
                if tid in bl_rewards and tid in or_rewards:
                    bl_vec_loo.append(1 if bl_rewards[tid] >= 0.999 else 0)
                    or_vec_loo.append(1 if or_rewards[tid] >= 0.999 else 0)

        a, b, c, d, chi2_stat, p_val = mcnemar_test(bl_vec_loo, or_vec_loo)
        n = len(bl_vec_loo)
        p_str = f"p={p_val:.4f}" if p_val is not None else "no discordant"
        sig = "*" if (p_val is not None and p_val < 0.05) else "n.s."
        chi2_str = f"{chi2_stat:.4f}" if chi2_stat is not None else "N/A"
        print(f"    Without seed {leave_out}: n={n}, b={b}, c={c}, chi2={chi2_str}, {p_str} {sig}")


if __name__ == "__main__":
    main()
