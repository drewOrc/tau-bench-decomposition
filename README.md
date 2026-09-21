# τ-bench Decomposition Study

> Does lightweight task decomposition improve LLM agent reliability on multi-turn tool-use tasks?
>
> 用輕量級的任務分解器在 LLM planner 之前做 task skeleton，能否提升 τ-bench 上的 agent 可靠性？

---

## Research Question

> **When LLM agents fail on τ-bench multi-step tasks, is the failure in decomposition (planning) or in execution (tool use)? And can a lightweight pre-decomposer improve pass^1 / pass^k?**

This extends the cost-aware cascade idea from the [CLINC150 hybrid router experiment](../cost-aware-hybrid-router) — if cheap keyword/embedding models can handle most single-turn intent classification, can a cheap decomposer handle most multi-turn task planning before the expensive LLM steps in?

---

## Hypotheses

- **H1**: ≥ 40% of τ-retail failures are decomposition-level (`wrong decision` + `partial resolve` categories from the paper sum to ~44%).
- **H2**: A lightweight pre-decomposer that extracts sub-goals from user instructions can improve pass^1 by ≥ 3pp on compound-request tasks.
- **H3**: Decomposer helps pass^k more than pass^1 — by giving the agent an explicit sub-goal list, trial-to-trial variance drops.

---

## Method

1. **Phase A — Reproduce baseline** on τ-retail (115 tasks) and τ-airline (50 tasks) using gpt-4o function-calling agent (paper baseline). 3 seeds (42/43/44).
2. **Phase B — Failure annotation**: classify every failure into the paper's 4 categories (wrong argument / wrong info / wrong decision / partial resolve) using LLM-as-judge + manual spot checks.
3. **Phase C — Decomposer design**: a pre-step that reads the initial user instruction and outputs a structured sub-goal list. Cheap model (Haiku 4.5 or embedding-based).
4. **Phase D — Ablation**: naive FC agent vs decomposer + FC agent. Compare pass^1 and pass^k.

---

## Baseline Results (Phase A)

gpt-4o function-calling agent + gpt-4o user simulator, temperature=0.0, 3 seeds (42/43/44).

### τ-retail (115 tasks)
| Seed | pass^1 | n_pass |
|------|--------|--------|
| 42 | 65.2% | 75/115 |
| 43 | 66.1% | 76/115 |
| 44 | 47.8% | 55/115 |
| **Mean ± std** | **59.7% ± 10.3pp** | — |
| Paper (Yao et al.) | 61.2% | — |
| pass^3 | 36.5% | 42/115 |

### τ-airline (50 tasks)
| Seed | pass^1 | n_pass |
|------|--------|--------|
| 42 | 48.0% | 24/50 |
| 43 | 54.0% | 27/50 |
| 44 | 46.0% | 23/50 |
| **Mean ± std** | **49.3% ± 4.2pp** | — |
| Paper (Yao et al.) | 35.2% | — |
| pass^3 | 32.0% | 16/50 |

Notes: We use the 2026 gpt-4o snapshot, which is stronger than the 2024 version in the original paper. Retail mean (59.7%) falls within the paper's range; airline mean (49.3%) is higher, likely due to model improvements and smaller sample size.

---

## Main Results (Phase C — 22 complex retail tasks, 3 seeds)

| Condition | Mean pass^1 | Δ from BL | OR | Decomposer Cost |
|-----------|------------|-----------|-----|-----------------|
| Baseline | 34.8% ± 22.4pp | — | — | — |
| Rule-based | 33.3% ± 13.9pp | −1.5pp | — | $0 (regex) |
| **Oracle** | **57.6% ± 13.9pp** | **+22.7pp** | **3.5** | $0 (gold) |
| Tiny-LM | 36.4% ± 4.5pp | +1.5pp | 1.07 | $0.0007/call |
| Same-model | 34.8% ± 2.6pp | +0.0pp | 1.00 | $0.001/call |

**Key findings:**
- **Planning quality gap = 22.7pp** (oracle 57.6% vs same-model 34.8%). Oracle decomposition works, but automated decomposers capture only 50% of gold sub-goals.
- **Same-model ablation** (gpt-4o as both planner and executor) rules out model capability: gains 0.0pp, identical to tiny-LM (p=1.0). The gap is information-limited, not model-limited.
- **Majority-vote robustness check** (n=22 independent tasks): oracle vs baseline is directionally consistent but underpowered (p=0.75). Evidence rests on effect size (OR=3.5) and cross-seed consistency.
- **Variance stabilization**: all planning conditions reduce cross-seed variance (baseline CV=0.64 → same-model CV=0.08).

---

## Folder Layout

```
tau-bench-decomposition/
├── README.md                         ← this file
├── DEVLOG.md                         ← experiment log (newest first)
├── EXPERIMENT_DESIGN.md              ← hypotheses + falsification criteria
├── paper/
│   ├── main.tex/pdf                  ← full write-up (LaTeX)
│   ├── main_zh.md                    ← 完整中文翻譯
│   └── explainer.md/pdf              ← 簡單解釋版（非技術讀者）
├── requirements.txt                  ← pinned Python dependencies
├── .env.example                      ← API key template
├── notes/
│   ├── 01_tau_bench_paper_notes.md   ← paper key points + failure taxonomy
│   ├── 02_setup_guide.md             ← install, env vars, smoke test, budget
│   ├── 05_related_work.md            ← literature positioning (2×2 matrix)
│   └── 06_paper_outline.md           ← paper structure
├── vendor/tau-bench-clean/           ← upstream tau-bench, pinned to 59a200c
│                                       (gitignored; clone it yourself, see Quick Start)
├── data/
│   ├── oracle_subgoals.json          ← gold sub-goals for 22 complex tasks
│   ├── annotations/                  ← failure annotations (215 total) + 10-sample spot-check
│   └── task_profile.json             ← task metadata
├── src/
│   ├── run_baseline.py               ← baseline experiment runner (Python API)
│   ├── run_decomposer.py             ← decomposer experiment runner
│   ├── merge_seeds.py                ← aggregate pass^1/pass^k + Wilson CI
│   ├── analyze_4conditions.py        ← 5-condition comparison + statistical tests
│   ├── mcnemar_per_seed.py           ← per-seed McNemar analysis
│   ├── mcnemar_majority_vote.py      ← majority-vote McNemar (n=22 independent)
│   ├── annotate_failures.py          ← LLM-as-judge failure annotator
│   ├── agent_with_decomposer.py      ← decomposer wrapper for tau-bench agent
│   └── decomposer/
│       ├── base.py                   ← ABC with SubGoal + DecompositionResult
│       ├── rule_based.py             ← regex-based (null result)
│       ├── tiny_lm.py                ← Claude Haiku 4.5 (~$0.0007/call)
│       ├── same_model.py             ← gpt-4o same-model ablation (~$0.001/call)
│       └── oracle.py                 ← gold sub-goal lookup (ceiling analysis)
└── results/
    ├── baseline/retail/seed{42,43,44}/
    ├── baseline/airline/seed{42,43,44}/
    ├── decomposer-rule-based/retail/seed{42,43,44}/
    ├── decomposer-oracle/retail/seed{42,43,44}/
    ├── decomposer-tiny-lm/retail/seed{42,43,44}/
    └── decomposer-same-model/retail/seed{42,43,44}/
```

---

## Quick Start

```bash
# 1. Fetch tau-bench (upstream, not vendored here; pinned for reproducibility)
git clone https://github.com/sierra-research/tau-bench vendor/tau-bench-clean
git -C vendor/tau-bench-clean checkout 59a200c

# 2. Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e vendor/tau-bench-clean/
pip install -r requirements.txt

# 3. Set API keys
cp .env.example .env  # then fill in OPENAI_API_KEY and ANTHROPIC_API_KEY

# 4. Smoke test (1 task)
python src/run_baseline.py --env retail --task-ids 0 --seeds 42

# 5. Full baseline (3 seeds)
python src/run_baseline.py --env retail --seeds 42 43 44 --concurrency 1

# 6. Run decomposer experiment (e.g., oracle on 22 complex tasks)
python src/run_decomposer.py --env retail --seeds 42 43 44 --decomposer oracle --concurrency 2

# 7. Compare all 5 conditions
python src/analyze_4conditions.py

# 8. Majority-vote McNemar robustness check
python src/mcnemar_majority_vote.py
```

---

## Status

- [x] Read τ-bench paper, extract failure taxonomy
- [x] Write setup guide
- [x] Clone repo + smoke test
- [x] Baseline reproduction (τ-retail 59.7% ± 10.3pp, τ-airline 49.3% ± 4.2pp)
- [x] Failure annotation (215 annotations, 7-category taxonomy)
- [x] Rule-based decomposer (null result: −1.5pp)
- [x] Oracle decomposer (+22.7pp, OR=3.5)
- [x] Tiny-LM decomposer (+1.5pp, null; quality gap = 21.2pp)
- [x] Same-model ablation (gpt-4o planner, +0.0pp; rules out model capability)
- [x] Majority-vote McNemar robustness check (n=22 independent tasks)
- [x] 10-sample human spot-check of failure taxonomy (80% agreement)
- [x] Full write-up ("Cheap Decomposition, Expensive Execution")

---

## Why This Study

1. **Multi-turn tool use, not classification.** Extends the cost-aware cascade question from single-turn intent routing to multi-step agent planning.
2. **Public benchmark.** tau-bench (Yao et al., 2024, Sierra), with a pinned upstream commit so the baseline is checkable.
3. **Ceiling before method.** The oracle condition measures what perfect decomposition is worth before asking whether any automated decomposer can reach it, so a null result on the method is still informative about the ceiling.
4. **Ablation over speculation.** The same-model condition rules out "the decomposer model was too weak" as a competing explanation.
5. **Reproducible.** MIT-licensed code, fixed seeds (42/43/44), per-seed numbers reported, and the underpowered significance test reported next to the effect size.
