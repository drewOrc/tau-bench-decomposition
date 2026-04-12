# Experiment Design — τ-bench Task Decomposition Study

> 版本：v0.1（2026-04-05）
> 狀態：草案，待 smoke test 後修訂

---

## 1. Research Question

**Primary RQ**
> When LLM agents fail on τ-bench multi-step tasks, is the failure in *decomposition* (planning / sub-goal identification) or in *execution* (tool use / argument filling)?

**Secondary RQ**
> Can a lightweight, cheap pre-decomposer (keyword + embedding based, no extra LLM call) improve pass^1 and pass^k on compound-request tasks?

**Why it matters for the application story**
延續 CLINC150 的 cost-aware cascade 概念——如果便宜模型能處理大部分 single-turn classification，那能否處理 multi-turn task decomposition？這讓 Phase 1 和 Phase 2 變成同一個研究軸線的兩個資料點。

---

## 2. Hypotheses

| ID | Hypothesis | Falsification criterion |
|---|---|---|
| **H1** | ≥ 40% of τ-retail failures are decomposition-level (wrong_decision + partial_resolve) | If < 30%, reject → pivot to execution-focused method |
| **H2** | Decomposer + FC agent improves pass^1 by ≥ 3pp on compound-request tasks (tasks with ≥ 2 write actions) | If ≤ 1pp or CI crosses 0, reject |
| **H3** | Decomposer helps pass^k more than pass^1 (Δpass^8 > Δpass^1) | If Δpass^8 ≤ Δpass^1, reject → decomposer only helps average, not reliability |

**Why pre-register falsification criteria**：workshop reviewer 最常抓的就是「selective reporting」。寫清楚什麼叫失敗，就算 H2 不成立，paper 也能寫成一篇 honest negative result。

---

## 3. Datasets

### τ-retail (primary)
- 115 tasks, 500 users, 50 products, 1,000 orders
- 7 write APIs + 8 read APIs
- Domain policy: ~500 tokens of return/exchange/cancel rules

### τ-airline (secondary, budget permitting)
- 50 tasks, 500 users, 300 flights, 2,000 reservations
- 6 write APIs + 7 read APIs
- 更複雜的 policy（membership tier × cabin class × baggage rules）

**為什麼 retail 為主**：115 tasks 足夠統計檢定、policy 簡單所以 failure mode 更純粹（不會被 rule-reasoning 噪音蓋掉 decomposition signal）。airline 之後做 generalization check。

---

## 4. Baselines

| Baseline | Model | Method | Purpose |
|---|---|---|---|
| B0 | paper reported | gpt-4o FC | 文獻 reference，不自己跑 |
| **B1** | Claude Sonnet 4.6 | Function Calling | main baseline，與 decomposer 對照 |
| B2 | Claude Haiku 4.5 | Function Calling | cheap model baseline，看 decomposer 對 weak model 的幫助 |
| B3 (optional) | Sonnet 4.6 | ReAct | method comparison |

**User simulator**：一律用 `gpt-4o-mini`（cheap 且穩定，避免 user sim 本身成為變異來源）。

---

## 5. Method: Lightweight Decomposer

### 5.1 核心思路
在 agent 第一次看到 user instruction 時，**先**跑一個 cheap decomposer 抽出 structured sub-goal list，塞進 system prompt 供 FC agent 參考。

```
User: "I want to return the water bottle, and exchange the pet bed and office chair to the cheapest version..."
              ↓ Decomposer (cheap, <$0.001 per call)
Sub-goals:
  1. RETURN: water bottle (order #W...)
  2. EXCHANGE: pet bed → cheapest variant
  3. EXCHANGE: office chair → cheapest variant
  Priority: money-saving preference
              ↓
FC Agent sees: [domain policy] + [sub-goal list] + [tool defs]
```

### 5.2 Decomposer 的實作選項

**Option A — Rule-based (便宜到爆)**
- 正則抓 action verbs (return/exchange/cancel/modify/book/refund)
- 正則抓 entity (order ID, item name)
- 輸出 `[(action, entity, constraint)]` tuple list

**Option B — Embedding similarity**
- 把 user instruction 分句，每句跟 "action template" embedding 比對
- 輸出最相近的 action type + 原句

**Option C — Tiny LM**
- Haiku 4.5 zero-shot，system prompt 固定，輸出 JSON 結構
- 成本約 $0.0005 / call

**建議先做 A + C，不做 B**（B 在 multi-action 句子上效果差）。

### 5.3 Agent wrapper
- 繼承 τ-bench 的 `ToolCallingAgent` class
- override `__init__` 在 build system prompt 時插入 decomposer output
- 不改 τ-bench 的 evaluation pipeline（保證 faithful comparison）

---

## 6. Metrics

| Metric | Formula | 用途 |
|---|---|---|
| pass^1 | `E[reward]` | 平均 task 成功率（主指標） |
| pass^k | `E[C(c,k)/C(n,k)]` for k=4, 8 | 一致性 / reliability |
| pass^1 @ compound | pass^1 on tasks with ≥2 write actions | H2 target metric |
| Decomposer accuracy | manual label on 50 task | decomposer 本身對不對 |
| Cost per task | agent tokens + user sim tokens + decomposer tokens | cost-awareness 論述 |
| Failure category % | wrong_arg / wrong_info / wrong_decision / partial_resolve | H1 指標 |

**統計檢定**：
- B1 vs B1+Decomposer 用 **McNemar paired test**（同一批 task，paired outcome）
- Multi-seed 平均用 **Wilson 95% CI**
- 3 seeds (42, 43, 44) 跟 CLINC150 一致

---

## 7. Experimental Pipeline

```
Phase A. Baseline                        Phase B. Failure Annotation
┌────────────────────┐                   ┌──────────────────────────┐
│ Sonnet 4.6 FC × 3  │ → trajectories    │ LLM-as-judge (Haiku)     │
│  seeds × 115 tasks │                   │  + 30 manual spot-checks │
└────────────────────┘                   │  → Cohen's Kappa         │
                                         │  → failure category %    │
                                         └──────────────────────────┘
                                                     │
                                                     ▼
Phase C. Decomposer v1                     Phase D. Ablation
┌────────────────────┐                   ┌──────────────────────────┐
│ Design decomposer  │                   │ B1 vs B1+decomposer      │
│  (rule-based or    │ → agent wrapper   │  × 3 seeds               │
│   tiny LM)         │                   │ McNemar, Wilson CI       │
└────────────────────┘                   │ pass^k curves            │
                                         └──────────────────────────┘
                                                     │
                                                     ▼
                                         Phase E. Writeup (4-page WS)
```

---

## 8. Budget

| Item | Estimate | Notes |
|---|---|---|
| Smoke test (3 tasks) | < $0.10 | Haiku + GPT-4o-mini |
| Baseline B1 (Sonnet × 3 seeds × 115) | $30-45 | 345 task runs |
| Baseline B2 (Haiku × 3 seeds × 115) | $5-8 | |
| Failure annotation (LLM-as-judge) | $2-3 | |
| Decomposer ablation (3 seeds × 115) | $30-45 | 同 B1 |
| Airline runs (optional) | $15-20 | 3 seeds × 50 |
| **Total** | **~$100-130** | |

**Budget checkpoint**：超過 $50 之前沒看到 baseline 結果，暫停重評。

---

## 9. Timeline (6 weeks)

| Week | Milestone |
|---|---|
| 1 | Clone repo, smoke test, baseline B1 start |
| 2 | Baseline finish, failure annotation schema + auto-judge |
| 3 | Decomposer v1 設計 + manual evaluation |
| 4 | Ablation run + McNemar analysis |
| 5 | Figures + paper draft |
| 6 | Revision + submission prep |

**Go/No-Go**：Week 2 結束時若 H1 成立（decomp failure ≥ 40%）才進 Phase C；否則 pivot。

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Sonnet 4.6 pass^1 遠低於 gpt-4o paper 數字 | Medium | 改用 opus 或確認 system prompt 對齊 paper |
| τ-bench repo 跑不起來（dep 問題） | High | Week 1 的 go/no-go，備案改用 MultiWOZ 2.2 |
| Decomposer 在實務上太難抽 sub-goal | High | 改為 sub-goal 輔助提示（hint），不用 strict list |
| pass^k 噪音太大、trial 不夠 | Medium | 把 trial 數從 8 降到 4，聚焦在 pass^4 |
| Budget 超支 | Low | Haiku-only ablation 當備案 |

---

## 11. Stretch Goals（時間夠才做）

- [ ] cross-domain generalization：retail 訓練的 decomposer 直接丟 airline 測
- [ ] decomposer 品質 ablation：rule-based vs Haiku-based 哪個 cost-effective
- [ ] 把 CLINC150 的 failure taxonomy 跟 τ-bench 的 4 類 failure 比對，看是否有跨 scale 的 pattern

---

## 12. Deliverables

1. `results/baseline/metrics_merged.json` — B1/B2 3-seed results
2. `results/decomposer/metrics_merged.json` — decomposer ablation results
3. `data/annotations/failures_labeled.jsonl` — failure taxonomy 標註
4. `results/figures/` — failure pie, pass^k curves, cost-accuracy scatter
5. `paper_draft.pdf` — 4-page workshop paper
6. GitHub repo（與 cost-aware-hybrid-router 呼應，同 MIT license）
