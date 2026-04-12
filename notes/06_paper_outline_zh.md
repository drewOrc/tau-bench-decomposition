# Workshop Paper 大綱（中文版）— Cheap Decomposition, Expensive Execution

> Paper 2 的中文思考版。英文版見 `06_paper_outline.md`。
> 目標投稿：NLP/ML agent workshop（候選：NeurIPS 2026 Workshop on Foundation Models for Decision Making、ACL 2026 NLP for Conversational AI、EMNLP 2026 Industry Track）。
> 長度：4 頁 short / 8 頁 long。
> 狀態：outline v0，實驗完成後要修。
> 日期：2026-04-05

---

## 暫定 Title（選項）

1. **「Cheap Decomposition, Expensive Execution: Cost-Aware Pre-Planning for Multi-Turn Tool-Agent-User Tasks」**
2. 「When Do Cheap Planners Help Expensive Agents? A τ-bench Case Study」
3. 「Decomposition or Execution? Diagnosing Failure Modes in Customer-Service LLM Agents」

我偏好 #1 —— 把貢獻框成一個 cost-aware 架構，而不是診斷工具。

---

## Abstract（中文草稿，約 200 字）

現今 SoTA function-calling LLM agent 在 τ-bench 超過一半的 task 上失敗，但這些失敗的**根本原因** —— planning 還是 execution —— 仍然沒被量化。我們問：一個輕量的 Haiku-4.5 pre-decomposer（把用戶請求解析成有序的 sub-goal list）能否改善下游 Sonnet tool-calling agent 的 pass^1 和 pass^k，同時不顯著增加成本？

我們 (i) 把 120+ 個 τ-bench 失敗 case 標註成 5 類 taxonomy（user_fault、called_wrong_tool、wrong_argument、wrong_value、partial_resolve），(ii) profile task 的 compound 程度，發現 40.9% 的 retail task 包含 ≥2 個 ground-truth write-action，(iii) 在 compound subset 上跨 3 個 seed 評估 cheap pre-decomposer。

結果：**{實驗後填入}**。我們的分析區分出 cost-aware cascade 在什麼時候能在 agent 場景生效，什麼時候 execution-time reliability 才是 bottleneck。

---

## 1. Introduction（約 0.75 頁）

**Hook**：Agent reliability gap。引用 τ-bench：就算是 SoTA FC agent，pass^k << pass^1。引用成本數字：Sonnet 跟 Haiku 差 ~10 倍價格。

**Motivation**：在生產環境的客服部署中（作者有一個這樣的系統），實務問題不是「哪個模型最好？」而是「在哪裡可以安全地用便宜模型替代？」

**兩個候選的替代點**：
- (A) **Execute 便宜，Plan 昂貴** —— 顯然 agent 品質會崩盤。
- (B) **Plan 便宜，Execute 昂貴** —— 在 multi-turn agent 上還沒人測過。這篇 paper 做這個。

**貢獻**：
1. 為 τ-bench 設計一份可重用的 5 類 failure taxonomy + LLM-as-judge 標註 protocol，用 30 個人工標註驗證（Cohen's κ 目標 ≥ 0.6）。
2. 一個 cheap-decomposer wrapper（`ToolCallingAgentWithDecomposer`），每個 task 加 <$0.001 的額外成本，且策略無關（tool-calling、ReAct、few-shot 都能用）。
3. 實證回答「cheap decomposition 有沒有幫助？」在 τ-retail/airline 的 compound subset 上，跨 3 個 seed + McNemar 顯著性檢定。
4. Failure mode 分析顯示 **{哪個類別主導}**，告訴後續 cost-aware 研究該聚焦在哪裡。

---

## 2. Related Work（約 0.5 頁）

結構用 2×2 矩陣（詳見 `05_related_work_zh.md`）：

- **Upfront 分解 + 同一 model**：Plan-and-Solve、Least-to-Most。
- **As-needed 分解 + 同一 model**：ADaPT、Tree of Thoughts、Reflexion。
- **單 turn 的 cost-aware cascade**：FrugalGPT、我們的 Phase 1 CLINC150 router。
- **我們的 quadrant**：Upfront 分解 + **不同**（便宜）model，在 multi-turn tool-use 上。

τ-bench（Yao et al. 2024）是我們的 substrate；ReAct（Yao et al. 2023）是底層的 agent loop。

---

## 3. τ-bench Failure Taxonomy（約 1 頁）

### 3.1 Setup
- τ-retail 115 tasks、τ-airline 50 tasks、3 seeds（42/43/44）。
- Baseline：claude-sonnet-4-5 當 agent、gpt-4o-mini 當 user simulator、temperature 0。
- 報告 pass^1、pass^3、Wilson 95% CI。

### 3.2 標註 Protocol
- **Stage 1**：LLM-as-judge（Haiku-4.5）把每個失敗 trajectory 分到 6 個 label 之一。
- **Stage 2**：第一作者對分層抽樣的 30 個 trajectory 做人工標註；計算 Cohen's κ。
- **Stage 3**：只有在 κ ≥ 0.6 時才呈現 LLM label；否則回去改 prompt。

### 3.3 結果
- **Failure 分佈**（表）：各類別佔比 + bootstrap CI。
- **Compound vs simple task**：失敗 case 中 compound（ground truth 有 ≥2 個 write-action）vs simple 的比例。
- **關鍵發現（假設）**：decomposition-adjacent 失敗（partial_resolve + called_wrong_tool）佔 compound-task 失敗的 X%。

---

## 4. Cheap Decomposer（約 0.75 頁）

### 4.1 架構
圖：user turn 0 → Decomposer（Haiku 或 regex）→ sub-goal list → 注入 agent 的 system prompt → Sonnet tool-calling loop → env。

### 4.2 兩種 Decomposer 變體
- **Rule-based**（`RuleBasedDecomposer`）：regex 比對 action verb + entity pattern。成本 $0。Latency < 1ms。
- **Tiny-LM**（`TinyLMDecomposer`）：Claude Haiku 4.5，用 JSON 輸出 prompt。成本 ~$0.0005/task。Latency ~800ms。

### 4.3 注入策略（ablation 軸）
- `system`：把 sub-goal list 接在 system prompt 後面。
- `user_prefix`：前置到 user turn 0 之前。
- `none`：跑 decomposer 但不注入（控制 Hawthorne effect）。

---

## 5. Experiments（約 1.25 頁）

### 5.1 Research Questions
- **RQ1 (H1)**：decomposition-adjacent 失敗是否佔 compound-task 失敗的 ≥30%？
- **RQ2 (H2)**：cheap decomposer 在 compound subset 上的 pass^1 是否提升 ≥1pp（配對 McNemar，α=0.05）？
- **RQ3 (H3)**：cheap decomposer 在 pass^3 上的提升是否 > pass^1 的提升（reliability gain）？

### 5.2 Metrics
- pass^1（per-seed 和 pooled）
- pass^3（三個 seed 全部通過）
- Wilson 95% CI
- McNemar 配對檢定（baseline vs decomposer，per seed）
- 每 task 總成本、decomposer 成本佔比
- Decomposer 品質 proxy：sub-goal list 與 ground-truth action-type sequence 的比對（recall@k）

### 5.3 Results Tables（待填）
- **T1**：Baseline pass^1/pass^3 × domain × seed
- **T2**：Decomposer pass^1/pass^3 × domain × variant (rule / tiny-lm) × injection
- **T3**：Per-seed McNemar
- **T4**：Decomposer 後的 failure 重新分佈（我們有沒有改變失敗模式？）

### 5.4 Analysis
- **如果 H2 成立**：哪些 sub-category 受益最多？Scatter 圖：compound 程度（n_writes）vs Δpass^1。
- **如果 H2 被 reject**：拆解「為什麼」。最可能的兇手：rule adherence 失敗佔大宗，這是 decomposition 修不好的。

---

## 6. Discussion（約 0.5 頁）

- **Cheap-plan-expensive-execute 什麼時候 work？** 初步回答：只有在 planning 是 bottleneck 時，而 planning 是 bottleneck 只出現在 entity ambiguity 的 compound task 上。
- **Limitations**：單一 benchmark（τ-bench）、單一 user-simulator model、單一 strong agent（Sonnet-4.5）。沒有測 distilled 的 local decomposer。
- **Future work**：(i) 把 Haiku-decomposer distill 到 3B local model（完整成本故事）、(ii) 與 Reflexion-style retry 疊加、(iii) 在 τ-bench-2 / 實際部署 log 上評估。

---

## 7. Conclusion（約 0.2 頁）

短而誠實。講結果、講 limitation、講下一個實驗。

---

## Reproducibility

- Code：`github.com/drewOrc/tau-bench-decomposition`（MIT，vendor tau-bench 排除）。
- Seeds：42、43、44。
- Model 版本：claude-sonnet-4-5-20250929、claude-haiku-4-5-20251001、gpt-4o-mini（user sim）。
- 重製完整 3-seed run × 2 domain 的預期成本：~$30。

---

## 給自己的寫作筆記

- **Style**：match cost-aware-hybrid-router paper 的風格。精簡、以數據為主、不要自誇。
- **每個 claim 都要有一行表格或一個數字。** 不要形容詞。
- **不要過度推銷。** 如果 H2 被 reject，paper 仍然有趣 —— 「cheap decomposition 不夠；以下是原因」。
- **Figures**：(1) 架構圖、(2) failure taxonomy bar chart、(3) Δpass^1 vs compound-degree scatter、(4) cost breakdown pie。
- **投稿前**：跑完最終 3-seed 實驗、算完所有數字、填好表格、最後寫 abstract。

---

## 投稿前時間軸

- **2026-04-07 那週**：Baseline smoke test（1 seed，10 tasks）。確認 decomposer wrapper end-to-end 能跑。
- **2026-04-14 那週**：Full baseline（3 seeds × 2 domain）、failure annotation。
- **2026-04-21 那週**：Decomposer run、merge_seeds、stats。
- **2026-04-28 那週**：寫 §3-5。
- **2026-05-05 那週**：寫 §1-2、§6-7。內部 review。
- **2026-05-12 那週**：修稿、投 workshop 或 arXiv preprint。

實驗後剩餘預算：~$50 用於寫 paper 時的額外 ablation。

---

## 中英對照（寫英文稿時參考）

| 中文 | 英文 |
|---|---|
| 分解 / 拆解 | decomposition |
| sub-goal / 子目標 | sub-goal |
| pre-decomposer / 前置分解器 | pre-decomposer |
| cascade / 級聯 | cascade |
| 多輪對話 | multi-turn dialogue |
| tool-calling agent / 工具呼叫代理 | tool-calling agent |
| user simulator | user simulator |
| reliability / 可靠度 | reliability |
| pass^k（可靠度指標）| pass^k |
| failure mode / 失敗模式 | failure mode |
| taxonomy / 分類法 | taxonomy |
| confidence-gated / 信心門檻 | confidence-gated |
| ablation / 消融實驗 | ablation study |
| Hawthorne effect / 霍桑效應 | Hawthorne effect |
| 配對檢定 | paired test |
| 分層抽樣 | stratified sampling |
