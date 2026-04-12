# τ-bench Paper Notes

> Yao et al. 2024, Sierra — *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains*
> arXiv: https://arxiv.org/abs/2406.12045 · Code: https://github.com/sierra-research/tau-bench · MIT License

---

## 1. 核心主張

τ-bench 測試 agent 在「動態對話」中的三件事：
1. 與真人（由 LM 模擬）互動來逐步收集資訊
2. 遵守 domain-specific policy（以 system prompt 形式給 agent）
3. 在多次 i.i.d. trial 下保持一致性（pass^k 指標）

與其他 agent benchmark 最大的差異：**user-in-the-loop**。AgentBench、ToolBench、BFCL 都是 single-turn，user instruction 一次給齊；τ-bench 的 user 會在對話中追加資訊、質疑、或授權。

---

## 2. 基本設定

| | τ-retail | τ-airline |
|---|---|---|
| DB | 500 users, 50 products, 1,000 orders | 500 users, 300 flights, 2,000 reservations |
| API tools | 7 write + 8 read | 6 write + 7 read |
| Tasks | **115** | **50** |

- POMDP formulation：state = DB state ⊗ user state，agent 看不到完整 DB，只能透過 API 讀寫。
- User 由 `gpt-4-0613` 模擬（LM temp=1.0），agent temp=0.0。
- Episode 上限 30 actions（tool call 或 user response），user 發 `###STOP###` 結束。
- **評估方式**：比較 episode 結束時的 DB state 和 ground truth goal state，objective 且 deterministic。

---

## 3. 關鍵指標：pass^k

$$\text{pass}^k = \mathbb{E}_\text{task}\left[\binom{c}{k}/\binom{n}{k}\right]$$

同一個 task 跑 n 次，其中 c 次成功，問「連續 k 次都成功」的機率。pass^1 = pass@1 = 平均成功率。

**paper 的核心發現**：即使 gpt-4o 在 τ-retail 上 pass^1 = 61.2%，pass^8 只有 < 25%。agent 的一致性/可靠性是真正的瓶頸。

---

## 4. Baseline 數字（pass^1, Function Calling）

| Model | retail | airline | avg |
|---|---|---|---|
| **gpt-4o** | **61.2** | **35.2** | **48.2** |
| gpt-4-turbo | 57.7 | 32.4 | 45.1 |
| gpt-4-32k | 56.5 | 33.0 | 44.8 |
| claude-3-opus | 44.2 | 34.7 | 39.5 |
| mistral-large | 30.7 | 22.4 | 26.6 |
| claude-3-sonnet | 26.3 | 27.6 | 27.0 |
| gemini-1.5-pro | 21.7 | 14.0 | 17.9 |
| gpt-3.5-turbo | 20.0 | 10.8 | 15.4 |
| claude-3-haiku | 19.0 | 14.4 | 16.7 |
| llama-3-70B (ReAct) | 14.8 | 14.4 | 14.6 |

> 注意：這是 2024-06 數字，Claude 3.5 Sonnet / Haiku 4.5 / GPT-4.1 / Sonnet 4 等之後的 model 沒有。後續 leaderboard 要另查。

Method 比較（τ-retail, gpt-4o）：
- FC (Function Calling) ≈ 61%
- ReAct ≈ 50%
- Act-only ≈ 45%
FC > ReAct > Act。text-formatted 的 reasoning trace 幫助有限。

---

## 5. Failure Taxonomy ★ （這是實驗的起點）

Paper 手動檢查 gpt-4o FC agent 在 τ-retail 的 40 個 failure case（扣掉 4 個 instruction 問題後剩 36 個）：

| 失敗類別 | 佔比 | 例子 |
|---|---|---|
| **Wrong argument** | 33.3% | tool call 類型對，但 argument 填錯（例：用戶想要 AC adapter 的 lamp，agent 挑錯 option） |
| **Wrong decision** | 25.0% | 違反 domain policy（例：policy 說 exchange 要一次 call 完，agent 分兩次） |
| **Wrong info** | 22.2% | 漏掉用戶要的資訊、算錯金額、報錯價格 |
| **Partial resolve** | 19.4% | 複合請求只處理一部分（例：用戶要改所有訂單地址，agent 只改一個） |

**觀察**：
- wrong argument + wrong info 合計 55% → 跟 **DB reasoning** 有關
- wrong decision 25% → 跟 **rule following** 有關
- partial resolve 19% → 跟 **task decomposition / long-context memory** 有關

paper 的 Table 3 做過一個 ablation：把 domain policy 從 system prompt 拿掉：
- τ-retail: gpt-4o 從 61.2 → 56.8（−4.4%，規則簡單，commonsense 能 cover）
- τ-airline: gpt-4o 從 33.2 → 10.8（−22.4%，規則複雜，policy 是關鍵）

→ 這暗示 airline domain 的 failure 大多跟 rule-following 有關，retail 比較偏 reasoning/memory。

---

## 6. Cost

paper 報告（2024 年價格）：
- gpt-4o FC agent + gpt-4 user sim，τ-retail：**$0.38 / $0.23 per task**（agent / user）
- 跑一次全 trial（115 task）約 $200
- 95.9% 的 cost 來自 input prompt（system prompt 很長：domain policy + function definitions）

對 workshop paper 的 budget 考量：
- 用 Claude Haiku 4.5 當 agent、GPT-4o-mini 當 user sim，可以把 cost 壓到 1/10 左右
- 但 baseline reproduction 至少要跑一次 SOTA pair，建議編 $50-100 做 baseline + method validation

---

## 7. 可能的 Research Angle（延續 CLINC150 hybrid router 的 story）

**核心 RQ 提案**：
> When LLM agents fail on τ-bench multi-step tasks, is the failure in **decomposition (planning)** or in **execution (tool use)**?

### H1: Decomposition-level errors dominate compound-request failures
- 在 failure 中，partial resolve (19%) 和 wrong decision (25%) 可能都是「plan 沒切好」→ 共約 44%
- 如果對，那麼 pre-decomposer 會有用

### H2: Lightweight decomposer 可以在 LLM planning 前做 task skeleton
- 在 user 第一句話後，先用 keyword/embedding 模型切出 sub-task list（類似 CLINC150 的 keyword router）
- LLM planner 拿到 skeleton 後執行，compound request 的完成率會提升
- Cost 幾乎不變（decomposer 很便宜），但 pass^1 / pass^k 應該會上升

### 實驗設計
1. **Phase A — Reproduce baseline**：用 Claude Sonnet 4 / Haiku 4.5 FC agent 跑 τ-retail 115 tasks，3 seed
2. **Phase B — Failure annotation**：手動或 LLM-as-judge 把 failure 分成 4 類，檢查 partial resolve 比例
3. **Phase C — Decomposer**：設計一個 pre-step，從 user instruction 抽出 sub-goal list
4. **Phase D — Ablation**：naive FC vs decomposer+FC，比 pass^1 和 pass^k（特別是 k=4, 8）

### 可能挑戰
- τ-bench 是 **multi-turn**，user instruction 不一次給齊 → decomposer 要能逐步更新，不是 one-shot plan
- ground truth annotation 在 Sierra 的 code 裡，failure mode 要自己標
- pass^k 需要大量 trial，成本要算清楚

---

## 8. Next Actions

1. Clone repo：`git clone https://github.com/sierra-research/tau-bench`
2. 跑起來（先 τ-retail 3-5 tasks smoke test，確認 API key + env 都 OK）
3. 讀 historical_trajectories/ 看真實 agent 表現
4. 設計 Phase A experiment 腳本
5. 寫 `02_reproduction_plan.md`
