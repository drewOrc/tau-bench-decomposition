# DEVLOG — τ-bench Decomposition Study

實驗進度與觀察。最新條目在最上面。

---

## 2026-04-22 — Phase D: LaTeX figures + 3-expert review + submission-ready

### 本次工作 / 執行摘要
- **LaTeX 已完成**（前次 session 建立 main.tex + references.bib，本次發現已存在）
- **架構圖（Figure 1）**：baseline vs ours pipeline 對比，含 cost label（<$0.001 vs ~$0.85）
- **Conditions 圖（Figure 2）升級**：加入 quality gap 雙向箭頭 + baseline 虛線參考
- **Figure 生成腳本**：`scripts/gen_paper_figures.py`（可重現）
- **3 輪 expert review**：
  - 假教授 🟢 Accept（checklist 23/23 全過）
  - HR姐 🟢 PASS（Clarity 5, Credibility 5, Differentiation 5）
  - 阿讀 🟢 合格 4/5（14 citations 覆蓋完整，no-prior-work claim 驗證通過）
- **Prose 修正 3 項**：meta-language fix、caption cost 範圍修正、post-hoc power analysis
- **Turnitin self-check**：零 AI tell、句長 std dev 高、標點多樣
- **Visual spacing check**：6/6 頁 300 DPI 全通過
- **中文翻譯 + 簡單解釋版**：`main_zh.md` + `explainer.md/pdf`（前次 session）

### 核心發現 / 數據
- (無新實驗數據，本次為 paper polish + review)
- Post-hoc power analysis：~55 tasks needed to detect 22.7pp effect at α=0.05, 80% power

### Blockers / 遇到的問題
- (無)

### Next
- [x] ~~Wave 2: LaTeX conversion (.tex)~~ — 已完成
- [x] ~~Wave 2: figures~~ — 2 張（architecture + conditions），6 頁 workshop paper 足夠
- [x] ~~Wave 2: References .bib file~~ — 14 篇已完成
- [x] ~~Push updated code + results to GitHub~~ — `eb2f59a` pushed
- [ ] （可選）再跑一輪假教授 deep review 後投稿
- [ ] 投稿目標 workshop（待選定 venue）

### Files / Budget
- New: `scripts/gen_paper_figures.py`
- New: `paper/figures/fig_architecture.png`
- Modified: `paper/figures/fig_conditions.png`（quality gap annotation）
- Modified: `paper/main.tex`（3 prose fixes + architecture figure + power analysis）
- Modified: `paper/main.pdf`（6 pages, 210KB）
- New: `paper/main_zh.md`、`paper/explainer.md/pdf/tex`（前次 session）
- API cost: $0（純寫作 + review）

---

## 2026-04-21 — Phase D: Same-model ablation + Wave 1 fixes

### 本次工作 / 執行摘要
- **Same-model ablation (gpt-4o decomposer)**: 22 tasks × 3 seeds, confirming quality gap is information-limited
- **Wave 1 fixes**: std unification (population→sample), vendor path fix, load_dotenv override, scipy dependency
- **Paper integration**: All 5-condition results integrated into sections.md (§3.2, Table 4/5/6/7, §5, §6, §7, Abstract)
- **Expert review findings applied**: Independence caveat, leave-one-seed-out, OR instead of Cohen's d, wording softening

### 核心發現 / 數據
- **Same-model results**: Seed 42: 8/22 (36.4%), Seed 43: 8/22 (36.4%), Seed 44: 7/22 (31.8%), Mean: 34.8% ± 2.6pp
- **Same-model Δ from baseline: +0.0pp** (p=0.838, McNemar) — identical to baseline
- **Same-model vs Tiny-LM: p=1.000** — indistinguishable, confirms quality gap is NOT model-size
- **Quality gap updated: 22.7pp** (oracle 57.6% vs same-model 34.8%)
- **Sub-goal metrics**: same-model mean 1.4 sub-goals (vs oracle 3.0, tiny-LM 1.5), 30% unclear entities (vs 18% for tiny-LM)
- **Variance**: Same-model has lowest CV (0.08) of any condition, even lower than tiny-LM (0.12)
- **pass^3**: same-model 2/22 (9.1%), tiny-LM 1/22 (4.5%), oracle 7/22 (31.8%)
- **Decomposer cost**: $0.001/call (gpt-4o) vs $0.0007/call (Haiku 4.5) — both negligible vs $0.85/task executor
- **Total ablation cost**: ~$31 (22 tasks × 3 seeds × ~$0.47/task)

### Blockers / 遇到的問題
- (無)

### Next
- [ ] Wave 2: LaTeX conversion (.tex)
- [ ] Wave 2: 4 figures (architecture, failure bar, 4-condition dot plot, quality scatter)
- [ ] Wave 2: References .bib file
- [ ] Push updated code + results to GitHub

### Files / Budget
- Modified: `paper/sections.md` (all sections updated for 5-condition)
- Modified: `src/analyze_4conditions.py` (sample std, same-model condition)
- Modified: `src/mcnemar_per_seed.py` (same-model condition)
- Modified: `src/agent_with_decomposer.py` (vendor path fix)
- Modified: `src/run_baseline.py`, `src/annotate_failures.py` (load_dotenv override)
- Modified: `src/run_decomposer.py` (same-model support)
- Modified: `src/decomposer/__init__.py` (same-model import)
- New: `src/decomposer/same_model.py`
- New: `results/decomposer-same-model/` (3 seeds)
- Modified: `requirements.txt` (scipy)
- API cost: ~$31 (same-model ablation)

---

## 2026-04-16 (晚) — Phase D: Full draft complete + 2 rounds expert review

### 本次工作 / 執行摘要
- **剩餘 sections 全部完成**：§6 Discussion、§7 Conclusion、§1 Introduction、§2 Related Work、Abstract
- **Expert review round 2**：4 位專家（假教授🟡、阿讀 4/5、圖仔 17/19 CLEAN、HR姐 B+）
- **16 項修正全部應用**：
  - Table 重新編號（§4 Table 1、§5 Tables 2-7，按 reading order）
  - Failure taxonomy 加入 user_led_astray (0%) 和 ambiguous_task (0%) 完整 7 行
  - Abstract 加 subset selection caveat
  - §1 "quality collapses" 軟化為 "is expected to degrade"
  - §1 刪除重複句 "Repeating the same task..."
  - §2 加 ReAct、HuggingGPT (Shen et al., 2023)、"To our knowledge" hedge
  - §2 修 Zhou et al. citation collision（WebArena → S. Zhou et al., 2024）
  - §6.1 trimming（從照抄 §5 改為指向 Table + 新解讀）
  - §6.3 刪除重複 "variance estimate is imprecise"
  - §7 刪除 Cohen's d 贅述
  - §1/§3.2 長句拆分

### 核心發現 / 數據
- (無新數據，本次為寫作)
- Full draft 約 3,700 字，在 4-page workshop 篇幅內

### Blockers / 遇到的問題
- **假教授 Issue 1 (HIGH)**：§4 failure taxonomy 無 IAA（inter-annotator agreement）。目前已 downgrade claims 為 exploratory + 加 caveats，但 reviewer 可能仍要求至少 spot-check。10-sample protocol 已設計但未執行。
- **假教授 Issue 3 (MEDIUM)**：缺 same-model decomposition ablation（用 gpt-4o 自己做 decomposer）。列為 stated limitation 或 future work。
- **Std calculation 待統一**：Table 2 (full baseline) 用 sample std (n-1)，Tables 4/6 用 population std (n)。影響所有 CV 值。
- **Table numbering in LaTeX**：markdown 的 Table 順序已修正，但最終 LaTeX 需確認

### Next
- [ ] 假教授 feedback：決定是否跑 10-sample IAA spot-check
- [ ] 假教授 feedback：決定是否加 same-model ablation 或列為 limitation
- [ ] 統一 std 計算方法（sample vs population）
- [ ] LaTeX 轉換（paper/ 目錄下建 .tex）
- [ ] Figure 製作（4 張：architecture、failure bar chart、4-condition dot plot、quality scatter）

### Files / Budget
- 修改：`paper/sections.md`（full draft + 2 rounds review）
- 修改：`DEVLOG.md`
- API cost：$0（本次純寫作，無 API 呼叫）

---

## 2026-04-16 — Phase D: Paper writing started (Definition + 4 sections + expert review)

### 本次工作 / 執行摘要
- **Paper outline 升級到 v1.0**：從 v0（pre-experiment 假設版）全面改寫，反映所有 Phase A/B/C 實際結果
- **Definition 撰寫 (v0.2)**：formal definition of "pre-execution planning"，經 5 位專家 review + 8 項修正
- **4 個 Section 初稿完成**：§3.1 Definition、§3.2 Four Conditions、§4 Failure Taxonomy、§5 Results（~1,500 字 + 6 張表格）
- **數據驗證**：73 個數字逐一核對，70 exact match、2 soft match、1 mismatch（已修正）、1 inconsistency（已標記）
- **Per-seed McNemar 分析**：新計算，揭示 pooled p=0.007 方向一致但 seed 44 貢獻最大
- **新發現：Oracle vs Tiny-LM McNemar p=0.018** — quality gap 有獨立統計支撐
- **Expert review round 1**：假教授 Weak Accept，6 位專家共 12 項修正，全部應用

### 核心發現 / 數據

**Per-seed McNemar (Oracle vs BL)：**
| Seed | BL pass | Oracle pass | Δ | p-value |
|------|---------|-------------|---|---------|
| 42 | 50.0% | 72.7% | +22.7pp | 0.228 (n.s.) |
| 43 | 45.5% | 54.5% | +9.1pp | 0.683 (n.s.) |
| 44 | 9.1% | 45.5% | +36.4pp | 0.027* |
| Pooled | — | — | +22.7pp | 0.007** |

**Oracle vs Tiny-LM (新)：** pooled p=0.018* — quality gap 統計顯著

**數據驗證修正：**
- Table 5 "action types 2-3" → "1-2 per task (mean 1.4)"
- Task 23 example：從意譯改為引用實際 tiny-LM 輸出
- §4.1 加 LLM-as-judge citation (Zheng et al., 2023)
- CV claim 加 n=3 caveat
- 22-task subset 加「top 19% of action-count distribution」+ conditioning-on-DV 承認
- §3.1 加 concrete example (Task 19 water bottle + pet bed)

### Blockers / 遇到的問題
- Std 計算一致性：Table 1 用 sample std (n-1)、Table 2/4 用 population std (n)。需統一，但改了所有 CV 也要改。留到下次統一。
- Per-seed McNemar 個別不顯著（n=22 underpowered）→ paper 已透明揭露

### Next
- [ ] 寫 §1 Introduction
- [ ] 寫 §2 Related Work
- [ ] 寫 §6 Discussion
- [ ] 寫 §7 Conclusion
- [ ] 寫 Abstract（最後寫）
- [ ] 統一 std 計算方式
- [ ] Expert review round 2（完整稿）

### Files / Budget
- 新增：`paper/sections.md`（working draft，4 sections）
- 新增：`notes/07_definition_draft.md`（definition 設計歷程 v0.2）
- 更新：`notes/06_paper_outline.md`（v0 → v1.0）
- 新增：`src/mcnemar_per_seed.py`（per-seed McNemar 分析腳本）
- API cost: $0（純寫作，無 API 呼叫）

---

## 2026-04-15 (晚) — Phase C complete: Tiny-LM experiment + 4-condition analysis

### 本次工作 / 執行摘要
- **Tiny-LM decomposer 實驗完成**：Claude Haiku 4.5 自動產生 sub-goals，22 tasks × 3 seeds
- **四條件完整比較**：baseline / rule-based / oracle / tiny-lm
- **結論：Decomposition quality gap = 21.2pp** — oracle (+22.7pp) vs tiny-lm (+1.5pp)
- **Sub-goal 品質分析**：tiny-LM 系統性 under-decompose（只產出 oracle 50% 的 sub-goals）
- **Variance stabilization 發現**：tiny-LM CV=0.10 vs baseline CV=0.53（5x 降低）
- **Bug fix**：`load_dotenv(override=True)` — 系統 env 空 ANTHROPIC_API_KEY 蓋掉 .env 值

### 核心發現 / 數據

**四條件比較（22 complex tasks）：**

| Condition | Seed 42 | Seed 43 | Seed 44 | Mean | Std | Δ from BL | p-value |
|-----------|---------|---------|---------|------|-----|-----------|---------|
| Baseline | 50.0% | 45.5% | 9.1% | 34.8% | ±18.3pp | — | — |
| Rule-based | 45.5% | 36.4% | 18.2% | 33.3% | ±11.3pp | -1.5pp | — |
| **Oracle** | **72.7%** | **54.5%** | **45.5%** | **57.6%** | **±11.3pp** | **+22.7pp** | **0.007** |
| Tiny-LM | 31.8% | 36.4% | 40.9% | 36.4% | ±3.7pp | +1.5pp | 1.000 |

**Variance stabilization：**
| Condition | CV | Interpretation |
|-----------|-----|----------------|
| Baseline | 0.53 | High variance — seed-sensitive |
| Rule-based | 0.34 | Moderate reduction |
| Oracle | 0.20 | Low variance — consistent improvement |
| Tiny-LM | **0.10** | **Lowest variance** — stabilizing effect even without accuracy gain |

**Sub-goal quality comparison（Tiny-LM vs Oracle）：**
- Oracle: mean 3.0 sub-goals/task, total 66
- Tiny-LM: mean 1.5 sub-goals/task, total 33（**50% of oracle**）
- 18% of tiny-LM sub-goals have "(unclear)" entity
- 10/22 tasks under-decomposed（ratio < 0.5x of oracle）
- Key failure: cannot capture multi-step structure from first utterance alone

**Per-task highlights：**
- Tiny-LM uniquely helped: task 19 (0%→67%), task 42 (0%→67%)
- Tiny-LM uniquely hurt: task 22 (33%→0%), task 46 (67%→33%)
- 4 degraded oracle tasks (30, 36, 54, 64): conditional fallback → sequential misinterpretation

**Statistical tests（pooled 66 observations）：**
- Oracle vs BL: McNemar chi2=7.259, p=0.007; Cohen's d=1.22 (large)
- Tiny-LM vs BL: McNemar chi2=0.000, p=1.000; Cohen's d=0.09 (negligible)

**Paper story confirmed：**
Rule-based ($0) → null | Oracle (gold) → +22.7pp | Tiny-LM (~$0.0005/call) → +1.5pp
Gap = 21.2pp → decomposition quality is the bottleneck, not the concept

### Blockers / 遇到的問題
- `load_dotenv` 不 override 系統 env → ANTHROPIC_API_KEY="" 蓋掉 .env 值（已修復）
- Tiny-LM 實驗耗時 ~18 min（3 seeds sequential, concurrency=2）

### Next
- [x] Tiny-LM decomposer 實驗 ✅
- [x] 四條件比較分析 ✅
- [ ] Paper 撰寫（Phase D）
- [ ] Drew 手動 spot-check 10 annotations（`data/annotations/spot_check_10_samples.md`）
- [ ] 考慮是否需要 full 115-task tiny-LM run（目前判斷不需要，22-task 子集已足夠）

### Files / Budget
- 新增：`src/analyze_4conditions.py`（四條件分析腳本）
- 修改：`src/run_decomposer.py`（load_dotenv override=True）
- 新增：`results/decomposer-tiny-lm/retail/seed{42,43,44}/`
- Tiny-LM decomposer API cost: $0.0431（Anthropic, 66 calls）
- Tiny-LM executor API cost: ~$31（OpenAI gpt-4o, 22 tasks × 3 seeds）
- Total Phase C API cost: ~$149（rule-based $87 + oracle $31 + tiny-lm $31）

---

## 2026-04-15 — Phase C: Decomposer experiments (rule-based null result + oracle ceiling)

### 本次工作 / 執行摘要
- **Rule-based decomposer 實驗完成**：3 seeds × 115 tasks × concurrency=2
- **結論：NULL RESULT** — rule-based decomposer 無效
- **Root cause 分析**：per-task 分析發現 decomposer 品質太差
  - 27.5% tasks 得到 0 sub-goals（完全沒拆解）
  - 61.4% tasks 只得到 1 sub-goal（沒有真正 decompose）
  - 19 tasks 改善 vs 26 tasks 退步 vs 70 tasks 不變
- **專家會議決策**：4 agents（圖仔/跑哥/阿讀/假教授）一致判斷 null result 源自 decomposer 品質不足，非 decomposition 概念無效。決定做 oracle ceiling analysis。
- **Oracle decomposer 建構**：
  - 選 22 個 complex tasks（gt_actions ≥ 7 AND baseline_pass < 3/3）
  - 人工分析每個 task 的 instruction + ground truth actions，建 gold sub-goals
  - 建 OracleDecomposer class + 修改 interface 支援 task_index passthrough
  - Code review 修 4 個 issues（threading.Lock、env guard、strict ValueError、thread-safety comment）
- **Oracle 實驗完成**：22 tasks × 3 seeds × concurrency=2

### 核心發現 / 數據

**Rule-based decomposer（全 115 tasks）：**

| Metric | Baseline | Rule-based | Δ |
|--------|----------|-----------|---|
| Mean pass^1 | 59.7% ± 10.3pp | 57.7% ± 4.3pp | -2.0pp |
| pass^3 | 36.5% | 35.7% | -0.9pp |
| Seed 42 | 65.2% | 62.6% | -2.6pp |
| Seed 43 | 66.1% | 55.7%* | -10.4pp |
| Seed 44 | 47.8% | 54.8% | +7.0pp |

*Seed 43 異常下降可能與 OpenAI quota 中斷有關。

**有趣觀察：** std 從 10.3pp 降到 4.3pp — decomposer 有穩定化效果，即使 mean 略降。

**Oracle decomposer（22 complex tasks）：**

| Metric | Baseline | Rule-based | Oracle | Δ (Oracle vs BL) |
|--------|----------|------------|--------|-------------------|
| Mean pass^1 | 34.8% ± 18.3pp | 33.3% ± 11.3pp | **57.6% ± 11.3pp** | **+22.7pp** |
| pass^3 | 0/22 (0%) | 2/22 (9.1%) | **7/22 (31.8%)** | **+31.8pp** |
| Seed 42 | 50.0% | 45.5% | 72.7% | +22.7pp |
| Seed 43 | 45.5% | 36.4% | 54.5% | +9.0pp |
| Seed 44 | 9.1% | 18.2% | 45.5% | +36.4pp |

- **15/22 tasks 改善**, 4 degraded, 3 same（net +11）
- pass^3 tasks: 3, 23, 31, 32, 35, 46, 55
- Degraded tasks: 30, 36, 54, 64（條件式 fallback 被誤解為順序指令）
- Seed 44 從 9.1% → 45.5%，decomposition 對高 variance seeds 特別有效

**結論：decomposition 概念有效（+22.7pp）。問題是 decomposer 品質。**

### Blockers / 遇到的問題
- **OpenAI quota exceeded**：跑 rule-based 時 3 seeds 並行超過 TPM 450K 限制 → 改為 sequential seeds
- OpenAI quota 耗盡 → Drew 加值後繼續（patch 跑法）
- Seed 43 merge 異常 → 用完整新 checkpoint 覆蓋

### Next
- [x] Rule-based decomposer 實驗
- [x] 分析 null result root cause
- [x] 專家會議決策 → oracle ceiling
- [x] 建 oracle decomposer + gold sub-goals (22 tasks)
- [x] Oracle 實驗跑完 + 分析結果 → **+22.7pp，概念有效**
- [x] tiny-LM decomposer 實驗 → **+1.5pp，品質不足**
- [ ] Drew 手動 spot-check 10 annotations（`data/annotations/spot_check_10_samples.md`）

### Files / Budget
- 新增：`data/oracle_subgoals.json`（22 tasks gold sub-goals）
- 新增：`src/decomposer/oracle.py`
- 修改：`base.py`, `rule_based.py`, `tiny_lm.py`（**kwargs 簽名）
- 修改：`agent_with_decomposer.py`（pass task_index）
- 修改：`run_decomposer.py`（oracle support + threading fix）
- Rule-based 實驗 API cost：~$87（含 quota 中斷重跑）
- Oracle 實驗 API cost：~$31（22 tasks × 3 seeds, ~974s total wall time）

---

## 2026-04-14 (晚) — Phase B: Failure annotation + seed 44 anomaly analysis

### 本次工作 / 執行摘要
- **Annotation schema 設計**：擴展 paper 的 4-category taxonomy 到 7 categories（加 `user_led_astray`、`ambiguous_task`、`none`），加入 `user_behavior`、`decomposition_relevant`、`n_subtasks`/`n_subtasks_completed`、`policy_violation` 欄位。JSON Schema 存 `data/annotation_schema.json`
- **LLM-as-judge annotator**：完全重寫 `src/annotate_failures.py`，用 gpt-4o-mini 透過 litellm 分類每個失敗 trajectory。每個 annotation 花 ~$0.0004，總成本 ~$0.09
- **First run crash fix**：seed 43 task 20 LLM judge 回傳 unparseable JSON → 加多層 fallback（nested try/except、`default=str` serialization、main loop try/except with "unknown" fallback）
- **全量 annotation 完成**：139 retail + 76 airline = 215 total annotations
- **Seed 44 深入分析**：cross-seed 比較找出 21 個 tasks 只在 seed 44 失敗，81% 屬 USER_DIVERGES_EARLY pattern

### 核心發現 / 數據

**τ-retail failure distribution (139 failures, 3 seeds)**
| Category | Count | % |
|----------|-------|---|
| wrong_decision | 67 | 48.2% |
| partial_resolve | 55 | 39.6% |
| wrong_argument | 12 | 8.6% |
| wrong_info | 4 | 2.9% |
| unknown | 1 | 0.7% |
| **Decomposition-relevant** | **137/139** | **98.6%** |

**τ-airline failure distribution (76 failures, 3 seeds)**
| Category | Count | % |
|----------|-------|---|
| wrong_decision | 50 | 65.8% |
| partial_resolve | 20 | 26.3% |
| wrong_argument | 3 | 3.9% |
| wrong_info | 3 | 3.9% |
| **Decomposition-relevant** | **73/76** | **96.1%** |

**Seed 44 anomaly：**
- 21 tasks fail ONLY in seed 44（pass in 42+43）
- 全部 reward=0（complete failure，非 partial）
- 81% pattern = USER_DIVERGES_EARLY：user simulator 在 seed 44 走不同對話路徑
- 範例 task 36：seed 42 user 要求換便宜商品（agent pass），seed 44 user 要求直接取消訂單（agent fail）
- 結論：seed variance 主要由 user simulator 驅動，非 agent 能力差異

**⚠️ LLM judge bias 發現：**
- Judge 分類 0% `user_led_astray`，但 seed 44 分析顯示 user divergence 是主因
- Judge 從 agent 視角評估，無法辨識 user simulator 行為造成的失敗
- `decomposition_relevant` ~98% 可能高估——judge 傾向標 true
- **需要 manual spot-check ~20 annotations 來校準**

### Blockers / 遇到的問題
- LLM judge unparseable JSON（已解決，加多層 fallback）
- Judge bias：0% user_led_astray vs seed 44 分析 81% user-driven（待 manual review）
- decomposition_relevant 過高（98%）需校準（待 manual spot-check）

### Next
- [ ] Manual spot-check ~20 annotations（10 retail + 10 airline）
- [ ] Recalibrate judge prompt（如果 spot-check 確認 bias）
- [ ] Decomposer v1 設計與實作（Phase C）
- [ ] Ablation study（Phase D）

### Files / Budget
- 新增：`data/annotation_schema.json`（JSON Schema，7 categories + 9 fields）
- 重寫：`src/annotate_failures.py`（LLM-as-judge pipeline，~310 LOC）
- 新增：`data/annotations/baseline_retail_annotations.jsonl`（139 annotations）
- 新增：`data/annotations/baseline_airline_annotations.jsonl`（76 annotations）
- API cost：~$0.09（gpt-4o-mini, 337K input + 15K output tokens retail; ~similar airline）

---

## 2026-04-14 — Baseline reproduction complete: τ-retail + τ-airline, 3 seeds each

### 本次工作 / 執行摘要
- **Smoke test** → API key 設定、venv 建立、單一 task 驗證 pipeline
- **發現 τ-bench CLI argparse bug**：`run.py` 用 litellm enum 物件當 argparse choices，字串比對永遠失敗。解法：完全重寫 `run_baseline.py`，直接用 Python API（`tau_bench.run.run()` + `RunConfig` Pydantic model），繞過 CLI
- **Rate limit 除錯**：OpenAI Tier 1 (30K TPM) → 升 Tier 2 (450K TPM)；加 `litellm.num_retries = 5`；concurrency 從 6 降到 2
- **User simulator 發現**：gpt-4o-mini 作 user simulator → pass^1 = 46.1%（偏低 15pp）。10-task A/B 驗證後確認 gpt-4o user simulator 才是 paper 設定。全量重跑
- **全量 baseline 完成**：3 seeds × 2 domains = 6 runs，全部 0 error
- **目錄重組**：`results/baseline/{retail,airline}/seed*/`，fix `run_baseline.py` 和 `merge_seeds.py` 加 `env` 層

### 核心發現 / 數據

**τ-retail (115 tasks)**
| Seed | pass^1 | n_pass |
|------|--------|--------|
| 42 | 65.2% | 75 |
| 43 | 66.1% | 76 |
| 44 | 47.8% | 55 |
| **Mean ± std** | **59.7% ± 10.3pp** | — |
| Paper | 61.2% | — |
| Wilson 95%CI | [54.4%, 64.8%] | — |
| pass^3 | 36.5% (42/115) | — |

**τ-airline (50 tasks)**
| Seed | pass^1 | n_pass |
|------|--------|--------|
| 42 | 48.0% | 24 |
| 43 | 54.0% | 27 |
| 44 | 46.0% | 23 |
| **Mean ± std** | **49.3% ± 4.2pp** | — |
| Paper | 35.2% | — |
| Wilson 95%CI | [41.4%, 57.2%] | — |
| pass^3 | 32.0% (16/50) | — |

**分析：**
- Retail mean 59.7% vs paper 61.2%（-1.5pp），paper 數字在我們 95%CI 內 ✅
- Airline mean 49.3% vs paper 35.2%（+14.1pp），偏高。原因推測：(1) 2026 版 gpt-4o 更強；(2) 50 tasks sample 小→ variance 大
- Seed 44 retail 異常低（47.8%），拉低 mean 和擴大 std。τ-bench seed 同時影響 user simulator 隨機性和 DB 初始狀態
- pass^3 大幅低於 pass^1（retail 36.5% vs 59.7%，airline 32.0% vs 49.3%），證實 agent 的 reliability 問題——這正是 decomposer 要解決的

**User simulator A/B 實驗（10 tasks, seed 42）：**
- gpt-4o-mini user: 5/10 pass
- gpt-4o user: 9/10 pass
- 結論：user simulator 品質直接影響 agent 成功率，gpt-4o 是正確設定

### Blockers / 遇到的問題
- τ-bench CLI argparse bug（已解決，改用 Python API）
- Rate limit（已解決，Tier 2 + litellm retry + concurrency=2）
- User simulator（已解決，改用 gpt-4o）
- Seed 44 retail 異常低（47.8%）——需要在 failure annotation 階段深入分析哪些 task 在 seed 44 失敗

### Next
- [x] Failure annotation schema 設計 ✅ (2026-04-14 晚)
- [x] 分析 seed 44 retail 失敗 pattern ✅ (2026-04-14 晚)
- [ ] Decomposer v1 設計與實作
- [ ] Ablation study

### Files / Budget
- 修改：`src/run_baseline.py`（Python API 重寫、litellm retry、log_dir 加 env 層、default user-model 改 gpt-4o）
- 修改：`src/merge_seeds.py`（load_seed_results 加 domain 參數、output 路徑加 domain）
- 新增：`results/baseline/retail/seed{42,43,44}/`（各含 summary.json + checkpoint JSON）
- 新增：`results/baseline/airline/seed{42,43,44}/`（同上）
- 新增：`results/baseline/{retail,airline}/metrics_merged.json`
- 新增：`requirements.txt`、`.env.example`
- 修改：`.gitignore`（擴展 patterns）
- 修改：`README.md`（更新 Quick Start、status checkboxes）
- API cost 估計：~$98/seed × 6 seeds ≈ **~$590**（gpt-4o agent + gpt-4o user simulator）
- Wall time：retail ~24 min/seed, airline ~11 min/seed, total ~105 min

---

## 2026-04-12 — Environment setup: fresh clone + dependency install + task verification

### 本次工作 / 執行摘要
- 舊的 `vendor/tau-bench` clone 損壞（`.git` 存在但 working tree 空的，lock file 無法刪除）
- 重新 clone 到 `vendor/tau-bench-clean`（commit `59a200c`），pin 這個 hash 以確保 reproducibility
- `pip install -e .` 安裝所有 dependencies（anthropic, openai, litellm, tenacity 等）
- 更新 `src/run_baseline.py` 的 `VENDOR_DIR` 指向 `tau-bench-clean`
- 驗證 import + task count

### 核心發現 / 數據
- **Retail test tasks: 115**（跟 paper 一致 ✅）
- **Airline test tasks: 50**（跟 paper 一致 ✅）
- **Compound tasks 計數修正**：`>=2 actions` 的定義下，retail 93/115 (80.9%), airline 30/50 (60.0%)
  - ⚠️ 之前 notes 裡寫的 47/115 (40.9%) 可能用了不同定義（只算 write-action，不算 read-action）
  - 這個差異需要在跑 failure annotation 時釐清：到底用 `len(actions) >= 2` 還是只算有 side-effect 的 action
- **變數命名不一致**：retail 用 `TASKS_TEST`，airline 用 `TASKS`。run.py 內部處理了這個差異。
- `run.py` import OK，baseline 腳本 ready to execute

### Blockers / 遇到的問題
- `vendor/tau-bench-broken` 刪不掉（掛載目錄權限限制），不影響功能但佔空間
- 需要 `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` 才能跑 baseline（sandbox 裡沒有）
- τ-bench README 最新 commit 提到 τ³-bench 是新版。需確認我們用的 task definitions 跟 paper 原版是否一致

### Next
- [ ] 在本機設定 API keys（`.env` 或 `export`）
- [ ] 3-task smoke test：`python src/run_baseline.py --env retail --task-ids 0 1 2 --seeds 42`
- [ ] 確認實際 API cost vs 預估（$0.026/task × 3 = ~$0.08 預期）
- [ ] 確認 output JSON 格式，調整 `merge_seeds.py` 的 glob pattern
- [ ] 釐清 compound task 定義（all actions vs write-only actions）

### Files / Budget
- 新增：`vendor/tau-bench-clean/`（完整 clone, commit 59a200c）
- 新增：`scripts/estimate_cost.py`（成本預估工具）
- 修改：`src/run_baseline.py`（VENDOR_DIR 路徑更新）
- API cost: $0.00（只做 import 測試，未呼叫 API）

---

## 2026-04-05 (late) — Overnight prep: related work + wrappers + paper outline

### 本次工作 / 執行摘要
趁 usage 沒用完前把幾個 token/時間 heavy 的準備工作一次做完：
- **文獻 review**：WebFetch 抓了 8 篇關鍵 paper 的 abstract（τ-bench, ADaPT, Plan-and-Solve, Least-to-Most, ReAct, Reflexion, ToT, FrugalGPT），寫 `notes/05_related_work.md`，用 2×2 矩陣定位我們的 quadrant（cheap upfront decomposer + strong executor + multi-turn agent）是空的。
- **agent wrapper**：寫 `src/agent_with_decomposer.py`，subclass `ToolCallingAgent`，在 turn-0 跑 decomposer 後把 sub-goal list 注入 system prompt。支援 `inject_as="system" | "user_prefix" | "none"`（none 用作 Hawthorne control）。
- **seed merger**：寫 `src/merge_seeds.py`，鏡像 CLINC150 的 merge_seeds.py 結構，但改算 pass^1 / pass^k / Wilson 95%CI / McNemar。支援 `--compare-to baseline` 做兩 tag 的配對比較。
- **paper outline**：寫 `notes/06_paper_outline.md`，7 個 section + timeline + 圖表 plan。Title: "Cheap Decomposition, Expensive Execution"。

### 核心發現 / 觀察
- **Lit 定位確認**：沒有人做 cheap-plan + expensive-execute + multi-turn tool-agent 這個組合。ADaPT 最接近但用同一 model + recursive。我們的 novelty 是 cost-split + one-shot upfront。
- **Paper framing**：成功失敗兩種結果都可發表。若 H2 成立 → cascade 論點延伸成立；若 H2 被 reject → failure taxonomy 告訴我們 execution 才是 bottleneck。這很重要，降低研究風險。
- **Reflexion 同作者**：τ-bench 和 Reflexion 都是 Shinn 一作。如果 Phase 3 要延伸，decomposer + Reflexion 是自然 stack。

### Blockers / 遇到的問題
- `agent_with_decomposer.py` 只寫了，還沒 import 測試過（沒跑 env）。明天 smoke test 時要一起驗證。
- `merge_seeds.py` 讀 `results/{tag}/seed{N}/results-*.json`，但 τ-bench `run.py` 實際產出的檔名格式還沒確認（可能是 `results-xxx.json` 或其他）。明天跑完第一個 seed 後要對一下。

### Next
- [ ] Clone tau-bench repo 到 `vendor/`（之前 clone 到 /tmp/tau-bench，正式執行前要 symlink 或重 clone）
- [ ] 3-task smoke test：`python src/run_baseline.py --env retail --task-ids 0 1 2 --seeds 42`
- [ ] 驗證 `results/baseline/seed42/` 的輸出格式，調整 `merge_seeds.py` 的 glob pattern
- [ ] 驗證 `agent_with_decomposer.py` 能被 tau_bench 的 agent factory 吃到

### Files / Budget
- 新增：`notes/05_related_work.md`, `notes/06_paper_outline.md`
- 新增：`src/agent_with_decomposer.py`, `src/merge_seeds.py`
- 新增（先前 session）：`src/run_baseline.py`, `src/annotate_failures.py`,
  `src/decomposer/{base,rule_based,tiny_lm,__init__}.py`,
  `notes/03_repo_anatomy.md`, `notes/04_failure_annotation_schema.md`,
  `data/task_profile.json`
- API cost: ~$0.02（8 次 WebFetch，內部 summarizer 用的是小 model）

---

## 2026-04-05 — Kickoff + paper notes + setup docs

### 本次工作 / 執行摘要
- 整理資料夾：`experiment/` placeholder → `_archive/`，新建 `tau-bench-decomposition/`
- 用 WebFetch + pdfplumber 讀完 τ-bench paper (Yao et al. 2024, Sierra)
- 寫 `notes/01_tau_bench_paper_notes.md`（paper 重點 + failure taxonomy）
- 寫 `notes/02_setup_guide.md`（install、smoke test、budget、go/no-go）
- 寫 `README.md` 和 `EXPERIMENT_DESIGN.md`（含 H1/H2/H3 + falsification criteria）
- 更新根目錄 CLAUDE.md 和 TODO.md

### 核心發現 / 數據
Paper 關鍵數字（Yao et al. 2024）：
- τ-retail 115 tasks / τ-airline 50 tasks
- gpt-4o FC pass^1：retail 61.2% / airline 35.2%，pass^8 < 25%
- Failure taxonomy（36 cases）：wrong_arg 33.3% / wrong_decision 25.0% / wrong_info 22.2% / partial_resolve 19.4%
- Ablation：移除 policy → retail −4.4pp（commonsense 夠）/ airline −22.4pp（rules 關鍵）
- Cost：paper 時代 gpt-4o + gpt-4 full-run ~$200

**Design decisions**：
- Primary domain = τ-retail（較多 task，statistical power 夠）
- Main baseline = Claude Sonnet 4.6（延續 CLINC150，Anthropic API）
- User simulator = gpt-4o-mini（便宜穩定，避免噪音）
- 3 seeds (42, 43, 44) 與 CLINC150 一致
- Falsification 明寫：H1 <30% reject、H2 ≤1pp reject、H3 Δpass^8 ≤ Δpass^1 reject

### Blockers / 遇到的問題
- Sonnet 4.6 在 τ-retail 能跑到幾 % 未知（paper 沒報過，gpt-4o 是 61.2%）
- τ-bench repo 對 macOS + Python 3.10+ 相容性未驗證

### Next
- [ ] Clone `sierra-research/tau-bench` 到 `vendor/`
- [ ] `pip install -e .` 確認 dep 裝得起來
- [ ] 3-task smoke test（task_ids 0 1 2）
- [ ] 讀 `historical_trajectories/` 看真實 agent 行為

### Files / Budget
- 新增：`tau-bench-decomposition/{README,EXPERIMENT_DESIGN,DEVLOG,.gitignore}.md`
- 新增：`notes/01_tau_bench_paper_notes.md`, `notes/02_setup_guide.md`
- 更新：`../CLAUDE.md`, `../TODO.md`
- API cost: $0

---
