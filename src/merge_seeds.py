"""Merge τ-bench per-seed result JSONs into aggregated metrics with pass^k + CIs.

Mirrors cost-aware-hybrid-router's merge_seeds.py pattern, adapted for τ-bench:
  - Input: results/{tag}/{domain}/seed{N}/*.json (from tau_bench.run)
  - Output: results/{tag}/{domain}/metrics_merged.json

Key metrics:
  - pass^1: mean per-task reward across tasks (pooled across seeds)
  - pass^k: fraction of tasks where ALL k seeds scored reward=1
  - per-seed pass^1 with std
  - Wilson 95% CI (pooled, n = n_tasks × n_seeds)
  - McNemar test between two tags (e.g. baseline vs decomposer)

Usage:
    # Aggregate one run
    python src/merge_seeds.py --tag baseline --domain retail --seeds 42 43 44

    # Compare two runs
    python src/merge_seeds.py --tag decomposer --domain retail --seeds 42 43 44 \\
        --compare-to baseline
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_seed_results(tag: str, seeds: List[int], domain: str = "") -> Dict[int, List[dict]]:
    """Load results-*.json files for each seed. Returns {seed: [records]}."""
    out: Dict[int, List[dict]] = {}
    for seed in seeds:
        if domain:
            seed_dir = RESULTS / tag / domain / f"seed{seed}"
        else:
            seed_dir = RESULTS / tag / f"seed{seed}"
        files = sorted(seed_dir.glob("results-*.json"))
        if not files:
            # tau-bench names files like tool-calling-gpt-4o-0.0_range_*.json
            files = sorted(
                p for p in seed_dir.glob("*.json")
                if p.name not in ("summary.json", "metrics_merged.json")
            )
        if not files:
            raise FileNotFoundError(f"No result JSON in {seed_dir}")
        # Take the most recent file per seed directory
        with open(files[-1]) as f:
            records = json.load(f)
        out[seed] = records
        print(f"  seed {seed}: {len(records)} tasks from {files[-1].name}")
    return out


def wilson_ci(k: int, n: int, z: float = 1.96) -> dict:
    if n == 0:
        return {"lower": 0.0, "upper": 0.0, "point": 0.0}
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    margin = z * ((p * (1 - p) / n + z ** 2 / (4 * n ** 2)) ** 0.5) / denom
    return {
        "lower": round(center - margin, 4),
        "upper": round(center + margin, 4),
        "point": round(p, 4),
    }


def agg(values: List[float]) -> dict:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    if len(values) < 2:
        return {"mean": round(values[0], 4), "std": 0.0,
                "min": round(values[0], 4), "max": round(values[0], 4)}
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def compute_pass_k(seed_results: Dict[int, List[dict]]) -> dict:
    """Compute pass^k: fraction of tasks where ALL k seeds scored reward=1.

    Also returns per-seed pass^1 and pooled pass^1.
    """
    # Index by task_id per seed
    by_task: Dict[int, Dict[int, float]] = defaultdict(dict)
    for seed, records in seed_results.items():
        for r in records:
            tid = r["task_id"]
            by_task[tid][seed] = float(r.get("reward", 0.0))

    n_seeds = len(seed_results)
    task_ids = sorted(by_task.keys())
    # Only keep tasks that appear in ALL seeds (fair pass^k)
    complete_tasks = [t for t in task_ids if len(by_task[t]) == n_seeds]
    n_complete = len(complete_tasks)

    # pass^k: reward == 1 on all seeds
    pass_k_count = sum(
        1 for t in complete_tasks
        if all(by_task[t][s] >= 0.999 for s in seed_results)
    )
    # pass^1 per seed
    pass_1_per_seed = {}
    for seed, records in seed_results.items():
        rewards = [float(r.get("reward", 0.0)) for r in records]
        pass_1_per_seed[seed] = {
            "pass_1": round(sum(r >= 0.999 for r in rewards) / len(rewards), 4),
            "mean_reward": round(statistics.mean(rewards), 4),
            "n": len(rewards),
        }

    # Pooled pass^1
    all_rewards = [r for recs in seed_results.values()
                   for r in [float(x.get("reward", 0.0)) for x in recs]]
    pooled_correct = sum(r >= 0.999 for r in all_rewards)
    pooled_n = len(all_rewards)

    return {
        "n_seeds": n_seeds,
        "n_tasks_complete": n_complete,
        "pass_k": round(pass_k_count / n_complete, 4) if n_complete else 0.0,
        "pass_k_count": pass_k_count,
        "pass_1_per_seed": pass_1_per_seed,
        "pass_1_pooled": {
            "point": round(pooled_correct / pooled_n, 4) if pooled_n else 0.0,
            "correct": pooled_correct,
            "total": pooled_n,
            "wilson_95ci": wilson_ci(pooled_correct, pooled_n),
        },
        "pass_1_mean_across_seeds": agg(
            [v["pass_1"] for v in pass_1_per_seed.values()]
        ),
    }


def mcnemar_paired(
    a_by_task: Dict[int, float],
    b_by_task: Dict[int, float],
) -> dict:
    """McNemar test: paired comparison on shared task IDs."""
    from math import comb
    common = sorted(set(a_by_task) & set(b_by_task))
    b_wins = sum(1 for t in common if b_by_task[t] >= 0.999 and a_by_task[t] < 0.999)
    a_wins = sum(1 for t in common if a_by_task[t] >= 0.999 and b_by_task[t] < 0.999)
    both = sum(1 for t in common if a_by_task[t] >= 0.999 and b_by_task[t] >= 0.999)
    neither = len(common) - b_wins - a_wins - both
    n = b_wins + a_wins
    # Exact binomial two-sided p-value
    if n == 0:
        p = 1.0
    else:
        k = min(b_wins, a_wins)
        p = 2.0 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
        p = min(1.0, p)
    return {
        "n_shared": len(common),
        "b_wins": b_wins, "a_wins": a_wins,
        "both": both, "neither": neither,
        "delta": round((b_wins - a_wins) / len(common), 4) if common else 0.0,
        "p_value": round(p, 4),
        "significant_at_0.05": p < 0.05,
    }


def compare_tags(tag_a: str, tag_b: str, seeds: List[int], domain: str = "") -> List[dict]:
    """Per-seed McNemar between two tags (e.g. baseline vs decomposer)."""
    results_a = load_seed_results(tag_a, seeds, domain=domain)
    results_b = load_seed_results(tag_b, seeds, domain=domain)
    out = []
    for seed in seeds:
        a_map = {r["task_id"]: float(r.get("reward", 0.0)) for r in results_a[seed]}
        b_map = {r["task_id"]: float(r.get("reward", 0.0)) for r in results_b[seed]}
        mc = mcnemar_paired(a_map, b_map)
        mc["seed"] = seed
        mc["a_tag"] = tag_a
        mc["b_tag"] = tag_b
        out.append(mc)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True, help="Results subdir under results/")
    p.add_argument("--domain", choices=["retail", "airline"], default="retail")
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--compare-to", default=None,
                   help="Compare this tag AGAINST another tag (McNemar per seed)")
    args = p.parse_args()

    print(f"Loading seed results for tag={args.tag}, domain={args.domain}")
    seed_results = load_seed_results(args.tag, args.seeds, domain=args.domain)
    pk = compute_pass_k(seed_results)

    merged = {
        "config": {
            "tag": args.tag,
            "domain": args.domain,
            "seeds": args.seeds,
            "n_seeds": len(args.seeds),
        },
        "pass_k_metrics": pk,
    }

    if args.compare_to:
        mc_records = compare_tags(args.compare_to, args.tag, args.seeds, domain=args.domain)
        merged["mcnemar_vs"] = args.compare_to
        merged["mcnemar_per_seed"] = mc_records
        merged["mcnemar_summary"] = {
            "significant_count": sum(1 for m in mc_records if m["significant_at_0.05"]),
            "mean_delta": round(
                statistics.mean(m["delta"] for m in mc_records), 4
            ) if mc_records else 0.0,
        }

    out_path = RESULTS / args.tag / args.domain / "metrics_merged.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    print("=" * 70)
    print(f"  Merged Results — tag={args.tag}, domain={args.domain}")
    print("=" * 70)
    print(f"\n  pass^1 per seed:")
    for seed, m in pk["pass_1_per_seed"].items():
        print(f"    seed {seed}: {m['pass_1']*100:>5.1f}% ({m['n']} tasks)")
    p1m = pk["pass_1_mean_across_seeds"]
    print(f"  pass^1 mean:  {p1m['mean']*100:.1f}% ± {p1m['std']*100:.1f}pp")
    print(f"  pass^{pk['n_seeds']}:       {pk['pass_k']*100:.1f}% "
          f"({pk['pass_k_count']}/{pk['n_tasks_complete']})")
    ci = pk["pass_1_pooled"]["wilson_95ci"]
    print(f"  Wilson 95%CI (pooled): [{ci['lower']*100:.1f}%, {ci['upper']*100:.1f}%]")

    if args.compare_to:
        print(f"\n  McNemar: {args.compare_to} vs {args.tag}")
        for m in merged["mcnemar_per_seed"]:
            print(f"    seed {m['seed']}: delta={m['delta']*100:+.2f}pp  "
                  f"p={m['p_value']:.4f}  sig={m['significant_at_0.05']}")
        print(f"    Significant in "
              f"{merged['mcnemar_summary']['significant_count']}/"
              f"{len(merged['mcnemar_per_seed'])} seeds")

    print(f"\n  Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
