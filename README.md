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

## Folder Layout

```
tau-bench-decomposition/
├── README.md                         ← this file
├── DEVLOG.md                         ← experiment log (newest first)
├── requirements.txt                  ← pinned Python dependencies
├── .env.example                      ← API key template
├── notes/
│   ├── 01_tau_bench_paper_notes.md   ← paper key points + failure taxonomy
│   └── 02_setup_guide.md             ← install, env vars, smoke test, budget
├── vendor/tau-bench-clean/           ← upstream repo (gitignored, commit 59a200c)
├── data/                             ← annotations, trajectories
├── src/
│   ├── run_baseline.py               ← main experiment runner (Python API)
│   ├── merge_seeds.py                ← aggregate pass^1/pass^k + Wilson CI
│   ├── agent_with_decomposer.py      ← decomposer wrapper (Phase C)
│   └── decomposer/                   ← decomposer modules
└── results/
    └── baseline/
        ├── retail/seed{42,43,44}/    ← per-seed summaries + trajectories
        └── airline/seed{42,43,44}/
```

---

## Quick Start

```bash
# 1. Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e vendor/tau-bench-clean/
pip install -r requirements.txt

# 2. Set API keys
cp .env.example .env  # then fill in your keys

# 3. Smoke test (1 task)
python src/run_baseline.py --env retail --task-ids 0 --seeds 42

# 4. Full baseline (3 seeds)
python src/run_baseline.py --env retail --seeds 42 43 44 --concurrency 1
```

---

## Status

- [x] Read τ-bench paper, extract failure taxonomy
- [x] Write setup guide
- [x] Clone repo + smoke test
- [x] Baseline reproduction (τ-retail 59.7% ± 10.3pp, τ-airline 49.3% ± 4.2pp, 3 seeds)
- [ ] Failure annotation schema
- [ ] Decomposer v1
- [ ] Ablation study
- [ ] Workshop paper draft

---

## Connection to Application Story

This experiment directly supports the MiuLab application:
1. **Agent reasoning, not classification** — addresses the critique that CLINC150 was "just classification"
2. **Public benchmark** — τ-bench is from Sierra (Yao et al. 2024), credible baseline
3. **Narrative continuity** — extends the cost-aware cascade story from single-turn to multi-turn
4. **Reproducibility** — MIT-licensed public code + fixed seeds
