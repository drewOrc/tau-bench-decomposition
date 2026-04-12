# Related Work（中文版）— LLM Agent 的 Task Decomposition

> Paper 2 的中文思考版。英文版見 `05_related_work.md`。
> 目標讀者：未來的自己寫 workshop paper 時，還有任何問「這東西有什麼新的？」的 reviewer。
> 目的：在 8 篇最相關的 paper 中定位我們的 τ-bench decomposition 工作。
> 日期：2026-04-05

---

## 我們的 RQ（回顧）

**當 LLM agent 在 multi-step 客服 task 上失敗時（τ-bench），失敗模式是在 *decomposition*（理解用戶要什麼）還是 *execution*（工具呼叫/規則遵守）？一個輕量的便宜 pre-decomposer 能否改善 pass^1 / pass^k，且不增加 Sonnet 等級的成本？**

兩條正交的軸把文獻分類：

1. **decomposition 發生在哪裡？** —— one-shot prompt（Plan-and-Solve）vs 遞迴/as-needed（ADaPT、Least-to-Most）vs reasoning loop 內部（ReAct、ToT、Reflexion）。
2. **成本模型是什麼？** —— 單一 model inference（大部分 paper）vs cascade / router（FrugalGPT、我們的 Phase 1）。

下面這份清單中，**沒有人同時做「multi-turn tool-using agent + 明確的便宜 decomposer 作為 pre-step」**。這就是我們的空隙。

---

## 每篇 paper 的 survey

### 1. τ-bench（Yao, Shinn, Razavi, Narasimhan — 2024）

- **是什麼**：我們使用的 benchmark。在有 rule 限制、工具使用、simulated user 的現實客服對話中評估 agent。
- **關鍵 metric**：`pass^k` —— agent 在同一個 task 上 i.i.d. 成功 k 次的機率。暴露 *reliability*，不只是準確率。
- **Headline finding**：SoTA FC agent 在 <50% 的 task 上成功；pass^8 遠低於 pass^1 → agent 很脆弱。
- **與我們的關係**：我們的 substrate。我們把他們的 failure taxonomy（wrong_arg / wrong_decision / wrong_info / partial_resolve）當起點，問一個 *pre-decomposition step* 能不能改變失敗分佈。

### 2. ADaPT — As-Needed Decomposition and Planning（Prasad et al., NAACL 2024 Findings）

- **Idea**：只有在 *LLM 執行失敗時* 才遞迴分解 task。分解是 reactive 的，不是 proactive。
- **Gain**：ALFWorld +28%、WebShop +27%、TextCraft +33%。
- **與我們的相似處**：都主張 multi-step task 上多做一點 decomposition 有幫助。
- **差異**：ADaPT 在 *execution 失敗* 時用 *同一個* LLM 分解。我們用 *更便宜* 的模型 *一次性、proactive 地* 在開頭分解。我們的是 one-shot pre-step；他們的是遞迴 fallback。不同的 cost/latency trade-off、不同的失敗假設：ADaPT 假設 planner 最終夠強；我們假設 planner 其實沒問題，只要 task 從 turn 1 就被正確 frame。
- **設計 takeaway**：我們的「為什麼不遞迴？」一節要引用 ADaPT 作為明顯的 alternative，然後論證：(a) τ-bench 的 user simulator 分批給 info，遞迴會跟 user turn 結構打架；(b) 成本天花板 —— 我們的 thesis 是 *便宜* decomposer，ADaPT-style 的遞迴會加倍 call 次數。

### 3. Plan-and-Solve Prompting（Wang et al., ACL 2023）

- **Idea**：兩階段 zero-shot CoT：先 devise plan、再 execute。單一 LLM、單一 pass。
- **Scope**：數學應用題、單一 agent reasoning。沒有工具、沒有 user simulator。
- **與我們的關係**：「decompose-then-act」frame 的直接祖先。我們把這個直覺移植到 multi-turn agent 場景 + 跨兩個不同大小的 model。
- **設計 takeaway**：Plan-and-Solve 的「devise a plan」prompt 是我們 Option C（tiny-LM decomposer）的候選 template —— 已經用類似的 JSON-schema prompt。

### 4. Least-to-Most Prompting（Zhou et al., ICLR 2023）

- **Idea**：把困難問題分解成有序的 simpler sub-problem list、依序解、每個 solution 作為下一個的 condition。
- **結果**：SCAN compositional generalization 從 16% → 99%。
- **與我們的關係**：最強的證據顯示「先分解再執行」在 compositional task 上有效。τ-bench *就是* compositional（用戶在一次對話裡組合 return + exchange + address change）。
- **差異**：Least-to-Most 用同一個 LLM 做分解和執行。沒有成本拆分、沒有外部 user、沒有工具。
- **設計 takeaway**：我們的 sub-goal list **本質上就是** least-to-most 分解，只是 materialize 成一次性注入到 turn 0 的 system hint，而不是 chain-prompted。

### 5. ReAct — Reason + Act（Yao et al., ICLR 2023）

- **Idea**：reasoning trace 和 tool action 交錯。每 turn = think → act → observe。
- **與我們的關係**：τ-bench 預設的 agent 策略是 ReAct/FC 變體。我們的 decomposer **不取代** ReAct —— 它 **augment** 第一則 system message，加上一個 pre-compute 的 sub-goal list。Agent 還是 turn-by-turn ReAct-loop。
- **定位**：我們不是跟 ReAct 競爭；我們是給 ReAct 更好的初始化。

### 6. Reflexion — Verbal RL for Agents（Shinn et al., NeurIPS 2023）

- **Idea**：Agent 寫一段 verbal「reflection」說明自己為什麼失敗、存到 episodic memory、再試一次。
- **與我們的關係**：Reflexion 跟 τ-bench 同一作（Shinn 一作）。Reflexion 透過 *跨 attempt 學習* 改善 pass^k。我們的 decomposer 試圖在 *單一 attempt 內* 改善 pass^1。
- **互補性**：兩者可以疊加。Phase 3 的 idea：把我們的 upfront decomposer 和 Reflexion-style 對 failed sub-goal 的 retry 結合。記為 future work。
- **關鍵差異**：Reflexion 需要 reward signal。我們的 decomposer 在 inference time 是 unsupervised 的 —— 不需要成功訊號。

### 7. Tree of Thoughts（Yao, Yu, Zhao, Shafran, Griffiths, Cao, Narasimhan — NeurIPS 2023）

- **Idea**：探索候選 reasoning path 的 tree、搭配 value estimation + backtracking。
- **與我們的關係**：ToT 是重量級的 inference-time search。我們的 decomposer 刻意做**相反** —— 一次便宜的 pass、沒有 search。
- **用作對比**：在 discussion section，「ToT 用 ~10-100× 更多 LLM 呼叫來買 reliability；我們的 decomposer 試圖用 <2× 總呼叫數（大部分在便宜 model 上）來買 reliability」。不同的 cost-quality frontier 位置。

### 8. FrugalGPT（Chen, Zaharia, Zou — 2023）

- **Idea**：LLM cascade —— 試便宜 model，信心低就升級到 GPT-4。相同準確率下最多 98% 成本降低。
- **與我們的關係（大連結）**：這是我們 Phase 1 cost-aware-hybrid-router **和** Phase 2 的祖先。
- **差異**：FrugalGPT cascade **答案**（單 turn Q&A）。我們 cascade **角色** —— 便宜 model 分解、昂貴 model 執行。兩個 step 在每個 task 上都發生；沒有 escalation signal。
- **定位**：我們的 thesis 把 FrugalGPT 的「right-sized model for the right sub-task」從 single-turn classification → multi-turn task-oriented dialogue。

---

## 我們在 2×2 上的位置

```
                      |  分解發生在...
                      |  ONCE（一次性上游）    |  AS-NEEDED / 遞迴
  --------------------+-----------------------+---------------------------
  同一個 model         |  Plan-and-Solve       |  ADaPT
  做分解和執行         |  Least-to-Most        |  ToT、Reflexion
                      |                       |
  不同 model           |  **我們（Phase 2）**  |  （沒 survey 到 — 很少見）
  （成本拆分）         |  FrugalGPT（分類）    |
```

左下 quadrant —— *便宜的上游 decomposer + 強下游 executor，在 multi-turn agent benchmark 上* —— 就是我們宣稱的空隙。我們的貢獻很窄但很具體：我們測試這個 quadrant 在 τ-bench 上是否可行。

---

## Workshop Paper 的候選 framing

- **Title 草稿**：「Cheap Decomposition, Expensive Execution: Cost-Aware Pre-Planning for Multi-Turn Tool-Agent-User Tasks」
- **一句話 claim**：在 τ-bench 的 compound task 上，Haiku-4.5 pre-decomposer 以 Y% 的成本 close 了 X% 的 pass^1 gap 到 Sonnet-only baseline，**只在** ground truth 包含 ≥2 個 write-action 的 subset 上。
- **Failure-case 故事（如果 H2 被 reject）**：「我們發現 decomposition 錯誤佔 τ-bench 失敗的 <Z%；主導的失敗模式是 execution 時的 rule adherence。這表示 cost-aware cascade 的 framing 應該瞄準 execution-time、而不是 planning-time 的 compute。」
- **不管哪種結果都可發表** —— 成功支持 cascade thesis，失敗修正 failure taxonomy。

---

## 給自己思考的 open question

1. **「decomposition」和「planning」的差別是什麼？** 在這批文獻裡兩個詞互換使用。我們 paper 裡要明說：decomposition = 把用戶話語 parse 成有序的 sub-goal struct；planning = 為每個 sub-goal 決定 tool-call sequence。我們做第一件，我們把第二件留給 Sonnet。

2. **Decomposer 能不能蒸餾到 3B model？** FrugalGPT 角度。如果 Haiku-4.5 可以，local Qwen-2.5-3B 能否 match？那是自然的 follow-up，且讓成本故事更有說服力（cheap stage 完全不用 API）。標記為 Phase 3。

3. **Decomposition 品質與 task reward 相關嗎？** Proxy metric：計算我們 decomposer 的 sub-goal list 與 ground-truth action sequence abstract signature 之間的 BLEU/structural match。如果相關性弱，decomposition 品質就不是對的 lever。

---

## Bibliography（BibTeX stub 之後補）

- Yao et al. 2024 — τ-bench — arXiv:2406.12045
- Prasad et al. 2024 — ADaPT — arXiv:2311.05772 — NAACL Findings
- Wang et al. 2023 — Plan-and-Solve — arXiv:2305.04091 — ACL
- Zhou et al. 2023 — Least-to-Most — arXiv:2205.10625 — ICLR
- Yao et al. 2023 — ReAct — arXiv:2210.03629 — ICLR
- Shinn et al. 2023 — Reflexion — arXiv:2303.11366 — NeurIPS
- Yao et al. 2023 — Tree of Thoughts — arXiv:2305.10601 — NeurIPS
- Chen, Zaharia, Zou 2023 — FrugalGPT — arXiv:2305.05176
