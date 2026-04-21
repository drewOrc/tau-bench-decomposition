# Workshop Paper Outline — Cheap Decomposition, Expensive Execution

> Target: NLP/ML agent workshop (NeurIPS 2026 FM-DM, ACL 2026 NLP4ConvAI, EMNLP 2026 Industry).
> Length: 4-page short paper (extended 8-page version as stretch).
> Status: **v1.0** (post Phase C, all experiments complete)
> Date: 2026-04-16

---

## Working Title

**"Cheap Decomposition, Expensive Execution: Quantifying the Planning Quality Gap in Multi-Turn Tool-Agent Tasks"**

Subtitle signals the actual finding: the gap, not a method improvement.

---

## Abstract (~150 words, to be written last)

Template (fill numbers from results):

Multi-turn tool-agent tasks require both planning (what sub-tasks to perform) and execution (how to perform them). We ask: can a lightweight pre-planner improve agent reliability on τ-bench, a customer-service benchmark where state-of-the-art agents fail on over 40% of tasks? We introduce the concept of *pre-execution planning*, a one-shot decomposition of compound user requests into typed sub-goal triples, and test four conditions: no planning (baseline), rule-based planning, automated planning (Claude Haiku 4.5, ~$0.0007/call), and oracle planning (gold sub-goals). On 22 complex tasks across 3 seeds, oracle planning improves mean pass^1 by 22.7 percentage points (p=0.007, McNemar), but automated planning gains only 1.5pp (p=1.0). This 21.2pp *planning quality gap* is our main finding: the concept of pre-execution planning works, but current small-model decomposers cannot capture the necessary sub-goal structure. We release code and annotations at github.com/drewOrc/tau-bench-decomposition.

---

## 1. Introduction (~0.75 page)

**Hook:** Agent reliability is the bottleneck. τ-bench (Yao et al., 2024): SoTA FC agents pass^1 ~ 60%, pass^k drops to ~35%. Repeating the same task 3 times, the agent succeeds all 3 times on only a third of tasks.

**Motivation:** In cost-aware deployment, the question is not "which model is best?" but "where can we substitute a cheaper model?" Two substitution points exist:
- (A) Cheap executor, expensive planner: quality collapses (execution is hard).
- (B) **Cheap planner, expensive executor: untested on multi-turn agents. This paper.**

**Our approach:** Before the agent makes any tool call, a lightweight model parses the user request into an ordered sub-goal list. We call this *pre-execution planning* (Section 3). The agent then executes sub-goals using its full capabilities.

**Main finding (state upfront):** The concept works (oracle: +22.7pp), but automated decomposers cannot yet capture sufficient sub-goal quality (tiny-LM: +1.5pp). The 21.2pp planning quality gap is the binding constraint.

**Contributions:**
1. A formal definition of *pre-execution planning* for multi-turn tool-agent tasks, distinguishing planning (action-type routing, entity identification, constraint specification) from execution (ID resolution, API calls, policy compliance).
2. A reusable failure taxonomy (7 categories) and LLM-as-judge annotation pipeline for τ-bench, applied to 215 failure trajectories.
3. A four-condition experiment isolating the planning ceiling: baseline, rule-based, oracle, and automated (tiny-LM) planning. Oracle yields +22.7pp (p=0.007); automated yields +1.5pp (n.s.).
4. Quantification of the *planning quality gap* (21.2pp) and diagnosis of its root cause: under-decomposition (automated planner generates 50% of gold sub-goals) and entity ambiguity (18% unclear entities).

---

## 2. Related Work (~0.5 page)

### 2x2 framing (from notes/05_related_work.md):

|  | Decompose once, upfront | Decompose as-needed |
|--|------------------------|---------------------|
| **Same model** | Plan-and-Solve (Wang+, ACL'23), Least-to-Most (Zhou+, ICLR'23) | ADaPT (Prasad+, NAACL'24), ToT (Yao+, NeurIPS'23), Reflexion (Shinn+, NeurIPS'23) |
| **Different models (cost split)** | **Ours** | (rare / unexplored) |

- **FrugalGPT** (Chen+, 2023): cascades *answers* (single-turn). We cascade *roles* (cheap planner + expensive executor, multi-turn).
- **ReAct** (Yao+, ICLR'23): τ-bench's default agent loop. Our planner augments ReAct, does not replace it.
- **τ-bench** (Yao+, 2024): Our substrate. We extend their 4-category failure taxonomy to 7 categories.

Gap: No prior work tests upfront decomposition with a cheaper model on a multi-turn tool-agent benchmark. We fill this gap and, critically, quantify when and why it fails.

---

## 3. Pre-Execution Planning (~0.75 page)

### 3.1 Definition (from notes/07_definition_draft.md v0.2, 2 paragraphs)

**Paragraph 1 (Definition):** Pre-execution planning = parsing compound user request into ordered sub-goal list before any tool call. Sub-goal = (action_type, entity, constraint). Action-type routing, entity identification, constraint specification = planning. ID resolution, API params, error handling, policy rules = execution.

**Paragraph 2 (Positioning):** Broader than "decomposition" in Plan-and-Solve/Least-to-Most (splitting only). ADaPT decomposes reactively; ours is proactive one-shot. Augments ReAct, not replaces.

### 3.2 Four Planning Conditions

| Condition | Method | Cost/call | Sub-goals |
|-----------|--------|-----------|-----------|
| **Baseline** | No planning; end-to-end FC agent | $0 | None |
| **Rule-based** | Regex on action verbs + entity patterns | $0 | Low quality (27.5% empty, 61.4% single) |
| **Oracle** | Gold sub-goals from human analysis | $0 | Perfect (3.0/task, 6 action types) |
| **Tiny-LM** | Claude Haiku 4.5, JSON-output prompt | ~$0.0007 | Partial (1.5/task, 50% of oracle, 18% unclear) |

### 3.3 Agent Wrapper

- `ToolCallingAgentWithDecomposer`: wraps τ-bench's `ToolCallingAgent`
- Decomposer runs on user turn 0 only, output injected into system prompt
- No modification to τ-bench evaluation pipeline (faithful comparison)
- Agent still executes via standard FC loop on all subsequent turns

---

## 4. Failure Taxonomy (~0.5 page)

### 4.1 Annotation Protocol

- 215 failed trajectories (139 retail + 76 airline), 3 seeds (42/43/44)
- LLM-as-judge: gpt-4o-mini classifies into 7 categories
- Judge confidence: mean 0.894 (retail) / 0.900 (airline)
- **Limitation (state explicitly):** No completed human IAA validation. 10-sample spot-check protocol designed but not yet executed. Two known judge biases: 0% user_led_astray (likely undercount), ~98% decomposition-relevant (likely overcount).

### 4.2 Failure Distribution

| Category | Retail (n=139) | Airline (n=76) | Description |
|----------|---------------|----------------|-------------|
| wrong_decision | 48.2% | 65.8% | Wrong strategic choice or policy violation |
| partial_resolve | 39.6% | 26.3% | Only some sub-tasks completed |
| wrong_argument | 8.6% | 3.9% | Right tool, wrong parameters |
| wrong_info | 2.9% | 3.9% | Incorrect information to user |
| other | 0.7% | 0% | Unknown/ambiguous |

**Key observation:** wrong_decision + partial_resolve = 87.8% (retail) / 92.1% (airline). These two categories are where planning-level intervention could help.

---

## 5. Experiments (~1.25 pages)

### 5.1 Setup

- **Agent:** gpt-4o (function-calling), temperature=0
- **User simulator:** gpt-4o, temperature=0
- **Seeds:** 42, 43, 44
- **Task subset:** 22 complex tasks (gt_actions >= 7 AND baseline_pass < 3/3)
- **Metrics:** pass^1 (mean ± std), pass^3 (all-seed agreement), McNemar (pooled), Cohen's d
- **Rule-based also run on full 115 tasks** (null result confirms rule quality is insufficient)

### 5.2 Baseline Results (Phase A, full dataset)

| Domain | Mean pass^1 | Std | Paper (Yao+) | pass^3 |
|--------|------------|-----|-------------|--------|
| τ-retail (115) | 59.7% | ±10.3pp | 61.2% | 36.5% |
| τ-airline (50) | 49.3% | ±4.2pp | 35.2% | 32.0% |

Note: We use the 2026 gpt-4o snapshot, stronger than the 2024 version in the original paper. Retail within range; airline higher, likely model improvements + smaller sample.

### 5.3 Main Results (Phase C, 22-task compound subset)

**Table 1: Four-condition comparison (22 complex retail tasks, 3 seeds)**

| Condition | Seed 42 | Seed 43 | Seed 44 | Mean | Δ from BL | p (McNemar) | Cohen's d |
|-----------|---------|---------|---------|------|-----------|-------------|-----------|
| Baseline | 50.0% | 45.5% | 9.1% | 34.8% ±18.3pp | — | — | — |
| Rule-based | 45.5% | 36.4% | 18.2% | 33.3% ±11.3pp | -1.5pp | n.s. | — |
| **Oracle** | **72.7%** | **54.5%** | **45.5%** | **57.6% ±11.3pp** | **+22.7pp** | **0.007** | **1.22** |
| Tiny-LM | 31.8% | 36.4% | 40.9% | 36.4% ±3.7pp | +1.5pp | 1.000 | 0.09 |

**Planning quality gap = 57.6% - 36.4% = 21.2pp**

**Table 2: McNemar contingency (pooled 66 observations)**

| Comparison | a (both pass) | b (BL pass, X fail) | c (BL fail, X pass) | d (both fail) | chi2 | p |
|------------|--------------|---------------------|---------------------|--------------|------|---|
| Oracle vs BL | 17 | 6 | 21 | 22 | 7.259 | 0.007 |
| Tiny-LM vs BL | 8 | 15 | 16 | 27 | 0.000 | 1.000 |

Note: Tiny-LM b=15, c=16 shows high churn (near-random shuffle, not systematic improvement).

### 5.4 Variance Stabilization

| Condition | CV (seed std / mean) | Interpretation |
|-----------|---------------------|----------------|
| Baseline | 0.53 | High: seed-sensitive |
| Rule-based | 0.34 | Moderate reduction |
| Oracle | 0.20 | Low: consistent |
| Tiny-LM | **0.10** | **Lowest: stabilizing effect without accuracy gain** |

Even a low-quality planner (tiny-LM) reduces trial-to-trial variance by 5x, suggesting planning structure helps consistency even when it does not help accuracy.

### 5.5 Sub-Goal Quality Analysis

| Metric | Oracle | Tiny-LM |
|--------|--------|---------|
| Mean sub-goals/task | 3.0 | 1.5 (50%) |
| Action types used | 6 (full range) | 2-3 |
| Unclear entities | 0% | 18% |
| Under-decomposed tasks (ratio < 0.5x) | 0 | 10/22 (45%) |

**Root cause of quality gap:** Under-decomposition. Tiny-LM generates half the sub-goals of oracle, misses multi-step structure, and cannot resolve entity ambiguity from the first utterance alone.

### 5.6 Cost Analysis

| Condition | Decomposer cost/task | Executor cost/task (est.) | Decomposer fraction |
|-----------|---------------------|--------------------------|---------------------|
| Baseline | $0 | ~$0.85 | 0% |
| Rule-based | $0 | ~$0.85 | 0% |
| Oracle | $0 | ~$0.85 | 0% |
| Tiny-LM | $0.0007 | ~$0.85 | 0.08% |

The decomposer is truly cheap: 0.08% of executor cost. The bottleneck is quality, not cost.

---

## 6. Discussion (~0.5 page)

### When does cheap-plan-expensive-execute work?

The oracle result (+22.7pp, p=0.007) demonstrates that pre-execution planning is a valid lever for improving agent reliability on compound tasks. The automated result (+1.5pp, n.s.) shows that current small-model decomposers cannot produce sufficient sub-goal quality to realize this potential.

### The quality gap as a research target

The 21.2pp gap between oracle and automated planning quantifies the improvement available if decomposer quality can be raised. This is a concrete, measurable target for future work.

### Variance stabilization: an unexpected finding

Even the tiny-LM planner (which provides no accuracy gain) reduces cross-seed variance by 5x (CV 0.53 to 0.10). This suggests that any structural pre-planning, regardless of quality, helps stabilize agent behavior. Future work should investigate whether variance reduction translates to reliability gains in production settings.

### Limitations

1. **Single benchmark:** τ-bench only. Generalization to WebArena, SWE-bench, or production logs untested.
2. **Single executor model:** gpt-4o. Weaker executors may benefit more from planning.
3. **No human IAA on failure annotations.** LLM judge has known biases (0% user_led_astray, ~98% decomp-relevant). We caveat all annotation-derived claims accordingly.
4. **22-task subset.** The compound subset is small; we mitigate with 3 seeds (66 pooled observations) and paired McNemar tests.
5. **Oracle sub-goals are not perfectly "gold."** They were produced by a single annotator reading instructions + ground-truth actions. A second annotator would strengthen validity.

---

## 7. Conclusion (~0.2 page)

On τ-bench compound tasks, pre-execution planning can improve agent pass^1 by up to 22.7pp when planning quality is high (oracle), but automated planners capture only 50% of the necessary sub-goal structure and yield no significant gain. The 21.2pp planning quality gap is a concrete target: closing it requires decomposers that can perform action-type routing, resolve entity ambiguity, and extract conditional constraints from underspecified user instructions. We release all code, annotations, and oracle sub-goals to support future work.

---

## Reproducibility

- **Code:** github.com/drewOrc/tau-bench-decomposition (MIT)
- **Seeds:** 42, 43, 44
- **Models:** gpt-4o (agent + user sim), claude-haiku-4.5 (tiny-LM decomposer)
- **Vendor:** τ-bench commit 59a200c (gitignored, instructions in README)
- **Total cost to reproduce Phase C:** ~$149 (rule-based $87 + oracle $31 + tiny-LM $31)
- **Total project cost:** ~$739 (Phase A $456 + Phase B $3 + Phase C $149 + misc ~$131)

---

## Figures (4 planned)

1. **Architecture diagram:** User turn 0 → Decomposer → sub-goal list → FC Agent → tools → env. Show the 4 conditions as variants.
2. **Failure taxonomy bar chart:** Stacked bar for retail + airline, 5 categories.
3. **Four-condition comparison:** Grouped bar chart or dot plot with error bars (3 seeds). Oracle stands out visually.
4. **Sub-goal quality scatter:** x = oracle sub-goal count, y = tiny-LM sub-goal count. Diagonal = perfect; points below = under-decomposition.

---

## Writing Schedule

| Date | Section | Status |
|------|---------|--------|
| 2026-04-16 | Definition (§3.1) | ✅ v0.2 drafted |
| 2026-04-16 | Outline v1.0 | ✅ this file |
| 2026-04-17-18 | §5 Results (tables + analysis) | TODO |
| 2026-04-19-20 | §3-4 Method + Taxonomy | TODO |
| 2026-04-21-22 | §1-2 Intro + Related Work | TODO |
| 2026-04-23 | §6-7 Discussion + Conclusion | TODO |
| 2026-04-24 | Abstract (written last) | TODO |
| 2026-04-25-27 | Expert review (假教授 + HR) | TODO |
| 2026-04-28 | Revision + final polish | TODO |

---

## Key Style Reminders (from 阿文)

- No em dashes. Use commas, colons, semicolons, parentheses.
- No filler: delve, nuanced, multifaceted, underscore, pivotal, landscape, leverage, foster, moreover, furthermore.
- Every claim gets a number or citation.
- "We" voice throughout.
- Match cost-aware-hybrid-router paper style: terse, data-first, no bragging.
- If the result is negative, say so honestly. The paper is interesting either way.
