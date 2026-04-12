# Failure Annotation Schema

> 給 τ-bench failure trajectories 做分類的 schema + prompts + 統計方法。
> 參考 Sierra 官方的 `auto_error_identification.py` + paper Figure 5 的 taxonomy。

---

## 1. 兩階段分析（延用 Sierra 官方）

### Stage 1: Fault Assignment（誰的錯？）

針對每個 failure trajectory（reward ≤ 0.001），判斷：
- `USER`: user simulator 給了不在 instruction 裡的資訊，誤導 agent
- `AGENT`: agent 決策錯誤（這才是我們要的）
- `ENVIRONMENT`: 其他（tool 壞掉、timeout 等）

只有 AGENT faults 進 Stage 2。

### Stage 2: Fault Type（agent 犯了什麼錯？）

Sierra 官方的 4 類：

| Sierra label | Paper label | Decomposition vs Execution |
|---|---|---|
| `called_wrong_tool` | wrong decision | **Decomposition** (plan 錯) |
| `used_wrong_tool_argument` | wrong argument | Execution (tool use 錯) |
| `goal_partially_completed` | partial resolve | **Decomposition** (plan 不完整) |
| `other` | (wrong info 等) | mixed |

**核心 mapping**：
- **Decomposition-level failures** = `called_wrong_tool` + `goal_partially_completed`
- **Execution-level failures** = `used_wrong_tool_argument`
- Paper 報的數字：wrong_decision 25% + partial_resolve 19.4% = **44.4%** decomposition-level

→ 這是 H1 的 target：> 40%。

---

## 2. 我們的 Extended Taxonomy

為了支持 H1/H2 分析，在 Sierra 4-class 之上加兩個軸：

### 軸 A: Error Stage（5 class, mutually exclusive）
1. `called_wrong_tool` — 選錯 tool
2. `wrong_argument` — tool 對但 arg 錯
3. `wrong_value` — 提供錯誤資訊給 user（paper 的 wrong info）
4. `partial_resolve` — compound 請求只完成一部分
5. `other` — timeout / infinite loop / refused / tool error

### 軸 B: Compound Flag（binary, 獨立於軸 A）
- `is_compound`: task.n_write_actions >= 2

### 統計會看：
- Stage 分布（H1 target）
- Compound task vs single-action task 上 decomposer 的 lift
- per-domain breakdown（retail vs airline）

---

## 3. LLM-as-Judge Prompt

模仿 Sierra 的做法，但合併成一次呼叫（減少 cost）：

### System prompt
```
You are a fault analyst for an AI agent evaluation benchmark called τ-bench.
You will be given:
  1. The user instruction (what the user was trying to do)
  2. The ground truth action sequence (correct tool calls)
  3. The actual trajectory (agent's messages and tool calls)

The trajectory has already been graded as FAILED.

Your job: classify the PRIMARY fault into ONE of the following categories.

CATEGORIES:
- user_fault: The user simulator gave information not grounded in the instruction,
  OR the user was inconsistent. Agent was not at fault.
- called_wrong_tool: Agent called a tool that should not have been called,
  or failed to call a required tool.
- wrong_argument: Agent called the correct tool but passed wrong arguments
  (wrong ID, wrong value, wrong filter).
- wrong_value: Agent provided incorrect information to the user that diverged
  the conversation (wrong price, wrong summary, wrong confirmation).
- partial_resolve: Agent only completed SOME of the requested actions,
  leaving others unaddressed.
- other: Timeout, refusal, infinite loop, tool error, or unclassifiable.

Return JSON only:
{
  "category": "<one of above>",
  "rationale": "<one sentence>",
  "first_error_turn": <int, message index where error first appears>
}
```

### User prompt template
```
--- User instruction ---
{instruction}

--- Ground truth action sequence ---
{ground_truth_actions_json}

--- Actual trajectory ---
{trajectory_formatted}

Classify the PRIMARY fault.
```

### Model
- Judge model: **Claude Haiku 4.5** (cheap, good at structured output)
- Temperature: 0.0
- Max tokens: 200 (JSON response is short)
- Estimated cost: ~$0.01 per failure trajectory × ~40-50 failures × 3 seeds ≈ $1.5

---

## 4. Manual Validation Protocol

LLM-as-judge 不能盡信。我們要做 spot-check：

1. **Sample 30 failures** (stratified: 6 per predicted category, random within)
2. **Jessie manually labels** each without seeing LLM prediction
3. **Cohen's Kappa** 計算 agreement
4. 目標：**κ ≥ 0.6**（substantial agreement）

κ 公式：
$$\kappa = \frac{p_o - p_e}{1 - p_e}$$
其中 p_o = observed agreement, p_e = random agreement。

如果 κ < 0.6：
- 重新設計 prompt（加 few-shot example）
- 或降低期望，先用 LLM label 做初篩，手動標主要結果

---

## 5. Output Schema (`data/annotations/failures_labeled.jsonl`)

每行一個 JSON：
```json
{
  "task_id": 4,
  "seed": 42,
  "domain": "retail",
  "reward": 0.0,
  "n_ground_truth_writes": 3,
  "is_compound": true,
  "llm_label": {
    "category": "partial_resolve",
    "rationale": "Agent exchanged only one item but user requested two.",
    "first_error_turn": 8
  },
  "manual_label": "partial_resolve",
  "agreement": true,
  "trajectory_length": 14
}
```

---

## 6. Summary Statistics Output

最後產出一個 `failure_summary.json`：

```json
{
  "total_failures": 42,
  "category_counts": {
    "user_fault": 3,
    "called_wrong_tool": 9,
    "wrong_argument": 14,
    "wrong_value": 6,
    "partial_resolve": 8,
    "other": 2
  },
  "decomposition_pct": 40.5,
  "execution_pct": 33.3,
  "by_compound": {
    "compound_tasks": {"partial_resolve": 8, "called_wrong_tool": 5, ...},
    "single_tasks": {"wrong_argument": 10, ...}
  },
  "kappa_manual_vs_llm": 0.72
}
```

**H1 decision rule**：
- decomposition_pct = (called_wrong_tool + partial_resolve) / total_agent_failures × 100
- If ≥ 40% → H1 supported, proceed to decomposer design
- If 30-40% → ambiguous, discuss
- If < 30% → reject H1, pivot to argument-filling

---

## 7. Implementation file: `src/annotate_failures.py`

```python
# Sketch
import json, os
from anthropic import Anthropic

JUDGE_PROMPT = """..."""  # from section 3 above

def load_results(path):
    """Load raw tau-bench trajectory JSON."""
    with open(path) as f: return json.load(f)

def call_judge(client, instruction, gt_actions, traj):
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200, temperature=0.0,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": format_case(...)}],
    )
    return json.loads(resp.content[0].text)

def main(results_path, output_path, domain, seed):
    results = load_results(results_path)
    failures = [r for r in results if r["reward"] < 1e-3]
    client = Anthropic()
    annotations = []
    for f in failures:
        label = call_judge(client, ...)
        annotations.append({...})
    with open(output_path, 'w') as f:
        for a in annotations: f.write(json.dumps(a)+'\n')
```
