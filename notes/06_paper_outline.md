# Workshop Paper Outline — Cheap Decomposition, Expensive Execution

> Target: NLP/ML agent workshop (candidates: NeurIPS 2026 Workshop on Foundation Models for Decision Making, ACL 2026 NLP for Conversational AI, EMNLP 2026 Industry Track).
> Length: 4-page short / 8-page long.
> Status: outline v0, to be revised after experiments complete.
> Date: 2026-04-05

---

## Working Title (options)

1. **"Cheap Decomposition, Expensive Execution: Cost-Aware Pre-Planning for Multi-Turn Tool-Agent Tasks"**
2. "When Do Cheap Planners Help Expensive Agents? A τ-bench Case Study"
3. "Decomposition or Execution? Diagnosing Failure Modes in Customer-Service LLM Agents"

I prefer #1 — frames the contribution as a cost-aware architecture, not a diagnostic.

---

## Abstract (draft, 150 words)

State-of-the-art function-calling LLM agents fail on more than half of τ-bench tasks, yet the *root cause* of these failures — planning vs. execution — remains under-quantified. We ask: can a lightweight Haiku-4.5 pre-decomposer that parses the user's request into an ordered sub-goal list improve pass^1 and pass^k for a downstream Sonnet-based tool-calling agent, without materially raising cost? We (i) annotate 120+ τ-bench failures into a 5-class taxonomy (user_fault, called_wrong_tool, wrong_argument, wrong_value, partial_resolve), (ii) profile task compoundness and find 40.9% of retail tasks contain ≥2 ground-truth write-actions, (iii) evaluate a cheap pre-decomposer on the compound subset across 3 seeds. Results: **{TODO: fill after experiments}**. Our analysis separates when cost-aware cascades pay off in agentic settings from when execution-time reliability is the binding constraint.

---

## 1. Introduction (~0.75 page)

**Hook:** Agent reliability gap. Quote τ-bench: even SoTA FC agents pass^k << pass^1. Cite cost numbers: Sonnet vs Haiku is ~10× price delta.

**Motivation:** In production customer-service deployments (the authors run one at an accounting firm), the practical question is not "which model is best?" but "where is it safe to substitute a cheap model?"

**Two candidate substitution points:**
- (A) **Execute cheap, plan expensive** — trivial; agent quality collapses.
- (B) **Plan cheap, execute expensive** — untested on multi-turn agents. This paper.

**Contributions:**
1. A reusable 5-class failure taxonomy and LLM-as-judge annotation protocol for τ-bench, validated against 30 human-labeled failures (Cohen's κ target ≥ 0.6).
2. A cheap-decomposer wrapper (`ToolCallingAgentWithDecomposer`) that adds <$0.001/task overhead and is strategy-orthogonal (works with tool-calling, ReAct, few-shot).
3. Empirical answer to "does cheap decomposition help?" on τ-retail/airline compound subsets, with McNemar significance across 3 seeds.
4. Failure-mode analysis showing **{which bucket dominates}**, informing where future cost-aware work should focus.

---

## 2. Related Work (~0.5 page)

Structured as 2×2 (see notes/05_related_work.md):

- **Decompose upfront + same model:** Plan-and-Solve, Least-to-Most.
- **Decompose as-needed + same model:** ADaPT, Tree of Thoughts, Reflexion.
- **Cost-aware cascade on single-turn tasks:** FrugalGPT, our prior Phase-1 CLINC150 router.
- **Our quadrant:** Decompose upfront + *different* (cheap) model, on multi-turn tool-use.

τ-bench (Yao et al. 2024) is our substrate; ReAct (Yao et al. 2023) is the underlying agent loop.

---

## 3. τ-bench Failure Taxonomy (~1 page)

### 3.1 Setup
- τ-retail 115 tasks, τ-airline 50 tasks, 3 seeds (42/43/44).
- Baseline: claude-sonnet-4-5 as agent, gpt-4o-mini as user simulator, temperature 0.
- Report pass^1, pass^3, Wilson 95% CI.

### 3.2 Annotation Protocol
- **Stage 1:** LLM-as-judge (Haiku-4.5) classifies each failed trajectory into one of 6 labels.
- **Stage 2:** First author manually labels a stratified 30-trajectory sample; compute Cohen's κ.
- **Stage 3:** Surface LLM label only if κ ≥ 0.6; otherwise refine prompt.

### 3.3 Results
- **Failure distribution** (table): percent in each category, with bootstrapped CIs.
- **Compound vs simple tasks:** fraction of failures that are compound (≥2 write-actions in ground truth) vs simple.
- **Key finding (hypothesis):** decomposition-adjacent failures (partial_resolve + called_wrong_tool) account for X% of compound-task failures.

---

## 4. Cheap Decomposer (~0.75 page)

### 4.1 Architecture
Diagram: user turn 0 → Decomposer (Haiku or regex) → sub-goal list → injected into agent system prompt → Sonnet tool-calling loop → env.

### 4.2 Two Decomposer Variants
- **Rule-based** (`RuleBasedDecomposer`): regex on action verbs + entity patterns. Cost: $0. Latency: <1ms.
- **Tiny-LM** (`TinyLMDecomposer`): Haiku-4.5 with JSON-output prompt. Cost: ~$0.0005/task. Latency: ~800ms.

### 4.3 Injection Strategies (ablation axis)
- `system`: append sub-goal list to system prompt.
- `user_prefix`: prepend to user turn 0.
- `none`: run decomposer but don't inject (control for decomposer as Hawthorne effect).

---

## 5. Experiments (~1.25 pages)

### 5.1 Research Questions
- **RQ1 (H1):** Do decomposition-adjacent failures account for ≥30% of compound-task failures?
- **RQ2 (H2):** Does cheap decomposer improve pass^1 on compound subset by ≥1pp (paired McNemar, α=0.05)?
- **RQ3 (H3):** Does cheap decomposer improve pass^3 more than it improves pass^1 (reliability gain)?

### 5.2 Metrics
- pass^1 (per-seed and pooled)
- pass^3 (all-seed agreement)
- Wilson 95% CI
- McNemar paired test (baseline vs decomposer, per seed)
- Total cost per task, decomposer cost fraction
- Decomposer quality proxy: sub-goal list vs ground-truth-action-type sequence (recall@k)

### 5.3 Results Tables (to be filled)
- **T1:** Baseline pass^1/pass^3 by domain × seed
- **T2:** Decomposer pass^1/pass^3 by domain × variant (rule / tiny-lm) × injection
- **T3:** McNemar per seed
- **T4:** Failure redistribution after decomposer (did we shift failure modes?)

### 5.4 Analysis
- **If H2 holds:** Which sub-category of tasks benefits most? Scatter: compound-degree (n_writes) vs delta-pass^1.
- **If H2 rejected:** Decompose the "why". Most likely culprit: rule adherence failures dominate, which decomposition cannot fix.

---

## 6. Discussion (~0.5 page)

- **When does cheap-plan-expensive-execute work?** Preliminary answer: only when planning is the bottleneck, and planning IS the bottleneck only on compound tasks with entity ambiguity.
- **Limitations:** Single benchmark (τ-bench), single user-simulator model, single strong agent (Sonnet-4.5). Does not test distilled local decomposer.
- **Future work:** (i) distill Haiku-decomposer into 3B local model (full cost story), (ii) stack with Reflexion-style retry, (iii) evaluate on τ-bench-2 / real deployment logs.

---

## 7. Conclusion (~0.2 page)

Short and honest. State the result, state the limitation, state the next experiment.

---

## Reproducibility

- Code: `github.com/drewOrc/tau-bench-decomposition` (MIT, vendor tau-bench excluded).
- Seeds: 42, 43, 44.
- Model versions: claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001, gpt-4o-mini (user sim).
- Expected cost to reproduce: ~$30 per full 3-seed run × 2 domains.

---

## Writing notes for myself

- **Style:** match cost-aware-hybrid-router paper style. Terse, data-first, no bragging.
- **Every claim gets a table row or number.** No adjectives.
- **Do not oversell.** If H2 rejected, the paper is still interesting as "cheap decomposition is not enough; here's why."
- **Figures:** (1) architecture diagram, (2) failure taxonomy bar chart, (3) delta-pass^1 vs compound-degree scatter, (4) cost breakdown pie.
- **Before submission:** run final 3-seed experiment, compute all numbers, fill tables, write abstract last.

---

## Timeline to submission

- **Week of 2026-04-07:** Smoke test baseline (1 seed, 10 tasks). Confirm decomposer wrapper works end-to-end.
- **Week of 2026-04-14:** Full baseline (3 seeds × 2 domains), failure annotation.
- **Week of 2026-04-21:** Decomposer runs, merge_seeds, stats.
- **Week of 2026-04-28:** Draft sections 3-5.
- **Week of 2026-05-05:** Draft sections 1-2, 6-7. Internal review.
- **Week of 2026-05-12:** Revise, submit to workshop or arXiv preprint.

Budget remaining after experiments: ~$50 for paper-writing experiments (extra ablations).
