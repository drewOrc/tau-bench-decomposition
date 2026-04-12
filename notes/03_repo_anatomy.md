# τ-bench Repo Anatomy

> 從 clone 下來的 `sierra-research/tau-bench` repo 實際摸清的架構。
> 這份 note 用來支持 decomposer wrapper 的實作。

---

## 1. Top-level layout

```
tau-bench/
├── run.py                        ← CLI entrypoint
├── setup.py                      ← pip install -e .
├── auto_error_identification.py  ← LLM-as-judge for failures（！先看這個）
├── tau_bench/
│   ├── run.py                    ← 實際 run 邏輯
│   ├── types.py                  ← Action / Task / SolveResult / RunConfig
│   ├── agents/
│   │   ├── base.py
│   │   ├── tool_calling_agent.py ← 主 baseline（FC）
│   │   ├── chat_react_agent.py
│   │   └── few_shot_agent.py
│   ├── envs/
│   │   ├── base.py               ← Env class (reset/step)
│   │   ├── user.py               ← LLMUserSimulationEnv
│   │   ├── tool.py
│   │   ├── retail/
│   │   │   ├── env.py
│   │   │   ├── rules.py          ← policy text
│   │   │   ├── wiki.md           ← system prompt for agent
│   │   │   ├── tasks_test.py     ← TASKS_TEST = [...] (115 tasks)
│   │   │   ├── tasks_train.py    ← TASKS_TRAIN
│   │   │   ├── tasks_dev.py      ← TASKS_DEV
│   │   │   ├── tools/            ← API implementations
│   │   │   └── data/             ← orders/products/users JSON
│   │   └── airline/
│   │       └── ...               ← 變數名叫 TASKS（不是 TASKS_TEST）
│   └── model_utils/              ← LLM wrapper helpers
├── few_shot_data/
└── historical_trajectories/      ← 前人跑過的 trajectory，可以當 reference
```

---

## 2. 核心型別 (`tau_bench/types.py`)

```python
class Action:
    name: str
    kwargs: Dict[str, Any]

class Task:
    user_id: str
    actions: List[Action]   # ← ground truth action sequence
    instruction: str        # ← 給 user simulator 的 system prompt
    outputs: List[str]

class SolveResult:
    reward: float           # 0.0 或 1.0（DB state 比對）
    messages: List[Dict]    # 完整對話 trajectory
    info: Dict[str, Any]
    total_cost: Optional[float]
```

**Reward 怎麼算**：`env.step` 在 episode 結束時比較 DB state 和 ground truth 的 `actions` 產生的 DB state。deterministic，不需要 LM judge。

---

## 3. Agent Loop（`ToolCallingAgent.solve`）

```python
messages = [
    {"role": "system", "content": self.wiki},      # domain policy + tool intro
    {"role": "user", "content": obs},                # user 第一句
]
for _ in range(max_num_steps):  # 預設 30
    res = completion(messages=messages, model=..., tools=self.tools_info, ...)
    next_message = res.choices[0].message
    action = message_to_action(next_message)        # tool call or respond
    env_response = env.step(action)                 # user reply or tool result
    reward = env_response.reward
    # extend messages with tool call + result OR user reply
    if env_response.done: break
```

**給 decomposer 的插入點**：
1. `wiki` 是 system prompt，裡面已經塞了 domain policy + tool defs。我們的 decomposer output 要 **prepend 或 append 到 wiki**。
2. 因為 agent 看不到原始 task.instruction，decomposer **不能一次看完整 instruction**。它只能看 user 第一句 `obs`（和後續 user reply）。
3. Incremental decomposer 設計：每次 user reply 後，更新 sub-goal list，塞進 assistant message 前面當 scratchpad（或當 system reminder）。

---

## 4. User Simulator（`LLMUserSimulationEnv`）

重點 system prompt rules：
- *"Do not give away all the instruction at once. Only provide the information that is necessary for the current step."*
- *"Do not hallucinate information that is not provided in the instruction."*
- *"If the instruction goal is satisfied, generate ###STOP###"*
- Default user model: gpt-4o（paper 用 gpt-4-0613）

**對 decomposer 設計的影響**：
- 用戶會分多輪揭露資訊 → decomposer 需要「partial information」下更新 plan
- 不能預設第一句就包含所有 sub-goal

---

## 5. Task Profile（我們自己跑出來的）

儲存於 `data/task_profile.json`。

### τ-retail (115 tasks)

| # write actions | # tasks | |
|---|---|---|
| 0 | 7 | info-only（refund check, policy Q&A） |
| 1 | 61 | single-action |
| 2 | 26 | compound |
| 3 | 15 | compound |
| 4 | 6 | compound |

**Compound (≥2 write actions)**: **47/115 = 40.9%** → 這是 H2 的 target subset

### τ-airline (50 tasks)

| # write actions | # tasks |
|---|---|
| 0 | 16 |
| 1 | 19 |
| 2 | 8 |
| 3 | 4 |
| 4 | 2 |
| 5 | 1 |

**Compound**: **15/50 = 30.0%**

### Instruction length
- retail: mean 429 chars / median 370 / max 1157
- airline: mean 439 chars / median 377 / max 1334

### Action types（retail, counts over all tasks）
Read-only：`get_order_details` (171), `get_product_details` (73), `find_user_id_by_name_zip` (62), `get_user_details` (59), `find_user_id_by_email` (15), `calculate` (14), `list_all_product_types` (6)

Write：`return_delivered_order_items` (42), `modify_pending_order_items` (39), `exchange_delivered_order_items` (36), `cancel_pending_order` (25), `modify_pending_order_address` (24), `modify_user_address` (11), `modify_pending_order_payment` (1), `transfer_to_human_agents` (4)

→ 7 write + 7 read（與 paper Table 1 說的 7 write + 8 read 差 1 個，`list_all_product_types` 算 navigation 不算核心 read）

---

## 6. `auto_error_identification.py`（重要發現！）

這個檔案就是 Sierra 官方的 **LLM-as-judge error classifier**。直接拿來當我們 failure taxonomy 的參考。需要細讀內容並比對 paper 的 4 類。

→ TODO: 寫 `04_failure_annotation_schema.md` 時要引用這個檔案的 prompt + label set。

---

## 7. CLI 參數（完整）

```bash
python run.py \
  --num-trials 1 \
  --env retail \
  --model claude-sonnet-4-5-20250929 \
  --model-provider anthropic \
  --user-model gpt-4o-mini \
  --user-model-provider openai \
  --agent-strategy tool-calling \  # or act, react, few-shot
  --temperature 0.0 \
  --task-split test \              # train/dev/test
  --start-index 0 --end-index -1 \
  --task-ids 0 1 2 \               # optional, override range
  --log-dir results \
  --max-concurrency 10 \
  --seed 10 \
  --user-strategy llm              # llm / human / verify / reflection / react
```

注意：
- `--seed` 控制 shuffle，LM sampling 是另一回事（user temp 預設 1.0）
- 要跑多 seed，需要在 CLI 外面包 loop（或開 PR 進 repo）

---

## 8. 實作計畫

### 我們需要寫的 code（住在 `src/` 不污染 vendor/）

```
src/
├── decomposer/
│   ├── rule_based.py          # Option A：正則 action verb + entity
│   ├── tiny_lm.py             # Option C：Haiku zero-shot JSON output
│   └── base.py                # interface
├── agent_with_decomposer.py   # subclass ToolCallingAgent
├── run_baseline.py            # wrap run.py for 3-seed + 我們的 log 格式
├── annotate_failures.py       # LLM-as-judge → failure category
└── merge_seeds.py             # 跟 CLINC150 實驗一致的 aggregator
```

### `agent_with_decomposer.py` 簡圖

```python
class DecomposerAgent(ToolCallingAgent):
    def __init__(self, *args, decomposer, **kwargs):
        super().__init__(*args, **kwargs)
        self.decomposer = decomposer
        self.sub_goals = []

    def solve(self, env, task_index=None, max_num_steps=30):
        # same loop as parent, but:
        # - after env.reset(), run decomposer on first obs
        # - prepend decomposer output to system prompt as <sub_goals>...
        # - after each user reply, optionally refresh sub_goals
```
