# τ-bench Setup Guide

> 本機環境：macOS + Python 3.10+
> Repo：https://github.com/sierra-research/tau-bench （MIT License）

---

## 1. Install

```bash
# 在工作目錄建立一個子資料夾放 clone 的 repo（和我們自己的 src/ 分開）
cd "研究所申請計劃 (1)/tau-bench-decomposition"
git clone https://github.com/sierra-research/tau-bench vendor/tau-bench
cd vendor/tau-bench
pip install -e .
```

Python deps 會自動裝 openai / anthropic / mistral / google-generativeai 等 client。

---

## 2. Environment Variables

```bash
export ANTHROPIC_API_KEY=...   # 主要用這個，延續 CLINC150 實驗
export OPENAI_API_KEY=...      # user simulator 用（paper 用 gpt-4-0613, 我們可用 gpt-4o-mini）
# 以下只有要測其他 model 才需要
export GOOGLE_API_KEY=...
export MISTRAL_API_KEY=...
```

API key 管理：延用 CLINC150 實驗的 `.env` 策略，**repo 永遠不要 commit key**。

---

## 3. Smoke Test

跑 3 個 task 看環境是否正常：

```bash
cd vendor/tau-bench
python run.py \
  --agent-strategy tool-calling \
  --env retail \
  --model claude-haiku-4-5-20251001 \
  --model-provider anthropic \
  --user-model gpt-4o-mini \
  --user-model-provider openai \
  --user-strategy llm \
  --max-concurrency 3 \
  --task-ids 0 1 2
```

預期輸出：
- 每個 task 印出 trajectory（tool calls + user messages）
- 最後給出 reward (0 or 1) 和 pass^1
- 結果存到 `./historical_trajectories/` 或類似位置

**成本估算**（smoke test, 3 task, haiku agent + gpt-4o-mini user）：
- 預估 < $0.10
- 如果超過 $1，先停下來檢查 config

---

## 4. Reference Run（Baseline Reproduction）

正式跑 τ-retail 全部 115 tasks：

```bash
python run.py \
  --agent-strategy tool-calling \
  --env retail \
  --model claude-sonnet-4-6 \
  --model-provider anthropic \
  --user-model gpt-4o-mini \
  --user-model-provider openai \
  --user-strategy llm \
  --max-concurrency 10 \
  --seed 42
```

建議：
- 先跑一次 seed=42 看結果（約 $20-40 with Sonnet）
- 再補 seed=43, 44 算 mean ± std
- 避免用 `--max-concurrency` 太高，rate limit 會拖慢

---

## 5. Folder Layout（本地 experiment 資料夾）

```
tau-bench-decomposition/
├── README.md                        ← 實驗總覽、RQ、方法
├── notes/
│   ├── 01_tau_bench_paper_notes.md  ← paper 重點
│   ├── 02_setup_guide.md            ← 本檔
│   └── 03_failure_annotation.md     ← TODO: 標註 schema
├── vendor/
│   └── tau-bench/                   ← 原 repo，.gitignore
├── data/
│   ├── annotations/                 ← 我們手動 / LLM-as-judge 標的 failure mode
│   └── trajectories/                ← 從 vendor 複製過來的 baseline 結果
├── src/
│   ├── decomposer.py                ← 我們要做的 lightweight pre-decomposer
│   ├── run_with_decomposer.py       ← 包一層 agent 跑 τ-bench
│   └── annotate_failures.py         ← failure taxonomy 自動分類
└── results/
    ├── baseline/                    ← naive FC agent
    ├── decomposer/                  ← decomposer+FC
    └── figures/
```

**.gitignore 要包含**：
- `vendor/` （別把別人的 repo 塞進自己的 commit）
- `data/trajectories/raw_*.json` （太大）
- `.env`, `*.key`

---

## 6. Risks & Go/No-Go Checkpoints

| Checkpoint | 時機 | Pass 條件 | 失敗怎麼辦 |
|---|---|---|---|
| Smoke test 跑得起來 | Day 1 | 3 task 跑完有 reward 輸出 | debug env / API key / package 問題 |
| Baseline 復現接近 paper | Week 1 | Sonnet 4 在 retail pass^1 ≥ 55% | model 差太多 → 改 prompt / 換 model |
| Failure taxonomy 可標 | Week 2 | 100 個 failure 標完，Kappa > 0.6 | schema 重設計 |
| Decomposer 有 lift | Week 3-4 | pass^1 或 pass^8 提升 ≥ 3pp | method 改設計或換 RQ |
| Writeup 可投稿 | Week 5-6 | 有 4 頁短 paper 初稿 | 再縮小 scope |

**時間盒**：總預算 5-6 週（約 100 小時）。超過就要 reassess。

---

## 7. 跟 CLINC150 實驗的 Story Connection

CLINC150 實驗證明了：
> 「便宜模型 (keyword/embedding) 先處理，LLM 再接手 hard case」—— 在 single-turn intent classification 上可行。

τ-bench 這個實驗的論述：
> 把同樣的想法搬到 **multi-turn task decomposition**——lightweight decomposer 先切 task skeleton，LLM planner 再執行——能不能在 agent reasoning 上也 work？

兩個實驗串起來就是一個 narrative：**cost-aware cascade 作為 agent architecture 設計原則**，從 classification scale 到 decomposition scale。這個故事正好對 MiuLab 的 agent reasoning 方向。
