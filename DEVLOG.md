# DEVLOG — τ-bench Decomposition Study

實驗進度與觀察。最新條目在最上面。

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
