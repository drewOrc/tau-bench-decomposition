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

## Method (Planned)

1. **Phase A — Reproduce baseline** on τ-retail (115 tasks, 3 seeds) using Claude Sonnet 4.6 FC agent.
2. **Phase B — Failure annotation**: classify every failure into the paper's 4 categories (wrong argument / wrong info / wrong decision / partial resolve) using LLM-as-judge + manual spot checks.
3. **Phase C — Decomposer design**: a pre-step that reads the initial user instruction and outputs a structured sub-goal list. Cheap model (Haiku 4.5 or embedding-based).
4. **Phase D — Ablation**: naive FC agent vs decomposer + FC agent. Compare pass^1 and pass^k (k = 1, 4, 8).

---

## Folder Layout

```
tau-bench-decomposition/
├── README.md                         ← this file
├── notes/
│   ├── 01_tau_bench_paper_notes.md   ← paper key points + failure taxonomy
│   └── 02_setup_guide.md             ← install, env vars, smoke test, budget
├── vendor/tau-bench/                 ← upstream repo (gitignored)
├── data/                             ← annotations, trajectories
├── src/                              ← decomposer + eval wrappers
└── results/
    ├── baseline/
    ├── decomposer/
    └── figures/
```

---

## Status

- [x] Read τ-bench paper, extract failure taxonomy
- [x] Write setup guide
- [ ] Clone repo + smoke test (3 tasks)
- [ ] Baseline reproduction (τ-retail, 3 seeds)
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
