# Related Work — Task Decomposition for LLM Agents

> Target audience: my future self writing the workshop paper, and any reviewer who asks "what's new here?"
> Goal: position our τ-bench decomposition work against 8 closely related papers.
> Date: 2026-04-05

---

## Our RQ (recap)

**When LLM agents fail on multi-step customer-service tasks (τ-bench), is the failure mode in *decomposition* (understanding what the user wants) or *execution* (tool calls / rule adherence)? Can a lightweight cheap pre-decomposer improve pass^1 / pass^k without adding Sonnet-level cost?**

Two orthogonal axes structure the literature:

1. **Where does decomposition happen?** — one-shot prompt (Plan-and-Solve) vs. recursive/as-needed (ADaPT, Least-to-Most) vs. inside the reasoning loop (ReAct, ToT, Reflexion).
2. **What is the cost model?** — single-model inference (most work) vs. cascade / router (FrugalGPT, our Phase 1).

Nobody in the list below sits in the intersection of *multi-turn tool-using agents + explicit cheap decomposer as a pre-step*. That is our gap.

---

## Papers surveyed

### 1. τ-bench (Yao, Shinn, Razavi, Narasimhan — 2024)

- **What it is:** The benchmark we're using. Evaluates agents in realistic customer-service dialogs with rule constraints, tool use, and a simulated user.
- **Key metric:** `pass^k` — probability an agent succeeds on the same task k times i.i.d. Exposes *reliability*, not just accuracy.
- **Headline finding:** state-of-the-art FC agents succeed on <50% of tasks; pass^8 is dramatically lower than pass^1 → agents are brittle.
- **Relation to us:** Our substrate. We take their failure taxonomy (wrong_arg / wrong_decision / wrong_info / partial_resolve) as a starting point and ask whether a *pre-decomposition step* changes the failure distribution.

### 2. ADaPT — As-Needed Decomposition and Planning (Prasad et al., NAACL 2024 Findings)

- **Idea:** Recursively decompose a task *only when the LLM fails to execute it*. Decomposition is reactive, not proactive.
- **Gains:** +28% ALFWorld, +27% WebShop, +33% TextCraft over flat planning.
- **Similarity to ours:** Both argue that more decomposition helps on multi-step tasks.
- **Difference:** ADaPT decomposes on *execution failure* using the *same* LLM. We decompose *proactively, once, upfront* using a *cheaper* model. Ours is a one-shot pre-step; theirs is a recursive fallback. Different cost/latency trade-off, different failure hypothesis: ADaPT assumes the planner is strong enough *eventually*; we assume the planner could be fine if only the task were framed correctly from turn 1.
- **Design takeaway:** Our Section "Why not recursive?" will cite ADaPT as the obvious alternative, and argue: (a) τ-bench's user-simulator emits info incrementally, so recursion interleaves badly with the user turn structure, and (b) cost ceiling — our thesis is *cheap* decomposer, and ADaPT-style recursion multiplies calls.

### 3. Plan-and-Solve Prompting (Wang et al., ACL 2023)

- **Idea:** Two-stage zero-shot CoT: first devise a plan, then execute. Single LLM, single pass.
- **Scope:** Math word problems, single-agent reasoning. No tools, no user simulator.
- **Relation to us:** Direct ancestor of "decompose-then-act" framing. We port the intuition to multi-turn agentic setting + split across two different-sized models.
- **Design takeaway:** Plan-and-Solve's "devise a plan" prompt is a candidate template for our Option C (tiny-LM decomposer) — already using similar JSON-schema prompt.

### 4. Least-to-Most Prompting (Zhou et al., ICLR 2023)

- **Idea:** Decompose a hard problem into an ordered list of simpler sub-problems, solve in sequence, each solution conditions the next.
- **Result:** 16% → 99% on SCAN compositional generalization.
- **Relation to us:** Strongest evidence that decomposition-before-execution works on compositional tasks. τ-bench *is* compositional (user combines return + exchange + address change in one conversation).
- **Difference:** Least-to-Most uses the same LLM for both decomposition and execution. No cost split, no external user, no tools.
- **Design takeaway:** Our sub-goal list IS essentially a least-to-most decomposition, materialized as a system-hint injected once at turn 0 rather than chain-prompted.

### 5. ReAct — Reason + Act (Yao et al., ICLR 2023)

- **Idea:** Interleave reasoning traces with tool actions. Every turn = think → act → observe.
- **Relation to us:** τ-bench's default agent strategy is a ReAct/FC variant. Our decomposer *does not replace* ReAct — it *augments* the first system message with a pre-computed sub-goal list. The agent still ReAct-loops turn by turn.
- **Positioning:** We're not competing with ReAct; we're feeding ReAct a better initialization.

### 6. Reflexion — Verbal RL for Agents (Shinn et al., NeurIPS 2023)

- **Idea:** Agent writes a verbal "reflection" on why it failed, stores in episodic memory, tries again.
- **Relation to us:** Same first author as τ-bench (Shinn). Reflexion improves pass^k by *learning across attempts*. Our decomposer tries to improve pass^1 *within a single attempt*.
- **Complementarity:** The two are stackable. Phase 3 idea: combine our upfront decomposer with Reflexion-style retry on failed sub-goals. Logged as future work.
- **Key contrast:** Reflexion needs a reward signal. Our decomposer is unsupervised at inference time — no success signal required.

### 7. Tree of Thoughts (Yao, Yu, Zhao, Shafran, Griffiths, Cao, Narasimhan — NeurIPS 2023)

- **Idea:** Explore a tree of candidate reasoning paths with value-estimation + backtracking.
- **Relation to us:** ToT is a heavyweight inference-time search. Our decomposer is deliberately the *opposite* — one cheap pass, no search.
- **Use as a foil:** In our discussion section, "ToT buys reliability with ~10-100× more LLM calls; our decomposer tries to buy reliability with <2× total calls, most on a cheap model." Different spot on the cost-quality frontier.

### 8. FrugalGPT (Chen, Zaharia, Zou — 2023)

- **Idea:** LLM cascade — try a cheap model; if confidence low, escalate to GPT-4. Up to 98% cost reduction at equal accuracy.
- **Relation to us (the BIG link):** This is the ancestor of our Phase 1 cost-aware-hybrid-router AND this Phase 2 work.
- **Difference:** FrugalGPT cascades *answers* (single-turn Q&A). We cascade *roles* — cheap model decomposes, expensive model executes. Both steps still happen on every task; there is no escalation signal.
- **Positioning:** Our thesis extends FrugalGPT's "right-sized model for the right sub-task" from single-turn classification → multi-turn task-oriented dialogue.

---

## Where we sit on the 2×2

```
                      |  Decomposition happens...
                      |  ONCE upfront         |  AS-NEEDED / recursive
  --------------------+-----------------------+---------------------------
  SAME model for both |  Plan-and-Solve       |  ADaPT
  decomp + execution  |  Least-to-Most        |  ToT, Reflexion
                      |                       |
  DIFFERENT models    |  **Ours (Phase 2)**   |  (not surveyed — rare)
  (cost split)        |  FrugalGPT (classify) |
```

The bottom-left quadrant — *cheap upfront decomposer + strong downstream executor, on a multi-turn agentic benchmark* — is where we claim a gap. Our contribution is narrow but specific: we test whether that quadrant is viable on τ-bench.

---

## Candidate framing for workshop paper

- **Title draft:** "Cheap Decomposition, Expensive Execution: Cost-Aware Pre-Planning for Multi-Turn Tool-Agent-User Tasks"
- **One-sentence claim:** On τ-bench compound tasks, a Haiku-4.5 pre-decomposer closes X% of the pass^1 gap to the Sonnet-only baseline at Y% of the cost, *only* on the subset where the ground truth contains ≥2 write-actions.
- **Failure-case story (if H2 is rejected):** "We find that decomposition errors account for <Z% of τ-bench failures; the dominant failure mode is rule adherence during execution. This suggests the cost-aware cascade framing must target execution-time, not planning-time, compute."
- **Either way the paper is publishable** — success supports the cascade thesis, failure refines the failure taxonomy.

---

## Open questions for me to think about

1. **What separates "decomposition" from "planning"?** — In this lit, the terms are used interchangeably. Be explicit in our paper: decomposition = parse user utterance into ordered sub-goal structs; planning = deciding tool-call sequence for each sub-goal. We do the first, we leave the second to Sonnet.

2. **Could the decomposer be distilled into a 3B model?** — FrugalGPT angle. If Haiku-4.5 works, can a local Qwen-2.5-3B match it? That's a natural follow-up and makes the cost story more compelling (no API at all for the cheap stage). Mark as Phase 3.

3. **Does decomposition quality correlate with task reward?** — Proxy metric: compute BLEU/structural match between our decomposer's sub-goal list and the ground-truth action sequence's abstract signature. If correlation is weak, decomposition quality is not the right lever.

---

## Bibliography (BibTeX stubs to fill in later)

- Yao et al. 2024 — τ-bench — arXiv:2406.12045
- Prasad et al. 2024 — ADaPT — arXiv:2311.05772 — NAACL Findings
- Wang et al. 2023 — Plan-and-Solve — arXiv:2305.04091 — ACL
- Zhou et al. 2023 — Least-to-Most — arXiv:2205.10625 — ICLR
- Yao et al. 2023 — ReAct — arXiv:2210.03629 — ICLR
- Shinn et al. 2023 — Reflexion — arXiv:2303.11366 — NeurIPS
- Yao et al. 2023 — Tree of Thoughts — arXiv:2305.10601 — NeurIPS
- Chen, Zaharia, Zou 2023 — FrugalGPT — arXiv:2305.05176
