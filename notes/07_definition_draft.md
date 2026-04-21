# Definition Draft — Pre-Execution Planning

> Status: **v0.2** (post expert review, 8 changes applied)
> Date: 2026-04-16
> Target: Paper 2 Section 3.1 (inline paragraphs for 4-page workshop paper)

---

## Expert Review Summary (v0.1 → v0.2)

| Expert | Verdict | Key Change |
|--------|---------|------------|
| 阿讀 | 🟡 | Added ADaPT to positioning; noted ReAct augmentation |
| 假教授 | 🟡 | Fixed boundary leak: entity identification vs resolution; constraint = decision rule vs truth condition |
| 跑哥 | 👍 | Triple matches oracle_subgoals.json; added "(or null)" for constraint |
| 圖仔 | 👎→🟡 | Removed 98% decomp_relevant from definition section entirely |
| 阿文 | 🟡 | Option B chosen, split into 2 paragraphs, broke long sentence, added "(in τ-retail)" |

---

## Final Version (Option B revised, 2 paragraphs, paper-ready)

### Paragraph 1: Definition

We define *pre-execution planning* as the process of parsing a compound user request into an ordered sub-goal list before any tool call is made. Each sub-goal is a triple of (action_type, entity, constraint). Action-type specifies which category of operation to perform: in τ-retail, the six types are MODIFY, EXCHANGE, RETURN, CANCEL, ADDRESS, and INFO, though the framework applies to any setting where distinct operation types map to distinct API endpoints. Entity identification specifies *what* to operate on in natural language (e.g., "the helmet in order #W123"); the downstream mapping to database IDs is execution. Constraint captures conditions, priorities, or fallback logic (e.g., "exchange if possible; otherwise return"), or is null when the action is unconditional. Constraints encode *decision rules*; execution resolves whether their truth conditions hold at runtime.

### Paragraph 2: Positioning

This definition is broader than "task decomposition" as used in Plan-and-Solve (Wang et al., 2023) and Least-to-Most (Zhou et al., 2023), which focus on splitting a reasoning problem into sub-problems without specifying operation types. ADaPT (Prasad et al., 2024) extends decomposition to agentic settings but decomposes reactively on failure; our definition targets proactive, one-shot planning before any tool call is made. In multi-turn tool-agent tasks, action-type routing is a planning-level decision that determines which API endpoint the agent will invoke. Selecting the wrong action type leads to a wrong-tool failure regardless of execution quality. We reserve the term *execution* for resolving sub-goals into concrete tool calls: discovering database IDs, selecting API parameters, handling error conditions, and following domain-policy rules. Our pre-execution planning step augments (not replaces) the agent's existing reasoning loop (e.g., ReAct; Yao et al., 2023).

---

## Extended Version (for 8-page paper, if needed)

### 3.1 What Is Pre-Execution Planning?

When a customer says "return the water bottle, exchange the pet bed and office chair to the cheapest version, and tell me how much I save," the agent must make several decisions before touching any API. It must (1) recognize three distinct sub-tasks, (2) classify each as a different operation type (RETURN vs. EXCHANGE vs. INFO), and (3) extract constraints ("cheapest version," "how much I save"). All three decisions occur *before* the first tool call. We call this *pre-execution planning*.

We define pre-execution planning as the process of parsing a compound user request into an ordered sub-goal list $G = [g_1, \ldots, g_n]$. Each sub-goal $g_i = (\texttt{action\_type}_i, \texttt{entity}_i, \texttt{constraint}_i)$ specifies three planning-level decisions:

1. **Action-type routing**: which category of operation to perform. In τ-retail, the six types are MODIFY, EXCHANGE, RETURN, CANCEL, ADDRESS, and INFO. Different action types invoke different API endpoints: MODIFY calls `modify_pending_order_items`, while EXCHANGE calls `return_delivered_order_items` followed by `exchange_delivered_order_items`. Selecting the wrong action type leads to a wrong-tool failure regardless of execution quality.

2. **Entity identification**: which object the operation targets, specified in natural language (e.g., "the helmet in order #W123"). Entity *resolution*, the mapping from natural language to database IDs, is execution.

3. **Constraint specification**: conditions, priorities, or fallback logic (e.g., "cheapest version available; if unavailable, cancel"), or null when the action is unconditional. Constraints encode *decision rules*; execution resolves whether their truth conditions hold at runtime.

This definition is broader than "task decomposition" in the Plan-and-Solve (Wang et al., 2023) and Least-to-Most (Zhou et al., 2023) traditions, which focus on splitting a reasoning problem into sub-problems without specifying operation types. ADaPT (Prasad et al., 2024) extends decomposition to agentic settings but decomposes reactively on execution failure using the same model; our definition targets proactive, one-shot planning using a potentially cheaper model. Our pre-execution planning step augments the agent's existing ReAct loop (Yao et al., 2023), not replaces it.

Our oracle sub-goals (Section 4.2) operationalize this definition: each gold sub-goal is a triple that a human annotator produced by reading the task instruction and ground-truth action sequence. The oracle experiment (Section 5) tests whether providing these triples to the agent improves pass^1, isolating the *planning ceiling*. The tiny-LM experiment tests whether an automated decomposer can approximate this ceiling.

---

## Design Decisions Log

1. **Why "pre-execution planning" instead of "decomposition"?**
   - "Decomposition" in the literature (Plan-and-Solve, Least-to-Most) strictly means "splitting a problem into parts."
   - Our oracle sub-goals encode more than splitting: action-type routing + constraint extraction.
   - "Pre-execution planning" is descriptively accurate and avoids overloading "decomposition."

2. **Why include action-type routing in planning?**
   - Empirical: oracle sub-goals use 6 distinct action_types; tiny-LM only generates 2-3.
   - Task 23 demonstrates: same user request contains both EXCHANGE (for delivered items) and MODIFY (for pending items). This routing decision happens before any API call.
   - Conceptual: choosing MODIFY vs EXCHANGE is analogous to choosing which API endpoint to call, which is a planning decision, not an execution decision.

3. **The entity identification / resolution boundary.**
   - "Which object?" in natural language = planning (entity identification).
   - "What's the database ID for that object?" = execution (entity resolution).
   - This distinction was flagged by 假教授 in review: without it, a reviewer could argue that entity errors are always execution errors.

4. **Constraints: decision rules vs truth conditions.**
   - Constraint "exchange if possible; otherwise return" encodes a decision rule = planning.
   - Checking whether the item is available for exchange = execution (resolving the truth condition).
   - This distinction prevents the boundary from leaking: conditional logic in constraints is planning; runtime evaluation is execution.

5. **98% decomp_relevant removed from definition section.**
   - Under this broad definition, 98% is tautological (even single-action tasks have an action_type decision).
   - The LLM judge was not validated on this axis; the number is likely inflated.
   - The paper's evidence stands on the 22-task quality gap, not on 98%.
   - If referenced at all, it belongs in the annotation methodology section with explicit caveats.

6. **τ-retail-specific vs generalizable.**
   - The six action types (MODIFY, EXCHANGE, RETURN, CANCEL, ADDRESS, INFO) are τ-retail-specific.
   - The *framework* (sub-goal = triple, planning = pre-execution) generalizes to any setting with typed API operations.
   - Added explicit "(in τ-retail)" and generalization note per 假教授 and 阿文 feedback.
