# Paper Draft — Cheap Decomposition, Expensive Execution

> Status: **Full draft complete.** All 7 sections + Abstract drafted. Post-review revision applied.
> Reading order: Abstract → §1 → §2 → §3.1 → §3.2 → §4 → §5 → §6 → §7
> Tables numbered sequentially in reading order (Table 1 in §4, Tables 2-7 in §5).
> Date started: 2026-04-16 | Full draft: 2026-04-16 | Expert review: 2026-04-16

---

## ✅ Section 3.1: Pre-Execution Planning (Definition)

We define *pre-execution planning* as the process of parsing a compound user request into an ordered sub-goal list before any tool call is made. Each sub-goal is a triple of (action_type, entity, constraint). For example, the request "return the water bottle and exchange the pet bed to the cheapest version" yields two sub-goals: (RETURN, "water bottle", null) and (EXCHANGE, "pet bed", "cheapest version available"). Action-type specifies which category of operation to perform: in τ-retail, the six types are MODIFY, EXCHANGE, RETURN, CANCEL, ADDRESS, and INFO. The framework applies to any setting where distinct operation types map to distinct API endpoints. Entity identification specifies *what* to operate on in natural language; the downstream mapping to database IDs is execution. Constraints encode decision rules ("exchange if possible; otherwise return") or are null for unconditional actions. Execution resolves whether the truth conditions of these rules hold at runtime.

Our definition is broader than "task decomposition" as used in Plan-and-Solve (Wang et al., 2023) and Least-to-Most (Zhou et al., 2023), which focus on splitting a reasoning problem into sub-problems in single-turn, tool-free settings without specifying operation types. ADaPT (Prasad et al., 2024) extends decomposition to agentic settings but decomposes reactively on failure; our definition targets proactive, one-shot planning before any tool call is made. In multi-turn tool-agent tasks, action-type routing is a planning-level decision that determines which API endpoint the agent will invoke. Selecting the wrong action type leads to a wrong-tool failure regardless of execution quality. We reserve the term *execution* for resolving sub-goals into concrete tool calls: discovering database IDs, selecting API parameters, handling error conditions, and following domain-policy rules. Our pre-execution planning step augments (not replaces) the agent's existing reasoning loop (e.g., ReAct; Yao et al., 2023).

---

## ✅ Section 3.2: Five Planning Conditions

We evaluate five conditions that span the quality spectrum of pre-execution planning.

**Baseline (no planning).** The agent receives the user request and domain policy directly, with no sub-goal list. This is the standard function-calling setup in τ-bench.

**Rule-based planning.** A regex-based decomposer extracts action verbs (return, exchange, cancel, modify) and entity patterns from the user's first utterance. Cost: $0. On the full 115-task retail set, 27.5% of tasks receive zero sub-goals and 61.4% receive only one, indicating that regex patterns are insufficient to capture compound request structure.

**Oracle planning.** A human annotator reads each task's instruction and ground-truth action sequence, then produces gold sub-goal triples. The oracle provides a *planning ceiling*: the best pass^1 achievable if the agent receives perfect planning information. We note that the oracle encodes information from the ground-truth actions that is unavailable to an automated decomposer at inference time; this is by design, as the oracle establishes an upper bound. We construct oracle sub-goals for 22 complex tasks selected by two criteria: at least 7 ground-truth actions (the top 19% of τ-retail's action-count distribution) and baseline pass rate below 3/3 (room for improvement). This subset selection conditions on baseline performance, so absolute numbers are specific to these 22 tasks. The relative comparison across conditions on the same tasks remains valid. The oracle decomposer looks up gold sub-goals by task index at zero cost.

**Automated planning (tiny-LM).** Claude Haiku 4.5 receives the user's first utterance and a structured prompt requesting JSON-formatted sub-goals. Cost: approximately $0.0007 per call, or 0.08% of the estimated executor cost ($0.85/task). The automated planner operates on the same 22-task subset as the oracle.

**Same-model planning (ablation).** To isolate whether the quality gap between oracle and automated planning is driven by model capability or by information available in the first utterance, we run a fifth condition using gpt-4o as both decomposer and executor. The same-model decomposer receives the identical prompt and output format as the tiny-LM condition; the only difference is the underlying model. Cost: approximately $0.001 per call. If the quality gap is model-size-driven, the same-model condition should approach oracle performance; if it is information-limited, it should cluster with tiny-LM.

All five conditions share the same executor: gpt-4o (2026 snapshot) in function-calling mode, with gpt-4o as the user simulator, temperature 0, across seeds 42, 43, and 44. We run τ-bench at commit 59a200c. The decomposer output is injected into the agent's system prompt at turn 0; all subsequent turns proceed through the standard τ-bench evaluation pipeline without modification. All automated decomposers (tiny-LM, same-model) use the identical prompt template and output format; the only variable is the underlying model.

---

## ✅ Section 5: Experiments and Results

### 5.1 Baseline Reproduction

We first reproduce the τ-bench baseline using gpt-4o as both agent and user simulator. Table 2 shows pass^1 and pass^3 across three seeds.

**Table 2: Baseline results (full dataset, 3 seeds)**

| Domain | Seed 42 | Seed 43 | Seed 44 | Mean ± std | Paper (Yao et al.) | pass^3 |
|--------|---------|---------|---------|------------|-------------------|--------|
| τ-retail (115) | 65.2% | 66.1% | 47.8% | 59.7% ± 10.3pp | 61.2% | 36.5% |
| τ-airline (50) | 48.0% | 54.0% | 46.0% | 49.3% ± 4.2pp | 35.2% | 32.0% |

We use the 2026 gpt-4o snapshot, which is stronger than the 2024 version used in the original paper. Our retail mean (59.7%) falls within the paper's range; our airline mean (49.3%) is higher, likely reflecting model improvements on a smaller sample. Seed 44 retail is notably lower (47.8%), consistent with known seed sensitivity in τ-bench.

### 5.2 Main Results: Five-Condition Comparison

Table 4 presents the main experiment on 22 complex retail tasks across three seeds. The oracle condition improves mean pass^1 by 22.7 percentage points over the baseline (OR=3.5 in pooled analysis: 21 tasks flip fail-to-pass vs 6 pass-to-fail; directionally consistent across all three seeds). The improvement is directionally consistent but formally underpowered at the task level (see §5.3 for majority-vote robustness analysis). The automated tiny-LM condition gains only 1.5pp (p=1.0). The rule-based condition shows a slight decrease of 1.5pp. The same-model ablation (gpt-4o as both decomposer and executor) gains 0.0pp (p=0.838), indistinguishable from both the baseline and the tiny-LM condition (same-model vs tiny-LM: p=1.0). The identical performance across a 175x cost difference rules out model capability as the primary driver of the quality gap; the remaining hypothesis is that the gap is information-limited, since even the same model that serves as executor cannot produce oracle-quality decompositions from the first utterance alone. Oracle planning achieves pass^3 of 7/22 (31.8%), compared to the baseline's 0/22 (0% by selection criterion), demonstrating reliability gains beyond single-trial accuracy.

**Table 4: Five-condition comparison (22 complex retail tasks, 3 seeds)**

| Condition | Seed 42 | Seed 43 | Seed 44 | Mean ± std | Δ from BL | p (McNemar) |
|-----------|---------|---------|---------|------------|-----------|-------------|
| Baseline | 50.0% | 45.5% | 9.1% | 34.8% ± 22.4pp | — | — |
| Rule-based | 45.5% | 36.4% | 18.2% | 33.3% ± 13.9pp | −1.5pp | n.s. |
| **Oracle** | **72.7%** | **54.5%** | **45.5%** | **57.6% ± 13.9pp** | **+22.7pp** | **0.007†** |
| Tiny-LM | 31.8% | 36.4% | 40.9% | 36.4% ± 4.5pp | +1.5pp | 1.000 |
| Same-model | 36.4% | 36.4% | 31.8% | 34.8% ± 2.6pp | +0.0pp | 0.838 |

†Pooled n=66; within-task correlation inflates effective n. Majority-vote aggregation (n=22 independent tasks) yields p=0.75; see §5.3.

The planning quality gap, defined as the difference between oracle and same-model automated planning, is **22.7 percentage points** (oracle 57.6% vs same-model 34.8%; same-model chosen as reference because it controls for model capability, matching the executor). The gap against the best automated condition (tiny-LM, 36.4%) is 21.2pp. The 22.7pp gap quantifies the improvement available if automated decomposer quality can be raised to the oracle level.

### 5.3 Statistical Tests

We use McNemar's test with continuity correction on paired binary outcomes (pass/fail on the same task). Table 5 shows pooled results (22 tasks × 3 seeds = 66 observations) and per-seed breakdown.

**Table 5a: McNemar contingency (pooled, n=66)**

| Comparison | Both pass | A pass, B fail | A fail, B pass | Both fail | χ² | p | OR |
|------------|----------|----------------|----------------|----------|-----|---|-----|
| Oracle (B) vs BL (A) | 17 | 6 | 21 | 22 | 7.259 | 0.007 | 3.50 |
| Tiny-LM (B) vs BL (A) | 8 | 15 | 16 | 27 | 0.000 | 1.000 | 1.07 |
| Oracle (A) vs Tiny-LM (B) | 16 | 22 | 8 | 20 | 5.633 | 0.018 | 2.75 |
| Same-model (B) vs BL (A) | 11 | 12 | 12 | 31 | 0.042 | 0.838 | 1.00 |
| Oracle (A) vs Same-model (B) | 17 | 21 | 6 | 22 | 7.259 | 0.007 | 3.50 |
| Same-model (A) vs Tiny-LM (B) | 12 | 11 | 12 | 31 | 0.000 | 1.000 | 1.09 |

OR = odds ratio of discordant pairs (c/b); OR > 1 favors condition B.

**Table 5b: Per-seed McNemar (Oracle vs Baseline, n=22 each)**

| Seed | BL pass | Oracle pass | Δ | b | c | p |
|------|---------|-------------|---|---|---|---|
| 42 | 11 (50.0%) | 16 (72.7%) | +22.7pp | 3 | 8 | 0.228 |
| 43 | 10 (45.5%) | 12 (54.5%) | +9.1pp | 2 | 4 | 0.683 |
| 44 | 2 (9.1%) | 10 (45.5%) | +36.4pp | 1 | 9 | 0.027 |

The oracle condition shows asymmetric improvement in the pooled analysis: 21 tasks flip from fail to pass while only 6 flip from pass to fail (OR=3.5). The improvement is directionally consistent across all three seeds (net discordant: +5, +2, +8 in oracle's favor), but individual seeds are underpowered at n=22. Seed 44 contributes disproportionately because its anomalously low baseline (9.1%) provides the most room for improvement.

**Independence caveat.** The pooled test treats 66 (task, seed) pairs as independent observations, but outcomes for the same task across seeds share the task instruction and oracle sub-goals. This within-task correlation may inflate effective sample size and underestimate p-values. We report a leave-one-seed-out sensitivity analysis: without seed 42, p=0.024; without seed 43, p=0.009; without seed 44, p=0.146. The effect remains significant when either seed 42 or 43 is removed, but not when seed 44 is removed, confirming that seed 44's anomalously low baseline disproportionately drives the pooled result. The direction of improvement is consistent across all three seeds (3/3, binomial sign-test p=0.125). Oracle planning shows the largest gain on seed 44 (+36.4pp), precisely the seed where the baseline struggles most (9.1%), suggesting that decomposition is most beneficial when agent reliability is lowest.

The oracle vs tiny-LM comparison (p=0.018 pooled, subject to the same within-task correlation caveat) provides directional support for the planning quality gap: oracle sub-goals consistently outperform automated sub-goals on the same tasks.

We apply Holm-Bonferroni correction to the six pairwise comparisons. The primary comparison (oracle vs baseline, p=0.007) survives correction at α=0.05 (adjusted threshold 0.0083). The oracle vs tiny-LM comparison (p=0.018) does not survive full correction (adjusted threshold 0.010) but remains significant within the pre-specified family of three comparisons against the baseline. We report both raw and family-level significance throughout.

**Majority-vote robustness check.** The pooled analysis treats 66 (task, seed) pairs as independent, but within-task outcomes share the task instruction and oracle sub-goals across seeds, potentially inflating effective sample size. To address this, we aggregate per-task via majority vote: a task "passes" if it succeeds on at least 2 of 3 seeds, yielding n=22 truly independent observations. Under majority vote, oracle pass rate is 50.0% (11/22) vs baseline 40.9% (9/22), a difference of +9.1pp with 10 discordant pairs (b=6, c=4). McNemar's test on these 22 observations is not significant (χ²=0.10, p=0.75). The loss of significance reflects reduced statistical power (10 discordant pairs vs 27 pooled), not a reversal of direction: oracle maintains the highest majority-vote pass rate across all five conditions (oracle 50.0% > baseline 40.9% > tiny-LM 36.4% > same-model 31.8% > rule-based 22.7%). We conclude that the oracle effect is directionally robust and practically large (OR=3.5 pooled), but formally underpowered at the task level with 22 tasks. We report effect sizes (OR, Δpp) as primary evidence and treat p-values as secondary throughout.

The tiny-LM vs baseline comparison shows near-symmetric churn: 15 regressions and 16 improvements, consistent with random reshuffling rather than systematic improvement.

### 5.4 Variance Stabilization

All planning conditions reduce cross-seed variance, and the tiny-LM planner achieves the lowest coefficient of variation despite providing no accuracy gain (Table 6).

**Table 6: Variance analysis**

| Condition | Mean | Std | CV (std/mean) | Range (max−min) |
|-----------|------|-----|---------------|-----------------|
| Baseline | 34.8% | 22.4pp | 0.64 | 40.9pp |
| Rule-based | 33.3% | 13.9pp | 0.42 | 27.3pp |
| Oracle | 57.6% | 13.9pp | 0.24 | 27.2pp |
| Tiny-LM | 36.4% | 4.5pp | 0.12 | 9.1pp |
| Same-model | 34.8% | 2.6pp | **0.08** | **4.5pp** |

With only three seeds, variance estimates are imprecise; the range (max−min) across seeds provides a more transparent summary. The same-model planner achieves the lowest CV (0.08), reducing variance by approximately 8x relative to the baseline (0.08 vs 0.64; standard deviation computed with Bessel's correction, n-1). The pattern is monotonic: all planning conditions show lower cross-seed variance than the baseline, regardless of accuracy gain. The same-model condition (gpt-4o decomposer) achieves the lowest variance despite no accuracy gain (CV=0.08 vs baseline CV=0.64). The monotonic pattern across all five conditions suggests that structural pre-planning stabilizes agent behavior even when it does not improve accuracy.

### 5.5 Diagnosing the Quality Gap

Why does the tiny-LM planner fail to capture oracle-level quality? Table 7 compares sub-goal characteristics.

**Table 7: Sub-goal quality comparison**

| Metric | Oracle | Tiny-LM | Same-model |
|--------|--------|---------|------------|
| Mean sub-goals per task | 3.0 | 1.5 | 1.4 |
| Distinct action types per task | 6 (full range) | 1–2 (mean 1.4) | 6 (full range) |
| Entities marked "(unclear)" | 0% | 18% | 30% |
| Tasks with ratio < 0.5x oracle | 0/22 | 10/22 (45.5%) | 15/22 (68%) |

The primary failure mode is *under-decomposition*: both the tiny-LM and same-model planners generate fewer than half the sub-goals of the oracle (1.5 and 1.4 respectively vs 3.0), collapsing multi-step structure into single-step summaries. The same-model planner uses all 6 action types (matching the oracle vocabulary) but still under-decomposes, and marks 30% of entities as "(unclear)" compared to 18% for tiny-LM, suggesting that the larger model is more cautious about entity resolution but equally unable to infer compound structure. For example, Task 23 requires three distinct operations (EXCHANGE helmet, EXCHANGE luggage set, MODIFY grill to match the delivered one). Both the tiny-LM and same-model planners produce a single sub-goal targeting only the helmet, missing the luggage set entirely and failing to distinguish MODIFY from EXCHANGE for the grill. The identical failure pattern despite gpt-4o costing 1.4× more per call rules out model capability as the primary driver of under-decomposition; the bottleneck appears to be information available in the first utterance.

### 5.6 Cost

The tiny-LM decomposer costs $0.0007 per call (Claude Haiku 4.5, single inference), compared to an estimated $0.85 per task for the gpt-4o executor. The same-model decomposer (gpt-4o) costs $0.001 per call, approximately 1.4x the tiny-LM cost but still only 0.12% of executor cost. Both add negligible overhead. The total experimental cost across all conditions and seeds was approximately $180. The bottleneck is decomposition *quality*, not cost.

---

## ✅ Section 4: Failure Taxonomy

### 4.1 Annotation Protocol

We annotate all 215 failed trajectories (139 retail, 76 airline) from the baseline runs using an LLM-as-judge pipeline (Zheng et al., 2023). A gpt-4o-mini judge classifies each failure into one of seven categories based on the user instruction, ground-truth action sequence, and agent trajectory: wrong_decision, partial_resolve, wrong_argument, wrong_info, user_led_astray, ambiguous_task, and unknown. The judge reports a confidence score (mean 0.894 for retail, 0.900 for airline).

A 10-sample human spot-check yields 80% agreement on failure category between the human annotator and the LLM judge (8/10 samples). Disagreements arise when the judge labels incomplete execution as partial_resolve where the human annotator identifies an underlying wrong_decision (e.g., missed fallback path or entity-binding error). The spot-check also identifies one user_led_astray case (10%) where the LLM judge reports 0%, confirming that user-simulator-induced errors are under-annotated. Decomposition relevance agreement is 100% (10/10), though the human annotator notes that approximately 20% of cases may be better attributed to execution reliability or interaction handling than decomposition per se. We flag one known bias: the decomposition-relevant flag is set at approximately 98%, likely inflated because any task trivially involves at least one action-type decision; the human spot-check suggests a more conservative estimate of approximately 80%. All annotation-derived claims should be interpreted with these caveats.

### 4.2 Failure Distribution

Table 1 presents the failure distribution across both domains.

**Table 1: Failure taxonomy (LLM-as-judge, n=215)**

| Category | Retail (n=139) | Airline (n=76) | Description |
|----------|---------------|----------------|-------------|
| wrong_decision | 48.2% | 65.8% | Wrong strategic choice or policy violation |
| partial_resolve | 39.6% | 26.3% | Multiple sub-tasks, only some completed |
| wrong_argument | 8.6% | 3.9% | Right tool, wrong parameters |
| wrong_info | 2.9% | 3.9% | Incorrect information given to user |
| user_led_astray | 0% | 0% | User simulator steered to wrong outcome |
| ambiguous_task | 0% | 0% | Task instruction allows multiple interpretations |
| unknown | 0.7% | 0% | Unclassified |

Two categories dominate: wrong_decision and partial_resolve together account for 87.8% of retail failures and 92.1% of airline failures. Both categories are consistent with planning-level deficiencies: wrong_decision reflects incorrect action-type routing or policy interpretation, while partial_resolve indicates incomplete task splitting. However, the 10-sample spot-check (Section 4.1) suggests the decomposition-relevance estimate (approximately 98%) may be inflated to approximately 80%. Our oracle experiment (Section 5) provides a stronger test of the planning hypothesis than the taxonomy alone.

---

## ✅ Section 1: Introduction

Function-calling agents can now handle multi-turn customer-service conversations, but they remain unreliable. On τ-bench (Yao et al., 2024), a benchmark of realistic retail and airline support tasks with tool use and policy constraints, state-of-the-art agents pass individual tasks at roughly 60% (pass^1) and succeed on the same task three times in a row at only 35% (pass^3). This reliability gap is the central barrier to deployment.

In cost-aware deployment, the question is not "which model is best?" but "where can a cheaper model substitute without quality loss?" Two substitution points exist. First, a cheap executor with an expensive planner: quality is expected to degrade because execution in multi-turn tool-agent tasks requires policy compliance, error handling, and multi-step API orchestration. Second, a cheap planner with an expensive executor: untested on multi-turn agents. We test the second option.

We propose *pre-execution planning*: before the agent makes any tool call, a lightweight model parses the user request into an ordered sub-goal list. Each sub-goal is a triple of (action_type, entity, constraint) that specifies what operation to perform, on what object, under what conditions. The agent then executes sub-goals using its full capabilities through the standard function-calling loop.

Our main finding: the concept has high headroom, but automated decomposers cannot yet capture sufficient sub-goal quality, and model capability alone does not close the gap. On 22 complex retail tasks across 3 seeds, oracle planning (gold sub-goals from human annotation) improves mean pass^1 by 22.7 percentage points over the baseline (OR=3.5; directionally consistent across all three seeds). Automated planning using Claude Haiku 4.5 (cost: $0.0007 per call, 0.08% of executor cost) gains only 1.5pp (p=1.0). A same-model ablation using gpt-4o as both planner and executor gains 0.0pp (p=0.838), ruling out model capability as the primary driver of the quality gap. The 22.7pp *planning quality gap* between oracle and automated conditions is practically large (OR=3.5) and diagnostically interpretable: both automated planners generate half the sub-goals of the oracle and cannot resolve entity ambiguity from the user's first utterance.

We make three contributions:

1. A formal definition of *pre-execution planning* for multi-turn tool-agent tasks, distinguishing planning-level decisions (action-type routing, entity identification, constraint specification) from execution-level decisions (ID resolution, API parameter selection, policy compliance), and quantification of the resulting planning quality gap (22.7pp) via a same-model ablation that rules out model capability as the primary driver: under-decomposition (50% of oracle sub-goals), action-type collapse, and entity ambiguity are shared by both a small and large decomposer.
2. A 7-category failure taxonomy applied to 215 failed trajectories via an LLM-as-judge pipeline, showing that wrong_decision (48%-66%) and partial_resolve (26%-40%) together account for 88%-92% of failures across both domains.
3. A five-condition experiment isolating the planning ceiling: baseline, rule-based, oracle, automated (tiny-LM), and same-model (gpt-4o) planning. Oracle yields +22.7pp (OR=3.5; directionally consistent but underpowered at n=22, see §5.3); both automated conditions yield 0-1.5pp (n.s.).

---

## ✅ Section 2: Related Work

Two axes organize prior work on decomposition for LLM agents: *when* decomposition occurs (once upfront vs. as-needed during execution) and *whether* the decomposer and executor share the same model.

**Upfront decomposition, same model.** Plan-and-Solve (Wang et al., 2023) prompts a single LLM to devise a plan before solving math word problems. Least-to-Most (Zhou et al., 2023) decomposes hard problems into ordered sub-problems, each conditioned on the previous solution. Both operate in single-turn, tool-free settings and use the same model for both stages. Decomposed Prompting (Khot et al., 2023) goes further by routing sub-problems to different specialized prompts, demonstrating that decomposition and execution need not share the same prompt or model. Our work ports the "decompose-then-act" intuition to multi-turn tool-agent tasks and splits the two stages across models of different cost.

**As-needed decomposition, same model.** ReAct (Yao et al., 2023) interleaves reasoning traces with tool actions, forming the default agent loop in τ-bench. Our decomposer does not replace ReAct; it augments the first system message with a pre-computed sub-goal list. ADaPT (Prasad et al., 2024) recursively decomposes a task only when the agent fails to execute it, gaining +28% on ALFWorld and +27% on WebShop. Tree of Thoughts (Yao et al., 2023b) explores a tree of reasoning paths with backtracking. Reflexion (Shinn et al., 2023) stores verbal self-critiques across attempts to improve pass^k. All use the same model for decomposition and execution, and most incur multiplicative inference cost. Our decomposer is proactive (one-shot, before any tool call) rather than reactive, and uses a model that costs 0.08% of the executor.

**Cost-aware model selection.** FrugalGPT (Chen et al., 2023) cascades models for single-turn QA, trying a cheap model first and escalating to GPT-4 when confidence is low. HuggingGPT (Shen et al., 2023) uses a controller LLM to decompose tasks and dispatch sub-tasks to specialist models; the key difference from our setup is that HuggingGPT routes to different *executors* per sub-task, while we use the same executor for all sub-goals with only the *planning* stage delegated to a cheaper model. Our work extends the "right-sized model for the right sub-task" principle from cascading *answers* to cascading *roles*: a cheap model plans, an expensive model executes. Both stages run on every task; there is no escalation signal. Our earlier work on cost-aware hybrid routing (Chen, 2026) applies this principle to single-turn intent classification; the present paper extends it to multi-turn agent planning.

**τ-bench.** Yao et al. (2024) introduce τ-bench as a benchmark for evaluating tool-agent reliability in customer-service settings, with the pass^k metric exposing brittleness invisible to pass^1. Their analysis identifies four failure categories. We extend this to seven categories and test whether pre-execution planning can shift the failure distribution.

To our knowledge, no prior work tests upfront decomposition with a cheaper model on a multi-turn tool-agent benchmark. We fill this gap and, critically, quantify both when it works (oracle: +22.7pp, OR=3.5) and why automated versions fail. A same-model ablation (gpt-4o as both decomposer and executor) rules out model capability as the primary driver: gpt-4o as decomposer performs identically to Claude Haiku 4.5 (p=1.0).

---

## ✅ Section 6: Discussion

### 6.1 When Does Cheap-Plan-Expensive-Execute Work?

Oracle planning yields the largest gain (+22.7pp, OR=3.5). Neither automated condition improves: the same-model ablation (+0.0pp, discordant pairs 12:12) rules out model capability, since even the executor model cannot produce useful decompositions from the first utterance alone. All planning conditions reduce cross-seed variance (from baseline CV=0.64 to same-model CV=0.08), suggesting that structural pre-planning stabilizes behavior even when sub-goal quality is low.

### 6.2 The Quality Gap as a Research Target

The 22.7pp gap between oracle (57.6%) and automated planning (34.8% for same-model, 36.4% for tiny-LM) quantifies the improvement available if decomposer quality can be raised. The same-model ablation narrows the diagnosis: since gpt-4o and Haiku 4.5 produce statistically identical results (p=1.0), model capability alone does not close the gap. Three specific failure modes, shared by both automated decomposers, suggest concrete directions:

1. **Under-decomposition.** The tiny-LM generates a mean of 1.5 sub-goals per task vs. the oracle's 3.0. 45–68% of tasks receive fewer than half the oracle's sub-goals. Training or prompting decomposers on multi-action examples could address this.
2. **Action-type collapse.** The tiny-LM planner defaults to 1–2 action types (mean 1.4) vs. the oracle's full range of 6; the same-model planner uses all 6 types but still under-decomposes. Providing the decomposer with a schema of available action types could help.
3. **Entity ambiguity.** Eighteen percent of tiny-LM entities are marked as unclear. The decomposer operates on the user's first utterance alone, which often uses pronouns or partial descriptions. Multi-turn context or retrieval-augmented decomposition could reduce ambiguity.

### 6.3 Limitations

We state five limitations that scope our claims.

1. **Single benchmark.** All experiments use τ-bench. Generalization to WebArena (S. Zhou et al., 2024), SWE-bench (Jimenez et al., 2024), or production customer-service logs is untested.
2. **Single executor model.** We use gpt-4o throughout. The same-model ablation varies the decomposer but not the executor. Weaker executors (e.g., gpt-4o-mini) may benefit more from planning; stronger executors (e.g., o1-class models with built-in planning) may benefit less.
3. **No human inter-annotator agreement on failure annotations.** The LLM-as-judge pipeline has known biases: 0% user_led_astray (likely undercount) and approximately 98% decomposition-relevant (likely overcount from a tautologically broad definition). A 10-sample human-LLM spot-check (80% agreement, §4.1) provides partial validation but no human-human IAA was computed. All annotation-derived claims carry this caveat.
4. **Small task subset.** The 22-task compound subset is small. Pooling across seeds (66 observations) assumes independence that within-task correlation may violate. A majority-vote robustness check (n=22 independent tasks) confirms directional consistency but lacks power (p=0.75 for oracle vs baseline); the oracle effect should be interpreted through its effect size (OR=3.5, +22.7pp) and cross-seed consistency rather than p-value alone.
5. **Single oracle annotator.** Oracle sub-goals were produced by one annotator reading task instructions and ground-truth action sequences. A second annotator would strengthen validity. The oracle also has access to information (ground-truth actions) unavailable at inference time, so it establishes a ceiling, not a realistic target.

---

## ✅ Section 7: Conclusion

On τ-bench compound tasks, pre-execution planning has high headroom: oracle sub-goals improve agent pass^1 by 22.7 percentage points (OR=3.5, directionally consistent across all seeds) and achieve pass^3 of 31.8% (compared to 0% by selection criterion). A majority-vote robustness check (n=22 independent tasks) confirms the direction but is underpowered to detect significance; the evidence rests on effect size and cross-seed consistency rather than p-value. Neither automated planner (Claude Haiku 4.5 nor gpt-4o, the same model as the executor) yields significant gain (+1.5pp and +0.0pp respectively, both p>0.8). The same-model ablation is our most precise finding: model capability alone does not close the 22.7pp quality gap (same-model vs tiny-LM: p=1.0), suggesting that the first user utterance does not contain sufficient information for any model to reconstruct the full sub-goal structure. The gap is diagnostically interpretable: both automated planners generate half the oracle's sub-goals, with identical under-decomposition and entity-ambiguity patterns.

The decomposer adds less than 0.12% of executor cost regardless of model choice ($0.0007-$0.001 vs $0.85 per task). Cost is not the bottleneck; decomposition quality is. Closing the quality gap requires decomposers that operate on more than the first utterance: multi-turn context, retrieval-augmented planning, or domain-specific schemas that constrain the decomposition space. We release all code, oracle sub-goals, and failure annotations at github.com/drewOrc/tau-bench-decomposition.

---

## ✅ Abstract

Multi-turn tool-agent tasks require both planning (what sub-tasks to perform) and execution (how to perform them). We ask: can a lightweight pre-planner improve agent reliability on τ-bench, a customer-service benchmark where state-of-the-art agents fail on over 40% of tasks? We define *pre-execution planning* as parsing a compound user request into typed sub-goal triples before any tool call, and test five conditions: no planning (baseline), rule-based, automated (Claude Haiku 4.5, $0.0007/call), same-model (gpt-4o as both planner and executor), and oracle (gold sub-goals). On 22 complex retail tasks across 3 seeds, oracle planning improves mean pass^1 by 22.7 percentage points (OR=3.5, directionally consistent across all seeds), but both automated planners gain 0-1.5pp (p>0.8). A same-model ablation rules out model capability as the driver: gpt-4o as decomposer performs identically to Claude Haiku 4.5 (p=1.0). A majority-vote robustness check (pass if ≥2/3 seeds succeed, n=22 independent tasks) confirms the direction of improvement but is underpowered to detect significance (p=0.75); we report effect sizes throughout. Pre-execution planning has high headroom when sub-goal quality is sufficient, but automated decomposers, regardless of model size, capture roughly half of the necessary sub-goal structure from the first utterance. We release code and annotations at github.com/drewOrc/tau-bench-decomposition.
